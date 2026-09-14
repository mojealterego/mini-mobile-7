# Project-72 Contracts

This directory defines the machine-readable assurance boundary for MINI-MOBILE-7.

## Non-negotiable semantics

- The Canonical Subscriber Store is the source of truth for subscriber intent and version.
- A capability is granted only by the Capability Broker after identity, scope, policy and risk checks.
- Every mutating execution carries an `idempotency_key` and `expected_version`.
- `EXECUTED` means an adapter accepted or completed an operation; it never means `VERIFIED`.
- `VERIFIED` requires authorization, policy approval, successful execution, authoritative readback and successful postcondition assertions.
- `STALE` means the authoritative projection/readback does not represent the expected version.
- `CONFLICT` means optimistic concurrency rejected the requested mutation because the expected version is no longer current.
- `DRIFT` means an authoritative projection differs from the canonical desired state.

## Security

Subscriber authentication material is represented only by `secret_refs`. Ki, OP/OPc, SQN, SIP credentials and database passwords must not be stored in these contracts, examples or generated repository configuration.

## Scope

The first Golden Path is `ACTIVATE 7001`. The same contracts apply to 7002–7007 and to later IMS/SIP/eSIM operations.
