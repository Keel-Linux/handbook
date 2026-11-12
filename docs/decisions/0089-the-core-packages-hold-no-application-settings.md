# 0089: The core packages hold no application settings

Date: 2026-11-12
Status: **the rule is decided by the maintainer, 2026-11-12.** The
maintainer asked how long new applications will continue to write into
the core layers. The coordinator proposed the rule below and a check in
the CI. The maintainer said yes to the two. The check is not built.

## What was asked

Each application has its own files, its own database, its own routes, and
its own way to keep them the same on two nodes. Odoo is not Nextcloud.
The maintainer asked: the settings that tell Coraza, Anubis, Syncthing
and the database how to react for one application must be in the layer of
that application, not in the core packages. How much will new
applications continue to change the core?

## What is true today

Read in the repositories on 2026-11-12.

- `keel-overlay-coraza` (`Keel-Linux/common`, `packages/coraza`) names no
  application in a line that nginx or Coraza reads. One comment in
  `keel-rules.conf` names an application.
- `keel-web` names applications only in comments (five files).
- The Nextcloud layer (`Keel-Linux/keel-nextcloud`) holds its own
  settings in files that the core only reads:
  - `/etc/coreruleset/plugins/keel-nextcloud-before.conf`, the Coraza
    exclusions;
  - `/etc/nginx/keel-front.d/`, `keel-default.d/` and `keel-static.d/`,
    one file in each, the routes and the paths that go past Anubis;
  - `/usr/share/keel/appliances/nextcloud.yaml`, the database, the paths
    that Syncthing copies, and the pair mode;
  - the gate that opens the site on the writer only (0087).
- The Nextcloud work changed two core packages. The two changes are not
  Nextcloud settings:
  - `keel-overlay-coraza` 0.1.5 corrects a defect of the core. A body
    with no Content-Type was inspected up to the global limit. Each
    application in a cloud mode had the defect.
  - `keel-web` 0.4.4 adds an extension point: a variable with the scheme
    of the client behind Anubis. Each application can use it. The value
    and the use are in the layer of the application.

## Decision

### 1. The rule

A core package holds no setting of one application. The core packages
are `keel`, `keel-web`, the overlays (`keel-overlay-coraza`,
`keel-overlay-anubis`, and each later overlay), and the base layers
`core`, `web`, `lnmp`, `lnpp` and the database layers.

These are settings of one application, and they go in the layer of that
application:

- a route, a path past Anubis, a static path;
- an exclusion or a limit of the web application firewall;
- a path that Syncthing copies;
- a database name, a database parameter, a schema;
- a rule that says which node serves.

### 2. When an application can change the core

A new application can cause a change in a core package in two cases only.

1. The application shows a defect of the core. The correction is for each
   application.
2. An extension point is missing. The core gets a general extension
   point (a directory of files that the core reads, a variable, a field
   of the appliance declaration). The text of the change names no
   application, and a second application can use the point with no
   change in the core.

The pull request that changes the core says which of the two cases
applies.

### 3. The check in the CI

The CI of each core package fails when a line that is not a comment
contains the name of an application. The list of names is one file in
the repository. Each new application layer adds its name to the list.
A comment can name an application, because a comment that says where a
measurement was made is useful.

## What this does not decide

- It does not move a setting that is in the correct place today.
- It does not say that the core is complete. A new type of application
  (Java, Node.js) can show a missing extension point. The expectation is
  that such changes become fewer with each application.
- CrowdSec is not examined in this note.

## Follow-up

- Build the check of item 3 in `Keel-Linux/common` and
  `Keel-Linux/keel-web`.
- Read the Odoo, WordPress and Laravel layers against item 1 and record
  each setting that is in the wrong place.
