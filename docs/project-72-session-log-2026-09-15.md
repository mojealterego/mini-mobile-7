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

The renderer suite verifies all seven outputs, deterministic subscriber/IMSI mapping, lab PLMN/APN/gNB settings, `0600` permissions, missing-secret rejection, malformed authentication-material rejection, cleanup of failed partial output and absence of direct authentication literals in the renderer source.

CI uses synthetic non-production authentication values only.

### 3. Runtime dry-run and preflight hardening

Added regression coverage confirming that runtime dry-run exits before construction of the MongoDB/Open5GS mutation path. Runtime `--execute` remains fail-closed without a durable idempotency URI and invokes preflight before provisioning mutation.

### 4. Read-only host evidence boundary

Added `scripts/project-72-host-evidence.sh` and a `make host-evidence` target. The collector records OS/kernel, IP addressing/routes, `ogstun`, IPv4 forwarding, firewall rules, listening sockets, relevant service status, MongoDB version when available, running services and hashes/permissions of deployment-local UERANSIM files. It uses `umask 077` and intentionally does not collect authentication material or mutate telecom state.

Updated `docs/runtime-acceptance.md` to make this collector part of the Gate 4E evidence procedure.

### 5. CI status

Run #165 for commit `5e982e6c554894514c17d4781eb3acf675ae4299` completed successfully before the latest runtime/documentation commits. It passed both the Project-72 assurance suite and UERANSIM renderer validation.

The current branch head `4674229cbab42a822a9acc2ce14de3daac2133e6` has a newer Project-72 workflow run #177 queued. The latest commit therefore remains **CI PENDING** until that workflow completes.

## Current engineering boundary

Code and deterministic tests cover:

- Project-72 contracts;
- canonical subscriber repository;
- capability authorization;
- assurance execution/readback/postcondition chain;
- optimistic concurrency;
- durable idempotency semantics and concurrent duplicate fail-closed behavior;
- Open5GS v2.8.0 projection/readback adapter;
- seven-subscriber deterministic projection tests;
- UERANSIM seven-UE rendering and validation;
- runtime preflight and dry-run safety boundary;
- read-only host evidence capture;
- private IMS scaffolding.

The following still require the actual controlled deployment host:

- MongoDB canonical/idempotency database acceptance;
- Open5GS v2.8.0 live projection and authoritative readback;
- UERANSIM gNB/UE attach and PDU-session validation for 7001–7007;
- UE Internet path validation;
- Kamailio/Asterisk TLS/SRTP registration and internal call validation;
- live drift injection/readback acceptance;
- final security/isolation evidence;
- physical RAN and handset validation.

No live telecom state is claimed from CI-only validation.

## Safety boundary

No production authentication secrets are stored in the repository or this log. Physical RF operation remains gated on suitable hardware and lawful Polish radio authorization. Public PSTN/PLMN interconnection remains outside the default private-lab path.
