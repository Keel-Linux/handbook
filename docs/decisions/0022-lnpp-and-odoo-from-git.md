# 0022: An LNPP stack, and Odoo installed and upgraded from git

Date: 2026-09-30
Status: **proposed**. The direction was set by the maintainer on
2026-09-30 and is listed under "Decided"; the questions at the end are
open.

## What was asked for

A stable release, tested at length on real applications, Odoo and
WordPress first. That needs the stacks under them stable (LAMP for
WordPress, LAPP and PostgreSQL for Odoo), and the maintainer asked for a
stack of its own for Odoo, faster than Apache in front of it: **LNPP**,
Linux, Nginx, PostgreSQL and Python. And Odoo itself installed the way
its community installs it: a git checkout of the source, upgraded with
git.

## Decided 2026-09-30

- **A stable release only after LAMP and LAPP are stable**, and after
  Odoo and WordPress have been tested on them at length. How long the
  release candidate is observed before `stable` is the maintainer's call,
  made at the time.
- **An LNPP stack layer:** nginx as the front, PostgreSQL local or remote
  (0013), Python from Debian. Odoo is its first application.
- **Odoo from git, not from a package.** Installed as a checkout of the
  source at a fixed revision, and upgraded by moving that checkout, which
  is what the Odoo community does. Not Odoo's apt repository.

## Why a new stack, and why this one

The brief (section 3) says to start from the stacks that exist and not to
invent new ones in the first milestone. That milestone is behind us, and
the brief's own tier-1 catalogue names Odoo, whose TurnKey appliance sits
on nothing Keel has: it is a Python application on PostgreSQL, and the
LAPP stack is Apache and PHP. The three parts section 10 asks for:

1. **Why what exists does not work.** LAPP carries Apache and PHP, which
   Odoo does not use, and an Apache in front of Odoo's own HTTP server
   adds a hop and a second configuration without adding anything nginx
   does not do better for a long-polling Python application.
2. **Whether it could be made to.** LAPP without PHP and with Apache as
   a proxy would be a different stack under the same name, which is
   worse than a new one.
3. **Why the new one is better.** nginx is what Odoo's own deployment
   documentation puts in front of it, it serves the static files and the
   websocket route without Python, and the layer is small: nginx, the
   PostgreSQL unit that already exists (decision 0010), and Debian's
   Python.

## Where the pieces come from

Sovereignty (decision 0013): an image nobody can rebuild from our own
sources should not ship. So:

| Piece | Source | Why |
| --- | --- | --- |
| Odoo | a git mirror in the organisation, `Keel-Linux/odoo`, of `github.com/odoo/odoo`, checked out at a fixed revision (a tag or a commit of the stable series) | the build and every appliance can be rebuilt from our own copy; upgrading is `git fetch` and a new revision, as the community does |
| Python libraries | Debian 13's `python3-*` packages | Odoo's own Debian packaging depends on exactly these; measured on trixie, everything Odoo needs is in the archive (`pypdf` replaces the old `PyPDF2`; `python3-zxcvbn` comes from the official trixie backports). No pip, no PyPI |
| nginx, PostgreSQL 17 | Debian 13 | as every other layer |
| **wkhtmltopdf** | **absent from Debian 13** | see "The hard part" |

## The hard part: PDF reports

Odoo renders every PDF report (invoices, quotations, delivery slips)
through `wkhtmltopdf`, and needs the build with the patched Qt for
headers and footers. Debian 13 no longer ships it, the upstream project
was archived in 2023, and the builds the community installs
(`wkhtmltox` from the project's old packaging repository) are a third
party's binary that receives no security fixes. None of the options is
free:

| Option | Cost |
| --- | --- |
| Build wkhtmltopdf with its patched Qt ourselves, into our archive | a large, old C++ build to own and patch alone |
| Take the upstream `wkhtmltox` binary into our archive, pinned, with the gap stated | fast; a known unmaintained binary on an internet-facing machine |
| Run it isolated (its own unprivileged user, no network, a systemd sandbox), whichever binary | reduces the exposure, not the maintenance |
| Wait for Odoo's own replacement, if its current series has one | depends on Odoo, not on us |

This note proposes the second and third together for the first release,
stated plainly in the appliance's documentation, with the first as the
work that follows if Odoo keeps depending on it.

## What the appliance does, and what apply converges

- Odoo runs as its own system user, under systemd, from
  `/opt/odoo/<series>` (the checkout) with its configuration in
  `/etc/odoo/odoo.conf` and its filestore in `/var/lib/odoo`, the mutable
  state brief 4.2 maps and decision 0020 later replicates.
- The spec gains an `odoo` section only where Keel converges something:
  the database endpoint (local or remote, 0013 phase 1), the workers, the
  admin password as a secret reference, the revision. Moving the
  revision is the orchestrated upgrade of milestone M3, not a plain
  apply: a minor revision is `git fetch`, a new checkout and
  `odoo -u all` with a backup first; a major version needs OpenUpgrade
  (brief section 9), and is refused by apply.

## How it is tested before `stable`

On the maintainer's VMs, in three places, in a VM and in an LXC
container, for Odoo on LNPP and WordPress on LAMP: first boot; inspect,
diff and apply; the network converge with its revert; the monitor on a
full disk; reboots; the daily security updates; backup and restore;
IPv6 only; a minor Odoo upgrade by git; real use for as long as the
maintainer decides. Nothing high severity open at the end.

## Open for the maintainer

- The Odoo series to ship (the current stable one), and whether the
  community edition only.
- wkhtmltopdf: the proposal above, or another.
- Whether `Keel-Linux/odoo` mirrors the whole upstream history or only
  the shipped series' branch (the full repository is several gigabytes).
