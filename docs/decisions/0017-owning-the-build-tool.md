# 0017: Owning fab, and how a package this project depends on is named

Date: 2026-09-28
Status: **decided by the maintainer**, 2026-09-28, in Keel-Linux/fab#8.
Implemented in Keel-Linux/fab#9, which also closes fab#7; not merged, and
the build host has not been converted. The note number was taken
deliberately: 0014, 0015 and 0016 are concurrent work, so this is not "the
next free one".

Decision note **0017**, and only 0017.

## What was wrong

The tool that builds every Keel layer ran at a version that was invented on
the machine it runs on.

Measured on the build host, 2026-09-28, read only:

    dpkg-query -W fab                  ->  fab 1.1.1+keel2
    /root/src/fab_1.1.1+keel2_all.deb      built 2026-09-27 17:14:56 UTC
    merge of that version's changelog      2026-09-27 19:58:53 UTC
    git tag -l                             v0.5 .. v1.1.1, upstream's only

The package was built and installed three hours before any branch carried
its version, and neither packaged version was ever tagged. The layer
manifest records the builder as a version string and nothing else, so
`core.manifest` on the mirror carries `fab_version 1.1.1+keel1`, a string
that resolved to no commit. The project's claim is that every image is
rebuildable from our own archive without asking anybody, and an image whose
builder cannot be named does not meet it however reproducible everything
downstream is.

Two things it is worth being precise about, because the first report of this
got both wrong.

The running files were **not** divergent from git. Comparing the extracted
`.deb` against the commit it was built from, `e610377`, file by file: 22 of
25 byte identical, and the three that differ do so only in `dh_python3`'s
shebang normalisation, `#!/usr/bin/python3` to `#! /usr/bin/python3`.
Nothing was running that was not committed.

And the changelog entry existed. It merged as fab#6 at 2026-09-27T19:58:53Z,
nine hours before fab#7 was filed. The report that said `1.1.1+keel2`
appeared nowhere in the history was reading a checkout made before that
merge, which is the trap handbook#13 is adding as "two machines answer to
tkldev, and they run different fab", in its other form: reading the wrong
clone rather than the wrong machine.

So the defect was never the missing entry. It was that **a version string
was the only provenance there was**, and that the version string itself said
"we patched somebody else's thing": `1.1.1+keel2` is upstream's 1.1.1 with a
number bolted on, and nothing in it distinguishes a release from a local
build. A suffix invites exactly what happened.

## Decision

**A Debian package this project depends on and modifies becomes a Keel
package with a version this project chooses.** For fab that is the source
and binary package `keel-fab` at `2.0.0`.

Three separate things follow, and they are separate on purpose.

1. **The package is renamed. The repository is not.** Decision 0006 rules
   that infrastructure keeps its upstream name with no prefix: `common`,
   `fab`, `buildtasks`. That rule is about repositories, and it stands. The
   Debian package name is a different axis, and this is the first time the
   two diverge, so it is stated here: `Keel-Linux/fab` builds `keel-fab`.
   The fork keeps its full history and its upstream compatibility, per
   decision 0008, and cherry-picks in both directions are unaffected.

2. **The version is ours and plain, and it goes up.** `2.0.0`, no `+keelN`.
   Brief section 7's `+keelN` rule is for a *rebuild of an upstream package*,
   and this stops being one. But a rename does **not** start the numbering
   over, which is the part that had to be learned: see below.

3. **Nothing a caller can see is renamed.** Every command, every path and
   the python module keep their names exactly.

### Why 2.0.0 and not 0.1.0

`0.1.0` was proposed first, and it was the obvious choice: it is the scheme
every package this project already owns starts at, `keel` 0.1.0,
`keel-transition` 0.1.0, `keel-archive-keyring` 0.1.0. The changelog gate
wired up in the same pull request refused it, which is the first thing that
gate has ever caught in this repository.

    dpkg --compare-versions 0.1.0 gt 1.1.1+keel2   ->  false

