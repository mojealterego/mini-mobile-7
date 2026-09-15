# MINI-MOBILE-7 Implementation Checklist

Last reviewed: 2026-09-16

## Gate 0 — repository and security

- [x] GitHub repository exists; current repository visibility is **public**.
- [x] Secret-handling policy documented.
- [x] `.env` excluded from Git.
- [x] No Ki/OP/OPc/API keys/private keys stored in repository.
- [x] Component versions pinned in `docs/version.md`.
- [x] Project-72 source-level security/isolation gate passes in CI.

## Gate 1 — runtime host

- [ ] Compliant Ubuntu 22.04 host provisioned.
- [ ] SSH access works from the administration device.
- [ ] `make runtime-capabilities` reports no hard runtime blocks.
- [ ] `make preflight` returns no missing prerequisites.
- [ ] MongoDB starts automatically and is reachable through the intended local/runtime path.
- [ ] Open5GS v2.8.0 installed and service supervision is operational.
- [ ] `ogstun` exists and uses the documented UE network.
- [ ] IPv4 forwarding enabled and readable.
- [ ] Required firewall policy is inspectable and matches the lab boundary.

**Current evidence:** the available Android/Termux `proot-distro` Ubuntu 22.04 userland is not a compliant live runtime host. It lacks systemd and required kernel/network capabilities, so the runtime gates correctly remain fail-closed.

## Gate 2 — Open5GS core / canonical authority

- [x] Project-72 contracts define subscriber, capability, execution, readback, postcondition and assurance-result records.
- [x] Canonical Subscriber Store implements deterministic seven-subscriber catalog and optimistic concurrency.
- [x] Capability Broker is fail-closed for authorization, scope, target, version, capability and risk checks.
- [x] Assurance Core requires authorization -> execution -> authoritative readback -> postcondition before `VERIFIED`.
- [x] Durable idempotency reservation prevents unsafe duplicate side effects and fails closed after uncertain interruption.
- [x] Drift detection classifies authoritative projection mismatches; no automatic repair.
- [ ] AMF/required 5GC network functions start without persistent errors on the actual runtime host.
- [ ] Subscriber database is reachable only from intended management/core paths.
- [ ] PLMN/TAC/S-NSSAI values match the selected lab mode on the actual runtime.
- [ ] One synthetic subscriber is provisioned through the runtime assurance path.
- [ ] Authentication succeeds in the software-only lab.

## Gate 3 — UERANSIM software lab

- [x] UERANSIM v3.3.0 source build path is pinned and renderer tests are covered in CI.
- [x] gNB configuration template matches the Project-72 lab addressing contract.
- [x] Seven UE configuration renderer uses external authentication references and 0600 runtime files.
- [x] ARM64 UERANSIM build completed successfully in the development environment; upstream test suite reported 59/59 passing.
- [ ] gNB starts against the actual Open5GS runtime.
- [ ] UE registration succeeds.
- [ ] PDU session establishes.
- [ ] UE receives the expected address from the configured pool.
- [ ] Controlled UE-to-WAN connectivity works.

## Gate 4 — seven controlled subscribers

- [x] Deterministic subscriber catalog covers 7001–7007.
- [x] Seven private identity records are generated deterministically outside runtime secret material.
- [x] Seven-subscriber lifecycle and wrong-version denial are covered by tests.
- [x] Runtime provisioner performs a preflight gate before mutation and requires durable idempotency storage for `--execute`.
- [ ] Seven subscriber records are provisioned on the actual MongoDB/Open5GS runtime.
- [ ] Each UE receives a unique authoritative address/session.
- [ ] No subscriber can access management interfaces outside the intended policy.

## Gate 5 — IMS / voice

- [x] Private IMS addressing and static safety boundary are defined.
- [x] Kamailio REGISTER routing is scoped to the private IMS network.
- [x] Asterisk/PJSIP renderer produces seven private TLS endpoints with external credentials and 0600 runtime output.
- [x] IMS static safety gate passes in CI.
- [ ] Kamailio configuration deployed on the actual host.
- [ ] SIP registration succeeds in the lab.
- [ ] TLS/SRTP voice path tested before physical RF.

## Gate 6 — physical radio

- [ ] Compatible RAN hardware selected.
- [ ] Compatible USIMs obtained and provisioned securely.
- [ ] Current Polish radio authorization/frequency conditions verified with UKE.
- [ ] RF configuration approved for the selected deployment.
- [ ] First physical handset tested.
- [ ] Only after successful first handset: expand to seven devices.

## Gate 7 — production-like hardening

- [ ] Management access restricted through VPN/firewall.
- [x] Backup/recovery procedure is implemented with separate canonical/idempotency/eSIM metadata domains, restricted artifacts and checksums.
- [ ] Backup restore test executed against an isolated MongoDB target.
- [x] Dependency-free bounded metrics exporter implemented and tested in CI.
- [ ] Monitoring and alerting enabled on the actual host.
- [ ] Configuration and software versions recorded from the actual deployment.
- [ ] Public numbering/interconnect remains disabled unless a lawful operator/MVNO arrangement exists.

## Project-72 runtime acceptance sequence

1. `make runtime-capabilities`
2. `make preflight`
3. `make provision-seven` (dry-run first)
4. Execute provisioning only after all runtime gates pass and durable idempotency storage is configured.
5. Collect `make host-evidence`.
6. Attach UERANSIM UEs one at a time and record authoritative Open5GS readback.
7. Validate lifecycle transitions and drift/fail-closed behavior.
8. Proceed to IMS live validation.
9. Physical RAN acceptance is a separate gate and requires the applicable Polish regulatory/hardware conditions.

## Acceptance rule

A gate is not marked complete because configuration files exist. It is complete only after the corresponding runtime test has passed on the actual deployment host and, where applicable, the physical radio environment. CI proves deterministic source-level behavior; it does not prove live Open5GS, UE attachment, IMS calls or physical RF operation.
