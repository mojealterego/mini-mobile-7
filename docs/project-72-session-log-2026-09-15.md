# Project-72 engineering session log — 2026-09-15

## Changes implemented

### 1. Concurrent idempotency reservation coverage

Added `project_72/assurance_core/test_idempotency_concurrency.py`.

The test runs two independent `AssuranceCore` instances concurrently against the same thread-safe idempotency store and the same `ACTIVATE 7001` request. The race is deliberately controlled so one caller owns the reservation while its side-effect executor is in progress. The second caller must fail closed as `CONFLICT`.

The test verifies exactly one side-effect execution, fail-closed duplicate handling and terminal assurance behavior.

### 2. UERANSIM renderer hardening

Added `project_72/assurance_core/test_ueransim_renderer.py` and wired it into `make assurance-test` and CI.

The renderer suite verifies all seven outputs, deterministic subscriber/IMSI mapping, lab PLMN/APN/gNB settings, `0600` permissions, missing-secret rejection, malformed authentication-material rejection, cleanup of failed partial output and absence of direct authentication literals in the renderer source.

CI uses synthetic non-production authentication values only.

### 3. Runtime dry-run and preflight hardening

Added regression coverage confirming that runtime dry-run exits before construction of the MongoDB/Open5GS mutation path. Runtime `--execute` remains fail-closed without a durable idempotency URI and invokes preflight before provisioning mutation.

### 4. Read-only host evidence boundary

Added `scripts/project-72-host-evidence.sh` and a `make host-evidence` target. The collector records OS/kernel, IP addressing/routes, `ogstun`, IPv4 forwarding, firewall rules, listening sockets, relevant service status, MongoDB version when available, running services and hashes/permissions of deployment-local UERANSIM files. It uses `umask 077` and intentionally does not collect authentication material or mutate telecom state.

Updated `docs/runtime-acceptance.md` to make this collector part of the Gate 4E evidence procedure.

### 5. Identity and eSIM artifact boundary

Added deterministic private identity generation for subscribers `7001–7007`, external eSIM activation-material resolution, LPA activation-artifact generation, metadata-only eSIM artifact persistence and an `ESIM_GENERATE` AssuranceCore path.

The eSIM implementation deliberately distinguishes `GENERATED`, `INSTALLED` and `VERIFIED`. It does not create a GSMA eSIM profile, impersonate an SM-DP+, install a profile on a device or claim device verification without authoritative external evidence.

### 6. External IMS/PJSIP repository audit

Audited the three supplied repositories:

- `mojealterego/pjproject-archive`
- `mojealterego/Pixel-turn-on-5G-Volte-and-automatically-register-with-IMS`
- `selvakn/gsm-sip-bridge`

The resulting architectural decisions are recorded in `docs/ims-external-reference-2026-09-15.md`.

Key decisions:

- `pjproject-archive`: historical PJSIP/PJMEDIA reference only; do not import its old source tree as the Project-72 IMS baseline.
- Pixel repository: adapt the idea of device-side IMS acceptance evidence, but reject carrier-specific debug/property forcing as proof of registration. A claimed Android registration property is not authoritative network evidence.
- `gsm-sip-bridge`: adapt strict configuration, TLS, recovery and observability patterns; do not turn the project into a carrier-facing GSM/VoWiFi/VoLTE gateway or uncontrolled PSTN/PLMN exit.

### 7. Private IMS configuration completion

Added `scripts/project-72-render-asterisk-pjsip.sh` to render all seven private Asterisk/PJSIP endpoints from external runtime secrets. The renderer does not accept passwords as CLI arguments, writes `0600` output and rejects unsafe configuration characters.

Added `project_72/assurance_core/test_asterisk_renderer.py` covering seven-way rendering, missing-secret fail-closed behavior, unsafe-character rejection, permissions and source secret-boundary checks.

Updated the Kamailio example so private `REGISTER` traffic is explicitly dispatched to the controlled Asterisk registrar after the private IMS ACL. This closes a configuration gap where the prior example would not route REGISTER requests.

The renderer and REGISTER route are configuration/automation completion only; live TLS, SIP registration and media still require the controlled host.

### 8. Documentation continuity

Updated `README.md`, `docs/project-status.md` and this session log with the IMS renderer, REGISTER boundary and external repository audit.

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
- deterministic private identities;
- eSIM activation-artifact generation and assurance path;
- Asterisk seven-subscriber PJSIP rendering;
- private Kamailio REGISTER dispatch;
- private IMS scaffolding and external IMS/PJSIP reference audit.

The following still require the actual controlled deployment host or external service/device:

- MongoDB canonical/idempotency database acceptance;
- Open5GS v2.8.0 live projection and authoritative readback;
- UERANSIM gNB/UE attach and PDU-session validation for 7001–7007;
- UE Internet path validation;
- Kamailio/Asterisk TLS/SRTP registration and internal call validation;
- live drift injection/readback acceptance;
- final security/isolation evidence;
- real SM-DP+ provisioning, LPA installation and authoritative eSIM/device readback;
- physical RAN and handset validation.

No live telecom state is claimed from CI-only validation.

## Safety boundary

No production authentication secrets are stored in the repository or this log. Physical RF operation remains gated on suitable hardware and lawful Polish radio authorization. Public PSTN/PLMN interconnection remains outside the default private-lab path.
