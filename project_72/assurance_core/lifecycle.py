from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .models import Subscriber, SubscriberStatus
from .store import StoreConflictError, SubscriberRepository


class LifecycleError(ValueError):
    """Raised when a subscriber lifecycle transition is invalid."""


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    operation: str
    source: SubscriberStatus
    target: SubscriberStatus


_ALLOWED: Mapping[str, LifecycleTransition] = {
    "ACTIVATE": LifecycleTransition("ACTIVATE", SubscriberStatus.PROVISIONED, SubscriberStatus.ACTIVE),
    "SUSPEND": LifecycleTransition("SUSPEND", SubscriberStatus.ACTIVE, SubscriberStatus.SUSPENDED),
    "DEACTIVATE": LifecycleTransition("DEACTIVATE", SubscriberStatus.SUSPENDED, SubscriberStatus.RETIRED),
}


def transition(subscriber: Subscriber, operation: str) -> Subscriber:
    """Return the next immutable canonical state without performing I/O."""
    try:
        rule = _ALLOWED[operation]
    except KeyError as exc:
        raise LifecycleError(f"unsupported lifecycle operation: {operation}") from exc
    if subscriber.status is not rule.source:
        raise LifecycleError(
            f"{operation} requires {rule.source.value}; "
            f"subscriber {subscriber.subscriber_id} is {subscriber.status.value}"
        )
    return Subscriber(
        subscriber_id=subscriber.subscriber_id,
        imsi=subscriber.imsi,
        ue_ip=subscriber.ue_ip,
        version=subscriber.version + 1,
        status=rule.target,
        secret_refs=subscriber.secret_refs,
        services=subscriber.services,
        msisdn=subscriber.msisdn,
    )


def apply(repository: SubscriberRepository, subscriber_id: str, operation: str, *, expected_version: int) -> Subscriber:
    """Apply one lifecycle transition with optimistic concurrency."""
    current = repository.get(subscriber_id)
    if current.version != expected_version:
        raise StoreConflictError(
            f"version conflict for {subscriber_id}: expected {expected_version}, current {current.version}"
        )
    target = transition(current, operation)
    return repository.put(target, expected_version=expected_version)


def validate_catalog(subscribers: Iterable[Subscriber]) -> tuple[Subscriber, ...]:
    """Validate the complete seven-subscriber addressing/catalog invariant."""
    items = tuple(subscribers)
    if len(items) != 7:
        raise LifecycleError(f"catalog must contain exactly 7 subscribers, got {len(items)}")
    ids = {item.subscriber_id for item in items}
    expected_ids = {f"700{i}" for i in range(1, 8)}
    if ids != expected_ids:
        raise LifecycleError("catalog must contain subscriber IDs 7001-7007 exactly once")
    imsies = {item.imsi for item in items}
    if len(imsies) != 7:
        raise LifecycleError("subscriber IMSIs must be unique")
    ips = {item.ue_ip for item in items}
    if len(ips) != 7:
        raise LifecycleError("subscriber UE IP addresses must be unique")
    expected_ips = {f"10.20.0.{10 + i}" for i in range(1, 8)}
    if ips != expected_ips:
        raise LifecycleError("catalog must map 7001-7007 to 10.20.0.11-10.20.0.17")
    return items
