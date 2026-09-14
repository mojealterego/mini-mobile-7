# Open5GS adapter

This package is the Project-72 boundary between the canonical subscriber store and the Open5GS MongoDB projection.

## Open5GS v2.8.0 compatibility

The adapter targets the `open5gs.subscribers` document structure used by the pinned Open5GS v2.8.0 database tooling:

- subscriber documents contain `schema_version`, `imsi`, `security`, `ambr`, `subscriber_status` and `slice`;
- the static UE IPv4 address is stored at `slice[0].session[0].ue.ipv4`;
- subscriber security uses `k`, `opc` and `amf`;
- APN/session data is represented inside `slice[].session[]`.

The adapter does not copy authentication material into source control. It resolves it from `secret_ref` only during execution.

## Invariants

1. The canonical subscriber store is the source of desired state.
2. Open5GS is a runtime projection and an authoritative readback source.
3. `ACTIVATE` advances the canonical subscriber from `PROVISIONED` version `N` to `ACTIVE` version `N+1` using optimistic concurrency.
4. Authentication material is resolved at execution time from an external `secret_ref`.
5. No Ki/OPc/SQN or other authentication material is stored in Git.
6. A projection replay is idempotent when its assurance marker already matches the canonical version and subscriber identity.
7. A projection newer than canonical state is rejected as a conflict/drift condition.
8. Drift detection has no repair side effect. Repair requires a separate authorized capability and assurance cycle.

## Runtime wiring

For a real Open5GS/MongoDB deployment, construct the adapter with:

```python
adapter = Open5GSAdapter.from_mongodb(
    canonical=canonical_repository,
    mongodb_uri=os.environ["OPEN5GS_DB_URI"],
    secret_resolver=secret_resolver,
)
```

The URI must be supplied by the deployment environment; credentials are not stored in this repository.

The adapter intentionally does not expose a public HTTP endpoint and does not provide public-network routing capabilities.

## Readback

`readback()` reads the Open5GS subscriber document and returns:

- observed canonical version marker,
- `ACTIVE` / `ABSENT` / `MISMATCH` state,
- deterministic SHA-256 fingerprint,
- target IMSI,
- projected `data` and `ims` service state,
- assurance metadata.

`MISMATCH` is classified by Assurance Core as `DRIFT`; it cannot become `VERIFIED` through a postcondition alone.
