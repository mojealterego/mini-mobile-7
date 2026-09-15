# Project-72 eSIM assurance boundary

## Scope

Project-72 distinguishes four states:

```text
PLANNED -> GENERATED -> INSTALLED -> VERIFIED
```

The current repository implements only `ESIM_GENERATE` for a provisioning artifact. It does not create a profile at an SM-DP+, install a profile on a handset, or assert device verification.

## Execution chain

`ESIM_GENERATE` uses the normal Project-72 assurance boundary:

```text
Capability authorization
        -> policy/risk
        -> idempotent execution
        -> expected_version check
        -> artifact-store readback
        -> postcondition
        -> VERIFIED
```

Here `VERIFIED` means **verified generation of the eSIM activation artifact**, not an installed or device-verified eSIM.

## Secret boundary

The canonical subscriber record contains an external `esim_activation` secret reference. The provisioning resolver supplies the opaque matching ID at execution time. The generated LPA URI is not persisted by the artifact repository. The repository stores only:

- subscriber ID;
- profile ID;
- SM-DP+ host metadata;
- secret reference;
- SHA-256 fingerprint of the activation URI;
- generated status;
- assurance version.

No Ki, OPc, matching ID, activation URI or other authentication/provisioning secret is committed to Git.

## Failure semantics

The operation fails closed when:

- the canonical `expected_version` is stale;
- the eSIM secret reference is absent;
- the profile ID is absent or invalid;
- the provisioning resolver does not return a matching ID;
- the artifact store reports a version/state conflict;
- canonical and artifact versions diverge during readback;
- the artifact fingerprint or status does not satisfy the postcondition.

The adapter does not automatically contact a real SM-DP+ as a fallback. A real provisioning integration must be explicit and provide authoritative installation/readback semantics before `INSTALLED` or device-level `VERIFIED` can be asserted.

## Current acceptance level

The deterministic assurance path is covered by unit/integration tests with synthetic provisioning material. Live SM-DP+, LPA and handset acceptance remains a deployment gate and is not claimed by repository CI.
