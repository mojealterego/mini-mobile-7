# Runtime Acceptance — MINI-MOBILE-7

This runbook is the boundary between deterministic CI validation and live controlled-lab validation.

## Gate 4A — host preflight

On the controlled Ubuntu 22.04 host:

```bash
make preflight
```

The gate must pass before any subscriber mutation. It checks Open5GS/MongoDB presence and activity, `ogstun`, UE routing, IPv4 forwarding, firewall policy, Python MongoDB support and all seven external authentication references without printing secret values.

## Gate 4B — canonical catalog

Start with a dry run:

```bash
make provision-seven
```

No mutation is permitted by the default command. Review the proposed seven identities and expected versions.

For an explicitly controlled bootstrap of missing canonical records and activation:

```bash
PYTHONPATH=. python3 scripts/project-72-provision-seven.py --execute --bootstrap-canonical
```

Do not use `--execute` until Gate 4A passes and the operator has confirmed the isolated lab boundary.

## Gate 4C — UERANSIM configuration

Resolve authentication material from the external secret store and render deployment-local UE files:

```bash
make render-ueransim
```

Verify that exactly seven generated files exist and that their permissions are restricted. Generated files remain under `runtime/` and must not be committed.

## Gate 4D — Open5GS projection readback

For each subscriber `7001`–`7007`, require the sequence:

```text
canonical vN
   -> authorized ACTIVATE
   -> Open5GS projection vN+1
   -> authoritative readback
   -> lifecycle postcondition
   -> VERIFIED
```

A projection without authoritative readback is not accepted as `VERIFIED`.

## Gate 4E — UERANSIM attach

Only after the seven projections are verified:

1. Start the Open5GS AMF/SMF/UPF services.
2. Start the UERANSIM gNB using the audited private lab addressing.
3. Attach one UE at a time, beginning with `7001`.
4. Confirm NGAP registration, PDU session establishment and UE address allocation.
5. Perform authoritative readback from the core and compare it with the canonical record.
6. Repeat for `7002`–`7007`.

Use the read-only evidence collector before and after the sequence:

```bash
bash scripts/project-72-host-evidence.sh ./runtime/evidence
```

The collector records host/service/network state and hashes of deployment-local configuration files; it does not print authentication material and does not change the telecom configuration.

No physical RF operation is implied by the UERANSIM test. The current RAN path is software-only.

## Gate 5 — IMS

After stable data-plane operation:

1. Start Kamailio on the private IMS network.
2. Start Asterisk behind the Kamailio boundary.
3. Validate TLS certificate chain and private-key permissions.
4. Validate SRTP negotiation.
5. Register only the seven authorized internal identities.
6. Place an internal test call between two authorized subscribers.
7. Validate SIP signalling, RTP/SRTP media and teardown.
8. Validate MESSAGE/SMS behavior only if the selected UE/core/IMS stack actually supports the required SMS-over-IMS path.

A SIP `200 OK` is not sufficient for Project-72 `VERIFIED`; the IMS state must have an authoritative readback and postcondition.

## Gate 6 — drift and recovery

Intentionally change one controlled Open5GS projection field in the lab, then run readback. Expected result:

```text
projection mismatch -> DRIFT
```

The assurance layer must not silently repair the projection. Repair, if introduced later, must be a separate explicitly authorized operation with its own assurance record.

## Gate 7 — security and isolation

Before acceptance is closed, verify:

- no public MongoDB listener;
- no public Open5GS management API;
- no public SIP listener;
- no public PSTN/PLMN route;
- firewall is fail-closed for management and IMS boundaries;
- no live credentials are present in Git;
- generated UE credentials remain deployment-local;
- logs do not print Ki/OPc/password material;
- physical RF remains disabled unless the separate Polish regulatory/hardware gate is satisfied.

## Final acceptance states

| State | Meaning |
|---|---|
| `PASS-CI` | Deterministic source tests pass in GitHub Actions |
| `PASS-HOST` | Controlled host preflight passes |
| `PASS-CORE` | Seven canonical Open5GS projections are verified |
| `PASS-RAN` | Seven UERANSIM attach/session tests pass |
| `PASS-IMS` | Internal IMS signalling/media acceptance passes |
| `PASS-DRIFT` | Drift is detected and remains fail-closed |
| `PASS-SECURITY` | Isolation/secrets/firewall checks pass |
| `VERIFIED` | All applicable gates pass with authoritative evidence |

A source-only review must never be represented as the final `VERIFIED` deployment state.
