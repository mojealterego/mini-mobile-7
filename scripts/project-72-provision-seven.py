#!/usr/bin/env python3
"""Provision the seven canonical subscribers into Open5GS through Project-72 assurance.

Default mode is dry-run. Use --execute only on the controlled Ubuntu/Open5GS host.
Use --bootstrap-canonical together with --execute to create missing initial
PROVISIONED records. Authentication material is resolved externally.
"""
from __future__ import annotations

import argparse
import os
import sys

from adapters.open5gs.adapter import Open5GSAdapter
from adapters.open5gs.secrets import EnvironmentSecretResolver
from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.catalog import build_seven_subscriber_catalog
from project_72.assurance_core.idempotency import MongoIdempotencyStore
from project_72.assurance_core.lifecycle_postconditions import lifecycle_postcondition
from project_72.assurance_core.models import AssuranceStatus, ExecutionRequest, SubscriberStatus
from project_72.assurance_core.store import MongoSubscriberRepository, SubscriberNotFoundError


def build_request(subscriber_id: str, version: int, operation: str) -> ExecutionRequest:
    request_id = f"req-{operation.lower()}-{subscriber_id}-runtime-v{version}"
    return ExecutionRequest(
        request_id=request_id,
        idempotency_key=f"{operation.lower()}-{subscriber_id}-runtime-v{version}",
        capability_id=f"cap-{request_id}",
        operation=operation,
        target=subscriber_id,
        expected_version=version,
    )


def make_core(mongodb_uri: str) -> tuple[MongoSubscriberRepository, Open5GSAdapter, AssuranceCore]:
    canonical = MongoSubscriberRepository.from_uri(mongodb_uri)
    adapter = Open5GSAdapter.from_mongodb(canonical, mongodb_uri, EnvironmentSecretResolver())
    broker = CapabilityBroker({
        "ACTIVATE": Policy(
            version="runtime-policy-1",
            allowed_operations=frozenset({"ACTIVATE"}),
            allowed_principals=frozenset({"project-72-runtime"}),
            max_risk="MEDIUM",
        )
    })
    idempotency = MongoIdempotencyStore(mongodb_uri)
    core = AssuranceCore(
        canonical,
        broker,
        adapter.execute,
        adapter.readback,
        lambda readback: lifecycle_postcondition("ACTIVE")(readback),
        idempotency_store=idempotency,
    )
    return canonical, adapter, core


def _catalog_match(current, expected) -> bool:
    return (
        current.imsi == expected.imsi
        and current.ue_ip == expected.ue_ip
        and current.secret_refs == expected.secret_refs
        and current.services == expected.services
    )


def provision_execute(mongodb_uri: str, bootstrap_canonical: bool) -> int:
    canonical, adapter, core = make_core(mongodb_uri)
    catalog = build_seven_subscriber_catalog()
    failures = 0

    for expected in catalog:
        try:
            current = canonical.get(expected.subscriber_id)
        except SubscriberNotFoundError:
            if not bootstrap_canonical:
                print(
                    f"BLOCK {expected.subscriber_id}: canonical record is absent; "
                    "rerun with --bootstrap-canonical --execute to create it",
                    file=sys.stderr,
                )
                failures += 1
                continue
            current = canonical.insert(expected)
            print(f"BOOTSTRAP {current.subscriber_id} PROVISIONED v{current.version}")

        if not _catalog_match(current, expected):
            print(
                f"BLOCK {expected.subscriber_id}: immutable canonical fields do not match "
                "the deterministic seven-subscriber catalog",
                file=sys.stderr,
            )
            failures += 1
            continue

        if current.status is SubscriberStatus.ACTIVE:
            readback = adapter.readback(current)
            postcondition_ok, postcondition_reason = lifecycle_postcondition("ACTIVE")(readback)
            if readback.observed_version == current.version and postcondition_ok:
                print(
                    f"{current.subscriber_id} VERIFIED "
                    f"observed_version={readback.observed_version} "
                    "reason=already-active-authoritative-readback"
                )
            else:
                print(
                    f"BLOCK {current.subscriber_id}: active canonical state failed "
                    f"authoritative readback/postcondition: {postcondition_reason}",
                    file=sys.stderr,
                )
                failures += 1
            continue

        if current.status is not SubscriberStatus.PROVISIONED or current.version != expected.version:
            print(
                f"BLOCK {expected.subscriber_id}: lifecycle state is "
                f"{current.status.value} v{current.version}; expected PROVISIONED v{expected.version}",
                file=sys.stderr,
            )
            failures += 1
            continue

        request = build_request(expected.subscriber_id, current.version, "ACTIVATE")
        result = core.execute(principal="project-72-runtime", request=request)
        print(
            f"{expected.subscriber_id} {result.status.value} "
            f"observed_version={result.observed_version} reason={result.reason}"
        )
        if result.status is not AssuranceStatus.VERIFIED:
            failures += 1

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="perform runtime mutation")
    parser.add_argument(
        "--bootstrap-canonical",
        action="store_true",
        help="insert missing canonical PROVISIONED records before activation",
    )
    parser.add_argument(
        "--mongodb-uri",
        default=os.environ.get("MM7_MONGODB_URI", "mongodb://localhost/open5gs"),
    )
    args = parser.parse_args()

    catalog = build_seven_subscriber_catalog()
    print("Project-72 seven-subscriber catalog:")
    for subscriber in catalog:
        print(
            f"  {subscriber.subscriber_id}: IMSI={subscriber.imsi} "
            f"UE={subscriber.ue_ip} version={subscriber.version} "
            f"status={subscriber.status.value}"
        )

    if not args.execute:
        print("DRY-RUN: no MongoDB/Open5GS mutation performed")
        return 0

    return provision_execute(args.mongodb_uri, args.bootstrap_canonical)


if __name__ == "__main__":
    raise SystemExit(main())
