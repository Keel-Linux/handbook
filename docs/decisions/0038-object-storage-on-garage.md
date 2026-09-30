# 0038: Object storage appliance on Garage

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-015).

## Decision

- **Object storage is an appliance on Garage**, delivered as an `s3`
  overlay in common.
- **Garage over MinIO:** it is designed for geo-distributed nodes on
  unequal links, it is one small binary, its zones map to the etcd site
  label (replication factor 3 across three zones), and it is AGPL without
  a commercial edition.
- **Object storage is the recommended home** for media, attachments and
  backups. File replication (0032) shrinks to what applications insist on
  keeping on a filesystem.
- **Garage nodes announce themselves in etcd** (0025).

## What this amends

- **0002, "Consequences"**: the `s3-endpoint-url` option for duplicity
  gets its target.
- **0032**: fewer paths to replicate by file.
- **0013's sovereignty claim**: Garage is not in Debian 13 (see the review
  note), so it ships as a Keel package.

## Review notes (open points for the maintainer)

- [ ] **Garage is absent from Debian 13**, measured with `apt-cache
  policy` on this Debian 13.7 machine, 2026-09-30. It needs a Keel package
  built from source into the Keel repository under 0039.
