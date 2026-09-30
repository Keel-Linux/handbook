# 0035: Mastodon as the reference appliance

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-012).

## Decision

Mastodon validates the composition model. PostgreSQL, Redis and Nginx come
from the mesh; Rails and Sidekiq are what is specific to it. A TurnKey
Mastodon appliance exists and is ported.

## What this amends

- **tracker#20** (which appliances next): Mastodon is placed by this
  decision, as the reference proof, rather than by the ranking of usage
  signals.
- **0006, item 2**: `keel-mastodon` was already named as a future
  appliance; it now has a role.

## Resolved (maintainer, 2026-09-30)

- **Mastodon remains the reference appliance.** It is the heaviest
  application of the set (Ruby, Node.js for its assets and streaming,
  PostgreSQL, Redis, Sidekiq, and usually object storage for media and a
  search engine), which is why it is the proof of the composition model.
  The roadmap builds it last in its phase, after WordPress, Odoo and
  Nextcloud have been built from manifests; that is an order of work, not
  a change of reference.
