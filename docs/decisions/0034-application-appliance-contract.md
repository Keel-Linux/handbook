# 0034: The application appliance contract

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-012a).

## Decision

An application appliance is described by a **manifest** that declares:

1. **Runtime overlays:** PHP-FPM, Python, Ruby, Node.js, Go.
2. **The data services it consumes** (0033).
3. **Its replication paths**, `replicate:` and `exclude:` (0032).
4. **Its workers**: stateless, reading a queue and writing to data
   services, never to local disk.

The web tier is always Keel Web (0030). Adding an application is a
manifest plus an application-specific inithook.

## What this amends

- **0010, "The three levels"**: "a recipe would declare the components it
  composes with their versions" is this manifest; the recipe level is now
  defined by it.
- **Brief section 4.2** (the mutable state map): becomes part of the
  manifest.
- **0021**: the monitor's checks come from the spec; for an application,
  the checks are generated from the manifest (0040).
- **0014, section 2**: the backup line waits for a backup service; the
  backup manifest of 0037 is derived from this one.

## Review notes (open points for the maintainer)

- [ ] **The manifest format is not specified, and it is the pivot of
  everything after it.** Backup (0037), monitoring (0040), upgrades
  (0039), directory replication (0032) and discovery (0026) all read it.
  Proposed: **its specification is the first deliverable** of this set of
  decisions, before any of those is built, written as a schema with
  examples for WordPress, Odoo and Mastodon so that the three shapes (PHP
  with one volume, Python with a filestore and workers, Ruby with media
  and Sidekiq) are covered from the start.
