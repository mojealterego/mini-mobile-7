from __future__ import annotations

import unittest

from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.catalog import build_seven_subscriber_catalog
from project_72.assurance_core.esim import EsimStatus
from project_72.assurance_core.esim_adapter import EsimProvisioningAdapter
from project_72.assurance_core.esim_repository import InMemoryEsimArtifactRepository, StoredEsimArtifact
from project_72.assurance_core.idempotency import InMemoryIdempotencyStore
from project_72.assurance_core.models import AssuranceStatus, ExecutionRequest
from project_72.assurance_core.store import InMemorySubscriberRepository


class Resolver:
    def __init__(self) -> None:
        self.calls = 0
        self.last_ref = ""

    def resolve(self, secret_ref: str) -> dict[str, str]:
        self.calls += 1
        self.last_ref = secret_ref
        return {"matching_id": "opaque-test-matching-id"}


class EsimAssuranceTests(unittest.TestCase):
    def setUp(self) -> None:
        subscribers = build_seven_subscriber_catalog()
        self.repository = InMemorySubscriberRepository({s.subscriber_id: s for s in subscribers})
        self.artifacts = InMemoryEsimArtifactRepository()
        self.resolver = Resolver()
        self.adapter = EsimProvisioningAdapter(
            self.repository,
            self.artifacts,
            self.resolver,
            smdp_address="smdp.example.invalid",
        )
        self.broker = CapabilityBroker(
            {
                "ESIM_GENERATE": Policy(
                    version="p72-esim-1",
                    allowed_operations=frozenset({"ESIM_GENERATE"}),
                    allowed_principals=frozenset({"project-72-operator"}),
                    max_risk="LOW",
                )
            }
        )

    def _request(self, *, key: str = "idem-esim-7001", expected_version: int = 1) -> ExecutionRequest:
        return ExecutionRequest(
            request_id="req-esim-7001",
            idempotency_key=key,
            capability_id="cap-req-esim-7001",
            operation="ESIM_GENERATE",
            target="7001",
            expected_version=expected_version,
        )

    def _core(self) -> AssuranceCore:
        return AssuranceCore(
            repository=self.repository,
            broker=self.broker,
            executor=self.adapter.execute,
            readback_provider=self.adapter.readback,
            postcondition=self.adapter.postcondition,
            idempotency_store=InMemoryIdempotencyStore(),
        )

    def test_generate_runs_authorized_executed_readback_postcondition(self) -> None:
        result = self._core().execute(principal="project-72-operator", request=self._request())
        self.assertEqual(result.status, AssuranceStatus.VERIFIED)
        subscriber = self.repository.get("7001")
        self.assertEqual(subscriber.version, 2)
        self.assertEqual(subscriber.esim_status, EsimStatus.GENERATED)
        stored = self.artifacts.get("7001")
        self.assertEqual(stored.version, 2)
        self.assertEqual(stored.status, "GENERATED")
        self.assertNotIn("opaque-test-matching-id", stored.__repr__())
        self.assertNotIn("LPA:1$", stored.__repr__())

    def test_same_idempotency_key_replays_without_second_side_effect(self) -> None:
        core = self._core()
        first = core.execute(principal="project-72-operator", request=self._request())
        second = core.execute(principal="project-72-operator", request=self._request())
        self.assertEqual(first.status, AssuranceStatus.VERIFIED)
        self.assertEqual(second, first)
        self.assertEqual(self.resolver.calls, 1)
        self.assertEqual(self.repository.get("7001").version, 2)

    def test_rejects_stale_expected_version_before_execution(self) -> None:
        result = self._core().execute(
            principal="project-72-operator",
            request=self._request(expected_version=99),
        )
        self.assertEqual(result.status, AssuranceStatus.DENIED)
        with self.assertRaises(KeyError):
            self.artifacts.get("7001")

    def test_reconciles_artifact_left_by_interrupted_canonical_commit(self) -> None:
        subscriber = self.repository.get("7001")
        self.artifacts.put(
            StoredEsimArtifact(
                subscriber_id="7001",
                profile_id=subscriber.profile_id or "",
                smdp_address="smdp.example.invalid",
                activation_code_ref=subscriber.secret_refs["esim_activation"],
                activation_uri_sha256="a" * 64,
                status="GENERATED",
                version=2,
            ),
            expected_version=0,
        )

        self.assertTrue(self.adapter.execute(self._request()))
        reconciled = self.repository.get("7001")
        self.assertEqual(reconciled.version, 2)
        self.assertEqual(reconciled.esim_status, EsimStatus.GENERATED)
        self.assertEqual(self.resolver.calls, 0)

    def test_reconciliation_rejects_mismatched_profile(self) -> None:
        self.artifacts.put(
            StoredEsimArtifact(
                subscriber_id="7001",
                profile_id="wrong-profile",
                smdp_address="smdp.example.invalid",
                activation_code_ref="env://MINI_MOBILE_7_ESIM/7001",
                activation_uri_sha256="a" * 64,
                status="GENERATED",
                version=2,
            ),
            expected_version=0,
        )
        with self.assertRaises(ValueError):
            self.adapter.execute(self._request())
        self.assertEqual(self.repository.get("7001").version, 1)

    def test_readback_detects_canonical_artifact_drift(self) -> None:
        self._core().execute(principal="project-72-operator", request=self._request())
        subscriber = self.repository.get("7001")
        self.repository.put(subscriber.__class__(
            subscriber_id=subscriber.subscriber_id,
            imsi=subscriber.imsi,
            ue_ip=subscriber.ue_ip,
            version=3,
            status=subscriber.status,
            secret_refs=subscriber.secret_refs,
            services=subscriber.services,
            msisdn=subscriber.msisdn,
            profile_id=subscriber.profile_id,
            esim_status=subscriber.esim_status,
        ), expected_version=2)
        readback = self.adapter.readback("7001")
        self.assertEqual(readback.state, "MISMATCH")

    def test_different_principal_is_denied(self) -> None:
        result = self._core().execute(principal="unauthorized", request=self._request())
        self.assertEqual(result.status, AssuranceStatus.DENIED)
        self.assertEqual(self.repository.get("7001").version, 1)


if __name__ == "__main__":
    unittest.main()
