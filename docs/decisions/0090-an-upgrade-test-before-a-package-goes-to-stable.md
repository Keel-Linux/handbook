# 0090: An upgrade test on each published application before a core package goes to stable

Date: 2026-11-12
Status: **the rule is decided by the maintainer, 2026-11-12.** The
maintainer asked if a new version of a core package can break Odoo or a
later application. The coordinator proposed the rule below. The
maintainer said yes. The test is done by hand today. The automatic test
is not built.

## What was asked

`keel-web` 0.4.4 and `keel-overlay-coraza` 0.1.5 came from the Nextcloud
work. The maintainer asked how the project knows that they do not affect
the other applications: Odoo, an application on Java, an application that
comes later.

## What is true today

- A package goes to `trixie-testing` after its CI passes. A person
  promotes it to `trixie` with `bin/promote`.
- The 0075 commissioning tests each application on new images. It does
  not test an installed node that gets the new package by `apt`.
- An installed node gets a core package from `trixie` at its next
  upgrade. Thus a promotion changes each installed node of each
  application.
- No absolute guarantee is possible. A test on the real platform before
  the promotion is the guarantee that the project can give.

## Decision

### 1. The rule

A core package (0089 item 1) is not promoted to `trixie` before an
upgrade test passes on one node of each published application.

### 2. The upgrade test

For each application that has a published stable image:

1. Make a node from the published stable image. Initialise it in a cloud
   mode, because Coraza and Anubis are in the request path there.
2. Do the checks of the application: the site answers, a login, a write,
   an upload. Each application layer names its checks in its repository.
3. Upgrade the node by `apt` to the candidate version, and to nothing
   else from `trixie-testing`.
4. Do `nginx -t`, then the same checks again.

The promotion goes on only when each check passes after the upgrade. The
results go into an evidence file.

### 3. A security correction

A security correction can go to `trixie` before the test is complete,
with the maintainer's yes. The test then runs immediately after, and a
failure is reported to the maintainer at once.
`keel-overlay-coraza` 0.1.5 went to `trixie` on 2026-11-12 in this way.

### 4. A new application

A new application is published only after its own commissioning (0075)
with the core packages of that day. When it is published, it joins the
list of item 2.

## Follow-up

- Record the first test by hand (Odoo and WordPress, `keel-web` 0.4.4 and
  `keel-overlay-coraza` 0.1.5) as evidence.
- Each application layer gets a file with its upgrade checks.
- Make the test automatic: a job that starts when a core package enters
  `trixie-testing`, and a gate in `bin/promote` that reads its result.
