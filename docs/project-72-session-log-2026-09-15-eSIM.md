# Project-72 session log — eSIM / external repository integration

## Scope

This session continued the MINI-MOBILE-7 Project-72 implementation after auditing the supplied UERANSIM/Open5GS/MongoDB/Terraform/Kubernetes repositories.

## Source audit

Audited:

- `mojealterego/UERANSIM`
- `mojealterego/open5gs_5gc_ueransim_sample_config`
- `mojealterego/open5gs`
- `mojealterego/terraform-provider-mongodb`
- `mojealterego/terraform-aws-mongodb-ec2`
- `mojealterego/End-to-End-Kubernetes-Three-Tier-DevSecOps-Project`

The UERANSIM fork is v3.3.0 and states that its radio interface is simulated over UDP. Its Open5GS configuration templates were used as reference only. The sample Open5GS/UERANSIM repository documents older Open5GS v2.7.0/UERANSIM v3.2.6 versions and therefore does not override the MINI-MOBILE-7 baseline.

The MongoDB Terraform repositories are infrastructure references. The Kubernetes repository is a CI/CD/GitOps/observability reference. None is allowed to bypass Project-72 assurance controls.

## Implementation

### Private identity generator

Added `project_72/assurance_core/identity.py`.

The generator deterministically maps `7001–7007` to private extensions and generates corresponding SIP/tel URIs. It deliberately does not fabricate public E.164 numbers.

### eSIM activation artifact generator

Added `project_72/assurance_core/esim.py`.

The generator accepts:

- subscriber ID;
- profile ID;
- SM-DP+ address;
- external `env://` activation-code reference;
- matching ID resolved from the external provisioning system.

It produces an LPA activation URI and a SHA-256 digest. The raw matching ID is never persisted by the artifact model.

The generator does not create a GSMA eSIM profile, contact an SM-DP+, install a profile on a device, or claim device-side verification.

### Contracts

Added:

- `project-72/contracts/schemas/private-identity.schema.json`
- `project-72/contracts/schemas/esim-activation-artifact.schema.json`
- schema-index entries for both contracts

### Tests

Added `project_72/assurance_core/test_identity_esim.py` covering:

- all seven deterministic identities;
- invalid subscriber rejection;
- external matching-ID resolution;
- LPA activation artifact construction;
- missing matching-ID failure;
- non-external secret-reference rejection;
- activation-string injection rejection.

### Make targets

Added:

```text
make generate-identities
make generate-esim
```

`make assurance-test` now includes the identity/eSIM suite.

## Security decision

No Ki, OPc, authentication password, SM-DP+ credential, activation token or matching ID was copied from the supplied repositories into MINI-MOBILE-7. Public repository examples containing credential-like material remain source material only.

## Acceptance state

- Identity generation: CODE IMPLEMENTED
- eSIM activation-artifact generation: CODE IMPLEMENTED
- eSIM profile installation: NOT CLAIMED
- eSIM device verification: NOT CLAIMED
- SM-DP+ live integration: PENDING external provisioning service
- UERANSIM live attach: PENDING host
- Open5GS live projection/readback: PENDING host
- physical RAN: BLOCKED by hardware and legal gate

## CI

GitHub Actions run #197 for commit `094aed9d4c2fa108947705cfa5c2172fea5b38be` completed successfully.
