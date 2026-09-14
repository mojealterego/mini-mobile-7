# Project Status

Phase 2A/2B/2C/2D implementation is being developed on `project-72/phase-2a` and is not yet merged to `main`.

| Stage | Status | Completion condition |
|---|---|---|
| Project-72 contracts | IMPLEMENTED IN CODE | Subscriber, capability, execution, readback, postcondition and assurance-result schemas |
| Canonical Subscriber Store | IMPLEMENTED IN CODE | MongoDB + deterministic seven-subscriber catalog |
| Capability Broker | IMPLEMENTED IN CODE | Fail-closed authorization, target/version/capability/risk checks |
| Assurance Core | IMPLEMENTED IN CODE | Authorization -> execution -> authoritative readback -> postcondition -> VERIFIED |
| Optimistic concurrency | IMPLEMENTED IN CODE | `expected_version` enforced atomically by canonical repository implementations |
| Idempotency | IMPLEMENTED IN CODE | Stable idempotency key returns the prior assurance result; key reuse with a different request is CONFLICT |
| Drift detection | IMPLEMENTED IN CODE | Projection mismatch is classified as DRIFT; no automatic repair |
| Open5GS v2.8.0 bootstrap | IMPLEMENTED | Exact source tag is built; floating `ppa:open5gs/latest` removed |
| Subscriber lifecycle | IMPLEMENTED IN CODE | PROVISIONED -> ACTIVE -> SUSPENDED -> RETIRED with optimistic concurrency |
| Lifecycle postconditions | IMPLEMENTED IN CODE | ACTIVATE/SUSPEND/DEACTIVATE each require authoritative readback and state-specific postcondition |
| Seven-subscriber lifecycle tests | TESTED IN CI | Catalog, full 7001 lifecycle and wrong-version denial covered by deterministic tests |
| CI validation | GREEN | Workflow #73 passed for commit `85e5a785f67a2ea2bd1de493b665ba89acb64941` |
| Runtime preflight | IMPLEMENTED | Ubuntu/Open5GS/MongoDB/network/firewall/secret-reference gate before mutation |
| UERANSIM gNB template | AUDITED | PLMN/TAC/SST/AMF/gNB addressing aligned with lab contract |
| Seven-UE renderer | IMPLEMENTED | Deployment-local UE configs for 7001-7007; external authentication references |
| Seven-UE renderer CI validation | IMPLEMENTED | Shell syntax and seven-config deterministic rendering tested with dummy credentials |
| UERANSIM attach | PENDING HOST | Requires actual UERANSIM/Open5GS runtime |
| Seven live subscriber projections | NEXT | Requires actual MongoDB/Open5GS runtime and external secrets |
| UE Internet | READY | Requires actual host routing/NAT configuration |
| IMS/Kamailio | SCAFFOLD | Requires stable Core/data plane |
| Physical RAN | BLOCKED | Requires lawful RF authorization, suitable hardware and conformity/location checks |

## Phase 2D — UERANSIM boundary

- Existing gNB and UE templates were audited.
- gNB lab contract: PLMN `001/01`, TAC `1`, SST `1`, AMF `10.10.0.5`, gNB `10.10.0.6`.
- Deployment-local rendering exists for all seven UE identities.
- Renderer validates IMSI, MCC/MNC, gNB address and external authentication material shape.
- Authentication material is not supplied to the renderer as command-line arguments.
- Generated runtime files are excluded from Git through `runtime/` in `.gitignore`.
- CI uses synthetic non-production authentication values only.

## CI correction

The renderer workflow previously failed because the script was invoked directly while its Git mode was `100644`; GitHub Actions therefore returned exit code 126. The workflow now invokes the renderer explicitly with `bash`.

The corrected concurrency-enabled HEAD passed the complete assurance test job and the UERANSIM renderer validation in workflow #73.

## Gate 3B — optimistic concurrency

- Added a deterministic two-writer race against `7001` with both writers using `expected_version=1`.
- Exactly one writer must commit `v2 ACTIVE`.
- The other writer must receive `StoreConflictError` and is classified as `CONFLICT` at the assurance layer.
- The in-memory repository now protects the compare-and-write operation with a lock; the MongoDB implementation already uses an atomic `find_one_and_update` predicate on `subscriber_id + version`.

## Validation note

CI validates deterministic source-level behavior only. No live Open5GS deployment, UE attach, RAN session, IMS call or public telephony interconnect has been claimed.

## Important limitation

The repository can prepare and validate the controlled lab configuration, but it cannot prove physical RF operation, lawful spectrum use, SIM/eSIM provisioning or real UE attachment without the actual deployment host, RAN hardware, USIM/eSIM credentials and required authorization.
