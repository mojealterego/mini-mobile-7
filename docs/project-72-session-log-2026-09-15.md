# Project-72 engineering session log — 2026-09-15

## Changes implemented

### 1. Concurrent idempotency reservation coverage

Added `project_72/assurance_core/test_idempotency_concurrency.py`.

The test runs two independent `AssuranceCore` instances concurrently against the same thread-safe idempotency store and the same `ACTIVATE 7001` request. It verifies that:

- both callers receive the same terminal `VERIFIED` outcome;
- no thread raises an exception;
- the telecom side-effect executor is entered exactly once;
- idempotency reservation is therefore the serialization boundary for duplicate concurrent requests.

This closes the previous test gap where durable reservation behavior was covered only sequentially.

### 2. Assurance test target expanded

Updated `Makefile` so `make assurance-test` explicitly executes the new concurrency test together with the existing assurance, lifecycle, drift, idempotency, runtime-wiring and Open5GS integration suites.

### 3. CI verification

GitHub Actions run #147 for commit `1133433154f633e392948bee1ec85b986202c223` completed with `success`.

This confirms the updated assurance suite, including the new concurrent idempotency test, passed in the Ubuntu 22.04 CI environment. The workflow also completed its seven-subscriber UERANSIM renderer validation.

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

No production authentication secrets are stored in this log or in the repository. The renderer CI uses synthetic test credentials only. Physical RF operation remains gated on appropriate hardware and lawful Polish radio authorization.
