# 0010: Composable component repositories instead of one shared tree

Status: **proposed**, 2026-09-27. Raised by the maintainer: can the appliance
work be split into small atomic repositories rather than following TurnKey's
monolithic arrangement? This note records the answer, the cost and the step
that would prove it. Nothing is migrated until the maintainer says so.

## Where the monolith actually is

Not in the appliance repositories. Each appliance is already its own
repository, and each image is already a content addressed layer whose parent
is another layer, so at the image level the decomposition exists: `core`,
`nodejs-nginx`, `nodebb`, and now `mariadb` and `postgresql`.

The shared tree is `common`: 37 overlays, 39 plans and 24 makefile includes in
one repository that every appliance depends on. Changing the MySQL overlay
means committing to the repository WordPress, Odoo and every other appliance
also build from. One version, one history, one gate for all of them; a
component cannot be released, pinned or rolled back on its own.

## What makes the split cheap

`fab` already supports composition and upstream does not use it. In
`share/product.mk`:

```
UNIT_DIRS ?= unit.d
root.spec/body:   unit_plans="$(wildcard $(UNIT_DIRS)/*/plan)"
root.patched:     for each unit.d/*: fab-apply-overlay unit/overlay, then
                  fab-chroot --script unit/conf
```

So a unit is a directory carrying `plan`, `overlay/` and an executable `conf`,
and the build resolves and applies it without any change to fab. No product in
the upstream clones has a `unit.d`. We would be the first user of a mechanism
the build system already ships, rather than bending it.

## The three levels, and which one changes

| Level | Unit | Today | Proposed |
| --- | --- | --- | --- |
| Image | content addressed layer | already atomic | unchanged |
| Component | overlay, conf script, plan fragment, hook | all inside `common` | one repository each, shipped as a fab unit |
| Recipe | appliance | one repository each | unchanged, composes pinned components |

A recipe would declare the components it composes with their versions; an
assembly step materialises `unit.d/` from those pins before the build. That
step is new code of ours, so it is testable and gated like everything else,
and it is what makes a build reproducible from a manifest rather than from
whatever `common` happened to contain that day.

## What it costs

- The assembly and pinning step has to exist and be maintained.
- Divergence from upstream grows precisely in the parts we separate, so
  contributing those back becomes harder. The brief asks us to keep upstream
  remotes and offer changes back, and this works against that for the split
  components. It is the main argument for going slowly.
- Every component repository is subject to the coverage standard, which is the
  point and also the cost: a component without tests cannot be split out
  cleanly.
- More repositories mean more CI surface and more places for a required check
  to be missing, which the audit of 2026-09-26 showed is easy to let slip.

## The step that would prove or sink it

Take one component out of `common` and leave everything else alone: `mariadb`,
because it is being built now. A repository `unit-mariadb` (naming to be
chosen; infrastructure is unprefixed per 0006) holding the plan fragment, the
overlay and the conf script, consumed by `keel-mariadb` through `unit.d`.

It is proven if the layer built that way is equivalent to the layer built from
`common` today, measured the way the M0 gate measures equivalence: the package
list identical, and every differing file explained. If it is, components move
one at a time as we touch them, never as a migration.

## What stays whole

`core` remains one recipe: it is the base, it has no components to share with
anything below it. Small stack layers such as `nodejs-nginx` are already a
handful of files and gain nothing from being split further.

## Verdict

Evidence and a recommendation, not the decision. The status line above stays
**proposed** until the maintainer rules on it.

The experiment of the previous section was run on 2026-09-27 on the project
build host, with one component and nothing else: `mariadb`, whose layer had
not been built yet. The mariadb pieces of our `common` fork
(`mk/turnkey/mysql.mk`, `plans/turnkey/mysql`, `overlays/mysql`,
`conf/mysql`, `removelists/mysql`) were copied into a scratch
`unit.d/mariadb/` holding `plan`, `overlay/` and an executable `conf`. No
repository was created, which is what this note asks for. The recipe lost the
two lines that pull the component from the shared tree: the
`mk/turnkey/mysql.mk` include in the `Makefile` and `#include <turnkey/mysql>`
in `plan/main`.

### The measurement

Three builds of `bt-layer mariadb --parent core`, all at
`SOURCE_DATE_EPOCH=1700000000`, against `common` f3de96a and product ac3c3cd,
fab 1.1.1+keel1, parent layer `core` 7acf2c53:

1. control, the recipe as it is today,
2. the same component supplied as a unit,
3. control again, to establish what two identical builds differ by.

The third build is the point. Without it a difference cannot be attributed.

