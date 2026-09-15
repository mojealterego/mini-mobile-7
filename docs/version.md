# Version Baseline

Last verified: 2026-09-14

## Core

- Open5GS: **v2.8.0** — pinned to the official source tag.
- MongoDB: **8.0** package line, matching the current Open5GS Ubuntu guidance.

## RAN / simulation

- UERANSIM: **v3.3.0** — use the tagged release rather than an unpinned development checkout.

## Deployment policy

1. Pin component versions for each deployment.
2. Verify upstream release notes before upgrading.
3. Do not replace a pinned version with a floating `latest` reference without a deliberate compatibility test.
4. Record any version change in this file and in the deployment commit.
5. The Ubuntu bootstrap builds Open5GS from the exact `v2.8.0` source tag; it no longer installs from the floating `ppa:open5gs/latest` channel.

## Verification reference

Open5GS v2.8.0 is an official upstream release dated 2026-06-20. The official build documentation describes source compilation with Meson/Ninja and Ubuntu 22.04 MongoDB 8.0 package setup.

- Open5GS v2.8.0 release: https://open5gs.org/open5gs/release/2026/06/20/release-v2.8.0.html
- Open5GS build guide: https://open5gs.org/open5gs/docs/guide/02-building-open5gs-from-sources/
- Open5GS documentation: https://open5gs.org/open5gs/docs/
- UERANSIM releases: https://github.com/aligungr/UERANSIM/releases
