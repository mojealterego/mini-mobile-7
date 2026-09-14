# Project Status

Phase 2A/2B/2C implementation is being developed on `project-72/phase-2a` and is not yet merged to `main`.

| Stage | Status | Completion condition |
|---|---|---|
| Repository | DONE | Repository initialized and protected against accidental secret commits |
| Security baseline | DONE | Secret-handling and firewall rules documented |
| Architecture | DONE | Core/RAN/IMS topology documented |
| Addressing | DONE | Management/Core/UE/IMS ranges documented |
| Project-72 contracts | IMPLEMENTED | JSON Schema contracts for subscriber, capability, execution, readback, postcondition and assurance result |
| Canonical Subscriber Store | IMPLEMENTED | Versioned canonical model plus MongoDB adapter and in-memory deterministic test adapter |
| Capability Broker | IMPLEMENTED | Fail-closed policy/scope/risk gate |
| Assurance Core | IMPLEMENTED | Authorization + policy + execution + authoritative readback + postcondition gate |
| Golden Path ACTIVATE 7001 | TESTED IN CODE | Deterministic path reaches VERIFIED and retry is idempotent |
| Open5GS version drift | FIXED IN BRANCH | Bootstrap builds exact v2.8.0 source tag instead of floating PPA package |
| Open5GS v2.8.0 subscriber schema | VERIFIED AGAINST PINNED TOOLING | Adapter follows the v2.8.0 `open5gs-dbctl` subscriber document layout |
| Open5GS projection adapter | IMPLEMENTED | Canonical lifecycle state is projected with external secret resolution and optimistic concurrency |
| Open5GS authoritative readback | IMPLEMENTED | Projection is read back and classified by canonical lifecycle state |
| Drift classification | IMPLEMENTED | Authoritative MISMATCH is classified as DRIFT and cannot be VERIFIED |
| Seven-subscriber catalog | IMPLEMENTED IN CODE | Deterministic 7001-7007 / 10.20.0.11-10.20.0.17 catalog with external secret refs |
| Subscriber lifecycle | IMPLEMENTED IN CODE | PROVISIONED -> ACTIVE -> SUSPENDED -> RETIRED with optimistic concurrency |
| Lifecycle postconditions | IMPLEMENTED IN CODE | ACTIVATE/SUSPEND/DEACTIVATE each require authoritative readback and state-specific postcondition |
| Seven-subscriber lifecycle tests | TESTED IN CODE | Catalog, full 7001 lifecycle and wrong-version denial covered by deterministic tests |
| CI validation | FIX IN PROGRESS | First CI run exposed an incorrect package export; export was corrected and requires a fresh CI run |
| Ubuntu bootstrap | READY | Run on the actual Linux host |
| Open5GS Core | READY | Requires actual Linux host and installation |
| One subscriber projection | TESTED IN CODE | Canonical Store -> Open5GS adapter -> authoritative readback path covered by deterministic tests |
| Seven live subscriber projections | NEXT | Requires actual MongoDB/Open5GS runtime and external secrets |
| UE Internet | READY | Requires actual host routing/NAT configuration |
| IMS/Kamailio | SCAFFOLD | Requires stable Core/data plane |
| Asterisk/PSTN gateway | ARCHITECTURE CAPTURED | Requires lawful operator SIP trunk, numbering and SBC policy |
| Physical USIM | BLOCKED | Requires physical compatible USIMs and provisioning process |
| Physical LTE/5G RAN | BLOCKED | Requires RAN hardware and lawful RF authorization |
| First physical handset | BLOCKED | Depends on RAN + USIM + regulatory gate |
| Seven physical handsets | BLOCKED | Depends on successful first-handset test |
| Public +48 telephony | CONDITIONAL | Only through lawful numbering/interconnect/operator arrangement |
| Monitoring | SCAFFOLD | Implement after Core/RAN stability |

## Implementation log

### Phase 2A — Project-72 assurance boundary

- Added machine-readable contracts under `project-72/contracts/`.
- Added explicit statuses `VERIFIED`, `UNVERIFIED`, `STALE`, `CONFLICT`, `DRIFT` and `FAILED`.
- Added `expected_version` and `idempotency_key` to mutation requests.
- Added canonical subscriber model with `secret_refs`; authentication material is not part of repository state.
- Added MongoDB canonical adapter in a dedicated `mini_mobile_7.canonical_subscribers` collection so canonical state is not conflated with the Open5GS projection database.
- Added fail-closed Capability Broker.
- Added Assurance Core and deterministic `ACTIVATE 7001` Golden Path test.

### Phase 2B — deterministic Core bootstrap and Open5GS boundary

- Replaced the floating `ppa:open5gs/latest` installation path with a source build pinned to the official `v2.8.0` tag.
- Kept MongoDB on the 8.0 package line.
- Verified the pinned Open5GS v2.8.0 `open5gs-dbctl` layout: static IPv4 belongs under `slice[0].session[0].ue.ipv4`; subscriber status is represented by `subscriber_status` with values 0/1. citeturn2view0
- Added the Open5GS projection adapter under `adapters/open5gs/`.
- Added a runtime `from_mongodb()` constructor; the MongoDB URI remains deployment-provided.
- Activation advances canonical state using optimistic concurrency and projects the resulting ACTIVE version to Open5GS.
- Authentication material is resolved only through an external `secret_ref` resolver; no supplied credentials are copied into Git.
- Added authoritative Open5GS readback with deterministic fingerprinting.
- Added explicit `MISMATCH -> DRIFT` classification in Assurance Core.

### Phase 2C — seven-subscriber lifecycle

- Added deterministic canonical catalog for 7001-7007.
- Enforced the UE address invariant `10.20.0.11` through `10.20.0.17`.
- Added lifecycle state machine: `PROVISIONED -> ACTIVE -> SUSPENDED -> RETIRED`.
- Added optimistic-concurrency lifecycle application.
- Extended Open5GS projection to ACTIVE/SUSPENDED/RETIRED using the v2.8.0 subscriber-status field.
- Added state-specific authoritative postconditions.
- Added deterministic seven-subscriber lifecycle tests.
- Kept PSTN outbound disabled in the canonical catalog by default.

### CI correction

The first GitHub Actions execution reached the test command and exposed a real package error: `project_72/__init__.py` imported modules from the wrong package level. That file has now been corrected to export from `project_72.assurance_core`. The failing run is retained as evidence of the defect discovery; the corrected branch still requires a fresh CI execution before being marked green.

## Validation note

A live Open5GS deployment has not been claimed. CI validation is being used for deterministic source-level tests; runtime validation still requires the actual Ubuntu/Open5GS/MongoDB host and external authentication secrets.

## Important limitation

The repository changes above are source-level implementation and deterministic tests. They do not claim that a live Open5GS core, RAN, IMS or public telephony interconnect is operational until the actual host and external dependencies have been tested.
