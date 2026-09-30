# 0039: Upgrades come from the Keel repository

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-016).

## Decision

- **Everything Keel installs is a `.deb` in the Keel repository**, the
  overlays included. `apt upgrade` is the only update mechanism.
- **Application packages carry a post-install migration hook**: Odoo's
  module update, Mastodon's `db:migrate`.
- **Upgrades are ordered across the mesh.** A database primary never
  upgrades while it is primary: it hands over to the standby, upgrades,
  and takes the role back after catching up (0031).
- **Two tracks, stable and testing**, declared in the YAML (0027). A
  simple installation defaults to stable, with unattended upgrades for
  security only.
- **The YAML is re-emitted after every upgrade.**

## What this amends

- **0016**: its `stable` and `testing` channels for layers and these
  tracks for packages carry the same two names on purpose; 0016's rule
  that a third channel is a decision applies to tracks too.
- **0012**: the dated pool and pinning are how the Keel repository is
  built; unchanged.
- **0020, "Order"**: "upgrade a replica, promote, upgrade the old primary"
  becomes the handover above, with automatic return after catch-up.
- **0022** (open, handbook#23): see the review note.

## Review notes (open points for the maintainer)

- [ ] **0022 installs Odoo from a git checkout and upgrades it by moving
  the checkout**, with Odoo-only Python libraries in a virtual
  environment. This note makes `apt upgrade` the only update mechanism.
  Either the checkout's revision and the wheels are wrapped in a `.deb`
  whose post-install hook runs the update, or 0022 is amended. To settle
  before Odoo is built from a manifest.
- [ ] Anubis, Coraza, Garage and a current CrowdSec (0029, 0030, 0038) are
  the first packages this note requires Keel to build.
