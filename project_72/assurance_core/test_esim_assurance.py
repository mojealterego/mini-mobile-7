from __future__ import annotations

import unittest

from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.catalog import build_seven_subscriber_catalog
from project_72.assurance_core.esim import EsimStatus
from project_72.assurance_core.esim_adapter import EsimProvisioningAdapter
from project_72.assurance_core.esim_repository import InMemoryEsimArtifactRepository
from project_72.assurance_core.idempotency import InMemoryIdempotencyStore
from project_72.assurance_core.models import AssuranceStatus, ExecutionRequest
from project_72.assurance_core.store import InMemorySubscriberRepository


class Resolver:
    def resolve(self, secret_ref: str) -> dict[str, str]:
        self.last_ref = secret_ref
        return {"matching_id": "opaque-test-matching-id"}


class EsimAssuranceTests(unittest.TestCase):
    def setUp(self) -> None:
        subscribers = build_seven_subscriber_catalog()
        self.repository = InMemorySubscriberRepository({s.subscriber_id: s for s in subscribers})
        self.artifacts = InMemoryEsimArtifactRepository()
        self.adapter = EsimProvisioningAdapter(
            self.repository,
            self.artifacts,
            Resolver(),
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

    def test_rejects_stale_expected_version_before_execution(self) -> None:
        result = self._core().execute(
            principal="project-72-operator",
            request=self._request(expected_version=99),
        )
        self.assertEqual(result.status, AssuranceStatus.DENIED)
        with self.assertRaises(KeyError):
            self.artifacts.get("7001")

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
