# 0060: Keel images for Incus, from Keel's own simplestreams remote

Date: 2026-10-16
Status: **proposed: a plan for when all applications are released as
stable on Keel's own image server.** The maintainer said on 2026-10-16:
"anota no adr como plano para quando tivermos todas as aplicações stable
lançadas no nosso servidor". Nothing in this note starts before the
trigger of step 2.

## Goal

Incus users consume Keel images. A user adds one remote and launches a
Keel container or a Keel VM with `incus launch`, as with any other
distribution.

## What we found (research of 2026-10-16)

The research asked one question: can Keel images go on the public
remote of Incus, `images.linuxcontainers.org`?

1. **Only the lab of the project builds and publishes the images.**
   `lxc/lxc-ci` builds the remote in the lab of Stéphane Graber
   (stgraber). In lxc-ci#959 he wrote: "We won't publish images that have
   been built in 3rd party environments."
   <https://github.com/lxc/lxc-ci/issues/959>
2. **No written policy exists.** No document in `lxc/lxc-ci` says which
   distributions go on the remote. stgraber decides each request.
3. **The project usually refuses a small derivative.** In lxc-ci#923 (secureblue)
   he wrote: "Building images, storing them and distributing them is both
   very time consuming and costly, so doing that for a small derivative
   of a major distro rarely makes sense. We also usually want to provide
   both container and VM images whenever possible."
   <https://github.com/lxc/lxc-ci/issues/923>
4. **The remote has no appliance images.** Each image is a base system
   of a distribution. No image carries an application stack.
5. **The project removes a distribution that nobody maintains.**
   Examples, from the git history of lxc-ci:
   - Funtoo, 2025-11-29:
     <https://github.com/lxc/lxc-ci/commit/f15f50a0bf8c859f6bc704a6679c055b2582d5aa>
   - Springdale Linux, 2026-04-04:
     <https://github.com/lxc/lxc-ci/commit/899653b35a7e22741b7d449c3fdbba5ef61f73f0>
   - Apertis, 2026-08-27:
     <https://github.com/lxc/lxc-ci/commit/5b364d29d6812b984b2487599c84605084c6d67e>
6. **The project accepted some requests.** The precedents:

   | Distribution | Request |
   | --- | --- |
   | openEuler | <https://github.com/lxc/lxc-ci/issues/649> |
   | Slackware | <https://github.com/lxc/lxc-ci/issues/778> |
   | NetBSD | <https://github.com/lxc/lxc-ci/issues/1011> |
   | Plamo | <https://github.com/lxc/lxc-ci/issues/1017> |
   | CachyOS | <https://github.com/lxc/lxc-ci/issues/1021> |

**Result.** stgraber would likely refuse a request for the keel-core
base now: Keel is a small derivative of Debian, with no outside users yet.
The appliances are out of scope on that remote in all cases.

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel publishes images
   for Proxmox only (`releases.keellinux.org/pve/aplinfo.dat`, and the
   files on `mirror.keellinux.org`, docs/releases-host.md). An Incus user
   cannot add a Keel remote. The public remote of Incus does not accept
   Keel now, as the research shows.
2. **Whether it can be made to work.** It can. Incus reads any
   simplestreams server over HTTPS. `distrobuilder` builds container and
   VM images from a YAML definition, and `incus-simplestreams` writes
   the index of the server. lxc-ci builds its own images with
   distrobuilder.
   The public services host already serves static files over HTTPS
   with a certificate from Let's Encrypt.
3. **Why this is better.** Keel controls its own remote, its release
   cadence and its appliances. The definition uses the format of lxc-ci,
   so the same file can go to lxc-ci later with no rewrite.

## The plan, in order

### Step 1: Keel's own simplestreams remote

1. **The name is `images.keellinux.org`.** It is a CNAME to the apex, as
   the other names are (docs/releases-host.md, section 2). The name goes
   into the SANs of the certificate of the host. It serves static files
   only.
