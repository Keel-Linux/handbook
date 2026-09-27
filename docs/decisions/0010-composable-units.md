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
