# 0061: One image build per merge, tested on the runner, promoted to testing

Date: 2026-10-16
Status: **decided 2026-10-16 by the maintainer** ("sim" to the flow: one
image build per merge, no second build). The coordinator decided the
details below under the maintainer's delegation of design calls, with
the option of least power each time. This note amends 0016 (who moves a
channel) and uses the staging key of 0011 (handbook#11, open) and the
release keys of 0055.

## The problem

An image reaches a tester only when somebody runs `keel-release` by hand
on the build host. A merge to `main` of an appliance repository does not
build an image. The appliance gate of each pull request
(`test-appliance.yml`) boots the layer that the mirror publishes, which
is older than the change, so no check boots the layer that the merge
makes. The step-12 pre-releases were built and signed by hand, and some
went out unsigned.

## The flow

1. **Detect.** A systemd timer on the build host,
   `keel-image-ci.timer`, runs every 5 minutes. It asks the Forgejo API
   on `git.pop.coop` for the head of the default branch of each watched
   repository. If no head changed, it stops.
2. **Build once, incrementally.** The build host fetches the new heads
   from `git.pop.coop` into its own CI tree and runs `keel-release
   --staging --match-source`. A layer is built again only when the
   commit that its manifest records is not the head of its source, or
   when its parent changed. So a merge builds the layer that changed and
   the layers above it, and nothing else.
3. **Sign with the staging key.** The build host signs the staged
   release with the staging key only. The signature files end in
   `.staging.asc`. This signature means only "the build host produced
   these bits" (0011). No appliance trusts the staging key.
4. **Hand off.** The build host pushes the staged release to a drop
   directory on the runner VM (Keel-Linux-Runner). Then it dispatches the
   workflow `image-boot.yml` of `Keel-Linux/image-gate` through the
   Forgejo API, with the build id and the sha256 of the staged
   `MANIFEST`.
5. **Test on the runner.** The job runs on the label `keel-lxc`. It
   checks the staging signature and every digest of the `MANIFEST`. Then
   it boots each appliance of the build with the boot test of its own
   repository, at the commit that the layer records. It boots the bits
   as built: the job does not upgrade the rootfs from the archive first.
6. **Promote, or stop.** The build host waits for that run, by its run
   id. If the run passes, the build host checks every digest again
   against its own staging record and signs the same files with the
   release keys, main and images (0055). It builds nothing again. If the
   run fails, the build host promotes nothing and opens an issue.

## The trust boundaries

| Machine | Holds | Can reach | Cannot |
| --- | --- | --- | --- |
| Build host | the signing subkeys (0055), the staging key, a Forgejo token for one repository, an ssh key for the drop user | `git.pop.coop`, the drop user on the runner VM | receive a connection from the runner |
| Runner VM | no secret key, no credential for the build host | `git.pop.coop`, the archive | sign, write on the build host |
| Forgejo | the merges to `main`, the runs | nothing on the build host | push to the build host |

- **Pull request code never reaches the build host.** The build host
  reads only the default branch of each watched repository, which branch
  protection guards. It does not read a pull request, a branch or a tag.
- **The runner holds no key.** It verifies with the public staging
  keyring, which is in `Keel-Linux/.github`. The subkeys stay on the
  build host (0055, point 5).
- **The direction is from the build host to the runner.** The drop user
  on the runner VM accepts one forced command: `rrsync -wo` into the
  drop directory. The key cannot open a shell and cannot read. The runner
  users can read the drop directory and cannot write to it. The nginx of
  the build host stays on loopback.
- **The result binds to the build.** The build host dispatches with
  `return_run_info` and waits for that run id, never for "the last run".
  The run gets the sha256 of the staged `MANIFEST` as an input and
  refuses another one. Nothing comes back from the runner except the
  conclusion of the run. The promoted files are the files on the build
  host.
- **What a compromised runner can do.** It can report a pass for a build
  that failed. Then the build host promotes bits that it built itself
  from protected `main` to testing, without a real test. It cannot change
  the bits, it cannot sign, and it cannot touch stable. We accept this.
- **The Forgejo token is not a signing credential.** It belongs to the
  bot user `keel-image-bot`, which has write access to
  `Keel-Linux/image-gate` only. It can dispatch the workflow and open an
  issue in that repository. It cannot push to `main` there, because
  branch protection allows only the maintainers. The token file is
  readable by root only.

## The trigger: the build host polls

**Decided: the build host polls the Forgejo API. Forgejo does not call
the build host.** A webhook needs a port on the build host that the
internet, or Forgejo, can reach, and code that parses a request from
outside on the machine that holds the subkeys. A poll needs no open port
and no secret. The API answers without a token, because the watched
repositories are public. The cost is up to 5 minutes from the merge to
the start of the build, which is small against the build.

## The watched repositories

The trigger set is the repositories whose tree `bt-layer` reads. Each one
maps to the lowest layer that it changes, in `conf/image-ci` of
`Keel-Linux/apt`:

| Repository | Layer | The build also makes |
| --- | --- | --- |
| `common` | core | every layer of the CI set |
| `keel-core` | core | every layer of the CI set |
| `keel-web` | web | lnmp, lnpp |
| `keel-lnmp` | lnmp | nothing more |
| `keel-lnpp` | lnpp | nothing more |
| `keel-mariadb` | mariadb | nothing more |
| `keel-postgresql` | postgresql | nothing more |
| `keel-redis` | redis | nothing more |

The CI set is core, web, lnmp, lnpp, mariadb, postgresql and redis.
nodejs-nginx, nodebb and wordpress are not in it until each one moves to
the current stack (0059).

**Package repositories do not trigger a build.** `keel`, `inithooks`,
`confconsole`, `keel-transition`, `keel-keys` and the package half of
`keel-web` and `keel-mariadb` reach an image only through the archive.
A layer installs its packages from the captured pool (0012), not from a
git tree. So a merge in a package repository does not change an image
until the package is in the archive and the pool is captured again.
`buildtasks` and `fab` are build tools. A person deploys them on the
build host, as before.

**So keel `main` does not enter an image.** A testing image carries the
keel package of the pool. This flow does not release keel. The keel
release waits for the BR3-THIN matrix, as planned.

## What "testing" means for an image

**Decided: a testing image is a promoted build on the build host. It is
signed by main and images, and it is not on a public server.**

- A promoted build is in `/srv/keel-ci/testing/<build-id>/`, with
  `layers/`, `images/` and a `MANIFEST` signed by main and images. The
  `MANIFEST` says `channel testing`, the build id, the commit of each
  watched repository and the URL of the run that passed.
- `/srv/keel-ci/testing/latest-<appliance>` points at the last promoted
  build of each appliance. A tester copies the `.tar.zst` from there, as
  for the step-12 pre-releases. Those pre-releases were built and signed
  by hand. This flow replaces them for every merge.
- **No Proxmox index.** A staged or promoted build has no `pve/`
  directory. `keel-release --staging` writes no index, so it cannot
  merge onto the published index or change it. The public index
  `releases.keellinux.org/pve/aplinfo.dat` stays as the last deliberate
  release left it.
- **No channel pointer moves.** The flow does not run `keel-channel set`.
  0016 says that a person moves a channel, and that stays true. A pointer
  that names a revision the mirror does not hold also stops the next
  `keel-publish-mirror` with exit 8.
- **Stable is not touched.** A stable release stays a deliberate act:
  `keel-release` and `keel-publish-mirror` by a person, as before.
- **Public delivery of the testing images is not decided here.** It needs
  a publication path that writes the mirror without a person, which 0016
  defers. It is its own decision.

The amendment to 0016 is therefore narrow: an unattended job may now sign
with the release keys, but only a promoted copy of a tested build, in the
CI tree, and it publishes nothing.

## Retention

- **Disk.** The build host had 21 GB free on 2026-10-16 (83% used). The
  CI tree keeps its own layer directory, about 7 GB. `keel-image-ci`
  refuses to start a build when less than 8 GB is free, and opens an
  issue.
- **Staged builds.** The build host keeps the last 3 staged builds and
  removes older ones. A staged build that is promoted shares its files
  with the promoted copy through hard links.
- **Promoted builds.** The build host keeps the last 3 promoted builds of
  each appliance, and always the build that each `latest-<appliance>`
  names.
- **The drop directory.** Each push replaces the whole drop directory
  (`rsync --delete`), so the runner VM holds one build at most.

## Failure

- **A build that fails** (`bt-layer`, `keel verify`, the key scan, the
  assembly): no hand-off and no promotion. The build host opens an issue
  in `Keel-Linux/image-gate` with the repositories, the commits and the
  last lines of the log.
- **A boot test that fails:** no promotion. The issue names the run URL.
- **A run that does not end** in 120 minutes: the build host stops
  waiting, promotes nothing and opens an issue.
- **A failed hand-off or dispatch:** no promotion, and an issue.
- **A busy build lock** (a person builds by hand): the poll stops and
  does not record the new heads, so the next poll tries again.
- **A head that changed again** during a build: the next poll builds it.
  The flow builds the newest head, not each commit.
- One issue for each failed build. The issue does not repeat while the
  heads do not change.

## Why this is better (brief section 10)

1. **Why the current approach is not enough.** No check boots the layer
   that a merge makes, and a testing image needs a person at the build
   host.
2. **Whether it can work.** `keel-release` already builds incrementally
   by parent digest and resumes, the staging key already signs unattended,
   and the runner already boots a layer chain without root
   (`unprivileged-lxc`).
3. **Why it is better.** Every merge that changes a layer gives a
   tested image signed by the release keys in about the time of the build,
   and the stable channel keeps its deliberate release.

## Measured while this note was written

- The build host reached `https://github.com` with HTTP 200 on
  2026-10-16. Earlier notes said that it could not. The flow does not
  depend on GitHub: it fetches from `git.pop.coop` only.
- A delta layer (web, lnmp, lnpp) took about 4 minutes in `bt-layer` on
  2026-10-16, and core about 8 minutes on 2026-10-12.

## Implementation

- `Keel-Linux/apt`: `keel-release --staging --match-source`,
  `bin/keel-image-ci`, `conf/image-ci`, the systemd units.
- `Keel-Linux/.github`: `bin/staged-release-verify`, and
  `ULX_NO_UPGRADE` in `bin/unprivileged-lxc`.
- `Keel-Linux/image-gate`: the workflow `image-boot.yml`.
- Infrastructure: the drop user on the runner VM, the bot user on
  Forgejo, the timer on the build host.
- Evidence: `docs/evidence/2026-10-16-image-per-merge.md`.
