from __future__ import annotations

from .lifecycle import validate_catalog
from .models import Subscriber, SubscriberStatus


def build_seven_subscriber_catalog() -> tuple[Subscriber, ...]:
    """Build the deterministic 7001-7007 canonical lab catalog.

    Authentication material is intentionally represented only by external secret_ref values.
    """
    subscribers = tuple(
        Subscriber(
            subscriber_id=f"700{i}",
            imsi=f"00101000000000{i}",
            ue_ip=f"10.20.0.{10 + i}",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": f"secret://mini-mobile-7/{7000 + i}"},
            services={"ims": True, "data": True, "pstn_outbound": False, "pstn_inbound": False},
        )
        for i in range(1, 8)
    )
    return validate_catalog(subscribers)
