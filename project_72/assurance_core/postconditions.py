from __future__ import annotations

from typing import Mapping

from .models import AuthoritativeReadback


def activate_postcondition(readback: AuthoritativeReadback) -> tuple[bool, str]:
    """Validate the minimum authoritative state required for ACTIVATE."""
    if readback.state != "ACTIVE":
        return False, f"subscriber is not ACTIVE in {readback.source}: {readback.state}"

    services = readback.details.get("services")
    if isinstance(services, Mapping) and services.get("ims") is False:
        return False, "IMS service is disabled"

    marker = readback.details.get("marker")
    if isinstance(marker, Mapping) and marker.get("status") != "ACTIVE":
        return False, "Open5GS assurance marker is not ACTIVE"

    return True, "activation postconditions satisfied"
