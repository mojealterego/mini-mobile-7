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
| Drift detection | IMPLEMENTED IN CODE | Target, lifecycle, version, IMSI, UE IP, assurance marker and service projection mismatches classify as DRIFT; malformed/missing authoritative fields fail closed; no automatic repair |
| Open5GS v2.8.0 bootstrap | IMPLEMENTED | Exact source tag is built; floating `ppa:open5gs/latest` removed |
| Subscriber lifecycle | IMPLEMENTED IN CODE | PROVISIONED -> ACTIVE -> SUSPENDED -> RETIRED with optimistic concurrency |
| Lifecycle postconditions | IMPLEMENTED IN CODE | ACTIVATE/SUSPEND/DEACTIVATE each require authoritative readback and state-specific postcondition |
| Seven-subscriber lifecycle tests | TESTED IN CI | Catalog, lifecycle and wrong-version denial covered by deterministic tests |
| Identity generator | IMPLEMENTED IN CODE | Deterministic private identity records for 7001–7007 |
| eSIM artifact generation | IMPLEMENTED IN CODE | External matching ID reference -> LPA artifact; no raw activation secret persisted |
| eSIM AssuranceCore path | TESTED IN CI | `ESIM_GENERATE` authorization, execution, readback and postcondition chain |
| eSIM interrupted-write reconciliation | IMPLEMENTED IN CODE | Matching artifact left by an interrupted canonical commit can be safely promoted; mismatched artifact fails closed |
| Asterisk PJSIP renderer | IMPLEMENTED IN CODE | Seven private endpoints rendered from external secrets; 0600 runtime file and injection checks |
| Kamailio REGISTER routing | IMPLEMENTED IN CONFIG | Private REGISTER traffic routed to controlled Asterisk registrar; live validation pending |
| IMS static safety gate | TESTED IN CI | Private bind, TLS/SRTP baseline, external credentials and no public telephony route checked in CI |
| Security/isolation static gate | IMPLEMENTED | Checked-in public binds, floating versions, credential/private-key literals and unsafe host/privileged defaults are rejected |
| Metrics exporter | IMPLEMENTED IN CODE | Dependency-free bounded Prometheus text exporter over evidence snapshots; no telecom mutation or secret labels |
| Backup/recovery procedure | IMPLEMENTED | Canonical/idempotency/eSIM metadata backup with restricted files, checksums and isolated restore acceptance procedure |
| IMS external reference audit | COMPLETE | PJSIP archive, Pixel IMS module and GSM-SIP bridge audited; decisions recorded in `docs/ims-external-reference-2026-09-15.md` |
| CI validation | PENDING NEW RUN | New security/metrics controls were added after the last confirmed successful run and require CI confirmation |
| Runtime preflight | IMPLEMENTED | Ubuntu/Open5GS/MongoDB/network/firewall/secret-reference gate before mutation |
| Runtime provisioner | IMPLEMENTED IN CODE | `--execute` requires durable MongoDB idempotency URI and injects `MongoIdempotencyStore` into AssuranceCore |
| Runtime dry-run boundary | IMPLEMENTED IN CODE | Dry-run exits before runtime database construction or mutation path |
| UERANSIM gNB template | AUDITED | PLMN/TAC/SST/AMF/gNB addressing aligned with lab contract |
| Seven-UE renderer | IMPLEMENTED | Deployment-local UE configs for 7001-7007; external authentication references |
| UERANSIM attach | PENDING HOST | Requires actual UERANSIM/Open5GS runtime |
| Seven live subscriber projections | PENDING HOST | Requires actual MongoDB/Open5GS runtime and external secrets |
| UE Internet | READY | Requires actual host routing/NAT configuration |
| IMS/Kamailio | SCAFFOLD+ | REGISTER routing and Asterisk endpoint rendering implemented; live TLS/SRTP registration/call validation remains pending |
| Host evidence collector | IMPLEMENTED | Read-only service/network/config evidence capture for Gate 4E/5/7 |
| Physical RAN | BLOCKED | Requires lawful RF authorization, suitable hardware and conformity/location checks |

## Security and isolation boundary

`scripts/project-72-security-check.sh` is a source-level gate. It rejects floating deployment versions, obvious checked-in credentials/private keys, public SIP binds and unsafe host-network/privileged defaults in controlled configuration. It also verifies the private IMS ACL, private TLS dispatcher and Asterisk media isolation baseline.

This is deliberately not a substitute for host firewall, systemd, container, filesystem or network evidence. Those remain Gate 7 host acceptance items.

## Monitoring boundary

`monitoring/project_72_metrics.py` provides a deterministic, dependency-free Prometheus text exporter over an already collected evidence snapshot. Labels are bounded to assurance status and subscriber IDs 7001–7007. IMSI, UE IP, authentication material, private keys and activation material are excluded from metrics. The exporter is read-only and does not create assurance state.

## Backup/recovery boundary

`scripts/project-72-backup.sh` backs up canonical subscriber, durable idempotency and optional eSIM metadata databases independently, with restricted permissions and checksums. Raw secret material and private keys are excluded. `docs/backup-recovery.md` defines isolated restore validation, index/schema checks and the fail-closed rule for uncertain telecom side effects.

A restore test is not yet claimed as executed against the production host; it requires an isolated MongoDB target and host evidence.

## Validation note

Workflow #313 completed successfully after the previous documentation/runtime batch: the Project-72 suite ran 63 tests, the IMS static safety gate passed, and both UERANSIM and Asterisk renderers passed their checks. The current branch now adds the security gate, metrics exporter, backup/recovery procedure and corresponding CI steps; a new run is required before those newest controls are marked `PASS-CI`.

CI validates deterministic source-level behavior only. No live Open5GS deployment, UE attach, RAN session, IMS call or public telephony interconnect has been claimed.

## Important limitation

The repository can prepare and validate the controlled lab configuration, but it cannot prove physical RF operation, lawful spectrum use, SIM/eSIM provisioning or real UE attachment without the actual deployment host, RAN hardware, USIM/eSIM credentials and required authorization.
