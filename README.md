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
make ims-config-check
```

`make ims-config-check` is a static safety gate. It does not prove live SIP registration, TLS certificate validation, SRTP negotiation or calls.

## Project-72 implementation log

Substantive Project-72 implementation work is recorded in `docs/project-72-session-log-2026-09-15.md` and `docs/project-status.md`. The current codebase includes the canonical subscriber store, fail-closed Capability Broker, Assurance Core, optimistic concurrency, durable idempotency, Open5GS v2.8.0 projection/readback, seven-UE UERANSIM rendering, runtime preflight/dry-run boundaries, host evidence collection, private identity generation and a controlled eSIM activation-artifact boundary.

The private IMS boundary now includes explicit Kamailio REGISTER routing, a deployment-time seven-subscriber Asterisk/PJSIP renderer and a static IMS safety gate covering private binds, TLS/SRTP requirements, external credentials and absence of an active public-telephony route.

The latest external IMS reference audit covers `mojealterego/pjproject-archive`, `mojealterego/Pixel-turn-on-5G-Volte-and-automatically-register-with-IMS` and `selvakn/gsm-sip-bridge`. The audit is documented in `docs/ims-external-reference-2026-09-15.md`. These repositories are used selectively as reference material; they do not replace Project-72 authorization, canonical state, Open5GS version pinning, or authoritative readback.

Latest previously confirmed Project-72 CI: workflow run #236 completed successfully for commit `48cf0904165e7a26f4199c08e1b7dc474ff35a09`. A new workflow was triggered after the IMS/CI changes and must complete before the latest HEAD is marked CI-verified.

### Current limitations

CI and source-level tests do not prove a live telecom deployment. Still pending are the actual MongoDB/Open5GS host acceptance, seven live UERANSIM attaches and PDU sessions, UE Internet validation, live Kamailio/Asterisk TLS/SRTP registration and internal calls, operational drift/security evidence, real SM-DP+ eSIM provisioning and device readback, and physical RAN/handset validation.

`GENERATED`, `INSTALLED` and `VERIFIED` remain distinct eSIM states. No source-only result is treated as physical or device verification.
