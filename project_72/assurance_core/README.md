# Project-72 Assurance Core

The Python package in this directory is the first executable assurance boundary. It is intentionally independent from Open5GS and Asterisk adapters.

## Execution gate

`AssuranceCore.execute()` enforces the sequence:

1. Load canonical subscriber state.
2. Ask the Capability Broker for an explicit ALLOW decision.
3. Execute through an adapter callback.
4. Perform authoritative readback.
5. Evaluate postconditions.
6. Emit `VERIFIED` only when every gate succeeds.

`EXECUTED` is never promoted to `VERIFIED` without readback and postcondition success.

## Concurrency and idempotency

Mutations carry `expected_version`. The repository rejects stale versions with `StoreConflictError`. The assurance layer also caches completed results by `idempotency_key` so a retry returns the same result rather than repeating a successful mutation.

The in-memory repository is for deterministic tests. `MongoSubscriberRepository` uses a dedicated `mini_mobile_7.canonical_subscribers` collection and must not be confused with the Open5GS projection database.

## Next adapter boundary

The next implementation stage connects this core to an Open5GS adapter that performs a controlled projection and then reads the resulting subscriber state back from the authoritative Open5GS interface. IMS/PSTN routing will be subject to the same capability and assurance boundary.
