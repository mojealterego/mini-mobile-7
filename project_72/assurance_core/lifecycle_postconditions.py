from __future__ import annotations

from .models import AuthoritativeReadback


def lifecycle_postcondition(expected_state: str):
    """Create a strict postcondition for one canonical lifecycle state."""
    def check(readback: AuthoritativeReadback) -> tuple[bool, str]:
        if readback.state != expected_state:
            return False, f"expected {expected_state}, observed {readback.state}"
        marker = readback.details.get("marker")
        if not isinstance(marker, dict) or marker.get("status") != expected_state:
            return False, "Open5GS assurance marker does not match expected lifecycle state"
        if expected_state == "ACTIVE":
            services = readback.details.get("services")
            if not isinstance(services, dict) or services.get("data") is not True:
                return False, "data service is not projected"
        return True, f"lifecycle postcondition satisfied: {expected_state}"

    return check