`require-changelog` compares the proposed top version against the base's
exactly that way, and `reprepro` and `dpkg-genchanges` read a changelog as
one monotonic series too; `dpkg-genchanges` was already warning on the 0.1.0
build that the version was earlier than the previous one. **A changelog is
one series whatever the source name does.** Renaming the source does not
give the file a fresh start, and nothing in the toolchain pretends it does.

The reset was the wrong signal as well as the wrong number. The other Keel
packages start at 0.1.0 because they had no predecessor. This code has been
building every layer in production since before it was ours, so a 0.x would
claim it is pre-release. `2.0.0` sorts above every upstream 1.x and above
both `+keelN` builds, carries no suffix, and says what actually happened: the
name, the numbering and the ownership change at once.

The rule, for the next package that moves: **a package that becomes ours
takes the next version above the highest it has already published, chosen by
what the change means.** A package with no predecessor still starts at 0.1.0.

### Why `keel-fab` is the name the tooling already wanted

`apt/lib/build.sh` decides whether a package is native to the project or a
rebuild of an upstream, and refuses a version without `+keelN` for a
rebuild. A package is native when three things hold: the `Source` starts with
`keel`, the clone has no `upstream` remote, and neither `debian/watch` nor
`debian/upstream/metadata` exists. The fab clone already satisfies the last
two. Naming the source `keel-fab` satisfies the first, so `bin/build-package`
accepts `0.1.0` on its own and the `+keelN` guard stops applying to fab
without anyone passing `--native` to override it.

This is the argument for the name rather than a decoration on it: the rule
that says which version scheme a package gets is keyed on the prefix, so a
package whose version scheme is ours has to carry the prefix or the tooling
and the policy disagree.

### The relationships, and what each one is actually for

`Provides: fab`, `Conflicts: fab`, `Replaces: fab`, all unversioned. This is
the first `Provides`/`Replaces`/`Conflicts` triple in this organization's
packaging, so the reasoning is recorded rather than left to be guessed at by
the next one, which is tracker#13's pair.

| Field | What it is for here |
| --- | --- |
| `Conflicts` | The load-bearing one. Both packages ship `/usr/bin/fab` and `/usr/share/fab`; they must never be co-installed, and `Conflicts` is what makes `apt-get install ./keel-fab_0.1.0_all.deb` remove the old one in the same transaction rather than fail on a file clash. |
| `Replaces` | Lets dpkg hand the shared paths over without reporting a conflict, which `Conflicts` alone does not. |
| `Provides` | Not what the callers need. `apt-cache rdepends fab` on the build host is empty and no `debian/control` in this organization depends on `fab`. It is there for the two places that install the package *by name*: `tkldev/plan/main:3` and `tkldev-setup:372`. apt installs a virtual package when exactly one real package provides it, so both keep working untouched. |

A versioned `Provides: fab (= 1.1.1+keel2)` was considered and rejected. It
would satisfy a versioned dependency on `fab`, of which there are none
anywhere in the organization, at the cost of writing upstream's version
number back into the package whose whole point is not to carry one, and of
going stale at the first release.

Note what the relationships do **not** do, because it is the thing most
likely to be assumed: none of them helps the nine places that read the
literal string `fab`. `Provides` does not satisfy `apt-cache policy fab`, a
`Package: fab` pin stanza, or a pool filename. Those are listed below and
each is somebody's issue.

## The commands must not change, and the call sites are why

The maintainer's instruction was to establish the call sites before deciding
rather than assume. Inventoried across all 31 repositories of the
organization and the trees on the build host, roughly 380 references:

