# Project forum: the first appliance built the Keel way

Decided 2026-09-26 by the maintainer: before rotating the signing subkey,
bring up the project forum on a Keel appliance in LXC and evaluate the whole
chain on it.

## Tool

NodeBB, one tool for both modes a distribution project needs: support
questions (categories with solved marking) and discussion that is not a
question (announcements, design decisions, governance). It also speaks
ActivityPub, which fits a project whose identity is sovereignty, without
being a day-one requirement. Apache Answer was considered: good at the
question mode, weak at the discussion mode, and it would force a second tool.

Runtime on Debian 13, all from the archive: nodejs 20.19 (NodeBB requires 18
or newer), redis-server 8.0, nginx. TurnKey already has `nodejs` and
`nodejs-nginx` plans in common and a redis vertical (brief section 8), so the
appliance is a stack of things that exist.

## Appliance: keel-nodebb

- Served at forum.keellinux.org (decided 2026-09-26, after a short detour via
  the apex): the apex and www.keellinux.org are the institutional site, the
  same content as keel-linux.github.io; the forum name is reverse-proxied by
  nginx on the public services VM to the appliance over IPv6.
- Layers: core, then the nodejs-nginx stack with redis, then the NodeBB
  delta, built with bt-layer on the build host and assembled with keel
  assemble into an LXC template.
- First boot from an instance spec: hostname and domain, static IPv6, ACME
  certificate through the existing dehydrated path, admin user and NodeBB
  secret by reference, IPv6 first everywhere, nginx in front on [::]:443.
- Verification: keel verify on the layers, keel diff after boot (no drift),
  forum reachable over IPv6 with a valid certificate, an account created,
  a post made.
- Packages used: the project's own inithooks, confconsole and keel from the
  build host's incoming pool. For this evaluation instance they come from the
  unsigned staging distribution on the build host itself, never published;
  the signed repository is what the exercise validates next, once the
  subkey is rotated.

## What this evaluates

The build (layers on core), the declarative first boot on a real service,
IPv6 end to end with a certificate, the operator surface (confconsole
Instance menu), and the packaging chain. If any of it fails, it fails before
the key is rotated and before anything is public.
