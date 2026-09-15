# Monitoring

Project-72 separates **evidence collection** from **metrics exposition**. Metrics must never become an alternate subscriber authority and must not contain authentication material.

## Metrics boundary

`project_72_metrics.py` is a dependency-free, read-only Prometheus text exporter. It consumes an already collected JSON evidence snapshot and emits only bounded labels:

- assurance terminal status;
- total drift classifications;
- subscriber IDs limited to 7001–7007;
- latest subscriber health as a gauge.

It does not query Open5GS, MongoDB, UERANSIM, Kamailio or Asterisk itself. This keeps collection, authorization and observation boundaries separate and makes the exporter deterministic in CI.

Example:

```bash
PYTHONPATH=. python3 monitoring/project_72_metrics.py runtime/evidence/metrics.json > runtime/evidence/metrics.prom
```

The resulting endpoint/file must be exposed only through the management/VPN plane. Do not add IMSI, UE IP, SIP credentials, Ki, OPc, private keys or activation material as metric labels.

## Operational metrics

The host acceptance layer should additionally collect, where the installed stack exposes authoritative values:

- Open5GS service state;
- AMF registration/UE counts;
- SMF PDU session counts;
- UPF packet counters;
- RAN NGAP/S1 connectivity state;
- IMS registration and call-session counters;
- host CPU/RAM/disk;
- interface packet loss/errors;
- database availability;
- Project-72 assurance outcomes and drift counts.

## Minimum operational acceptance

For each controlled subscriber, record:

- registration success;
- PDU session success;
- assigned UE address;
- reachability test;
- IMS registration where enabled;
- internal call test where enabled;
- last successful health-check timestamp.

Operational telemetry is evidence supporting acceptance. It does not by itself create `VERIFIED`.
