#!/usr/bin/env python3
"""Provision the seven canonical subscribers into Open5GS through Project-72 assurance.

Default mode is dry-run. Use --execute only on the controlled Ubuntu/Open5GS host.
Authentication material is resolved externally from env:// secret references.
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
from project_72.assurance_core.lifecycle_postconditions import lifecycle_postcondition
from project_72.assurance_core.models import AssuranceStatus, ExecutionRequest
from project_72.assurance_core.store import MongoSubscriberRepository


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
    policies = {
        operation: Policy(
            version="runtime-policy-1",
            allowed_operations=frozenset({operation}),
            allowed_principals=frozenset({"project-72-runtime"}),
            max_risk="MEDIUM",
        )
        for operation in ("ACTIVATE", "SUSPEND", "DEACTIVATE")
    }
    broker = CapabilityBroker(policies)
    core = AssuranceCore(
        canonical,
        broker,
        adapter.execute,
        adapter.readback,
        lambda readback: lifecycle_postcondition("ACTIVE")(readback),
    )
    return canonical, adapter, core


def provision_execute(mongodb_uri: str) -> int:
    canonical, _adapter, core = make_core(mongodb_uri)
    catalog = build_seven_subscriber_catalog()
    failures = 0

    for subscriber in catalog:
        current = canonical.get(subscriber.subscriber_id)
        if current.version != subscriber.version or current.status is not subscriber.status:
            print(
                f"BLOCK {subscriber.subscriber_id}: canonical state is "
                f"{current.status.value}/v{current.version}; expected "
                f"{subscriber.status.value}/v{subscriber.version}",
                file=sys.stderr,
            )
            failures += 1
            continue

        request = build_request(subscriber.subscriber_id, current.version, "ACTIVATE")
        result = core.execute(principal="project-72-runtime", request=request)
        print(
            f"{subscriber.subscriber_id} {result.status.value} "
            f"observed_version={result.observed_version} reason={result.reason}"
        )
        if result.status is not AssuranceStatus.VERIFIED:
            failures += 1

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="perform runtime activation")
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

    return provision_execute(args.mongodb_uri)


if __name__ == "__main__":
    raise SystemExit(main())
