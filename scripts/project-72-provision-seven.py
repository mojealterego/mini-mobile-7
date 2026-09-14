#!/usr/bin/env python3
"""Provision the seven canonical subscribers into Open5GS through Project-72 assurance."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from adapters.open5gs.adapter import Open5GSAdapter
from adapters.open5gs.secrets import EnvironmentSecretResolver
from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.catalog import build_seven_subscriber_catalog
from project_72.assurance_core.idempotency import MongoIdempotencyStore
from project_72.assurance_core.lifecycle_postconditions import lifecycle_postcondition
from project_72.assurance_core.models import AssuranceStatus, ExecutionRequest, SubscriberStatus
from project_72.assurance_core.store import MongoSubscriberRepository, SubscriberNotFoundError, StoreConflictError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SCRIPT = PROJECT_ROOT / "scripts" / "project-72-preflight.sh"


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


def run_preflight() -> bool:
    if not PREFLIGHT_SCRIPT.is_file():
        print(f"BLOCK: runtime preflight script missing: {PREFLIGHT_SCRIPT}", file=sys.stderr)
        return False
    env = os.environ.copy()
    env["MM7_SKIP_SECRET_PREFLIGHT"] = "0"
    result = subprocess.run(
        ["bash", str(PREFLIGHT_SCRIPT)],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        print("BLOCK: runtime preflight failed; no provisioning mutation permitted", file=sys.stderr)
        return False
    return True


def make_core(mongodb_uri: str, idempotency_uri: str) -> tuple[MongoSubscriberRepository, Open5GSAdapter, AssuranceCore]:
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
    durable_idempotency = MongoIdempotencyStore(idempotency_uri)
    core = AssuranceCore(
        canonical,
        broker,
        adapter.execute,
        adapter.readback,
        lambda readback: lifecycle_postcondition("ACTIVE")(readback),
        idempotency_store=durable_idempotency,
    )
    return canonical, adapter, core


def _catalog_match(current, expected) -> bool:
    return (
        current.imsi == expected.imsi
        and current.ue_ip == expected.ue_ip
        and current.secret_refs == expected.secret_refs
        and current.services == expected.services
    )


def provision_execute(mongodb_uri: str, idempotency_uri: str, bootstrap_canonical: bool) -> int:
    if not run_preflight():
        return 2

    canonical, adapter, core = make_core(mongodb_uri, idempotency_uri)
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
            try:
                current = canonical.ensure_initial(expected)
            except StoreConflictError as exc:
                print(f"BLOCK {expected.subscriber_id}: canonical bootstrap conflict: {exc}", file=sys.stderr)
                failures += 1
                continue
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
                print(f"{current.subscriber_id} VERIFIED observed_version={readback.observed_version} reason=already-active-authoritative-readback")
            else:
                print(f"BLOCK {current.subscriber_id}: active canonical state failed authoritative readback/postcondition: {postcondition_reason}", file=sys.stderr)
                failures += 1
            continue

        if current.status is not SubscriberStatus.PROVISIONED or current.version != expected.version:
            print(f"BLOCK {expected.subscriber_id}: lifecycle state is {current.status.value} v{current.version}; expected PROVISIONED v{expected.version}", file=sys.stderr)
            failures += 1
            continue

        request = build_request(expected.subscriber_id, current.version, "ACTIVATE")
        result = core.execute(principal="project-72-runtime", request=request)
        print(f"{expected.subscriber_id} {result.status.value} observed_version={result.observed_version} reason={result.reason}")
        if result.status is not AssuranceStatus.VERIFIED:
            failures += 1

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="perform runtime mutation")
    parser.add_argument("--bootstrap-canonical", action="store_true", help="insert missing canonical PROVISIONED records")
    parser.add_argument("--mongodb-uri", default=os.environ.get("MM7_MONGODB_URI", "mongodb://localhost/open5gs"))
    parser.add_argument("--idempotency-mongodb-uri", default=os.environ.get("MM7_IDEMPOTENCY_DB_URI"))
    args = parser.parse_args()

    catalog = build_seven_subscriber_catalog()
    print("Project-72 seven-subscriber catalog:")
    for subscriber in catalog:
        print(f"  {subscriber.subscriber_id}: IMSI={subscriber.imsi} UE={subscriber.ue_ip} version={subscriber.version} status={subscriber.status.value}")

    if not args.execute:
        print("DRY-RUN: no MongoDB/Open5GS mutation performed")
        return 0

    if not args.idempotency_mongodb_uri:
        print("BLOCK: --execute requires MM7_IDEMPOTENCY_DB_URI or --idempotency-mongodb-uri", file=sys.stderr)
        return 2

    return provision_execute(args.mongodb_uri, args.idempotency_mongodb_uri, args.bootstrap_canonical)


if __name__ == "__main__":
    raise SystemExit(main())
