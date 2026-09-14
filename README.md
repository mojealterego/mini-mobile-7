# MINI-MOBILE-7

Private LTE/5G laboratory and private cellular network blueprint for up to 7 controlled devices.

## Scope

This repository contains configuration templates, deployment documentation, security guidance, lab scaffolding, and the Project-72 assurance boundary for a small private mobile network.

Target stack:
- Open5GS Core + MongoDB
- UERANSIM for no-RF laboratory validation
- Kamailio IMS for private voice/IMS experiments
- Asterisk/PJSIP for controlled application voice and optional lawful SIP trunk integration
- srsRAN or a compatible small-cell RAN for physical testing
- Up to 7 controlled subscriber identities

## Network model

```text
Internet / controlled SIP interconnect
          |
   Firewall / VPN / SBC
          |
      Open5GS Core
          |
       IMS layer
    Kamailio / Asterisk
          |
      LTE / 5G RAN
          |
   +--+--+--+--+--+--+
   7001 ...       7007
```

Public telephony is not intrinsic to the private core. It is an explicitly controlled gateway capability and requires a lawful operator SIP trunk/interconnect and valid numbering arrangement.

## Addressing

| Segment | CIDR | Purpose |
|---|---|---|
| Core | 10.10.0.0/24 | Core services |
| UE | 10.20.0.0/24 | Subscriber data plane |
| Management | 10.30.0.0/24 | Administration |
| IMS | 10.40.0.0/24 | SIP/IMS services |

Internal test numbers are **7001–7007**. They are internal identifiers, not Polish public +48 mobile numbers.

## Project-72 assurance boundary

The canonical subscriber state is separated from Open5GS and IMS projections. Mutating operations require:

1. explicit capability authorization;
2. policy and risk approval;
3. idempotent execution;
4. optimistic concurrency using `expected_version`;
5. authoritative readback;
6. postcondition verification.

Only the complete chain may produce `VERIFIED`. `EXECUTED` alone is never sufficient. The contracts live under `project-72/contracts/` and the first executable Golden Path is `ACTIVATE 7001` under `project_72/assurance_core/`.

## Lab-first rule

The software stack is developed and tested in a no-RF lab first. UERANSIM does not turn an Android phone into a cellular UE; real phones require physical RAN hardware, compatible USIMs, lawful spectrum use, and appropriate radio authorization.

## Legal gate

Do not transmit on cellular spectrum until the applicable Polish frequency allocation, permit, equipment conformity, location, power, antenna, and other regulatory requirements have been verified with UKE. Do not self-assign public numbering or create unauthorized interconnection to public mobile networks.

## Security baseline

- Never commit Ki, OPc, SQN secrets, API keys, passwords, private keys, or VPN credentials.
- Keep MongoDB and management interfaces off the public Internet.
- Prefer VPN-only administration.
- Use host firewall/security groups and least-privilege service accounts.
- Rotate any credential that has been exposed.
- Store production secrets outside GitHub.
- Use `secret_ref` references in canonical subscriber state rather than authentication material.
- Do not use floating `latest` image/package references in a deployment baseline.

## Repository layout

```text
core/open5gs/          Core configuration templates
ran/lte/                LTE RAN templates
ran/5g/                 5G RAN templates
ims/kamailio/           IMS configuration scaffolding
subscribers/templates/ Subscriber templates without real secrets
network/firewall/       Network security baseline
monitoring/             Monitoring scaffolding
project-72/contracts/   Machine-readable assurance contracts
project_72/             Assurance Core implementation and tests
docs/                   Architecture, deployment, legal and status notes
```

## Deployment stages

1. Repository and security baseline
2. Deterministic Open5GS + MongoDB
3. Project-72 assurance boundary
4. UERANSIM lab
5. First canonical subscriber
6. Canonical → Open5GS projection and authoritative readback
7. Lab Internet/NAT
8. IMS/voice lab
9. SMS lab where supported
10. Seven subscribers
11. Controlled SIP gateway, only after lawful interconnect is available
12. Physical USIM preparation
13. Physical RAN after legal gate
14. First controlled handset
15. Seven controlled handsets
16. Monitoring, backups and operations

