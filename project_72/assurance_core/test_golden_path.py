from __future__ import annotations

import unittest

from project_72.assurance_core.assurance import AssuranceCore
from project_72.assurance_core.broker import CapabilityBroker, Policy
from project_72.assurance_core.models import (
    AssuranceStatus,
    AuthoritativeReadback,
    ExecutionRequest,
    Subscriber,
    SubscriberStatus,
)
from project_72.assurance_core.store import InMemorySubscriberRepository


class Activate7001Test(unittest.TestCase):
    def test_golden_path_verifies_only_after_readback_and_postcondition(self) -> None:
        subscriber = Subscriber(
            subscriber_id="7001",
            imsi="001010000000001",
            ue_ip="10.20.0.11",
            version=1,
            status=SubscriberStatus.PROVISIONED,
            secret_refs={"authentication": "secret://mini-mobile-7/7001/auth"},
            services={"ims": True, "data": True, "pstn_outbound": True},
        )
        repository = InMemorySubscriberRepository({"7001": subscriber})
        broker = CapabilityBroker({
            "ACTIVATE": Policy(
                version="policy-1",
                allowed_operations=frozenset({"ACTIVATE"}),
                allowed_principals=frozenset({"assurance-service"}),
                max_risk="MEDIUM",
            )
        })

        def executor(request: ExecutionRequest) -> bool:
            current = repository.get(request.target)
            repository.put(
                Subscriber(
                    subscriber_id=current.subscriber_id,
                    imsi=current.imsi,
                    ue_ip=current.ue_ip,
                    version=current.version + 1,
                    status=SubscriberStatus.ACTIVE,
                    secret_refs=current.secret_refs,
                    services=current.services,
                    msisdn=current.msisdn,
                ),
                expected_version=request.expected_version,
            )
            return True

        def readback(target: str) -> AuthoritativeReadback:
            current = repository.get(target)
            return AuthoritativeReadback(
                request_id="req-activate-7001-0001",
                source="CANONICAL_STORE",
                target=target,
                observed_version=current.version,
                state=current.status.value,
                fingerprint=f"subscriber:{target}:v{current.version}",
                details={"services": dict(current.services)},
            )

        def postcondition(value: AuthoritativeReadback) -> tuple[bool, str]:
            ok = value.state == "ACTIVE" and value.details["services"]["ims"] is True
            return ok, "activation postconditions satisfied" if ok else "activation postcondition failed"

        core = AssuranceCore(repository, broker, executor, readback, postcondition)
        request = ExecutionRequest(
            request_id="req-activate-7001-0001",
            idempotency_key="activate-7001-v1",
            capability_id="cap-req-activate-7001-0001",
            operation="ACTIVATE",
            target="7001",
            expected_version=1,
            parameters={"service": "IMS"},
        )

        result = core.execute(principal="assurance-service", request=request)
        self.assertEqual(result.status, AssuranceStatus.VERIFIED)
        self.assertTrue(result.authorization)
        self.assertTrue(result.policy)
        self.assertTrue(result.execution)
        self.assertTrue(result.readback)
        self.assertTrue(result.postcondition)
        self.assertEqual(result.observed_version, 2)

        self.assertIs(core.execute(principal="assurance-service", request=request), result)


if __name__ == "__main__":
    unittest.main()
