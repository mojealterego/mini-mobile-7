# Project Status

Phase 2A/2B implementation is being developed on `project-72/phase-2a` and is not yet merged to `main`.

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
| Golden Path ACTIVATE 7001 | TESTED IN CODE | Deterministic in-memory path reaches VERIFIED and retry is idempotent |
| Open5GS version drift | FIXED IN BRANCH | Bootstrap builds exact v2.8.0 source tag instead of floating PPA package |
| Open5GS v2.8.0 subscriber schema | VERIFIED AGAINST PINNED TOOLING | Adapter follows the v2.8.0 `open5gs-dbctl` subscriber document layout |
| Open5GS projection adapter | IMPLEMENTED | Canonical ACTIVE state is projected with external secret resolution and optimistic concurrency |
| Open5GS authoritative readback | IMPLEMENTED | Open5GS projection is read back and classified as ACTIVE/ABSENT/MISMATCH |
| Drift classification | IMPLEMENTED | Authoritative MISMATCH is classified as DRIFT and cannot be VERIFIED |
| Ubuntu bootstrap | READY | Run on the actual Linux host |
| Open5GS Core | READY | Requires actual Linux host and installation |
| One subscriber projection | TESTED IN CODE | Canonical Store -> Open5GS adapter -> authoritative readback path covered by deterministic tests |
| UE Internet | READY | Requires actual host routing/NAT configuration |
| IMS/Kamailio | SCAFFOLD | Requires stable Core/data plane |
| Asterisk/PSTN gateway | ARCHITECTURE CAPTURED | Requires lawful operator SIP trunk, numbering and SBC policy |
| Seven subscribers | READY | Requires actual subscriber provisioning |
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
- Added `make assurance-test`.

### Phase 2B — deterministic Core bootstrap and Open5GS boundary

- Replaced the floating `ppa:open5gs/latest` installation path with a source build pinned to the official `v2.8.0` tag.
- Kept MongoDB on the 8.0 package line.
- Verified the pinned Open5GS v2.8.0 `open5gs-dbctl` layout: static IPv4 belongs under `slice[0].session[0].ue.ipv4`, and the subscriber document uses the `security`, `slice`, `ambr` and subscriber-status structures implemented by the adapter. citeturn2view0
- Added the Open5GS projection adapter under `adapters/open5gs/`.
- Added a runtime `from_mongodb()` constructor; the MongoDB URI remains deployment-provided.
- Activation advances canonical state using optimistic concurrency and then projects the resulting ACTIVE version to Open5GS.
- Authentication material is resolved only through an external `secret_ref` resolver; no supplied credentials are copied into Git.
- Added authoritative Open5GS readback with deterministic fingerprinting.
- Added explicit `MISMATCH -> DRIFT` classification in Assurance Core.
- Added deterministic adapter, drift and assurance integration tests.

## Validation note

The test suite is committed but has not been executed against a live repository checkout from this chat environment. A local/CI execution of `make assurance-test` is still required before the branch is considered validated.

## Important limitation

The repository changes above are source-level implementation and deterministic tests. They do not claim that a live Open5GS core, RAN, IMS or public telephony interconnect is operational until the actual host and external dependencies have been tested.
