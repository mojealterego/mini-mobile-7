# Open5GS adapter

This package is the Project-72 boundary between the canonical subscriber store and the Open5GS MongoDB projection.

## Invariants

1. The canonical subscriber store is the source of desired state.
2. Open5GS is a runtime projection and an authoritative readback source.
3. `ACTIVATE` advances the canonical subscriber from `PROVISIONED` version `N` to `ACTIVE` version `N+1` using optimistic concurrency.
4. Authentication material is resolved at execution time from an external `secret_ref`.
5. No Ki/OPc/SQN or other authentication material is stored in Git.
6. A projection replay is idempotent when its assurance marker already matches the canonical version and subscriber identity.
7. A projection newer than canonical state is rejected as a conflict/drift condition.

## Runtime wiring

The production constructor should receive the `mini_mobile_7` canonical repository, the Open5GS `open5gs.subscribers` collection, and an external `SecretResolver`.

The adapter intentionally does not expose a public HTTP endpoint and does not provide public-network routing capabilities.

## Readback

`readback()` reads the Open5GS subscriber document and returns:

- observed canonical version marker,
- `ACTIVE` / `ABSENT` / `MISMATCH` state,
- deterministic SHA-256 fingerprint,
- target IMSI and assurance metadata.

`MISMATCH` is classified by Assurance Core as `DRIFT`; it cannot become `VERIFIED` through a postcondition alone.
