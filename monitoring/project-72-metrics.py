#!/usr/bin/env python3
"""Render bounded Project-72 metrics from a JSON evidence snapshot.

The exporter is intentionally dependency-free and read-only. It consumes a
snapshot rather than querying telecom systems itself, keeping collection and
authorization boundaries separate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SUBSCRIBERS = tuple(str(7000 + i) for i in range(1, 8))
ASSURANCE_STATUSES = ("AUTHORIZED", "DENIED", "EXECUTED", "VERIFIED", "UNVERIFIED", "STALE", "CONFLICT", "DRIFT", "FAILED")


def _counter(name: str, value: int, labels: dict[str, str] | None = None) -> str:
    label_text = ""
    if labels:
        label_text = "{" + ",".join(f'{k}="{v}"' for k, v in sorted(labels.items())) + "}"
    return f"{name}{label_text} {value}"


def render(snapshot: dict[str, Any]) -> str:
    lines = [
        "# HELP mm7_assurance_operations_total Project-72 assurance operations by terminal status.",
        "# TYPE mm7_assurance_operations_total counter",
    ]
    operations = snapshot.get("assurance_operations", {})
    if not isinstance(operations, dict):
        raise ValueError("assurance_operations must be an object")
    for status in ASSURANCE_STATUSES:
        value = operations.get(status, 0)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid assurance count for {status}")
        lines.append(_counter("mm7_assurance_operations_total", value, {"status": status}))

    lines += [
        "# HELP mm7_drift_events_total Project-72 authoritative drift classifications.",
        "# TYPE mm7_drift_events_total counter",
    ]
    drift = snapshot.get("drift_events", 0)
    if not isinstance(drift, int) or drift < 0:
        raise ValueError("drift_events must be a non-negative integer")
    lines.append(_counter("mm7_drift_events_total", drift))

    lines += [
        "# HELP mm7_subscriber_health Subscriber health state from the latest authoritative evidence snapshot.",
        "# TYPE mm7_subscriber_health gauge",
    ]
    subscribers = snapshot.get("subscribers", {})
    if not isinstance(subscribers, dict):
        raise ValueError("subscribers must be an object")
    for subscriber_id in SUBSCRIBERS:
        item = subscribers.get(subscriber_id, {})
        if not isinstance(item, dict):
            raise ValueError(f"subscriber {subscriber_id} must be an object")
        healthy = item.get("healthy", False)
        if not isinstance(healthy, bool):
            raise ValueError(f"subscriber {subscriber_id}.healthy must be boolean")
        lines.append(_counter("mm7_subscriber_health", int(healthy), {"subscriber_id": subscriber_id}))

    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} SNAPSHOT.json", file=sys.stderr)
        return 2
    try:
        snapshot = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict):
            raise ValueError("snapshot root must be an object")
        sys.stdout.write(render(snapshot))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"metrics export failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
