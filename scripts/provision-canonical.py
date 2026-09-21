#!/usr/bin/env python3
"""Provision the canonical seven-subscriber catalog into MongoDB.

This command writes only canonical metadata and secret_ref values. Authentication
material is never read or copied by this process.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from project_72.assurance_core.models import Subscriber, SubscriberStatus
from project_72.assurance_core.store import MongoSubscriberRepository
from project_72.assurance_core.lifecycle import validate_catalog

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "subscribers/templates/canonical-7001-7007.json"


def load_manifest(path: Path) -> tuple[Subscriber, ...]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported manifest schema_version")
    raw_subscribers = payload.get("subscribers")
    if not isinstance(raw_subscribers, list):
        raise ValueError("manifest subscribers must be a list")

    subscribers = tuple(
        Subscriber(
            subscriber_id=item["subscriber_id"],
            imsi=item["imsi"],
            ue_ip=item["ue_ip"],
            version=int(item["version"]),
            status=SubscriberStatus(item["status"]),
            secret_refs=item["secret_refs"],
            services=item["services"],
            msisdn=item.get("msisdn"),
        )
        for item in raw_subscribers
    )
    return validate_catalog(subscribers)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--mongo-uri",
        default=os.environ.get("MM7_CANONICAL_MONGO_URI"),
        help="Canonical MongoDB URI; defaults to MM7_CANONICAL_MONGO_URI",
    )
    parser.add_argument("--database", default="mini_mobile_7")
    parser.add_argument("--apply", action="store_true", help="Write the validated catalog")
    args = parser.parse_args()

    subscribers = load_manifest(args.manifest)
    print(f"validated {len(subscribers)} canonical subscribers")
    for subscriber in subscribers:
        print(
            f"{subscriber.subscriber_id} imsi={subscriber.imsi} "
            f"ue_ip={subscriber.ue_ip} version={subscriber.version} "
            f"status={subscriber.status.value}"
        )

    if not args.apply:
        print("dry-run: no database changes made")
        return 0
    if not args.mongo_uri:
        print("error: --mongo-uri or MM7_CANONICAL_MONGO_URI is required with --apply", file=sys.stderr)
        return 2

    repository = MongoSubscriberRepository.from_uri(args.mongo_uri, database_name=args.database)
    for subscriber in subscribers:
        try:
            existing = repository.get(subscriber.subscriber_id)
        except KeyError:
            repository.insert(subscriber)
            continue
        if existing.to_document() != subscriber.to_document():
            raise RuntimeError(
                f"refusing to overwrite existing subscriber {subscriber.subscriber_id}; "
                "canonical state differs"
            )
    print("canonical catalog provisioned without changing existing divergent records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