## Local verification

```bash
make validate
make assurance-test
```

The assurance test is deterministic and does not require a live cellular core.

## Acceptance criteria

The project is complete only when each applicable stage has been tested and documented, secrets remain external, canonical state and projections have authoritative readback, and physical RF deployment has passed the legal and hardware gates.

## Important limitation

Repository implementation can be completed remotely, but a real cellular network cannot be truthfully marked as deployed until a suitable Linux host, RAN hardware, compatible USIMs, and lawful radio authorization are actually available.

---

# Project-72 Implementation Log

This is the persistent engineering log. Every substantive implementation step, architectural decision, validation result, and known limitation is recorded here so the repository itself remains the continuity record between work sessions.

## 2026-09-14 — takeover and baseline audit

The original repository was audited before implementation. It contained Open5GS, UERANSIM, IMS scaffolding, firewall/network templates, monitoring scaffolding and subscriber templates, but the Project-72 assurance layer was absent.

Initial maturity assessment:

| Area | Initial state |
|---|---:|
| Documentation | 75% |
| Security baseline | 70% |
| Network architecture | 65% |
| Open5GS implementation | 35% |
| UERANSIM | 35% |
| IMS | 20% |
| Monitoring | 20% |
| Subscriber management | 20% |
| Canonical Subscriber Store | 0% |
| Capability Broker | 0% |
| Assurance Core | 0% |
| Authoritative Readback | 0% |
| Postcondition engine | 0% |
| Drift Detection | 0% |
| Optimistic concurrency | 0% |
| Project-72 contracts | 0% |

Critical findings were recorded for the missing canonical store, capability authorization, authoritative readback, formal `VERIFIED` state, concurrency control and drift detection.

The supplied architecture material was treated as source material rather than already-verified production implementation. Plaintext credentials, hardcoded authentication material, floating container tags, privileged host networking and public SIP exposure were rejected for the repository baseline. Real authentication secrets are not reproduced or committed.

## Project-72 contracts

Added machine-readable contracts under `project-72/contracts/`: subscriber, capability, execution, authoritative readback, postcondition and assurance-result schemas, schema index, and an `ACTIVATE 7001` request example.

Defined assurance states include `AUTHORIZED`, `DENIED`, `EXECUTED`, `VERIFIED`, `UNVERIFIED`, `STALE`, `CONFLICT`, `DRIFT` and `FAILED`.

Core invariant:

```text
AUTHORIZED
   -> POLICY
   -> EXECUTION
   -> AUTHORITATIVE READBACK
   -> POSTCONDITION
   -> VERIFIED
```

`EXECUTED` without authoritative evidence is never promoted to `VERIFIED`.

## Canonical Subscriber Store

Implemented `project_72/assurance_core/store.py` with repository abstraction, in-memory implementation and MongoDB implementation. Canonical state is deliberately separate from Open5GS projection data. MongoDB canonical records use unique indexes for `subscriber_id` and `imsi` and optimistic version checks for lifecycle mutations.

## Deterministic seven-subscriber catalog

Implemented `project_72/assurance_core/catalog.py` and lifecycle catalog validation.

```text
7001 -> 10.20.0.11
7002 -> 10.20.0.12
7003 -> 10.20.0.13
7004 -> 10.20.0.14
7005 -> 10.20.0.15
7006 -> 10.20.0.16
7007 -> 10.20.0.17
```

The catalog enforces exactly seven subscribers, unique IMSIs/IPs, external authentication references, IMS/data enabled and public PSTN inbound/outbound disabled by default.

## Capability Broker

Implemented explicit capability and policy validation. The broker does not execute mutations and cannot grant itself permissions. Checks include principal, operation, target, capability identity, expected version, risk and public-PSTN restrictions.

## Assurance Core

Implemented the Project-72 execution boundary with capability authorization, request fingerprinting, idempotency, optimistic concurrency, authoritative readback, postcondition evaluation and explicit assurance states. Readback version older than or equal to the expected version is treated as stale. State mismatch produces `DRIFT`.

## Idempotency and crash safety

