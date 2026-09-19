<div align="center">

<img src="./assets/social-preview.svg" alt="MINI-MOBILE-7 — project visual" width="100%">

## MOJEALTEREGO · PROJECT PROFILE

</div>

---

# MINI-MOBILE-7

Private LTE/5G laboratory and private cellular network blueprint for up to 7 controlled devices.

## Scope

This repository contains configuration templates, deployment documentation, security guidance, and lab scaffolding for a small private mobile network.

Target stack:
- Open5GS Core + MongoDB
- UERANSIM for no-RF laboratory validation
- Kamailio IMS for private voice/IMS experiments
- srsRAN or a compatible small-cell RAN for physical testing
- Up to 7 controlled subscriber identities

## Network model

```text
Internet
   |
Firewall / VPN
   |
Open5GS Core
   |
IMS (Kamailio)
   |
LTE / 5G RAN
   |
+--+--+--+--+--+
7 controlled devices
```

## Addressing

| Segment | CIDR | Purpose |
|---|---|---|
| Core | 10.10.0.0/24 | Core services | 
| UE | 10.20.0.0/24 | Subscriber data plane | 
| Management | 10.30.0.0/24 | Administration | 
| IMS | 10.40.0.0/24 | SIP/IMS services | 

Internal test numbers are **7001–7007**. They are internal identifiers, not Polish public +48 mobile numbers.

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

## Repository layout

```text
core/open5gs/          Core configuration templates
ran/lte/                LTE RAN templates
ran/5g/                 5G RAN templates
ims/kamailio/           IMS configuration scaffolding
subscribers/templates/ Subscriber templates without real secrets
network/firewall/       Network security baseline
monitoring/             Monitoring scaffolding
docs/                   Architecture, deployment and legal notes
```

## Deployment stages

1. Repository and security baseline
2. Open5GS + MongoDB
3. UERANSIM lab
4. First subscriber and PDU session
5. Lab Internet/NAT
6. IMS/voice lab
7. SMS lab where supported
8. Seven subscribers
9. Physical USIM preparation
10. Physical RAN after legal gate
11. First controlled handset
12. Seven controlled handsets
13. Monitoring, backups and operations
14. Public telephony only through a lawful operator/MVNO/interconnect arrangement

## Acceptance criteria

The project is complete only when each applicable stage has been tested and documented, secrets remain external, and physical RF deployment has passed the legal and hardware gates.

## Important limitation

This repository can be prepared remotely, including from an Android device, but a real cellular network cannot be truthfully marked as deployed until a suitable Linux host, RAN hardware, USIMs and lawful radio authorization are actually available.
