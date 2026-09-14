# Project Status

Phase 2A/2B/2C/2D implementation is being developed on `project-72/phase-2a` and is not yet merged to `main`.

| Stage | Status | Completion condition |
|---|---|---|
| Project-72 contracts | IMPLEMENTED IN CODE | Subscriber, capability, execution, readback, postcondition and assurance-result schemas |
| Canonical Subscriber Store | IMPLEMENTED IN CODE | MongoDB + deterministic seven-subscriber catalog |
| Capability Broker | IMPLEMENTED IN CODE | Fail-closed authorization, target/version/capability/risk checks |
| Assurance Core | IMPLEMENTED IN CODE | Authorization -> execution -> authoritative readback -> postcondition -> VERIFIED |
| Optimistic concurrency | IMPLEMENTED IN CODE | `expected_version` enforced by canonical repository |
| Idempotency | IMPLEMENTED IN CODE | Stable idempotency key returns the prior assurance result |
| Drift detection | IMPLEMENTED IN CODE | Projection mismatch is classified as DRIFT; no automatic repair |
| Open5GS v2.8.0 bootstrap | IMPLEMENTED | Exact source tag is built; floating `ppa:open5gs/latest` removed |
| Subscriber lifecycle | IMPLEMENTED IN CODE | PROVISIONED -> ACTIVE -> SUSPENDED -> RETIRED with optimistic concurrency |
| Lifecycle postconditions | IMPLEMENTED IN CODE | ACTIVATE/SUSPEND/DEACTIVATE each require authoritative readback and state-specific postcondition |
| Seven-subscriber lifecycle tests | TESTED IN CI | Catalog, full 7001 lifecycle and wrong-version denial covered by deterministic tests |
| CI validation | PENDING CURRENT HEAD | Renderer CI fix committed; current workflow must complete |
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

The first renderer workflow failure was caused by the script being invoked directly while its Git mode was `100644`; GitHub Actions therefore returned exit code 126. The workflow now invokes the renderer explicitly with `bash`, removing the executable-bit dependency.

The assurance/lifecycle suite itself passed before the renderer step failed. The corrected HEAD requires a fresh workflow run before this status can be marked GREEN.

## Validation note

CI validates deterministic source-level behavior only. No live Open5GS deployment, UE attach, RAN session, IMS call or public telephony interconnect has been claimed.

## Important limitation

The repository can prepare and validate the controlled lab configuration, but it cannot prove physical RF operation, lawful spectrum use, SIM/eSIM provisioning or real UE attachment without the actual deployment host, RAN hardware, USIM/eSIM credentials and required authorization.
