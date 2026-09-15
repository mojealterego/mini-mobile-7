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
| Security/isolation static gate | TESTED IN CI | Checked-in public binds, floating versions, credential/private-key literals and unsafe host/privileged defaults are rejected |
| Metrics exporter | TESTED IN CI | Dependency-free bounded Prometheus text exporter over evidence snapshots; no telecom mutation or secret labels |
| Backup/recovery procedure | IMPLEMENTED | Canonical/idempotency/eSIM metadata backup with restricted files, checksums and isolated restore acceptance procedure; backup execution remains host-only |
| IMS external reference audit | COMPLETE | PJSIP archive, Pixel IMS module and GSM-SIP bridge audited; decisions recorded in `docs/ims-external-reference-2026-09-15.md` |
| CI validation | PASS-CI | Workflow #347 succeeded on `project-72/phase-2a` after security-gate quoting fix; all workflow steps passed |
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

The scanner was hardened so its own shell quoting is syntax-safe and it does not self-match. Workflow #347 confirmed the complete CI gate after this fix.

This is deliberately not a substitute for host firewall, systemd, container, filesystem or network evidence. Those remain Gate 7 host acceptance items.

## Monitoring boundary

`monitoring/project_72_metrics.py` provides a deterministic, dependency-free Prometheus text exporter over an already collected evidence snapshot. Labels are bounded to assurance status and subscriber IDs 7001–7007. IMSI, UE IP, authentication material, private keys and activation material are excluded from metrics. The exporter is read-only and does not create assurance state. Its tests pass in workflow #347.

## Backup/recovery boundary

`scripts/project-72-backup.sh` backs up canonical subscriber, durable idempotency and optional eSIM metadata databases independently, with restricted permissions and checksums. Raw secret material and private keys are excluded. The backup now uses MongoDB Database Tools `--config` for sensitive connection URIs so credentials are not placed in the `mongodump` process arguments, and it rejects empty archives. `docs/backup-recovery.md` defines isolated restore validation, index/schema checks and the fail-closed rule for uncertain telecom side effects.

A restore test is not yet claimed as executed against the production host; it requires an isolated MongoDB target and host evidence.

## Validation note

Workflow #347 completed successfully for commit `568848a74b21f194f4e2b8501db660bee61966aa`. The Ubuntu 22.04 CI job passed the Project-72 assurance suite, metrics exporter, IMS static safety gate, security/isolation gate, UERANSIM renderer and Asterisk PJSIP renderer. The branch subsequently received additional defensive hardening for malformed Open5GS assurance markers and backup URI handling; the resulting commits require the next CI run for final confirmation.

CI validates deterministic source-level behavior only. No live Open5GS deployment, UE attach, RAN session, IMS call or public telephony interconnect has been claimed.

## Important limitation

The repository can prepare and validate the controlled lab configuration, but it cannot prove physical RF operation, lawful spectrum use, SIM/eSIM provisioning or real UE attachment without the actual deployment host, RAN hardware, USIM/eSIM credentials and required authorization.