2. **distrobuilder builds the images from one definition.** The file is
   in the format of lxc-ci (`images/keel.yaml` style):
   - The source is `debootstrap`, suite `trixie`.
   - The Keel archive (`archive.keellinux.org`) and the
     `keel-archive-keyring` package go in early, before any Keel
     package.
   - The `default` variant uses `systemd-networkd` and
     `systemd-resolved`.
   - The `cloud` variant adds `cloud-init`.
   - The VM image adds `incus-agent`.
   - Architecture: `amd64` first. Other architectures come later.
3. **`incus-simplestreams` publishes the images.** It adds each
   container and VM image to the tree and writes the index.
4. **The checks of lxc-ci test each image.** `bin/test-image` of
   `lxc/lxc-ci` runs on a container and on a VM of each variant:
   - `systemctl --failed` is empty.
   - The instance has IPv4 and IPv6.
   - DNS resolves names.
   - `cloud-init` applies user data and vendor data (`cloud` variant).
   - The instance stops cleanly.

   Each run on the real platform ships an evidence file (0053).
5. **The user adds the remote with one command:**

   ```
   incus remote add keel https://images.keellinux.org --protocol=simplestreams
   ```

6. **The trust model is HTTPS and a sha256 in the index.** Incus checks
   the TLS certificate of the server and the sha256 of each file that
   the index lists. simplestreams has no GPG signature. The evidence
   file and the page of the remote must say this. What Keel signs stays
   as 0055 says: the APT archive with the archive keys, and the layer
   `.hash` files, the release `MANIFEST` and the Proxmox
   `aplinfo.dat.asc` with the `images` key, together with main until
   every verifier trusts `images`. A later change can sign the
   simplestreams index with the `images` key and publish the signature
   beside it, so that a careful user can check it.
7. **The first boot does not wait for a console.** An Incus instance
   usually has nobody at its console. The first boot runs unattended,
   as inithooks#47 makes it do
   (docs/evidence/2026-10-15-inithooks-first-boot-again.md). The secrets and the domain come from
   `cloud-init` or from a keel spec. If neither gives a secret, the
   hook does not stop the boot. It writes 1 line and exits, as
   `35pgsqlpass` does after common#55.

### Step 2: the trigger to start

Step 1 starts when all applications are released as stable on Keel's
own Proxmox image server (`releases.keellinux.org`, `mirror.keellinux.org`).
Until then, work on the Proxmox images comes first.

### Step 3: later, when Keel has outside users

1. **First an issue on `lxc/lxc-ci`, for the keel-core base only.** The
   issue comes before any pull request. It gives:
   - The definition, which already passes the `bin/test-image` checks,
     with the evidence.
   - A named maintainer for the image.
   - The release cadence of Keel.
2. **A pull request only if stgraber agrees.** It adds
   `images/keel.yaml` and `jenkins/jobs/image-keel.yaml`. Each commit
   has a DCO sign-off (`Signed-off-by:`), as lxc-ci requires.
3. **The appliances stay on Keel's remote.** They do not go to lxc-ci.

## Open questions

1. Does the remote also serve the appliances (LNMP, LNPP, WordPress and
   the others of 0059), or the keel-core base only at first?
2. Which tool runs the build: the build host with `keel-release`, or a
   new job on the Keel runners? The build of a VM image needs
   `/dev/kvm` on the runner.
3. Which Incus version is the minimum that Keel tests and supports?
4. How many old versions of each image does the remote keep, and how
   does a withdrawal remove one?
5. Does Keel sign the simplestreams index with the `images` key (step 1,
   item 6), and does a Keel tool check that signature?
6. Does `images.keellinux.org` stay on the public services host, or go
   to a host of its own when the files get large?
7. Who is the named maintainer of step 3?

## When to revisit

- When all applications are released as stable on the Proxmox image
  server: this note becomes a decision, and step 1 starts.
- When Keel has outside users who ask for Incus images: step 3.
- If lxc-ci publishes a written policy for new distributions.
