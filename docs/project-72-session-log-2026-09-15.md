# Project-72 engineering session log — 2026-09-15

## Changes implemented

### 1. Concurrent idempotency reservation coverage

Added `project_72/assurance_core/test_idempotency_concurrency.py`.

The test runs two independent `AssuranceCore` instances concurrently against the same thread-safe idempotency store and the same `ACTIVATE 7001` request. The race is deliberately controlled so one caller owns the reservation while its side-effect executor is in progress. The second caller must fail closed as `CONFLICT`.

The test verifies:

- exactly one caller reaches terminal `VERIFIED`;
- the competing caller receives `CONFLICT` while the reservation is in progress;
- no thread raises an unexpected exception;
- the telecom side-effect executor is entered exactly once;
- idempotency reservation is therefore the serialization boundary for duplicate concurrent requests.

The test was hardened after review because the first version could permit either caller to finish before the other observed the reservation, making the expected result scheduler-dependent. The current version is deterministic and explicitly tests the fail-closed concurrent path.

### 2. Assurance test target expanded

Updated `Makefile` so `make assurance-test` explicitly executes the concurrency test together with the existing assurance, lifecycle, drift, idempotency, runtime-wiring and Open5GS integration suites.

### 3. CI verification

GitHub Actions run #147 for commit `1133433154f633e392948bee1ec85b986202c223` completed with `success` before this deterministic-race correction.

The race correction is now committed as `3ee146ff65d37c9232b25384bd557adc2995f1b9` and has triggered a new CI run. That run must finish before the corrected revision is marked CI-green.

### 4. Gate 4E preparation review

Reviewed the current UERANSIM renderer and runtime acceptance boundary. The renderer already produces seven deployment-local UE configurations from external authentication references and validates the deterministic seven-UE IMSI mapping. Gate 4E remains a host-runtime task: start the pinned Open5GS/AMF path, start the UERANSIM gNB, attach one UE at a time, validate PDU session establishment and compare authoritative runtime state with canonical state.

No host execution was claimed because no live Open5GS/UERANSIM target is available through this repository session.

## Current engineering boundary

The following remain code-complete but require host acceptance:

- MongoDB canonical store against the deployment database;
- durable MongoDB idempotency store against the deployment database;
- Open5GS v2.8.0 live projection/readback;
- UERANSIM attach/session validation;
- IMS registration/call validation;
- physical RAN and handset validation.

No live telecom state is claimed from CI-only validation.

## Safety boundary

No production authentication secrets are stored in this log or in the repository. The renderer CI uses synthetic non-production authentication values only. Physical RF operation remains gated on appropriate hardware and lawful Polish radio authorization.
