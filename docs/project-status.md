# Project Status

Phase 2A/2B/2C/2D implementation is being developed on `project-72/phase-2a` and is not yet merged to `main`.

| Stage | Status | Completion condition |
|---|---|---|
| Project-72 contracts | IMPLEMENTED IN CODE | Subscriber, capability, execution, readback, postcondition and assurance-result schemas |
| Canonical Subscriber Store | IMPLEMENTED IN CODE | MongoDB + deterministic seven-subscriber catalog |
| Capability Broker | IMPLEMENTED IN CODE | Fail-closed authorization, target/version/capability/risk checks |
| Assurance Core | IMPLEMENTED IN CODE | Authorization -> execution -> authoritative readback -> postcondition -> VERIFIED |
| Optimistic concurrency | IMPLEMENTED IN CODE | `expected_version` enforced atomically by canonical repository implementations |
| Idempotency | IMPLEMENTED IN CODE | Durable MongoDB reservation + terminal-result persistence; concurrent duplicate execution fails closed |
| Drift detection | IMPLEMENTED IN CODE | Projection mismatch is classified as DRIFT; no automatic repair |
| Open5GS v2.8.0 bootstrap | IMPLEMENTED | Exact source tag is built; floating `ppa:open5gs/latest` removed |
| Subscriber lifecycle | IMPLEMENTED IN CODE | PROVISIONED -> ACTIVE -> SUSPENDED -> RETIRED with optimistic concurrency |
| Lifecycle postconditions | IMPLEMENTED IN CODE | ACTIVATE/SUSPEND/DEACTIVATE each require authoritative readback and state-specific postcondition |
| Seven-subscriber lifecycle tests | TESTED IN CI | Catalog, lifecycle and wrong-version denial covered by deterministic tests |
| CI validation | PENDING FRESH RUN | Renderer/runtime-wiring hardening committed; newest workflow must complete |
| Runtime preflight | IMPLEMENTED | Ubuntu/Open5GS/MongoDB/network/firewall/secret-reference gate before mutation |
| Runtime provisioner | IMPLEMENTED IN CODE | `--execute` requires durable MongoDB idempotency URI and injects `MongoIdempotencyStore` into AssuranceCore |
| Runtime dry-run boundary | IMPLEMENTED IN CODE | Dry-run exits before runtime database construction or mutation path |
| UERANSIM gNB template | AUDITED | PLMN/TAC/SST/AMF/gNB addressing aligned with lab contract |
| Seven-UE renderer | IMPLEMENTED | Deployment-local UE configs for 7001-7007; external authentication references |
| Seven-UE renderer test suite | IMPLEMENTED IN CODE | Seven-way mapping, 0600 permissions, missing/malformed secret rejection and source secret-literal guard |
| UERANSIM attach | PENDING HOST | Requires actual UERANSIM/Open5GS runtime |
| Seven live subscriber projections | NEXT | Requires actual MongoDB/Open5GS runtime and external secrets |
| UE Internet | READY | Requires actual host routing/NAT configuration |
| IMS/Kamailio | SCAFFOLD | Private-network ACL scaffold corrected; requires live Kamailio/Asterisk host validation |
| Host evidence collector | IMPLEMENTED | Read-only service/network/config evidence capture for Gate 4E/5/7 |
| Physical RAN | BLOCKED | Requires lawful RF authorization, suitable hardware and conformity/location checks |

## Phase 2D — UERANSIM boundary

- Existing gNB and UE templates were audited.
- gNB lab contract: PLMN `001/01`, TAC `1`, SST `1`, AMF `10.10.0.5`, gNB `10.10.0.6`.
- Deployment-local rendering exists for all seven UE identities.
- Renderer validates IMSI, MCC/MNC, gNB address and external authentication material shape.
- Authentication material is not supplied to the renderer as command-line arguments.
- Generated runtime files are excluded from Git through `runtime/` in `.gitignore`.
- CI uses synthetic non-production authentication values only.
- Dedicated renderer tests verify all seven identity mappings, `0600` output permissions, missing-secret fail-closed behavior and malformed authentication-material rejection.

## Gate 3B — optimistic concurrency

- Added a deterministic two-writer race against `7001` with both writers using `expected_version=1`.
- Exactly one writer must commit `v2 ACTIVE`.
- The other writer must receive `StoreConflictError` and is classified as `CONFLICT` at the assurance layer.
- The in-memory repository now protects the compare-and-write operation with a lock; the MongoDB implementation already uses an atomic `find_one_and_update` predicate on `subscriber_id + version`.

## Gate 3C — durable idempotency reservation

- Added `InMemoryIdempotencyStore` as a deterministic reference implementation.
- Added `MongoIdempotencyStore` backed by a unique `key` index.
- A request reserves its idempotency key before execution; another process with the same key cannot start a second execution.
- Same key + different fingerprint is `CONFLICT`.
- Same key + completed result is replayed without execution.
- A reservation without a terminal result fails closed as `CONFLICT`; there is deliberately no automatic lease takeover because taking over after an unknown crash could duplicate a non-idempotent telecom side effect.
- Runtime `--execute` now requires the durable MongoDB idempotency URI and injects the durable store into AssuranceCore.
- Added a deterministic concurrent race test proving that a second caller cannot execute the same telecom side effect while another caller owns the reservation.

## Gate 4D — runtime wiring and seven-way projection

- Runtime preflight receives the same canonical MongoDB URI and durable idempotency URI used by execution.
- Runtime `--execute` refuses to proceed without durable idempotency storage.
- Dry-run remains dependency-free from the mutation path and must not construct runtime MongoDB/Open5GS adapters.
- Open5GS adapter/integration coverage exercises all seven catalog subscribers through projection and authoritative readback.

## Gate 4E — host acceptance boundary

- Added a read-only host evidence collector for Ubuntu/service/network/firewall/socket state and deployment-local UERANSIM file hashes.
- The collector intentionally does not mutate services, subscribers or Open5GS state and is designed to capture evidence before/after live acceptance.
- Actual UERANSIM attach, PDU-session establishment and seven-subscriber live readback remain pending on the deployment host.

## IMS boundary correction

- Corrected the Kamailio example ACL to use a deterministic private IMS source-address check instead of the previously unverified `ipops_check_ip` expression.
- The example remains deployment scaffolding and requires validation with the installed Kamailio version before live activation.
- Asterisk TLS/SRTP configuration remains a deployment template; no public SIP/PSTN trunk is configured.

## Validation note

CI validates deterministic source-level behavior only. No live Open5GS deployment, UE attach, RAN session, IMS call or public telephony interconnect has been claimed.

## Important limitation

The repository can prepare and validate the controlled lab configuration, but it cannot prove physical RF operation, lawful spectrum use, SIM/eSIM provisioning or real UE attachment without the actual deployment host, RAN hardware, USIM/eSIM credentials and required authorization.
