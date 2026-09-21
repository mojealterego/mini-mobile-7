from __future__ import annotations

import hashlib
import unittest

from project_72.assurance_core.esim import (
    EsimActivationArtifact,
    EsimArtifactGenerator,
    EsimProfileMetadata,
    EsimProvisioningError,
    EsimStatus,
)
from project_72.assurance_core.identity import IdentityGenerator
from project_72.assurance_core.catalog import build_seven_subscriber_catalog


class FakeEsimSecretResolver:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def resolve(self, secret_ref: str) -> dict[str, str]:
        if secret_ref != "env://MM7_ESIM/7001":
            raise AssertionError(f"unexpected secret ref: {secret_ref}")
        return self.values


class IdentityAndEsimTests(unittest.TestCase):
    def test_private_identity_generator_covers_all_seven(self) -> None:
        identities = IdentityGenerator().generate_all()
        self.assertEqual([item.subscriber_id for item in identities], [f"700{i}" for i in range(1, 8)])
        self.assertEqual(identities[0].extension, "7001")
        self.assertEqual(identities[-1].sip_uri, "sip:7007@ims.mm7.local")
        self.assertEqual(identities[3].tel_uri, "tel:7004")

    def test_identity_rejects_unknown_subscriber(self) -> None:
        with self.assertRaises(ValueError):
            IdentityGenerator().generate("7008")

    def test_catalog_has_profile_and_external_esim_ref_for_all_seven(self) -> None:
        subscribers = build_seven_subscriber_catalog()
        self.assertEqual(len(subscribers), 7)
        for subscriber in subscribers:
            self.assertEqual(subscriber.profile_id, f"mm7-{subscriber.subscriber_id}")
            self.assertEqual(
                subscriber.secret_refs["esim_activation"],
                f"env://MINI_MOBILE_7_ESIM/{subscriber.subscriber_id}",
            )
            self.assertEqual(subscriber.esim_status, EsimStatus.PLANNED)

    def test_esim_artifact_uses_external_matching_id(self) -> None:
        metadata = EsimProfileMetadata(
            subscriber_id="7001",
            profile_id="mm7-7001",
            smdp_address="smdp.example.invalid",
            activation_code_ref="env://MM7_ESIM/7001",
        )
        artifact = EsimArtifactGenerator().generate(
            metadata,
            FakeEsimSecretResolver({"matching_id": "opaque-token-from-smdp"}),
        )
        self.assertIsInstance(artifact, EsimActivationArtifact)
        self.assertEqual(artifact.status, EsimStatus.GENERATED)
        self.assertEqual(artifact.activation_uri, "LPA:1$smdp.example.invalid$opaque-token-from-smdp")
        self.assertEqual(
            artifact.activation_uri_sha256,
            hashlib.sha256(artifact.activation_uri.encode("utf-8")).hexdigest(),
        )

    def test_esim_artifact_does_not_generate_missing_matching_id(self) -> None:
        metadata = EsimProfileMetadata("7001", "mm7-7001", "smdp.example.invalid", "env://MM7_ESIM/7001")
        with self.assertRaises(EsimProvisioningError):
            EsimArtifactGenerator().generate(metadata, FakeEsimSecretResolver({}))

    def test_esim_artifact_requires_external_secret_ref(self) -> None:
        metadata = EsimProfileMetadata("7001", "mm7-7001", "smdp.example.invalid", "inline-secret")
        with self.assertRaises(EsimProvisioningError):
            EsimArtifactGenerator().generate(metadata, FakeEsimSecretResolver({"matching_id": "opaque-token"}))

    def test_esim_artifact_rejects_activation_injection_characters(self) -> None:
        metadata = EsimProfileMetadata("7001", "mm7-7001", "smdp.example.invalid", "env://MM7_ESIM/7001")
        for matching_id in ("bad$token", "bad\nTOKEN", "bad\rTOKEN"):
            with self.subTest(matching_id=matching_id):
                with self.assertRaises(EsimProvisioningError):
                    EsimArtifactGenerator().generate(metadata, FakeEsimSecretResolver({"matching_id": matching_id}))


if __name__ == "__main__":
    unittest.main()
