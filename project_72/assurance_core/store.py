from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Lock
from typing import Any, Mapping

from .models import Subscriber, SubscriberStatus


class StoreConflictError(RuntimeError):
    """Raised when expected_version does not match canonical state."""


class SubscriberNotFoundError(KeyError):
    """Raised when a canonical subscriber does not exist."""


class SubscriberRepository(ABC):
    @abstractmethod
    def get(self, subscriber_id: str) -> Subscriber:
        raise NotImplementedError

    @abstractmethod
    def put(self, subscriber: Subscriber, *, expected_version: int) -> Subscriber:
        raise NotImplementedError


class InMemorySubscriberRepository(SubscriberRepository):
    def __init__(self, initial: Mapping[str, Subscriber] | None = None) -> None:
        self._items: dict[str, Subscriber] = dict(initial or {})
        self._lock = Lock()

    def get(self, subscriber_id: str) -> Subscriber:
        with self._lock:
            try:
                return self._items[subscriber_id]
            except KeyError as exc:
                raise SubscriberNotFoundError(subscriber_id) from exc

    def put(self, subscriber: Subscriber, *, expected_version: int) -> Subscriber:
        with self._lock:
            current = self._items.get(subscriber.subscriber_id)
            if current is None:
                if expected_version != 0:
                    raise StoreConflictError("subscriber does not exist; expected_version must be 0")
            elif current.version != expected_version:
                raise StoreConflictError(
                    f"version conflict for {subscriber.subscriber_id}: "
                    f"expected {expected_version}, current {current.version}"
                )
            self._items[subscriber.subscriber_id] = subscriber
            return subscriber


class MongoSubscriberRepository(SubscriberRepository):
    """Canonical store adapter; deliberately separate from Open5GS collections."""

    def __init__(self, mongodb_uri: str, *, database: str = "mini_mobile_7") -> None:
        from pymongo import MongoClient

        self._client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        self._collection = self._client[database]["canonical_subscribers"]
        self._collection.create_index("subscriber_id", unique=True)
        self._collection.create_index("imsi", unique=True)

    @classmethod
    def from_uri(cls, mongodb_uri: str, *, database_name: str = "mini_mobile_7") -> "MongoSubscriberRepository":
        return cls(mongodb_uri, database=database_name)

    def get(self, subscriber_id: str) -> Subscriber:
        document = self._collection.find_one({"subscriber_id": subscriber_id})
        if document is None:
            raise SubscriberNotFoundError(subscriber_id)
        return _from_document(document)

    def insert(self, subscriber: Subscriber) -> Subscriber:
        """Insert an initial canonical record; refuse duplicate subscriber or IMSI."""
        from pymongo.errors import DuplicateKeyError

        try:
            self._collection.insert_one(subscriber.to_document())
        except DuplicateKeyError as exc:
            raise StoreConflictError(
                f"canonical subscriber already exists: {subscriber.subscriber_id}"
            ) from exc
        return subscriber

    def put(self, subscriber: Subscriber, *, expected_version: int) -> Subscriber:
        from pymongo import ReturnDocument

        replacement = subscriber.to_document()
        result = self._collection.find_one_and_update(
            {
                "subscriber_id": subscriber.subscriber_id,
                "version": expected_version,
            },
            {"$set": replacement},
            upsert=expected_version == 0,
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            raise StoreConflictError(
                f"version conflict for {subscriber.subscriber_id}; expected {expected_version}"
            )
        return _from_document(result)


def _from_document(document: Mapping[str, Any]) -> Subscriber:
    try:
        status = SubscriberStatus(str(document["status"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("canonical subscriber contains an invalid status") from exc
    return Subscriber(
        subscriber_id=str(document["subscriber_id"]),
        imsi=str(document["imsi"]),
        ue_ip=str(document["ue_ip"]),
        version=int(document["version"]),
        status=status,
        secret_refs=dict(document["secret_refs"]),
        services=dict(document["services"]),
        msisdn=document.get("msisdn"),
    )
