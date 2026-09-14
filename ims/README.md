# MINI-MOBILE-7 IMS boundary

## Architecture

```text
UE / UERANSIM
      |
      | SIP signalling over private IMS network
      v
Kamailio P-CSCF / SIP routing boundary
      |
      | private TLS
      v
Asterisk service/media endpoint
```

Network contract:

- IMS subnet: `10.40.0.0/24`
- Kamailio: deployment-assigned private IMS address
- Asterisk: `10.40.0.20` in the example configuration
- SIP is not exposed to the public Internet.
- No PSTN gateway or public PLMN interconnect is configured.

## Security boundary

- TLS is the signalling baseline for the Asterisk service endpoint.
- SRTP is required by the example endpoint through `media_encryption=sdes`.
- Certificate and private-key material is supplied only at deployment time.
- SIP credentials are external runtime secrets; no live credentials belong in Git.
- Routing to public PSTN/PLMN destinations is disabled by architecture, not merely by documentation.

## Assurance boundary

IMS activation must follow the Project-72 sequence:

```text
Canonical Subscriber Store
        -> Capability Broker
        -> Execution
        -> IMS authoritative readback
        -> Postcondition
        -> VERIFIED
```

A SIP `200 OK` alone is not sufficient for Project-72 `VERIFIED` status.

## Current status

The repository contains deployment templates only. Live Kamailio registration, SIP call establishment, SMS over IMS, TLS certificate validation, SRTP negotiation and UE IMS attachment remain host-level acceptance tests.

The current implementation must not claim VoLTE/IMS operation until those tests have been executed against the controlled Open5GS/UERANSIM runtime.
