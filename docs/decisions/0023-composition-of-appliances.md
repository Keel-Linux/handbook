# 0023: Composition of appliances instead of monolithic appliances

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-001 of the
architecture session of that day; the mapping is in
[README.md](README.md)). The first of eighteen notes, 0023 to 0040, that
record that session. Each says which earlier notes it amends.

## Decision

Each service (PostgreSQL, MariaDB, Redis, Nginx) is a first-class
component that can run standalone or be consumed by another appliance.

- **LAMP and LAPP cease to exist as appliances.** The stack becomes LEMP
  (Linux, Nginx, PHP-FPM, a database), and LEMP is a recipe built from
  components, not an image with an identity of its own.
- **Every appliance is also a publishable overlay.** Application
  appliances (WordPress, Odoo, Nextcloud, Mastodon) declare the components
  they consume, in the manifest of 0034.
- **This is a redesign of the build system** (fab, common, buildtasks),
  and it is the change that justifies the fork.

What is shared by two images and what is an appliance is drawn in 0036;
Apache's retirement and the web tier are 0030.

## What this amends

- **0013, "The catalog shape"**: the artefacts `lamp` and `lapp`, with and
  without a local database, and the `apache-php` layer they sit on, are
  superseded. The principle that note set stays: an image is split when
  its content differs, never by topology.
- **0010, "Direction taken"**: the proof of the split was to be LAMP built
  as core plus components. The composition model stands; the proof moves
  to the first application built from a manifest (WordPress on Keel PHP,
  0034 and 0036). Where components live (one repository each in 0010,
  overlays in common in 0036) is settled by 0036.
- **0006, item 2**: `keel-lamp`, `keel-lapp` and `keel-nginx-php-fastcgi`
  stop being appliances to maintain; their names are kept only as the
  history of the organisation.
- **0022** (open, handbook#23): the LNPP stack layer becomes a composition
  (Keel Python, PostgreSQL, Keel Web) rather than a stack image. Odoo on
  it is unchanged by this note.
- **0008**: the fork's divergence from upstream now includes the build
  system's composition model, which that note named as what would make
  offering changes back harder. The reason is stated here, as 0008 asks.

## Resolved (maintainer, 2026-09-30)

- **Apache is retired appliance by appliance.** The WordPress work in
  progress (Templates A and B, keel-wordpress) is built on Apache, on the
  LAMP layer, and is not rewritten now. It migrates to Keel PHP when Keel
  Web (0030) exists; until then the Apache-based images are what gets
  tested and published.
