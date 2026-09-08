# Repository Research — 2026-09-09

## Purpose

This document records the technical assessment of external repositories reviewed for MINI-MOBILE-7. The goal is to identify reusable architecture patterns, not to copy unrelated projects wholesale.

## Decisions

| Repository | Area | Decision | Rationale |
|---|---|---|---|
| mishakorzik/VirtualPhoneNumber | Public/free virtual-number directory | REFERENCE ONLY | Provides a directory of public/free SMS number sites. Not suitable as a controlled private-network numbering layer. Source is Apache-2.0. |
| tjlytle/SMSProxy | SMS proxy/routing | REFERENCE | Useful conceptual pattern for routing inbound SMS from one public-facing number toward controlled destinations. Old PHP code; do not adopt as production core. |
| di2pra/twilio-virtual-phone | Twilio voice/SMS application | REFERENCE / OPTIONAL GATEWAY | Useful application-level pattern for provisioning and handling SMS/voice via a CPaaS provider, with PostgreSQL + Redis + environment-based secrets. Too old to become the core telecom stack. |
| GrizzlySMS-Git/grizzly-sms-mcp | SMS API + MCP | OPTIONAL ADAPTER | Strong pattern for an MCP adapter around an external SMS provider. Do not use verification-number rental as the numbering authority for MINI-MOBILE-7. |
| alvaromendoza1882/TempSMS | Temporary/disposable numbers | EXCLUDE FROM CORE | Disposable-number service does not model ownership/control of our private subscribers. |
| Kourva/OnlineSimBot | OnlineSim virtual numbers + Telegram bot | EXCLUDE FROM CORE | External virtual-number marketplace/bot workflow, not a private LTE/5G subscriber system. |
| azzamasghar1/ion-intl-tel-input | International phone-number UI | ADOPT PATTERN | Useful UX component idea for E.164 parsing/validation and country selection. Use a maintained current library in our own UI rather than importing the old repository wholesale. |
| terraform-ibm-modules/terraform-ibm-landing-zone-vsi | Cloud VM infrastructure | REFERENCE / OPTIONAL | Good IaC patterns: repeatable VM creation, networks, security groups, storage, reserved IPs, load balancers, explicit module version pinning. Vendor-specific; only use if IBM Cloud is selected. |
| igrishaev/virtuoso | Java virtual threads | EXCLUDE | Unrelated to mobile-network architecture; only potentially useful to a future JVM control-plane service. |
| mojealterego/virtual-phone | Virtual number forwarding | REFERENCE ONLY | Fork of an old 2013 Ruby/Twilio/Tropo project. Architecture is conceptually relevant to number provisioning/forwarding but technically obsolete. |
| mojealterego/eSim | FOSSEE eSim electronics CAD/simulation | EXCLUDE | This is electronic-circuit simulation, not cellular eSIM. Avoid name collision. |
| coetaur0/ESIM | NLP model | EXCLUDE | ESIM here means Enhanced Sequential Inference Model, not cellular eSIM. |
| Silentely/eSIM-Tools | eSIM transfer/conversion web tooling | REFERENCE / UI | Interesting automation/PWA/security patterns for eSIM workflows, but it targets existing Giffgaff/Simyo consumer accounts, not private-network profile issuance. License is mixed in the repository; check individual files before reuse. |
| frg-fossee/eSim-Cloud | Circuit simulation cloud | EXCLUDE | Electronics simulation platform, not cellular eSIM. |
| alibaba/esim-response-selection | NLP response selection | EXCLUDE | ESIM is an NLP architecture, not SIM/eSIM technology. |
| mojealterego/NekokoLPA | Android/iOS LPA | HIGH PRIORITY | Most directly relevant repository. Provides an open-source Android/iOS LPA architecture with device adapters, LPA domain layer, native bridges, QR support, data stores, and multi-platform structure. Current fork states NekokoLPA 2 adds Telephony API + OMAPI and desktop support, with open-source release planned later in 2026. Use as architectural reference; preserve upstream license notices and review upstream changes before incorporating code. |
| esimfreeorg/free-esim | Consumer/global eSIM distribution | REFERENCE ONLY | Useful as a model for QR-based activation, web UX and provisioning presentation. Not a substitute for our SM-DP+/SM-DS/operator-side eSIM infrastructure. |

