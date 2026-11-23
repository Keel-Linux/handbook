# 0096: Upstream packages update by themselves, and the maintainer gets only questions of intent

Date: 2026-11-23
Status: **proposed 2026-11-23.** The maintainer gave the direction on
2026-11-23. Section 3, the automatic promotion to `trixie`, needs the
maintainer's confirmation (open point A). Nothing in this note is built.

## What was asked

The maintainer gave this direction on 2026-11-23:

- Each upstream software that Keel packages as a Debian package updates
  as automatically as possible. This applies to all such packages.
- A technical change is never a reason to call the maintainer. Examples:
  a new Go version, a new build dependency, a patch that must be
  rebased, a change of the build system.
- The maintainer is told only when no technical solution exists and the
  problem becomes a question of intent.
- "Do the basic thing and do it well."

## What is true today

Read in the repositories on 2026-11-23. The facts about the packages
come from two read-only reports of 2026-11-23: the package inventory
(`package-inventory-2026-11-23.md`) and the patch analysis of `anubis`
(`anubis-patches-analysis-2026-11-23.md`). The two reports are not in
the handbook yet.

- The archive has 33 source packages. 5 are upstream software that Keel
  builds from source (class B and C): `anubis`, `libcoraza`,
  `libnginx-mod-http-coraza`, `coreruleset`, `syncthing`. `keel-nodejs`
  repacks the official Node.js binary (class E, 0083).
- Each of the 6 is behind upstream. `anubis` 1.27.0 does not have the
  security fixes of 1.28.0.
- No timer looks for a new upstream version. A person sees it.
- Each package repository has a CI that builds and tests
  (`.forgejo/workflows/package.yml` of `Keel-Linux/anubis`). It calls
  `lxc-trixie.yml` of `Keel-Linux/.github` on a `keel-lxc` runner, in an
  LXC system container. It runs `gbp buildpackage`, then
  `lintian --fail-on error,warning`, then autopkgtest with the null
  runner in the container. No Docker is used.
- The build host builds again for the archive: `bin/build-package` of
  `Keel-Linux/apt` (`lib/build.sh`) runs `apt-get build-dep` and
  `dpkg-buildpackage`. This build has no lintian and no autopkgtest.
  Thus the published files are not the files that the CI tested.
- `bin/publish` puts the packages into `trixie-testing` with reprepro.
  The build host signs with no person (0055).
- `bin/keel-publish-mirror --archive-only` copies the archive to
  `archive.keellinux.org`. It runs from a workstation through the
  maintainer's forward (README of `Keel-Linux/apt`, step 3). Only the
  channel pointers go out with no person
  (`infra/build-host/keel-channel-push`).
- `bin/promote` copies a package from `trixie-testing` to `trixie`.
  `lib/promote.sh` says that this is the maintainer's act "and nothing
  else does it".
