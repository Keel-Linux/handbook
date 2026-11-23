# 0096: Upstream packages update by themselves, and the maintainer gets only questions of intent

Date: 2026-11-23
Status: **proposed 2026-11-23.** The maintainer gave the direction on
2026-11-23. Section 3, the automatic promotion to `trixie`, needs the
maintainer's confirmation (open point A). Open point B asks if a
technical stop sends a message. Nothing in this note is built.

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
- The pipeline is code: scripts, timers and CI. No program that decides
  by its own judgement does the work.

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
- The 5 packages of class B and C are behind upstream. `anubis` 1.27.0
  does not have the security fixes of 1.28.0. `keel-nodejs` 24.22.3 was
  not compared with nodejs.org.
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
- A node on the stable track reads Keel `trixie` and Keel
  `trixie-security`. It does not read `trixie-testing`. cron-apt installs from Keel `trixie-security`
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
   one timer, 5 fixed repairs, one automatic upgrade test and one
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
- The TurnKey packages that Keel changed (class D, 10). TurnKey seldom
  changes them, and the Keel changes are Keel commits. A Keel commit
  changes them.
- `webmin`. Decision 0094 retires it.
- `ojs-3.5`. It enters after its first publication (0084).
- A later package enters when it is published and has the items of
  section 7.

### 2. Three layers

**The pipeline is deterministic code only.** It is scripts, timers and
CI. Each step gives the same result for the same input. No program that
writes or changes packaging by its own judgement runs in the pipeline.
A change that needs judgement is the work of a person, in a normal PR
with review and CI.

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

#### Layer 2: fixed repairs

If a check of layer 1 is red, the pipeline tries the fixed repairs
below, and no other change. Each repair is a new commit in the same PR.
The same CI and the same upgrade test are the only judge. If the PR
becomes green, layer 1 goes on. Nobody is told.

1. **Toolchain.** The pipeline reads the `go` line of `go.mod`. It
   takes the first Debian suite of section 4 that has this Go version.
   It changes the version number in `Build-Depends` and in the
   toolchain path of `debian/rules`, and nothing else.
2. **Patch refresh.** If a patch applies with an offset and with fuzz
   0, the pipeline runs `quilt refresh` on it. It never rewrites a
   patch. A patch that needs fuzz or does not apply stops the version.
3. **Patch drop.** A patch can have the fate "drop when upstream >= X"
   (section 7). If the new version is X or higher, the pipeline removes
   the patch from the series.
4. **Changelog.** The pipeline adds the next `debian/changelog` entry,
   with the next `+keelN` version and the list of the repairs it did.
5. **Rebuild.** If the Debian Go toolchain gets a security fix, or the
   `nginx-abi` of trixie changes, the pipeline makes a rebuild with no
   source change. The only change is the changelog entry.

These rules apply to each pipeline commit:

1. It never removes, skips or weakens a test. It does not change
   `debian/tests/`, the CI workflows or a lintian override.
2. It changes only `debian/changelog`, `debian/patches/` and the
   toolchain lines of item 1. A CI check fails if a pipeline commit
   touches another path.
3. It never removes a patch whose fate is `keel-only`.
4. It never changes what the package does on the node: the maintainer
   scripts, the systemd units, the default configuration, the paths and
   the users stay the same.

**If the fixed repairs do not make the PR green, the version stops.**
The version goes to no suite. The published version stays. The pipeline
opens one issue in `Keel-Linux/tracker` with the facts: the check that
failed, the repairs that it tried, and the links to the PR and the CI
runs. A person does this work as ordinary engineering, through a normal
PR with review and CI. It is not a question for the maintainer. Open
point B asks if a stop also sends a message. A stopped security release
(section 6) always sends one ntfy message of level `notice` to
`keel-alerts`, as layer 3 does.

A failure of the infrastructure does not stop the version. Examples: a
runner that is down, a test VM that does not answer. The pipeline runs
again the next day, and the failure goes to the infrastructure work.

#### Layer 3: the maintainer

The pipeline stops and tells the maintainer only for one of these
reasons. Each one is a question of intent:

1. The upstream licence changes, or a new vendored part has a licence
   that is not free (DFSG).
2. Upstream removes or reverses a function that Keel uses by design.
3. A `keel-only` patch goes against the intent of upstream and can no
   longer be carried.
4. Upstream is dead: the repository is archived, or upstream says that
   the project ends.
