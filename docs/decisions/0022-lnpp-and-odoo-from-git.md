# 0022: An LNPP stack, and Odoo installed and upgraded from git

Date: 2026-09-30
Status: **proposed, mostly decided**. The direction was set by the maintainer on
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
- **Odoo 18.0, Community, with the OCA ready** (decided the same day):
  the addons path is laid out for OCA repositories checked out at their
  `18.0` branches, so adding an OCA module is a clone and an install, not
  a rebuild. 18.0 over 19.0 for the maturity of the OCA's 18.0 branches;
  Odoo supports 18.0 until about October 2027, so the move to the next
  series is the orchestrated upgrade's first real case, with OpenUpgrade.
- **wkhtmltopdf: the patched upstream package, pinned, from our
  archive.** TurnKey's own Trixie work (the `wish/odoo-v19-trixie`
  branch of the fork, `docs/v19.0-testing.md`) measured that
  `wkhtmltox 1:0.12.6.1-3.bookworm` installs and renders on Debian 13,
  its old library names being provided by Trixie's `t64` packages; it
  pins the package by SHA-256
  (`98ba0d157b50d36f23bd0dedf4c0aa28c7b0c50fcdcdc54aa5b6bbba81a3941d`)
  and checks its name, version, architecture and `--version` ("with
  patched qt"). Keel does the same with one difference: the package is
  copied into archive.keellinux.org, signed there like everything else,
  so a build downloads nothing from a third party. It is still an
  unmaintained binary, and the appliance documentation says so; it runs
  as Odoo's user and renders pages Odoo produced, so a sandbox of its
  own is a follow-up, not a blocker.

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

Decided: the second, pinned and served from our archive (see
"Decided"), stated plainly in the appliance's documentation; the third
and the first are the work that follows if Odoo keeps depending on it.

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

## Choosing what Odoo carries: localization, then verticals

Decided by the maintainer on 2026-09-30: the operator chooses in
confconsole, by business function rather than by repository name, first
a localization, then the verticals. Each choice is an OCA repository set
checked out at `18.0`, which makes its modules available in Odoo's Apps
list; installing a module into a database stays Odoo's own act. The
screens configure this machine only (decision 0013's rule), and the
choice is written to the spec, so `keel diff` and a rebuilt machine see
the same set.

Every repository below had an active `18.0` branch when measured
(2026-09-30); `l10n-uk` has none and is not offered.

| Screen | Choice | OCA repositories |
| --- | --- | --- |
| Localization (one) | Brazil, Spain, Portugal, Italy, France, Germany, Netherlands, Belgium, Switzerland, Mexico, Colombia, Chile, Peru, Ecuador, USA, Canada | `l10n-<country>` |
| Always, the base | | `server-tools`, `server-ux`, `web`, `reporting-engine`, `queue`, `partner-contact`, `product-attribute` |
| Verticals (any) | Stock | `stock-logistics-warehouse`, `-workflow`, `-tracking`, `-barcode`, `-reporting`, `delivery-carrier` |
| | Website | `website`, `web`, `e-commerce` |
| | Sales | `sale-workflow`, `sale-reporting`, `crm` |
| | Purchase | `purchase-workflow` |
| | Accounting | `account-financial-tools`, `account-financial-reporting`, `account-invoicing`, `account-payment`, `bank-payment`, `account-reconcile`, `mis-builder` |
| | Field Service | `field-service` |
| | Helpdesk | `helpdesk` |
| | Projects | `project`, `timesheet` |
| | People | `hr`, `hr-attendance`, `hr-holidays`, `payroll` |
| | Manufacturing | `manufacture` |
| | Point of Sale | `pos` |
| | Contracts | `contract` |
| | Documents | `dms` |

A module's `depends` can name a module of a repository the operator did
not pick; the recent OCA series dropped `oca_dependencies.txt`, so the
set is closed by reading the manifests of the checked-out repositories
and adding the repositories that hold the missing modules, and the plan
says which it added and why.

**Python beyond Debian.** Odoo itself runs on Debian's `python3-*`
packages, but the OCA repositories carry their own requirements, and not
all are in Debian: of `l10n-brazil`'s 15, ten are not (`nfelib`, the
`erpbrasil.*` family, `brazilcep`, `brazilfiscalreport`, `workalendar`
and others). So "Debian's Python only" holds for Odoo and not for the
verticals, and one of these is needed:

| Option | Cost |
| --- | --- |
| A virtual environment with `--system-site-packages` (Debian's libraries first), the rest installed with `pip --require-hashes` from wheels mirrored in our own archive | the community's way, reproducible, sovereign; a small index to run and refresh |
| Package each missing library as a `.deb` in our archive | the most Debian-like; dozens of packages to own, per country |
| `pip` from PyPI | the fastest; a third party at build and at every vertical chosen later |

**Not decided yet.** The maintainer leans towards the second, packaged
the Debian Python Team way in our archive and offered to Debian over
time, and asked for its size to be measured before deciding whether it
is worth it. The measurement is in
[docs/odoo-python-packaging-map.md](../odoo-python-packaging-map.md):
Odoo 18.0 itself needs nothing outside trixie; the whole OCA catalogue
needs 34 libraries more (30 direct, 4 in their closure), all pure
Python, none with a licence that keeps it out of main; Brazil alone
accounts for 12, Portugal for none. Sponsorship, not the NEW queue, is
the wall for sending them to Debian (tracker#15).

## How it is tested before `stable`

On the maintainer's VMs, in three places, in a VM and in an LXC
container, for Odoo on LNPP and WordPress on LAMP: first boot; inspect,
diff and apply; the network converge with its revert; the monitor on a
full disk; reboots; the daily security updates; backup and restore;
IPv6 only; a minor Odoo upgrade by git; real use for as long as the
maintainer decides. Nothing high severity open at the end.

## Open for the maintainer

- How the verticals get the Python Debian lacks: the three options above,
  measured in the map; and, if packages, in which order.
- The catalogue above: add or drop verticals.
- Whether `Keel-Linux/odoo` mirrors the whole upstream history or only
  the `18.0` branch (proposed: the branch; the full repository is
  several gigabytes, and the upgrade to the next series adds its branch
  then).
