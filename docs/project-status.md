# Project Status

Phase 2A/2B/2C/2D implementation is being developed on `project-72/phase-2a` and is not yet merged to `main`.

| Stage | Status | Completion condition |
|---|---|---|
| Project-72 contracts | IMPLEMENTED IN CODE | Subscriber, capability, execution, readback, postcondition, assurance-result, private-identity and eSIM artifact schemas |
| Canonical Subscriber Store | IMPLEMENTED IN CODE | MongoDB + deterministic seven-subscriber catalog |
| Capability Broker | IMPLEMENTED IN CODE | Fail-closed authorization, target/version/capability/risk checks, including eSIM operations |
| Assurance Core | IMPLEMENTED IN CODE | Authorization -> execution -> authoritative readback -> postcondition -> VERIFIED |
| Optimistic concurrency | IMPLEMENTED IN CODE | `expected_version` enforced atomically by canonical repository implementations |
| Idempotency | IMPLEMENTED IN CODE | Durable MongoDB reservation + terminal-result persistence; concurrent duplicate execution fails closed |
| Drift detection | IMPLEMENTED IN CODE | Projection mismatch is classified as DRIFT; no automatic repair |
| Open5GS v2.8.0 bootstrap | IMPLEMENTED | Exact source tag is built; floating `ppa:open5gs/latest` removed |
| Subscriber lifecycle | IMPLEMENTED IN CODE | PROVISIONED -> ACTIVE -> SUSPENDED -> RETIRED with optimistic concurrency |
| Lifecycle postconditions | IMPLEMENTED IN CODE | ACTIVATE/SUSPEND/DEACTIVATE each require authoritative readback and state-specific postcondition |
| Seven-subscriber lifecycle tests | TESTED IN CI | Catalog, lifecycle and wrong-version denial covered by deterministic tests |
| Identity generator | IMPLEMENTED IN CODE | Deterministic private identity records for 7001–7007 |
| eSIM artifact generation | IMPLEMENTED IN CODE | External matching ID reference -> LPA artifact; no raw activation secret persisted |
| eSIM AssuranceCore path | TESTED IN CI | `ESIM_GENERATE` authorization, execution, readback and postcondition chain |
| CI validation | PASS-CI | Latest confirmed Project-72 run #236 passed |
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
| IMS external reference audit | COMPLETE | PJSIP archive, Pixel IMS module and GSM-SIP bridge audited; decisions recorded in `docs/ims-external-reference-2026-09-15.md` |
| Host evidence collector | IMPLEMENTED | Read-only service/network/config evidence capture for Gate 4E/5/7 |
| Physical RAN | BLOCKED | Requires lawful RF authorization, suitable hardware and conformity/location checks |

## Gate 4E — host acceptance boundary

- Added a read-only host evidence collector for Ubuntu/service/network/firewall/socket state and deployment-local UERANSIM file hashes.
- The collector intentionally does not mutate services, subscribers or Open5GS state and is designed to capture evidence before/after live acceptance.
- Actual UERANSIM attach, PDU-session establishment and seven-subscriber live readback remain pending on the deployment host.

## IMS boundary correction

- Corrected the Kamailio example ACL to use a deterministic private IMS source-address check instead of the previously unverified `ipops_check_ip` expression.
- The example remains deployment scaffolding and requires validation with the installed Kamailio version before live activation.
- Asterisk TLS/SRTP configuration remains a deployment template; no public SIP/PSTN trunk is configured.

## External IMS reference decisions

### PJSIP archive

`mojealterego/pjproject-archive` is treated as a historical PJSIP/PJMEDIA reference. Its README describes an old classic PJSIP build flow and is not used as the Project-72 version authority. No source-tree copy is imported into MINI-MOBILE-7.

### Pixel VoLTE/IMS module

`mojealterego/Pixel-turn-on-5G-Volte-and-automatically-register-with-IMS` is treated as a device-side diagnostic/reference source. Its boot-time operator detection, IMS service restart and registration observation are useful as concepts, but carrier-specific debug properties and a claimed `imsregistered` property are not accepted as authoritative network proof.

### GSM-SIP bridge

`selvakn/gsm-sip-bridge` is treated as an interoperability/reference implementation. Strict configuration, TLS, recovery and observability patterns are adaptable. Its carrier-facing VoWiFi/ePDG, host-side carrier VoLTE, automated cellular outbound calling and privileged/host-network container defaults are not adopted as the MINI-MOBILE-7 private IMS architecture.

The resulting private IMS architecture remains:

```text
Canonical Subscriber Store
        -> Capability Broker
        -> Assurance Core
        -> Open5GS projection
        -> private IMS authorization/config
        -> Kamailio
        -> Asterisk/PJSIP
```

The external repositories do not become alternative subscriber authorities and cannot bypass Project-72 authorization, idempotency, `expected_version`, authoritative readback or postconditions.

## eSIM boundary

Project-72 can generate an LPA activation artifact only when a real provisioning system supplies an external matching ID through a secret reference. It does not manufacture a GSMA profile, impersonate an SM-DP+, install a profile on a handset, or claim device verification.

`GENERATED != INSTALLED != VERIFIED`.

A future live eSIM gate requires an actual SM-DP+/provisioning service, supported LPA/device, device-side installation evidence and authoritative readback.

## Validation note

CI validates deterministic source-level behavior only. No live Open5GS deployment, UE attach, RAN session, IMS call or public telephony interconnect has been claimed.

## Important limitation

The repository can prepare and validate the controlled lab configuration, but it cannot prove physical RF operation, lawful spectrum use, SIM/eSIM provisioning or real UE attachment without the actual deployment host, RAN hardware, USIM/eSIM credentials and required authorization.