5. A security fix of upstream does not pass the upgrade test of 0090.

Reason 3 starts from a stop: the person who does the work finds that
the patch cannot be carried, and opens the layer 3 notice.

The notice is one ntfy message and one tracker issue:

- The message goes to the topic `keel-alerts` (0063) with the level
  `notice` (0085). It gives the package, the version, the reason number
  above and the link to the issue.
- The issue in `Keel-Linux/tracker` gives what upstream changed and
  what the nodes have now. It links to the PR and the CI runs. It asks
  one question that the maintainer can answer with yes, no or a letter. It says what happens with no answer: the
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
   refresh time of 0073 item 7. A node on the stable track does not read
   `trixie-testing`. Thus only the daily test adds evidence, not the calendar.
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
build time. If no Debian suite has the version, the version stops
(section 2, layer 2). If a security release stops, a person backports
the upstream fix as a patch through a normal PR. Its fate is "drop when
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
   because a change of the patch can change it.
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

- `challenge-without-gzip`: `keel-only`, rebased by a person. The guard is the
  `behind-nginx` step with 512 requests and no `Accept-Encoding`.
- `redirect-domains-ipv6`: `keel-only`, with no guard test, because Keel
  does not set `REDIRECT_DOMAINS`. It applies with no change on 1.28.2
  and stays.
- `redir-same-host`: `keel-only`, rewritten in `PassChallenge` by a
  person. The guard
  is the `behind-nginx` cases that refuse another host.
- `redir-validate`: `drop-when-upstream >= 1.28.0`. Its `behind-nginx`
  cases stay and must pass on the upstream code. Upstream 1.28.2 gives
  the same messages that the test looks for: "Invalid redirect" and
  "Redirect domain not allowed" (`lib/localization/locales/en.json`).
- `keep-cookie-of-request-without-cookie`: `drop-when-upstream >= 1.28.0`.

Two patches do not apply on 1.28.2, and the `.wasm` component is new.
Thus the first run of the pilot stops. This is the expected result, and
it tests the stop.

The pilot must show these results before the next package enters:

1. The timer finds 1.28.2 and imports it with the signature check, with
   no person.
2. The fixed repairs choose Go 1.27 and drop the 2 patches with the
   fate `drop-when-upstream >= 1.28.0`. The version then stops on the 2
   patches that do not apply, and the pipeline opens one tracker issue.
3. A person adds the `.wasm` component, rebases one patch and rewrites
   the other, through a normal PR. No file in `debian/tests/` changes.
4. The upgrade test of 0090 is green on each published image that holds
   `anubis`.
5. The CI files go to `trixie-testing` with no person.
6. A layer 3 case, made on purpose in a test repository, sends exactly
   one ntfy message and one tracker issue.
7. The evidence file exists.

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

B. **A technical stop (section 2, layer 2).** When a version stops for
a technical reason, is the maintainer told by ntfy? Answer with a
letter:

- B1: no message. Only the tracker issue goes into the queue
  (proposed).
- B2: one ntfy message of level `notice` for each stop.

With B1 or B2, a security release that stops always sends one message.

## Work, in order

Nothing is started.

1. Add the `Keel-Fate` and `Keel-Guard` fields to the 5 `anubis`
   patches.
2. Write `.forgejo/keel-pipeline.yaml` for `anubis`.
3. Add the CI check that fails when a pipeline commit touches a path
   outside the list of layer 2.
4. Write the import step: `uscan`, the signature check, `gbp import`,
   the branch and the PR.
5. Write the daily timer on the build host.
6. Make the upgrade test of 0090 run from a PR, in the test VM of a
   site.
7. Make `bin/publish` take the CI files of a merged PR.
8. Make the archive push run with no person, with a restricted key as
   `keel-channel-push` has.
9. Write the 5 fixed repairs of layer 2.
10. Write the stop issue of layer 2 and the layer 3 notice: the ntfy
    message and the tracker issue.
11. Run the pilot with `anubis` 1.28.2 and write its evidence.
12. Add `govulncheck` and the toolchain and `nginx-abi` triggers.
13. Make the build-only suite for toolchain backports.
14. If open point A is yes: the automatic promotion.
15. Bring the next packages in, in the order of section 9.

## Related notes

It applies 0053, 0055, 0063, 0073, 0083, 0085 and 0090. Decision 0095
makes this pipeline item 1 of the product level: an image goes to
stable only when its third-party packages are in the pipeline.