## Recommended MINI-MOBILE-7 Architecture Additions

### 1. Subscriber & numbering control plane

Keep numbering authoritative inside our own subscriber database and Open5GS provisioning workflow. Internal test identities remain distinct from public +48 numbering.

Suggested logical entities:

- subscriber
- supi/imsi
- msisdn (only when legitimately assigned)
- iccid
- eid (when eSIM is used)
- profile state
- service state
- SMS route
- voice route
- device binding
- audit events

### 2. SMS abstraction layer

Add an internal provider-neutral SMS interface with adapters:

- `local-ims-sms` — future private-network SMS path
- `twilio` — optional external CPaaS interconnect
- `generic-http-sms` — future provider adapter
- `mcp-provider` — optional AI/MCP facade for operations, never the underlying telecom authority

The internal contract should support:

- send
- receive/webhook
- delivery status
- message correlation
- idempotency
- retry policy
- audit event

Do not make Grizzly/OnlineSim/TempSMS a dependency of the private core.

### 3. eSIM/LPA layer

Create a mobile-device-facing `esim` domain separated from the cellular core:

```text
mobile app / LPA
        |
        v
provisioning API
        |
        +--> profile/order database
        |
        +--> SM-DP+ / eSIM provider adapter
        |
        +--> QR / activation-code generator
        |
        +--> audit + lifecycle state machine
```

The app must not embed long-term operator secrets. Profile provisioning belongs behind a controlled backend.

### 4. Phone-number UX

For an administrative UI, support:

- E.164 parsing and formatting
- country selector
- validation
- display normalization
- internal extension/short-number mode (e.g. 7001–7007)
- clear distinction between internal identities and public MSISDNs

### 5. Infrastructure automation

Keep the current single-host lab path, but prepare an IaC boundary so the same stack can be reproduced on a VPS/cloud VM later.

The IBM landing-zone module demonstrates patterns worth preserving generally:

- explicit version pinning
- repeatable server creation
- network/security-group separation
- reserved IP handling
- storage lifecycle
- optional load balancing

Do not bind MINI-MOBILE-7 to IBM Cloud unless selected later.

## Priority Matrix

| Priority | Component | Action |
|---|---|---|
| P0 | Open5GS + UERANSIM | Remain core lab stack |
| P0 | Internal subscriber DB model | Add explicit eSIM/numbering/SMS fields |
| P0 | Security boundary | Keep USIM/eSIM/operator secrets outside Git |
| P1 | NekokoLPA architecture | Use as reference for future Android/iOS LPA client |
| P1 | SMS abstraction | Design provider-neutral interface |
| P1 | Phone-number input/validation | Add modern maintained library/pattern |
| P2 | Twilio adapter | Optional external voice/SMS gateway |
| P2 | Cloud IaC | Add provider-neutral deployment interface |
| P3 | MCP SMS adapter | Optional operations interface; not telecom core |
| EXCLUDE | TempSMS / OnlineSim / free public numbers | Do not use as subscriber authority |
| EXCLUDE | NLP/electronics projects named ESIM | Not cellular eSIM |

## Licensing Notes

This file records architecture decisions only. Before copying source code from any external repository, verify the repository license and preserve required notices. In particular, `mojealterego/eSim` and `mojealterego/NekokoLPA` are user-owned forks and must still be checked against their upstream license obligations.

## Security Boundary

Never place the following into this repository:

- Ki
- OP / OPc
- SQN
- eSIM activation secrets
- SM-DP+ credentials
- Twilio/API provider secrets
- SIP passwords
- VPN/SSH private keys
- database credentials
- private webhook signing secrets

External services such as Twilio, Grizzly SMS, OnlineSim or public temporary-number sites must be treated as untrusted external dependencies and isolated behind explicit adapters.