| | packages | regular files | symlinks |
| --- | --- | --- | --- |
| control | 438 | 35,315 | 3,380 |
| unit | 438 | 35,315 | 3,380 |
| control, second run | 438 | 35,315 | 3,380 |

The package lists are identical, all 438 entries, name and version, in every
pair. The symlinks are identical, all 3,380, target and path, in every pair.
No path exists on one side and not the other.

173 of 35,315 regular files differ, and the three pairwise sets of differing
paths are the same 173 paths:

| pair | differing files |
| --- | --- |
| control vs unit | 173 |
| control vs control, second run | 173 |
| control, second run, vs unit | 173 |

Differences attributable to the unit form, that is the control-vs-unit set
minus the control-vs-control set: **zero**. The unit build differs from the
control by exactly the files by which the control differs from itself.

### The 173, named and explained

| Count | Path | Difference |
| --- | --- | --- |
| 167 | `/var/lib/mysql/**` | the MariaDB data directory created when the conf script starts the server. Every file is the same size and 8 to 11 bytes differ. In `mysql/user.frm` the bytes are the table creation time to the microsecond, `1790475089620377` against `1790475323514142`, the two wall clocks four minutes apart. The `.MAI`, `.MAD`, `.ibd`, `aria_log_control` and `ib_logfile0` differences are the matching creation stamps and log sequence numbers. |
| 1 | `/etc/webmin/mysql/config` | line order only, identical after `sort`. Already covered by the `/etc/webmin/*/config` row of the M0 allow-list, Perl hash order. |
| 1 | `/var/webmin/module.infos.cache` | line order, on the allow-list. |
| 2 | `/var/log/alternatives.log`, `/var/log/webmin/webmin.log` | log content, on the allow-list. |
| 1 | `/var/cache/ldconfig/aux-cache` | on the allow-list. |
| 1 | `/root/.wget-hsts` | the HSTS entry written when the conf script downloads mysqltuner, `1790475096` against `1790475333`, a clock. |

Five of the seven rows are already frozen on the M0 allow-list. The two that
are not, `/var/lib/mysql/**` and `/root/.wget-hsts`, are install-time state of
the same kind as the entries that are, and the control-vs-control run proves
it rather than asserting it. They belong on the allow-list for any layer that
installs a database, independently of this proposal.

So the proof criterion of the section above is met: the package list is
identical and every differing file is named and explained.

### What the experiment also found, and it is not small

The measurement passing is not the whole answer. Four things were looked for
on purpose. Three are real and did not bite this component. The fourth bites.

**Order. Real, harmless here.** A unit is not resolved where `COMMON_CONF`
is. `share/product.mk` applies units after the common overlays, the common
conf scripts, the common patches and the common removelists, and before the
product-local overlay and `conf.d`. The build logs show it:

```
control:  overlays  tkl-bashlib  systemd-chroot  common/overlays/mysql  products/mariadb/overlay
          conf      turnkey.d/hostname  common/conf/mysql
          then      removelists/mysql  removelists/turnkey  overlay  conf.d/main

unit:     overlays  tkl-bashlib  systemd-chroot  products/mariadb/overlay
          conf      turnkey.d/hostname
          then      removelists/turnkey
          then      unit.d/mariadb/overlay  unit.d/mariadb/conf
          then      overlay  conf.d/main
```

Two inversions. The component overlay moves from before the recipe's own
overlay to after it, which reverses the precedence the recipe's own comment
depends on, "After mysql.mk, so a file of this overlay wins over the shared
one". It did no harm because the two overlays share no path, five files
against six, and because `overlay/` is also `ROOT_OVERLAY` and is applied a
second time after the units, which restores the win by accident rather than by
design. The conf script moves from before the common removelists to after
them, which did no harm because `removelists/turnkey` removes only
`/etc/resolvconf/resolv.conf.d/original` and `/var/www/html`. Units do still
run before `removelists-final`, which `conf/mysql` needs, since that list
removes `/usr/local/src/tkl-bashlib` and `/usr/local/bin/service` and the
script uses both. None of this is guaranteed for the next component. It has
to be checked per component, which is a cost the section above does not name.

**The removelist. Real, empty here.** The unit loop in `product.mk` reads
`overlay/` and `conf` and nothing else. There is no removelist slot, so a unit
cannot carry one. `common/removelists/mysql` is 0 bytes, so nothing was lost.
A component with a non-empty removelist cannot be expressed as a unit without
changing `product.mk`.

