# Project Status

| Stage | Status | Completion condition |
|---|---|---|
| Repository | DONE | Private repository initialized |
| Security baseline | DONE | Secret-handling and firewall rules documented |
| Architecture | DONE | Core/RAN/IMS topology documented |
| Addressing | DONE | Management/Core/UE/IMS ranges documented |
| Project-72 contracts | IMPLEMENTED | JSON Schema contracts for subscriber, capability, execution, readback, postcondition and assurance result |
| Canonical Subscriber Store | IMPLEMENTED | Versioned canonical model plus MongoDB adapter and in-memory deterministic test adapter |
| Capability Broker | IMPLEMENTED | Fail-closed policy/scope/risk gate |
| Assurance Core | IMPLEMENTED | Authorization + policy + execution + authoritative readback + postcondition gate |
| Golden Path ACTIVATE 7001 | TESTED | Deterministic in-memory test reaches VERIFIED and retry is idempotent |
| Open5GS version drift | FIXED IN BRANCH | Bootstrap builds exact v2.8.0 source tag instead of floating PPA package |
| Ubuntu bootstrap | READY | Run on the actual Linux host |
| Open5GS Core | READY | Requires actual Linux host and installation |
| Open5GS authoritative adapter | NEXT | Requires adapter against a real Open5GS instance |
| UERANSIM lab | READY | Requires actual Linux host and simulator installation |
| One subscriber projection | NEXT | Canonical Store -> Open5GS adapter with authoritative readback |
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

### Phase 2B — deterministic Core bootstrap

- Replaced the floating `ppa:open5gs/latest` installation path with a source build pinned to the official `v2.8.0` tag.
- Kept MongoDB on the 8.0 package line.
- The repository now treats Open5GS version drift as an explicit deployment failure rather than an acceptable upgrade.

## Important limitation

The repository changes above are source-level implementation and deterministic tests. They do not claim that a live Open5GS core, RAN, IMS or public telephony interconnect is operational until the actual host and external dependencies have been tested.