| Symbol | References | What it is |
| --- | --- | --- |
| `fab-chroot` | ~100 | command on `PATH` |
| `fab-apply-overlay` | 34 | command on `PATH` |
| `fab-plan-resolve` | 25 | command on `PATH` |
| `fab-apply-removelist` | 12 | command on `PATH` |
| the other five `fab-*` tools | 21 | commands on `PATH` |
| `fab-investigate`, `fab-rewind` | 17 | commands on `PATH` |
| `FAB_PATH` | ~256 | make variable, `/turnkey/fab-keel` |
| `FAB_ARCH` | ~92 | make variable |
| `$(FAB_PATH)/common` | 65 | a git checkout, not a packaged path |
| `/usr/share/fab` | 9 | packaged path, via `FAB_SHARE_PATH` |
| `import fab` | 0 | the module is `fablib`, and always was |

The conclusion is stronger than "they appear everywhere". **Not one of those
references reads the Debian package name.** They are `$PATH` command
lookups, make variables and filesystem paths, and Debian imposes no relation
between a binary package's name and the paths it ships. So `/usr/bin/fab`,
the nine `fab-*` aliases, `/usr/share/fab/product.mk` and `fablib` can all
stay byte identical under a package called `keel-fab`, and `buildtasks`, the
shared makefiles and all 22 recipe Makefiles need no change at all.

Renaming the binaries would be a different and much larger change. It is not
in this note and not in fab#9.

**Decision 0015 does not apply to these commands.** 0015 rules that an
operator facing command carries the Keel name with the `turnkey-*` name kept
as a relative symlink. `fab-chroot` and its siblings are not operator facing:
they exist on the build host and inside a build, an appliance never has them,
and no operator ever types one. 0015's subject is the appliance's surface.
Extending it to build tools would rename 380 call sites to no operator's
benefit, and would do it inside a change whose whole purpose is that the
build host keeps building.

### The one call site inside this repository that did read the package name

`fab --version` ran `apt-cache policy fab` and printed the third field. That
asks about whatever package is called `fab` on this machine rather than about
itself. After the rename it answers `(none)`, measured against a real virtual
package on the build host, and `bt-layer:214` writes that answer into every
layer manifest as `fab_version`. The rename would have silently written
`(none)` into the provenance record of every image built afterwards.

The fix is that the package records its own version: `debian/rules` writes
the parsed changelog version to `/usr/share/fab/version` and
`fablib/version.py` reads it back. That is also the right answer on a host
that installed a `.deb` from a file, where apt has no entry to report either
way, which has been true of the build host from the start.

## Which fab built this layer, in both directions

A manifest records a version string, so the string has to resolve to a
commit, and a commit has to resolve back to the versions built from it.

- **Manifest to commit.** A tag per released version, `<source>/<version>`,
  so `fab_version 1.1.1+keel1` becomes `git rev-parse fab/1.1.1+keel1`.
  `bin/check-release-tags` in fab#9 makes that total and CI keeps it so:
  every changelog entry whose distribution is not `UNRELEASED` is a release,
  and every release below the newest must have such a tag whose tree carries
  that version at the top of its changelog. The newest entry is exempt,
  being the release a pull request is proposing. The source name comes from
  the entry, so the two versions released before the rename are tagged
  `fab/1.1.1+keel1` and `fab/1.1.1+keel2`, which now exist and point at
  `b07a733` and `e610377`. That is what makes the two layers already on the
  mirror traceable.
- **Commit to manifest.** `git describe --match '*/*'` names a commit's
  release and that tag's changelog gives the version a manifest would
  record. No new machinery.

The tag namespace is `<source>/<version>` rather than `vX.Y.Z` because
upstream's tags are `v0.5` through `v1.1.1` in the same repository, and a
future `keel-fab` version must never be able to collide with one of them.

### Recording the commit in the manifest as well: wanted, and not yet

