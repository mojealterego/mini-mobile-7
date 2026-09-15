from __future__ import annotations

from .identity import IdentityGenerator
from .lifecycle import validate_catalog
from .models import EsimStatus, Subscriber, SubscriberStatus


def build_seven_subscriber_catalog() -> tuple[Subscriber, ...]:
    """Build the deterministic 7001-7007 canonical lab catalog.

    Authentication and eSIM provisioning material remain external secret refs.
    """
    subscribers = tuple(
        Subscriber(
            subscriber_id=f"700{i}",
            imsi=f"00101000000000{i}",
            ue_ip=f"10.20.0.{10 + i}",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={
                "authentication": f"env://MINI_MOBILE_7/{7000 + i}",
                "esim_activation": f"env://MINI_MOBILE_7_ESIM/{7000 + i}",
            },
            services={"ims": True, "data": True, "pstn_outbound": False, "pstn_inbound": False},
            profile_id=f"mm7-{7000 + i}",
            esim_status=EsimStatus.PLANNED,
        )
        for i in range(1, 8)
    )
    identities = IdentityGenerator().generate_all()
    if tuple(identity.subscriber_id for identity in identities) != tuple(s.subscriber_id for s in subscribers):
        raise ValueError("identity catalog does not match subscriber catalog")
    return validate_catalog(subscribers)