Implemented process-local and MongoDB-backed idempotency stores. The durable store atomically reserves an idempotency key before execution and persists the terminal assurance result. A second execution with the same completed key replays the result instead of executing the telecom side effect again.

A reserved key without a terminal result fails closed as `CONFLICT`. No lease takeover is implemented intentionally: after an uncertain process crash, the system must not automatically repeat a potentially completed telecom mutation.

## Optimistic concurrency

Implemented `expected_version` checks in canonical lifecycle mutation. Deterministic concurrency testing verifies that two writers using the same version produce exactly one successful mutation and one conflict.

## Open5GS v2.8.0 baseline

Corrected the original version drift: the bootstrap previously used a floating Open5GS package source while documentation specified v2.8.0. The bootstrap now builds the exact Open5GS `v2.8.0` source tag. MongoDB 8.0 and UERANSIM v3.3.0 remain pinned according to the project baseline.

## Open5GS adapter

Implemented lifecycle projection and authoritative readback. The adapter resolves authentication values only through the external secret resolver, validates canonical versus projected state, handles Open5GS v2.8.0 subscriber schema details, validates nested Internet UE IPv4 state, records Project-72 assurance marker data, rejects projection state newer than canonical state and exposes authoritative readback for postcondition evaluation.

Integration tests cover activation, suspension, nested UE IP representation, service state, marker state, replay and drift detection.

## UERANSIM renderer

Implemented deployment-local rendering of seven UE configurations from external authentication references. Generated configuration files are runtime-only and permission-restricted. Authentication values are not placed in Git and are not passed as command-line arguments. CI validates the renderer with synthetic non-production values.

The RAN remains no-RF laboratory software until physical hardware and lawful radio authorization are available.

## IMS boundary

Added private IMS boundary templates: Kamailio private-source ACL, dispatcher boundary to Asterisk over TLS, Asterisk PJSIP TLS/SRTP template and IMS documentation. Public SIP/PSTN access is not enabled by the baseline.

Live IMS registration, calling and SMS remain deployment/host acceptance tasks. The templates are not represented as live-validated IMS infrastructure.

## Gate 4A — mandatory runtime preflight

Implemented `scripts/project-72-preflight.sh` as the host safety gate. It validates the Ubuntu 22.04 host baseline, required commands, MongoDB, Open5GS services/configuration, `ogstun`, UE routing, IPv4 forwarding, firewall posture, Python dependencies, MongoDB connectivity and external secret references.

The runtime provisioner now invokes this preflight before any provisioning mutation. The diagnostic preflight script may expose a secret-preflight skip for controlled diagnostics, but runtime `--execute` explicitly overrides that environment setting and refuses to execute without the secret checks.

**Gate 4A code status: IMPLEMENTED. PASS-HOST: PENDING actual host execution.**

## Runtime seven-subscriber provisioner

Implemented `scripts/project-72-provision-seven.py` with dry-run mode, mandatory durable idempotency URI for `--execute`, mandatory runtime preflight, deterministic catalog validation, Project-72 assurance execution, authoritative readback for already-active records and no secret-value printing.

The provisioner cannot claim live activation without an actual MongoDB/Open5GS host.

## Gate 4B — canonical bootstrap hardening

Hardened the canonical bootstrap so initial records are not silently overwritten. The target semantics are:

```text
missing record
     |
     +-- atomic insert --> ACCEPT
     |
     +-- concurrent duplicate --> authoritative readback
                                   |
                                   +-- identical --> ACCEPT/replay
                                   |
                                   +-- different --> CONFLICT
```

There is no automatic reconciliation of conflicting canonical identity data. A mismatch is fail-closed. MongoDB uses unique identity indexes and duplicate insertion is handled through authoritative comparison rather than overwrite.

**Gate 4B code status: IMPLEMENTED. Host/database acceptance: PENDING.**

## CI validation

The Project-72 workflow validates the assurance suite and UERANSIM renderer. Completed run #110 passed its principal assurance and renderer steps. Runtime-preflight and canonical-bootstrap changes triggered subsequent runs, including run #120 for the bootstrap-hardening revision. The latest revision must have its CI result checked before being marked CI-green.

## Implementation commit trail

