# IMS external reference audit — 2026-09-15

This document records how three externally supplied repositories are used as references for MINI-MOBILE-7 IMS/voice work. They are reference sources, not version or security authorities for the project.

## 1. `mojealterego/pjproject-archive`

The repository is a PJSIP/PJMEDIA source archive. Its top-level README is an old PJSIP/PJMEDIA getting-started document whose own header dates the document to 2007. It describes the classic `./configure`, `make dep`, `make clean`, `make` build flow and the `pjsua` application.

### Decision

**ADAPT AS HISTORICAL PJSIP REFERENCE. DO NOT IMPORT AS THE MINI-MOBILE-7 IMS BASELINE.**

Reasons:
- the archive is not a pinned contemporary IMS implementation for this project;
- MINI-MOBILE-7 already uses Asterisk/PJSIP only as a controlled application/media endpoint behind the private IMS boundary;
- the Project-72 assurance layer must own subscriber authorization and lifecycle state instead of allowing a SIP client stack to become a second subscriber authority.

The archive may be consulted for PJSIP transport/API behavior when implementing or validating a narrow integration, but no source tree copy or unpinned dependency is introduced into the project.

## 2. `mojealterego/Pixel-turn-on-5G-Volte-and-automatically-register-with-IMS`

The supplied repository is a Magisk module for Pixel devices. Its service script waits for Android boot completion, reads the detected operator, applies vendor/debug properties intended to enable VoLTE/IMS, restarts `vendor.imsd` and `ril-daemon`, and checks `dumpsys telephony.registry` for an IMS registration indication. Its `system.prop` likewise sets VoLTE/IMS-related Android properties.

### Decision

**ADAPT THE OBSERVABILITY/DEVICE-VALIDATION IDEA; REJECT THE OPERATOR-SPECIFIC FORCE-PROPERTY METHOD FOR MINI-MOBILE-7.**

The useful concept is a device-side acceptance gate: configuration change -> IMS service restart/recovery -> authoritative device-side registration observation. The Project-72 implementation must not treat a property such as `persist.radio.imsregistered=1` as proof of registration. A claimed property is not authoritative network evidence.

For MINI-MOBILE-7, a future Android acceptance collector should instead capture actual device/network state (for example IMS registration state exposed by the supported Android diagnostics interface) and correlate it with the canonical subscriber and IMS identity. The result must remain `VERIFIED` only after authoritative readback and postcondition checks.

The operator-specific China Mobile/Unicom/Telecom branches and vendor debug overrides are not copied into the private Polish lab configuration. They are carrier/device-specific and are not a portable Open5GS IMS control plane.

## 3. `selvakn/gsm-sip-bridge`

The repository is a substantial Rust GSM-to-SIP bridge supporting circuit-switched GSM, carrier VoWiFi/ePDG and host-side VoLTE. Its documented architecture separates carrier-facing IMS handling from the SIP side. It also contains PJSIP bindings for the SIP/media side, TLS configuration, recovery/watchdog behavior, Prometheus metrics and a local control interface.

The project explicitly documents that VoWiFi/VoLTE paths are opt-in and that outbound calling is disabled by default. Its configuration supports environment-backed SIP passwords and strict configuration parsing. The project also documents that its Docker quick-start uses privileged/host-network operation for modem/ALSA/SIP media access; those deployment choices are not suitable as defaults for MINI-MOBILE-7.

### Decision

**ADAPT SELECTED ENGINEERING PATTERNS; REJECT THE CARRIER-GATEWAY ROLE FOR THE PRIVATE CORE.**

Adaptable patterns:
- explicit SIP transport selection and TLS verification;
- strict configuration parsing;
- separation between carrier-facing signaling and SIP/media processing;
- bounded recovery and watchdog behavior;
- non-blocking observability/Prometheus metrics;
- control-plane operations separated from call/media processing.

Rejected for the MINI-MOBILE-7 core:
- carrier-facing VoWiFi/ePDG and host-side carrier VoLTE as the private IMS architecture;
- automatic outbound cellular dialing or public-number routing;
- privileged/host-network containers as a generic deployment baseline;
- any topology that creates an uncontrolled PSTN/PLMN exit;
- using the bridge's local database as the canonical subscriber store.

The bridge is therefore an **external interoperability/reference implementation**, not a replacement for Kamailio + Asterisk inside the Project-72 private IMS boundary.

## Resulting MINI-MOBILE-7 IMS architecture

```text
Canonical Subscriber Store
          |
          v
Capability Broker
          |
          v
Assurance Core
          |
          +--------------------+
          |                    |
          v                    v
Open5GS projection      IMS authorization/config
                              |
                              v
                    Kamailio private proxy
                              |
                              v
                    Asterisk/PJSIP endpoint
                              |
                         RTP/SRTP media
                              |
                     7001 ... 7007 only
```

The external repositories inform implementation details, but they do not alter the Project-72 invariants:

- canonical subscriber state remains the sole source of truth;
- authorization is fail-closed;
- mutations are idempotent and version-checked;
- `EXECUTED` is not `VERIFIED`;
- IMS registration/call acceptance requires authoritative runtime evidence;
- no public PSTN/PLMN exit is enabled by default;
- physical RF remains behind the Polish/UKE legal and hardware gate.

## Acceptance consequences

Before claiming live IMS completion, Gate 5 must demonstrate on the actual host:

1. Kamailio and Asterisk are running with the expected private bindings.
2. TLS certificate/CA validation succeeds for the configured IMS transport.
3. A controlled subscriber is authorized by the canonical store.
4. The subscriber registers from the intended private IMS/RAN path.
5. Authoritative readback confirms the registration identity and expected subscriber state.
6. A controlled internal call between authorized identities completes with expected SIP signaling and media security.
7. No public PSTN/PLMN route is available.
8. Evidence is captured without collecting private authentication material.

A device property, source-code review, or successful CI test alone cannot satisfy these gates.
