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

### 2. UERANSIM renderer hardening

Added `project_72/assurance_core/test_ueransim_renderer.py` and wired it into `make assurance-test` and CI.

The renderer suite now verifies:

- all seven `7001`-`7007` outputs are produced;
- deterministic subscriber/IMSI mapping remains aligned with the seven-UE catalog;
- the lab PLMN, APN and gNB search address are present;
- generated runtime configuration permissions are exactly `0600`;
- a missing external authentication reference fails closed and leaves no output for the failed subscriber;
- malformed authentication material is rejected and its partial output is removed;
- the renderer source contains no direct authentication literals.

CI continues to use synthetic non-production authentication material only.

### 3. CI verification

GitHub Actions run #165 for commit `5e982e6c554894514c17d4781eb3acf675ae4299` completed with `success`. Both the full Project-72 assurance test target and the dedicated UERANSIM renderer validation step passed.

This supersedes the earlier pending state from run #154. The corrected concurrent-idempotency behavior and renderer hardening are now CI-green on the current branch head.

### 4. Gate 4E preparation review

The current UERANSIM renderer and runtime acceptance boundary remain deployment-local. Gate 4E is still a host-runtime task: start the pinned Open5GS/AMF path, start the UERANSIM gNB, attach one UE at a time, validate PDU session establishment and compare authoritative runtime state with canonical state.

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