| Commit | Purpose |
|---|---|
| `e02217377b77a0ccd3bf20ac644bfab3039ecdaf` | Project-72 assurance contracts |
| `dc18751a273e2ccc545a88de3cfdafd854447178` | Canonical store + Assurance Core |
| `75908df51581a85d9e339eecc454174feeb792e6` | Capability/execution binding |
| `c5ccf0e61e14ee68e360438aea6f670c573bdbe5` | Open5GS version drift correction |
| `ba870f01e80c7e5fb1f81081434a049ebc5747dd` | UERANSIM renderer |
| `6197d62aa070e5df1c268d295aaa49cdeb04c5f9` | Runtime replay/idempotency |
| `e0836448cfd76245d263e3020aff9bf242ef41ad` | Idempotency subsystem |
| `9bbe81da95c833fe1959e31976a76bdb1b75c7c8` | AssuranceCore idempotency integration |
| `5b4b5835dcc06835fd02c26015810cc3293bd720` | Atomic idempotency reservation |
| `f999e0beb9bddf0b894dc7bd6a3f5d932f1d85e6` | Durable reservation enforcement |
| `50ae1df60b8a4d593115f88ead5ec1bc5590decd` | Kamailio IMS boundary |
| `e23179768e19294949682e9396cc677139056f14` | Asterisk TLS/SRTP boundary |
| `1f5f3fd69502d43fd78b823245d29c8faac2b968` | Runtime acceptance documentation |
| `8f146862bb8e34122dddfa3984db6e36eb09d16f` | Mandatory runtime preflight enforcement |
| `054f16eff78722bb812b2e0d04cda1e67d9d8a8d` | Runtime preflight wiring tests |
| `7fdcda0d49fd457b86df750103c2c31850f1ddfe` | Canonical atomic bootstrap implementation |
| `adfff92ed7e4f5abb74a15faf30438d7f779046b` | Canonical bootstrap/idempotency tests |

## Current status — 2026-09-15

### Implemented in code

- Project-72 contracts
- Canonical Subscriber Store abstraction
- deterministic seven-subscriber catalog
- Capability Broker
- Assurance Core
- authoritative Open5GS readback
- postcondition verification
- optimistic concurrency
- durable idempotency reservation and terminal-result persistence
- drift detection
- lifecycle state machine
- Open5GS v2.8.0 pinned bootstrap
- UERANSIM configuration renderer
- mandatory runtime preflight
- canonical bootstrap conflict protection
- IMS/Kamailio/Asterisk security boundary templates
- CI assurance and renderer validation

### Pending host validation

- Ubuntu 22.04 host preflight PASS
- live MongoDB canonical store acceptance
- live Open5GS projection for 7001–7007
- authoritative Open5GS readback on target host
- UERANSIM attach
- UE data-plane/NAT validation
- live IMS registration
- voice/SMS acceptance
- drift/recovery acceptance against running core
- final security/isolation acceptance

### Blocked until external prerequisites exist

- physical RAN transmission
- physical USIM activation
- controlled handset attachment through physical RAN
- public-network/PSTN interconnection without the required lawful operator arrangement

## Next engineering sequence

```text
Gate 4A  Mandatory host preflight             [CODE IMPLEMENTED / HOST PENDING]
   |
Gate 4B  Canonical 7001-7007 bootstrap        [CODE IMPLEMENTED / HOST PENDING]
   |
Gate 4C  UERANSIM deployment configuration    [CODE IMPLEMENTED / HOST PENDING]
   |
Gate 4D  Open5GS projection + readback        [NEXT]
   |
Gate 4E  UERANSIM attach                      [HOST]
   |
Gate 5   IMS/VoLTE/SMS                        [HOST]
   |
Gate 6   Drift/recovery                       [HOST + CI]
   |
Gate 7   Security/isolation                   [HOST]
   |
FINAL    VERIFIED                             [ALL APPLICABLE GATES]
```

## Engineering rule for future work

Every substantive implementation step must update this `README.md` in the same work stream with what changed, why it changed, affected files/components, validation performed, CI result when available, remaining limitations and next gate.

This log is not a claim of live deployment. It is the persistent record of repository engineering progress and acceptance state.
