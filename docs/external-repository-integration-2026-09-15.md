# External repository integration — 2026-09-15

The following repositories were audited as implementation sources or infrastructure references for MINI-MOBILE-7:

- `mojealterego/UERANSIM`
- `mojealterego/open5gs_5gc_ueransim_sample_config`
- `mojealterego/open5gs`
- `mojealterego/terraform-provider-mongodb`
- `mojealterego/terraform-aws-mongodb-ec2`
- `mojealterego/End-to-End-Kubernetes-Three-Tier-DevSecOps-Project`

## UERANSIM

The fork is UERANSIM v3.3.0 and explicitly describes the radio interface as simulated over UDP rather than a complete physical NR layer. Its repository contains Open5GS-specific `open5gs-gnb.yaml` and `open5gs-ue.yaml` templates. These are useful upstream/reference material, but MINI-MOBILE-7 keeps deployment-specific UE credentials external and renders seven runtime configurations from the canonical catalog.

The upstream-style sample UE configuration contains authentication material. Those values are not copied into MINI-MOBILE-7. The Project-72 renderer continues to require external secret references and writes runtime configuration with restrictive permissions.

## Open5GS + UERANSIM sample configuration

The sample repository documents a multi-VM Open5GS/UERANSIM simulation with separate control-plane and user-plane nodes, multiple DNNs and multiple UEs. It is useful for topology and troubleshooting patterns, including NG Setup, UE registration, PDU session establishment and packet observation.

Its documented versions are Open5GS v2.7.0 and UERANSIM v3.2.6. MINI-MOBILE-7 deliberately remains pinned to its own baseline: Open5GS v2.8.0 and UERANSIM v3.3.0. The sample is therefore treated as architectural/reference material, not as the project's version authority.

## Open5GS fork

The `open5gs` repository is the Open5GS source tree. MINI-MOBILE-7 uses Open5GS as the telecom projection target, while keeping canonical subscriber state outside the Open5GS database. The Project-72 adapter is responsible for lifecycle projection and authoritative readback.

No direct fork-specific code is required in MINI-MOBILE-7 merely to consume Open5GS. Version pinning and adapter compatibility remain the controlling interfaces.

## Terraform MongoDB provider

The repository is a Terraform provider for MongoDB and includes provider examples and Docker-based development material. Its README also contains local-development credentials such as a sample MongoDB root password. Those values are treated as insecure examples and are not imported into MINI-MOBILE-7.

For Project-72, Terraform may be used as an infrastructure layer, but canonical data mutation remains under the assurance boundary. Infrastructure provisioning must not become an alternative path that bypasses capability authorization, idempotency, expected-version checks, authoritative readback or postconditions.

## Terraform AWS MongoDB EC2

The module provisions MongoDB on AWS EC2 and supports public/private subnet deployment, replication and persistent EBS-backed storage. The documented examples include public addressing and older Ubuntu/MongoDB defaults.

MINI-MOBILE-7 may use this repository as an infrastructure reference only after the module is hardened for the project's baseline. In particular, MongoDB must remain private, credentials must stay external, versions must be explicitly pinned, and the deployment must not expose the canonical or idempotency databases to the public Internet.

The module's own README states that it has no out-of-the-box monitoring support and that dynamic replica-node scaling is not supported. These are known infrastructure limitations, not Project-72 assurance features.

## Kubernetes three-tier DevSecOps repository

The repository demonstrates a React/Node/MongoDB three-tier application deployed on AWS EKS with Jenkins, Terraform, Helm, Prometheus, Grafana and ArgoCD. It is relevant as a CI/CD, GitOps and observability reference.

It is not a telecom-core implementation and is not used as a substitute for Open5GS/UERANSIM runtime controls. If Kubernetes is later introduced for management-plane services, the Project-72 fail-closed invariants must remain at the service boundary and Kubernetes deployment tooling must not be allowed to bypass them.

## Resulting architecture decision

```text
                   INFRASTRUCTURE LAYER
       Terraform / AWS / MongoDB / Kubernetes / CI-CD
                              |
                              v
                    PROJECT-72 CONTROL PLANE
       Capability Broker -> Assurance Core -> Idempotency
                    |              |
                    |              +--> Canonical Subscriber Store
                    |              |
                    |              +--> authoritative readback
                    v
             TELECOM PROJECTIONS / LAB RUNTIMES
             Open5GS ---- UERANSIM ---- IMS

       eSIM artifact boundary is parallel to telecom projection:

       subscriber -> private identity -> eSIM metadata
                                  |
                                  +--> external SM-DP+ secret/ref
                                  +--> LPA activation artifact
                                  +--> QR payload when requested

       GENERATED != INSTALLED != VERIFIED
```

## eSIM boundary

Project-72 now contains a deterministic private identity generator and an eSIM activation-artifact generator.

The eSIM generator can create an LPA activation URI only when a real provisioning system supplies an external matching ID through a secret reference. It does not manufacture a GSMA eSIM profile, impersonate an SM-DP+, install a profile on a handset, or claim handset/device verification.

The generated activation URI is sensitive and is returned only at runtime. The repository stores the secret reference and a SHA-256 digest in the artifact model, not the matching ID.

A future live eSIM gate requires an actual SM-DP+/provisioning service, supported LPA/device, device-side installation evidence and authoritative readback. Only then can eSIM state participate in the Project-72 `VERIFIED` chain.

## Validation boundary

The integration audit does not change the legal RF gate. UERANSIM remains a no-RF simulation environment; physical RAN operation requires appropriate hardware and lawful authorization.