**`CONF_VARS`. Real, unread here.** `mk/turnkey/mysql.mk` line 1 is
`CONF_VARS += MYSQL_PASS`. `_CONF_VARS` is computed by make before any unit is
looked at, so the unit form drops it and there is no way for a unit to add
one. `MYSQL_PASS` is written in that one line and read by nothing: the only
other mentions in `common` and in `keel-mariadb` are the documentation saying
so. A component whose conf script reads a build-time variable cannot be a pure
unit.

**`bt-layer` does not see `unit.d` at all. This one bites.** There is no
occurrence of the string `unit` anywhere in `buildtasks`. `bt-layer` works out
what a child layer has to do by word arithmetic over `COMMON_CONF` and
`COMMON_OVERLAYS` in `bin/layer-lib` (`layer_child_conf`,
`layer_child_overlays`), passes the result as make overrides, and records both
in the layer manifest. The two manifests show the consequence:

```
control:  common_overlays  turnkey.d mysql /turnkey/fab-keel/products/mariadb/overlay
          common_conf      turnkey.d mysql
unit:     common_overlays  turnkey.d /turnkey/fab-keel/products/mariadb/overlay
          common_conf      turnkey.d
```

The component has disappeared from the layer's provenance record. Two things
follow. First, a child layer cannot subtract a unit the parent already
applied, because nothing tells it the parent applied one, so a LAMP or
WordPress layer built on a unit-based `mariadb` would re-apply the overlay and
re-run the conf script. `conf/mysql` runs under `bash -e` and does
`ln -s /etc/init.d/mariadb /etc/init.d/mysql`, which fails with "File exists"
the second time, so that child build breaks. It would also re-download
mysqltuner and re-run the secure-installation SQL. Second, the manifest is
where a layer says what it is made of. `common_commit` pins the shared tree; a
unit's version is pinned nowhere. That is the opposite of the proposal's own
argument, a build "reproducible from a manifest rather than from whatever
`common` happened to contain that day".

`mariadb` is the cheap case for four reasons at once, and all four are
accidents of this component: it is a leaf with no child layer yet, its
removelist is empty, its `CONF_VARS` entry is read by nothing, and its overlay
shares no path with the recipe's. The first component that is not a leaf hits
the fourth finding on its first child build.

### Recommendation

Do not migrate on this result. Keep the shared tree for now, and do not create
component repositories yet.

The equivalence question is answered and the answer is yes: a layer built from
a unit is the same layer, to the package and to the file, once install-time
state is discounted the way the M0 gate discounts it. That is worth having and
it removes the technical objection to the idea. It is not sufficient, because
the mechanism `fab` ships is only two thirds of what a component is. `fab`
resolves a unit's plan, overlay and conf script; it has no slot for a
removelist or a `CONF_VARS` contribution, and `buildtasks` does not know units
exist, so the layer graph, which is the thing that makes this project's images
atomic, cannot see them.

The order to do this in, if the maintainer wants it:

1. Make `bt-layer` unit-aware before any component moves. Record the units and
   their versions in the manifest, and subtract the parent's units in the
   child path the way `COMMON_CONF` and `COMMON_OVERLAYS` are subtracted.
   Without this a split component is a broken child build, not a released
   component. This is the gate, and it is a change to a repository that
   already has a coverage standard, so it is testable without building
   anything.
2. Decide the removelist and `CONF_VARS` questions. Either add the two slots
   to our `share/product.mk`, which widens the divergence from upstream that
   this note already lists as the main cost, or rule that a component needing
   either one stays in `common`. The second is cheaper and covers `mysql`,
   whose removelist is empty and whose variable is dead.
3. Only then move components one at a time as we touch them, re-running this
   three-build comparison for each, including the control-vs-control run.
   Never as a migration.

### What it costs either way

Migrating, per component: the two blocking items above, once, which is a
change to `buildtasks` and possibly to `share/product.mk`; then per component
an assembly and pinning step, a repository with its own CI and its coverage
floor, a check that the order inversion above is harmless for that component,
and the three builds. For `mariadb` the three builds were 91, 64 and 64
seconds of `root.patched` plus about 30 seconds of packing each, so the
measurement itself is cheap. The standing cost is the one already named in
this note: divergence grows exactly in the parts we separate, and offering
those changes back upstream gets harder.

Keeping the shared tree: `common` stays 37 overlays, 39 plans and 24 makefile
includes with one history and one gate, so a component still cannot be
released, pinned or rolled back on its own, and a change to the MySQL overlay
is still a commit to the repository every appliance builds from. That is the
cost the proposal was written to remove, and it is unchanged. Nothing about
today's result makes it worse, and the experiment is repeatable at any time
against any component, because the scratch unit is a directory and not a
repository.