`fab_commit` beside `fab_version` would close the one case a tag cannot: a
package built from an untagged or dirty tree, which is exactly what happened
on 2026-09-27. It is cheap. `keel` already keeps a manifest key it does not
know and writes it back unchanged (`keel/docs/layers.md`, "Optional
fields"), so it costs one line at `bt-layer:214` and **nothing at all in
`keel`**.

It is not needed now, and it is not in fab#9, for two reasons. It is a
`buildtasks` change, so it is a pull request in that repository, filed as
Keel-Linux/buildtasks#12. And the tag invariant plus its CI job already close
the hole for every layer built from here on, with the historic tags covering
the two already built. So it is belt and braces rather than a prerequisite,
and it lands after fab#9 so that `fab --version` is truthful before anything
new reads it.

## Converting the build host, and the way back

fab builds every layer. A broken fab stops the project, so the package and
the plan are the deliverable and the conversion is a scheduled step. Nothing
was built, installed or changed on the build host for this work: access was
read only, no lock was taken, no layer was published or rebuilt.

The package was built in a throwaway `debian:trixie` container instead, and
its contents compared against the `.deb` the host has installed. `keel-fab
2.0.0` against `fab 1.1.1+keel2`: **all 28 paths the old package had are
present and 26 of them are byte identical**, including all nine
`/usr/bin/fab-*` symlinks and `share/product.mk`. The two that differ are
`/usr/bin/fab`, by the `get_version` change alone, and
`runtime.d/*.rtupdate`, by the package name inside it. Two files are new,
`fablib/version.py` and `/usr/share/fab/version`. Nothing is missing.

That measurement is the evidence the conversion is safe, and it is the only
kind of evidence that can be, since no assertion about `debian/` can prove
what a build produces.

Forward, once fab#9 is merged and the package is built and published:

    apt-get install ./keel-fab_2.0.0_all.deb        # removes fab, Conflicts
    # /etc/apt/preferences.d/keel-fab becomes  Package: keel-fab
    #                                          Pin: version 2.*

Back, at any time, because `fab_1.1.1+keel2_all.deb` stays in `/root/src` and
nothing deletes it:

    apt-get install /root/src/fab_1.1.1+keel2_all.deb   # removes keel-fab
    # restore the pin stanza

Either direction is verified with `fab --version`, `dpkg -L keel-fab | grep
/usr/bin` for the twelve commands, and one `fab-chroot` in a scratch tree.
The old package stays installable indefinitely; that is the property that
makes this reversible, and it is why the conversion does not have to be
scheduled alongside anything else.

Two things to settle before scheduling it, both in Keel-Linux/apt#15.
`/etc/apt/preferences.d/keel-fab` pins `Package: fab` at `1.1.1+keel1*` while
`1.1.1+keel2` is installed, so **that pin matches nothing today** and only
Debian version ordering keeps the local build ahead of upstream's `1.1.1` at
priority 999. That is a live defect independent of this note and it is fixed
first, renamed second. And `docs/build-host.md` sections 2 and 3 describe the
package, the pin and the `.deb`, and need the new name at conversion time,
not before.

## Justification (three parts, brief section 10)

1. **Why the present state does not hold.** A `+keelN` suffix on somebody
   else's version string is a claim about somebody else's release, and it
   gives the project no numbering of its own to be disciplined about. What it
   produced is measured above: a version bumped at packaging time on the
   machine, no tag, and a manifest field that named no commit for the layers
   already published. The suffix also puts the package on the wrong side of
   the one rule that decides which version scheme applies, so the tooling
   would have had to be overridden for as long as the arrangement lasted.

2. **Whether it can be made to work.** Partly, and not well enough. Adding
   the changelog entry and the tags under the name `fab` would have made
   `1.1.1+keel2` reconstructible, and `bin/check-release-tags` would have
   worked unchanged. But the next rebuild is `+keel3`, still keyed to an
   upstream release the project no longer tracks, still classified as a
   rebuild, and still carrying a version whose first three digits are a
   promise about upstream's code rather than about ours. And the deeper
   problem is unreachable that way: `fab --version` asked apt about a
   hard-coded package name, so the provenance field in every manifest was
   only ever as good as the machine's apt state. Fixing that is fixing the
   package, and once the package is being fixed the name is the honest part.

3. **Why this is better.** The version numbers become ours, so they can say
   what we mean and a release is a release. The tooling classifies the
   package correctly with no override, so the policy and the code agree. The
   provenance question gets a total answer in both directions, from a tag
   rather than from a string. And the cost is bounded and was measured rather
   than assumed: no command name changes, no path changes, no recipe changes,
   380 call sites untouched, and the built package ships the same paths as
   the one it replaces.

## Consequences

- **`Keel-Linux/fab` builds `keel-fab`.** The repository keeps its name. This
  is the first divergence between the two axes and 0006 is read accordingly:
  its naming rule is about repositories.
- **A package this project owns gets a plain version**, and brief section 7's
  `+keelN` is for rebuilds of upstream packages only. The boundary is the one
  `apt/lib/build.sh` already implements, and a package that crosses it
  crosses both at once or neither.
- **A rename does not reset the numbering.** A changelog is one monotonic
  series however the source is renamed, because `require-changelog`,
  `reprepro` and `dpkg-genchanges` all read it that way. A package that
  becomes ours takes the next version above the highest it has already
  published; only a package with no predecessor starts at 0.1.0.
- **A release is a tag.** Every packaged version of a repository that ships a
  package names the commit it was built from, enforced in CI. A `.deb` built
  from an untagged tree is not a release, and the build host must not run one.
  This applies beyond fab and should be adopted by the other repositories that
  ship packages as they are touched; it is not retrofitted here.
- **The command names are out of scope for decision 0015.** A build tool is
  not operator facing. If that is ever revisited it is its own note and its
  own change, not a rider on a packaging one.
- **The relationship triple recorded above is the precedent** for tracker#13's
  `keel-version` and `keel-sysinfo`, which take over from packages that
  *do* have a reverse dependency and an operator facing command, so their
  `Provides` will be doing real work that fab's is not. They should not copy
  the fields without reading why each is here.
- **The conversion is reversible and unscheduled.** The old `.deb` stays
  installable, the way back is two commands, and nothing in this work leaves
  the build host unable to build.

## What this does not decide

- **When the build host is converted.** The maintainer schedules it. Nothing
  here installs anything.
- **Whether the binaries are ever renamed.** Out of scope, and the note
  argues against bundling it with anything.
- **What happens to the other packages the project rebuilds.** `inithooks`
  2.3.6+keel5 and `confconsole` 2.2.3+keel4 are still rebuilds of upstream
  packages and this note does not move them. tracker#15 is where the
  per-package verdicts live. What this note settles is the rule to apply
  when one of them does move.
- **The `fab` repository's own upstream posture.** Decision 0008 stands: the
  fork stays upstream compatible and the remote stays. Renaming a Debian
  package does not shrink or widen the fork.

## Traps found while writing this

One is the entry handbook#13 is adding, "two machines answer to tkldev, and
they run different fab", which gained a second face before it reached the
default branch: a claim measured from the wrong clone reads exactly like a
claim measured from the wrong machine. The report this note answers stated
that `1.1.1+keel2` existed in no commit, which was true of the checkout it
was read from and false of the repository, and that checkout was the build
host's own `master`, which `git branch -vv` there reports as `behind 4`.
That entry's fix applies unchanged with one word added: name the clone and
its head, not only the machine. It is left to handbook#13 rather than
amended from here, so the two do not collide in the same file.

The other is new and this note adds it: **debhelper keys its per-package
files on the binary package name, and dh_python3 finds a private directory
the same way.** Renaming a package silently drops whatever
was being picked up by name, and the failure surfaces at the first use rather
than at packaging time. Found by building the package and comparing, which is
also the only thing that could have found it.

## Implementation

- Package and provenance: Keel-Linux/fab#9, closing fab#8 and fab#7. Four
  suites, 125 of 125 checks, 100 percent. Tags `fab/1.1.1+keel1` and
  `fab/1.1.1+keel2` pushed.
- The pin that matches nothing, and the archive's rebuild example:
  Keel-Linux/apt#15.
- `fab_commit` in the manifest: Keel-Linux/buildtasks#12, after fab#9.
- The seven other repositories that ship something and do not gate their
  changelog: Keel-Linux/tracker#18.
