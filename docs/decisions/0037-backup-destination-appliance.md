# 0037: Backup as a destination appliance

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-014).

## Decision

- **TKLBAM stays as the client**: profile and delta backups, through
  duplicity.
- **New: the Keel Backup appliance**, a storage backend plus a key
  service, installable by anyone as an LXC or a VM.
- **The backup manifest is derived from the composition manifest**
  (0034).
- **A backup destination is never in the same site as its data.** It
  refuses, or in a simple installation warns loudly.
- **Restores are tested periodically** into a throwaway container, and the
  result is reported to etcd.
- **Database backups are taken from the hot standby** (0031).
- **TKLBAM gets a backend abstraction** so that it targets Keel Backup
  instead of the Hub and S3.

It depends on 0038, the object storage it stores into.

## What this amends

- **0002**: TKLBAM remains the last component ported, and the port is now
  defined: a backend abstraction, not a rewrite; the "needs a Keel
  service" rows of docs/hub-inventory.md are answered by Keel Backup.
- **0014, section 2** (open, handbook#6): the login says there is no
  backup service. That note's own condition for change ("a backup service
  in the archive, configured from confconsole") is what this builds; when
  it lands, that section is superseded.
- **0013, problem 5** ("a replica should not be backed up like a
  primary"): answered, the standby is the one backed up.
