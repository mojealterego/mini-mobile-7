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

The collector is systemd-aware: when `systemctl` is absent it records an explicit `UNAVAILABLE` result instead of emitting misleading command failures.

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

### 7. Private IMS configuration completion

Added `scripts/project-72-render-asterisk-pjsip.sh` to render all seven private Asterisk/PJSIP endpoints from external runtime secrets. The renderer does not accept passwords as CLI arguments, writes `0600` output and rejects unsafe configuration characters.

Added `project_72/assurance_core/test_asterisk_renderer.py` and the private Kamailio REGISTER dispatch.

### 8. Static IMS safety gate and CI closure

Added `scripts/project-72-ims-config-check.sh` and `make ims-config-check` as a deterministic static gate. The latest CI workflow continues to enforce the gate.

### 9. Drift detection hardening

Expanded `DriftDetector` so an `IN_SYNC` result requires authoritative agreement on target, lifecycle state, version, IMSI, UE IPv4, assurance marker and the `data`/`ims` service projections. Missing or malformed marker/service evidence is classified fail-closed as `DRIFT`.

### 10. eSIM interrupted-write reconciliation

Hardened `ESIM_GENERATE` around its two persistence domains. Exact matching artifacts can be reconciled after an interrupted canonical commit; mismatched artifacts are rejected. The mechanism does not assume a cross-store transaction.

### 11. Lifecycle cleanup

Simplified lifecycle transition state preservation while retaining immutable canonical state and optimistic concurrency semantics.

### 12. Security/isolation static gate

Added `scripts/project-72-security-check.sh`. The gate rejects floating deployment versions, obvious checked-in credentials/private keys, public IMS SIP binds and unsafe host-network/privileged defaults. It also verifies the private IMS ACL, private TLS dispatcher and Asterisk media-isolation baseline.

The first CI attempt exposed a shell-quoting syntax defect in the scanner itself. The scanner was rewritten with simpler independent expressions and exclusion of its own file. The corrected workflow passed.

### 13. Monitoring/telemetry boundary

Added `monitoring/project_72_metrics.py`, a dependency-free read-only Prometheus text exporter over collected evidence snapshots. Its label cardinality is bounded to assurance statuses and subscriber IDs `7001–7007`; sensitive subscriber/authentication material is excluded. Added deterministic exporter tests and a Make target.

### 14. Backup/recovery boundary

Added `scripts/project-72-backup.sh` and `docs/backup-recovery.md`. The procedure independently backs up canonical, durable idempotency and optional eSIM metadata databases, restricts backup permissions, creates checksums and excludes raw secrets/private keys. The backup was hardened to use MongoDB Database Tools `--config` for sensitive URIs, preventing credentials from appearing in `mongodump` process arguments, and to reject empty archives.

The procedure explicitly refuses remote MongoDB backup unless `MM7_BACKUP_ALLOW_REMOTE=1` is deliberately enabled.

### 15. Open5GS projection fail-closed hardening

Hardened `adapters/open5gs/adapter.py` so malformed `mm7_assurance.canonical_version` or `subscriber_status` values cannot raise an uncontrolled conversion exception during readback/projection comparison. Malformed values now fail closed as a mismatch. Added a regression test proving a malformed assurance marker becomes non-verified readback state rather than an exception.

### 16. CI enforcement

Workflow #358 succeeded for the hardened commit `e15bdc4b555394cade7bb469cc1914c127e494fe`, passing the Project-72 assurance suite, metrics exporter, IMS static safety gate, security/isolation gate, UERANSIM renderer and Asterisk PJSIP renderer. The documentation-only follow-up workflow #369 also completed successfully after the status and runtime-diagnostic updates.

### 17. Runtime capability diagnostics

Added `scripts/project-72-runtime-capabilities.sh` and `make runtime-capabilities`. This is a read-only environment diagnostic, not a provisioning gate. It reports the presence and operational state of systemd, cgroup visibility, KVM/TUN device access, network inspection, IPv4 forwarding sysctl visibility, iptables access, socket inspection and kernel SCTP visibility.

The purpose is to distinguish a 22.04 userland/container from a host capable of supporting the Project-72 live runtime. It performs no package installation, interface creation, service start, firewall mutation or telecom operation.

## Current engineering boundary

Code and deterministic tests cover the Project-72 assurance contracts, canonical store, authorization, authoritative readback, postconditions, concurrency/idempotency, Open5GS projection, drift detection, UERANSIM rendering, runtime preflight/dry-run, host evidence collection, private identity/eSIM artifacts, private IMS configuration, static security isolation, bounded metrics and backup/recovery procedures.

Still requiring the actual controlled deployment host or external service/device:

- live MongoDB/Open5GS acceptance;
- seven UERANSIM attaches and PDU sessions;
- UE Internet path validation;
- Kamailio/Asterisk TLS/SRTP registration and internal call validation;
- live drift injection/readback acceptance;
- final host security/isolation evidence;
- real SM-DP+ provisioning, LPA installation and authoritative eSIM/device readback;
- physical RAN and handset validation.

No live telecom state is claimed from source-level or CI validation.

## Safety boundary

No production authentication secrets are stored in the repository or this log. Physical RF operation remains gated on suitable hardware and lawful Polish radio authorization. Public PSTN/PLMN interconnection remains outside the default private-lab path.
