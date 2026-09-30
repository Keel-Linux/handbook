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
- **0022** (open, handbook#23): superseded on how Odoo is updated; see
  "Resolved".

## Resolved (maintainer, 2026-09-30)

- **`apt upgrade` is the only update path, Odoo included.** 0022 installs
  Odoo from a git checkout and upgrades it by moving the checkout, with
  Odoo-only Python libraries in a virtual environment. That point of 0022
  is superseded: Odoo from git becomes a **Keel-maintained package**. The
  package is built from the organisation's git mirror at a fixed
  revision, carries the Odoo-only wheels, and its post-install hook runs
  the module update. What 0022 decided about the source (the mirror, the
  series, the OCA layout, Debian's Python first, never pip into the
  system Python) stands; only the delivery changes.

## The first packages this requires (checked 2026-09-30 against the Debian archive and WNPP)

| Piece | Debian | Keel |
| --- | --- | --- |
| Coraza (0030) | no package and no ITP | builds it |
| Anubis (0030) | not in Debian; ITP #1102132, being packaged; upstream publishes a `.deb` (v1.27.0) | builds it |
| Garage (0038) | not in Debian; ITP #1118368, being packaged | builds it |
| CrowdSec (0029) | 1.4.6-10 in trixie, upstream 1.8.1 | trixie's or a current one, an implementation task of 0029 |
| Odoo (0022) | not applicable | builds it from its git mirror |

Anubis and Garage are candidates for Keel to contribute to Debian through
the existing Debian packaging effort (tracker#15), coordinating with the
owners of their ITPs.