- The upgrade test of 0090 is done by hand (handbook#186, handbook#194).
- The image build of 0061 starts for image repositories only. A package
  repository does not start it.
- A node reads Keel `trixie` and Keel `trixie-security`. It does not
  read `trixie-testing`. cron-apt installs from Keel `trixie-security`
  with no person (0073 item 5).

| Package | `debian/watch` | autopkgtest | Patch series | Build in CI |
| --- | --- | --- | --- | --- |
| `anubis` | yes, signature check | `behind-nginx` | 5 patches | yes |
| `libcoraza` | yes | no, tests at build | none | yes |
| `libnginx-mod-http-coraza` | yes | `crs-blocks` | 2 patches | yes |
| `coreruleset` | yes | no, `crs-blocks` of the module | none | yes |
| `syncthing` | no | no | none, native format | no, static check only |
| `keel-nodejs` | no | no | none, native | `tests.yml` only |

## Why (brief section 10)

1. **Why it is necessary.** A new upstream version waits for a person
   today. Thus a security fix of upstream does not get to the nodes. The
   `anubis` package shows this: it is 1 minor version and 33 hardening
   fixes behind.
2. **Whether it can be made to work.** It can. Most steps exist: the
   watch files, the CI build, lintian, autopkgtest, the unattended
   signature (0055) and the upgrade test of 0090. The missing parts are
   one timer, one repair step, one automatic upgrade test and one
   unattended archive push.
3. **Why this is better.** The CI is the only judge of a technical
   change. The maintainer reads only a question that a test cannot
   answer.

## Decision

### 1. Scope

These source packages are in the pipeline:

| Package | Upstream | Note |
| --- | --- | --- |
| `anubis` | TecharoHQ/anubis | the pilot |
| `libcoraza` | corazawaf/libcoraza | |
| `libnginx-mod-http-coraza` | corazawaf/coraza-nginx | also a rebuild when the `nginx-abi` of trixie changes |
| `coreruleset` | coreruleset/coreruleset | |
| `syncthing` | syncthing/syncthing | the 2.x line, until Debian has v2 (0050) |
| `keel-nodejs` | nodejs.org | the LTS line of 0083 only, today 24 |

These source packages are not in the pipeline:

- Keel's own packages (class A, 16). Keel is their upstream. A Keel
  commit changes them.
- The TurnKey packages that Keel changed (class D, 10). Keel carries 1 to
  37 own revisions on each of them, thus Keel is their upstream in
  practice. A Keel commit changes them.
- `webmin`. Decision 0094 retires it (handbook#197).
- `ojs-3.5`. It enters after its first publication (0084).
- A later package enters when it is published and has the items of
  section 7.

### 2. Three layers

#### Layer 1: automatic

A timer on the build host runs each day for each package in the scope.

1. `uscan` reads `debian/watch` and finds a new upstream version. The
   timer also starts a rebuild when one of these changes:
   - the Debian Go toolchain of the build gets a security fix;
   - the `nginx-abi` of trixie changes (`libnginx-mod-http-coraza`);
   - a vendored Go module gets a security advisory (section 6).
2. The import step gets the tarball and checks its upstream signature.
   It imports the tarball into the `upstream` branch with `gbp`.
3. The step applies the patch series and adds a `debian/changelog`
   entry with the next `+keelN` version.
4. The step pushes a branch and opens a PR in the package repository.
5. The CI of the PR builds, runs lintian and runs autopkgtest. This CI
   exists today.
6. The upgrade test of 0090 runs on the PR's packages: one node of each
   published application that holds the package, from the published
   image, in a cloud mode. For `anubis`, this is a node of `keel-web`
   and of each image on it. For `syncthing`, the test is a pair. The
   node is in the test VM of a site, one nested Proxmox VE VM for each
   site. It is not on the BR1 or BR2 cluster. The test destroys its
   containers at the end.
7. If each check is green, the pipeline merges the PR with a merge
   commit. It never merges on a red check (0053).
8. The build host takes the `.deb` files that the CI built and tested.
   It does not build them again. `bin/publish` puts them into
   `trixie-testing`. The archive push follows with no person.
9. The pipeline writes one evidence file for each version (0053).

Steps 5 and 8 (`bin/publish`, the signature) exist. Steps 1 to 4, 6, 7,
9, the use of the CI files and the unattended archive push are to build.

#### Layer 2: automated repair

If a check of layer 1 is red, an automated repair step changes the
packaging on a new commit in the same PR. Examples: a newer Go toolchain
(section 4), a new build dependency, a patch rebase, a change of the
build system. The same CI and the same upgrade test are the only judge.
If the PR becomes green, layer 1 goes on. Nobody is told.

The automated repair step obeys these rules:

1. It never removes, skips or weakens a test. It does not change
   `debian/tests/`, the CI workflows or a lintian override. A CI check
   fails if a repair commit touches one of these paths.
2. It never removes a Keel patch whose fate (section 7) is "Keel-only".
   It can rebase or rewrite such a patch. The guard test of the patch
   must pass with no change.
3. It removes a patch only when its fate is "drop when upstream >= X"
   and the new version is X or higher.
4. It never changes what the package does on the node: the maintainer
   scripts, the systemd units, the default configuration, the paths and
   the users stay the same.
5. Its changes are ordinary commits in the PR. The CI gates them as
   any other commit.
6. One attempt is one repair commit and one complete CI run. It makes
   at most 3 attempts for one upstream version. The count starts again
   for a newer upstream version.

A failure of the infrastructure is not an attempt and is not a reason
for layer 3. Examples: a runner that is down, a test VM that does not
answer. It goes to the infrastructure work.

#### Layer 3: the maintainer

The pipeline stops and tells the maintainer only for one of these
reasons:

1. The upstream licence changes, or a new vendored part has a licence
   that is not free (DFSG).
2. Upstream removes or reverses a function that Keel uses by design.
3. A Keel-only patch goes against the intent of upstream and can no
   longer be carried. The guard test fails after 3 attempts.
4. Upstream is dead: the repository is archived, or upstream says that
   the project ends.
5. The repair failed after 3 attempts.
6. A security fix of upstream does not pass the upgrade test of 0090.

The notice is one ntfy message and one tracker issue:

- The message goes to the topic `keel-alerts` (0063) with the level
  `notice` (0085). It gives the package, the version, the reason number
  above and the link to the issue.
- The issue in `Keel-Linux/tracker` gives what upstream changed and
  what the nodes have now. It links to the PR and the CI runs. It asks one question that the maintainer can answer with
  yes, no or a letter. It says what happens with no answer: the
  published version stays.
- The issue joins the list of tracker#1. There is no reminder.

### 3. Promotion from `trixie-testing` to `trixie`: the maintainer must confirm

**The maintainer must confirm this section (open point A).** On
2026-11-23 the maintainer said "acho que sim" (I think so).

The proposed rule:

1. **A normal release.** The pipeline promotes a version to `trixie`
   after 7 green days. A green day is one daily run of the upgrade test
   of 0090 on the candidate, with each check green. A red run starts the
   count again. The number 7 is the time of the reminder of 0085 and the
   refresh time of 0073 item 7. A node does not read `trixie-testing`.
   Thus only the daily test adds evidence, not the calendar.
2. **A security release (section 6).** The pipeline promotes after one
   green run of the upgrade test, with no wait. The test runs, thus no
   yes of the maintainer is necessary (0090 item 3 is for a promotion
   before the test).
3. **`trixie-security`.** The package goes to Keel `trixie-security`
   only when 0073 item 5 allows it. The package repository says if the
   maintainer scripts restart a paired service or an etcd member. If it
   says yes, or says nothing, the package goes to `trixie` only, with an
   advisory (0073 item 6).
4. `bin/promote` does the copy, as today. The pipeline runs it.

If the maintainer says no: the pipeline stops at `trixie-testing`. It
still runs the daily test. After 7 green days it writes the evidence and
the exact `bin/promote` command line into one tracker issue. The
maintainer runs the command.

### 4. Toolchains

The compiler of a build comes only from a Debian archive, in this order:

1. trixie;
2. trixie-backports, for example `golang-1.27-go` for `anubis` 1.28.2;
3. a Keel backport of the Debian source package from forky or sid. The
   pipeline builds it like any package in the scope. It goes to a
   build-only suite that no node reads. This suite is to build.

The pipeline reads the version that upstream needs. For Go, this is the
`go` line of `go.mod`. The pipeline takes the first source in this list
that has the version.
It never uses `/usr/local`, a tarball of the toolchain or a download at
build time. If no Debian suite has the version, the package waits at
its version. For a security release that waits, the automated repair
step backports the upstream fix as a patch with the fate "drop when
upstream >= X".

Gaps today: `syncthing` uses Go from `/usr/local/go1.26` on the build
host. `keel-nodejs` and `ojs-3.5` download at build time.

### 5. Vendored and generated files

1. **Origin.** A vendored or generated file comes from a signed release
   artifact of upstream. The import step checks the signature. If
   upstream signs nothing, the import step records the sha256 of the
   artifact and the commit of the upstream tag in the package
   repository.
2. **The build is offline.** Only the import step uses the network. The
   build uses `GOPROXY=off` and `-mod=vendor`, as `anubis` does today.
3. **Record.** `debian/README.source` names each generated file and the
   upstream command that makes it. `debian/copyright` names the licence
   of each vendored part.
4. **Reproducibility.** The build sets `SOURCE_DATE_EPOCH`, as
   `lib/build.sh` does today. The published files are the files that
   the CI tested (layer 1, step 8).

The example is `anubis` 1.28.2. Anubis does not start without the
`.wasm` files of `web/static/wasm/`, and the Go build does not make
them. Upstream ships them in `anubis-src-vendor-npm-1.28.2.tar.gz`, with
a signature file `.asc` beside it. The pipeline takes this tarball as a
second component, with its signature check. It does not build the
`.wasm` files with cargo. This tarball can also replace the npm
component that Keel makes by hand today.

### 6. Security

The pipeline finds a security release from these sources:

- the security advisories of the upstream repository (GHSA);
- an upstream release note that names a security fix or a CVE;
- `govulncheck` on the vendored Go modules of each Go package, each
  day;
- the Debian security advisories for the Go toolchain and for nginx.

A security release goes first in the queue. Section 3 item 2 gives its
short path. A node with `apt` sees nothing until Keel publishes. The
upstream release is not in any suite that a node reads. Thus each day
in the pipeline is a day with the defect on each node. The published
images hold the old version until they are built again (0073 item 7).

### 7. What a package repository must hold

1. `debian/watch` with the upstream signature check, if upstream signs.
2. At least one autopkgtest that installs the package and uses it as a
   node uses it.
3. A guard test in `debian/tests/` for each Keel patch that carries a
   security or design property. A test inside the patch is not enough,
   because a rewrite of the patch can change it.
4. A patch series with a DEP-3 header on each patch. A field
   `Keel-Fate` gives one of: `keel-only`, `forwarded <URL>`,
   `drop-when-upstream >= X`. A field `Keel-Guard` names the guard test.
5. `Maintainer: KeelLinux maintainers <admin@keellinux.org>` and a
   person in `Uploaders`.
6. A file `.forgejo/keel-pipeline.yaml`. It names the images that hold
   the package, for the upgrade test. It names the line to follow, if
   there is one. It says if the package can go to `trixie-security`.
   dpkg-source
   ignores `.forgejo/` (`debian/source/options` of `anubis`).

Gaps today: no repository has items 4 and 6. `libcoraza` and
`coreruleset` have no autopkgtest of their own. `syncthing` has no
watch file, no `gbp` configuration and no build in its CI.
`keel-nodejs` has no watch file and no autopkgtest.

### 8. Relation to Debian

Each package stays in a form that a Debian team can take, but nothing
goes to Debian or to upstream without the maintainer's word.

### 9. Pilot and order

The pilot is `anubis` 1.28.2, to `trixie-testing` only. Its patches go
as follows (the patch analysis):

- `challenge-without-gzip`: `keel-only`, rebased. The guard is the
  `behind-nginx` step with 512 requests and no `Accept-Encoding`.
- `redirect-domains-ipv6`: `keel-only`. It applies with no change on
  1.28.2 and stays.
- `redir-same-host`: `keel-only`, rewritten in `PassChallenge`. The guard
  is the `behind-nginx` cases that refuse another host.
- `redir-validate`: `drop-when-upstream >= 1.28.0`. Its `behind-nginx`
  cases stay and must pass on the upstream code.
- `keep-cookie-of-request-without-cookie`: `drop-when-upstream >= 1.28.0`.

The pilot must show these results before the next package enters:

1. The timer finds 1.28.2 and imports it with the signature check, with
   no person.
2. The automated repair step makes the Go 1.27, `.wasm` and patch
   changes. The CI is green, and no file in `debian/tests/` changed.
3. The upgrade test of 0090 is green on each published image that holds
   `anubis`.
4. The CI files go to `trixie-testing` with no person.
5. A red case that cannot be repaired, made on purpose in a test
   repository, sends exactly one ntfy message and one tracker issue.
6. The evidence file exists.

The order after the pilot: `libcoraza`, `libnginx-mod-http-coraza`,
`coreruleset`, `syncthing`, `keel-nodejs`. Each package enters after the
one before it published one version through the pipeline.

## What this amends

- **0090**: the upgrade test becomes automatic and daily. Its rule does
  not change. If open point A is yes, the pipeline promotes, not a
  person.
- **0061**: a package in the scope starts its own upgrade test. The
  image build stays as 0061 says.
- **`Keel-Linux/apt`**: `bin/promote` stays. If open point A is yes,
  the comment "nothing else does it" in `lib/promote.sh` changes.
  `bin/publish` takes the files that the CI built.

## Open points

A. **The promotion of section 3.** Answer with a letter:

- A1: yes, as proposed: 7 green days, a security release after one
  green run.
- A2: yes, but 14 green days for a normal release.
- A3: no. `bin/promote` stays the maintainer's act. The pipeline writes
  the command line into a tracker issue.

## Work, in order

Nothing is started.

1. Add the `Keel-Fate` and `Keel-Guard` fields to the 5 `anubis`
   patches.
2. Write `.forgejo/keel-pipeline.yaml` for `anubis`.
3. Add the CI check that fails when a repair commit touches
   `debian/tests/`, a workflow or a lintian override.
4. Write the import step: `uscan`, the signature check, `gbp import`,
   the branch and the PR.
5. Write the daily timer on the build host.
6. Make the upgrade test of 0090 run from a PR, in the test VM of a
   site.
7. Make `bin/publish` take the CI files of a merged PR.
8. Make the archive push run with no person, with a restricted key as
   `keel-channel-push` has.
9. Write the automated repair step with the rules of layer 2.
10. Write the layer 3 notice: the ntfy message and the tracker issue.
11. Run the pilot with `anubis` 1.28.2 and write its evidence.
12. Add `govulncheck` and the toolchain and `nginx-abi` triggers.
13. Make the build-only suite for toolchain backports.
14. If open point A is yes: the automatic promotion.
15. Bring the next packages in, in the order of section 9.

## Related notes

It applies 0053, 0055, 0063, 0073, 0083, 0085 and 0090.
