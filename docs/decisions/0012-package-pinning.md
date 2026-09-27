# 0012: Pinning the packages an image is built from

Status: **accepted and implemented**, 2026-09-27. The proof is pending, and
the proof criterion needs an amendment the maintainer has to rule on; both
are in the last two sections. Needed by 0010, which is judged on equivalence
between two builds, and by the reproducibility claim the project makes about
itself.

## What is wrong today

`SOURCE_DATE_EPOCH` makes the squashfs and the ISO reproducible from one
`root.patched`, and `root.patched` itself is not reproducible, because nothing
says which package versions go into it. The daily self check has reported
`drift` every morning since it was switched on, for that reason and no other.
A signal that is always red is a signal nobody reads.

It also makes 0010 unmeasurable. Two control builds of the same recipe already
differ in 173 files, so "equivalent" currently means "equivalent within a
noise floor we did not choose".

## The three ways, and what each one actually promises

**Record the versions only.** Write the exact version of every package into
the layer manifest and pin with apt preferences. Cheap, and it is a promise
that cannot be kept: Debian removes superseded versions from the archive, and
`archive.turnkeylinux.org` keeps no snapshots at all, so within weeks the
recorded versions are no longer fetchable and the record documents an image
nobody can rebuild.

**Build against snapshot.debian.org.** Authoritative and signed, and it costs
us no storage. It also makes every build depend on a third party service that
is slow, rate limited and periodically unavailable, and it covers Debian only,
not the TurnKey packages our images install.

**Capture what we install into our own archive, per release.** Self contained,
fast, and it works with the machine offline. It costs storage and a step that
captures. For a project whose stated goal is a sovereign cloud, this is the
only one of the three that makes the claim true: being able to rebuild an
image without asking anybody's permission is what sovereignty means here.

## Proposed

All three, in their proper roles:

1. The exact versions are recorded in the layer manifest. That is the record,
   and it is what a rebuild compares against.
2. The `.deb` files those versions name are captured into a per release pool
   in our own archive, and a rebuild of that release installs from that pool.
   Scale: `core` installs 412 packages, `nodebb` 830, an installed footprint of
   831 MiB for core. The implementation measures the pool size as its first
   step, because that number decides whether a pool is kept per release or per
   milestone.
3. `snapshot.debian.org` is the recovery path for a package that predates the
   capture, not a build dependency.

## Proof

The daily self check reports `match` for `core` on two consecutive mornings,
having reported `drift` every morning before. Then the same for one appliance
layer. No other evidence counts: passing once can be luck, and the check is
the instrument the project already trusts for this question.

## What this does not cover

Reproducing `root.patched` bit for bit also needs install time state out of
the image, which is a separate matter already measured by the M0 gate: 49
differing files, all of them install time state. Pinning is the prerequisite,
not the whole answer, and the gate's allow list stays the record of what is
legitimately allowed to differ.

## The measurement that decided the shape

Taken first, as the proposal asks, on the build host on 2026-09-27, by
asking the archives what the exact installed versions of each built layer
would cost (`apt-get download --print-uris`, sizes summed):

| Layer | Packages | Offered | Size |
| --- | --- | --- | --- |
| `core` | 412 | 411 | 268.2 MiB |
| `nodejs-nginx` | 826 | 824 | 369.3 MiB |
| `nodebb` | 830 | 824 | 369.1 MiB |
| `mariadb` | 438 | 433 | 288.3 MiB |
| all four, union | | 847 files | 388.9 MiB |

The union is the number that decides, because the layers overlap almost
entirely: `nodebb` adds four packages to `nodejs-nginx`, and everything
sits on `core`. A whole release is 389 MiB, not five times 300.

So: **one pool per release, over one shared file store.** A file is named
by what it holds, `name_version_arch.deb`, and that name is immutable, so
two releases that install the same version share one copy on disk and each
release has its own index naming the subset it used. The first release
pays 389 MiB; a later one pays its delta, which for a week of Debian
security updates is a few megabytes, plus an index of a few hundred
kilobytes. Per milestone was the alternative the proposal left open. It is
not needed: per release costs almost the same and is worth more, because
the pool a release names can be verified against that release alone.

Measured after the first capture: `/srv/keel-pool` holds 272 MiB for
`core`, captured in 80 seconds.

## What was built

`repos/apt`, commit `ad1e0ad`, and one line group in `common`
(`removelists-final/turnkey`, commit `897ad4c`).

- **The versions are recorded.** `keel-release` reads the exact name,
  version and architecture of every installed package out of the built
  layer, writes them beside the manifest as `<layer>.packages`, publishes
  that file with the layer, and adds `packages`, `packages_sha256` and
  `pool` to the manifest `bt-layer` wrote. No change was needed in
  buildtasks.
- **The files are captured and verifiable.** `bin/keel-pool capture` asks
  the archives for the files those exact versions name and checks each one
  twice before it is stored: against the SHA256 the archive states, and
  against its own control fields, so a file that is not the package the
  manifest names is refused rather than pooled. The digest is kept with
  the file in `dists/<id>/files` and in the `Packages` index, which means
  apt checks it again on every use, and `keel-pool verify` checks the
  whole pool against the same digests on demand.
- **A rebuild installs from the capture.** The pool is hard linked into
  the tree a build starts from (the bootstrap for a rootfs layer, the
  parent layer's rootfs for a child) with an apt source that reads it over
  a `file:` URI and a pin at priority 1001, above 1000 so a captured
  version wins even when it is lower than what the live archives now
  offer. No server and no network: a build works with the machine
  offline, which is the whole argument for capturing rather than leaning
  on snapshot.debian.org. `keel-release` and `keel-selfcheck` take the
  three paths back out of the build tree afterwards, and
  `common/removelists-final/turnkey` takes them out of the image, beside
  the build-only apt configuration it already removed.
- **The TurnKey packages are captured the same way**, which is the point
  of doing this now: `archive.turnkeylinux.org` keeps no snapshots, so
  its packages are the ones that vanish first and the capture is the only
  copy that will exist.

One package of `core` cannot be captured and is recorded in
`dists/<id>/gaps`: `turnkey-core-19.0` version 1, which no archive has
because fab builds it inside the chroot from the product version. A gap is
recorded, not fatal; the recovery path for a gap is snapshot.debian.org,
and for this one it is the build itself.

## The instrument gained a second dimension

`keel-selfcheck` now compares two things and needs both to be green for a
`match`: the digest of the tarball, which is the whole layer, and the
digest of the package list, which is what this decision pins. They are
reported apart, in `STATUS` and in `reproducibility.json`, because they
fail for different reasons and one word would hide it. `packages=drift`
means the pool was not used or no longer holds what the manifest names.
`packages=match` under a tarball that differs means the versions were
held and what is left is install-time state.

Nothing was relaxed: drift in either dimension is still `drift` and still
exits 1.

## What was run on 2026-09-27, and what it showed

Pool `2026-09-27` was captured from the rootfs of the 03:36 self check
build, the build the reference digest came from: 411 members, 272 MiB,
80 seconds, `keel-pool verify` 411 members and 0 bad.

`keel-selfcheck --reseed` then rebuilt `core` at epoch 1700000000 pointed
at that pool, 05:10 to 05:17 UTC, 404 seconds:

| | |
| --- | --- |
| packages fetched from `file:/keel-pool` | 302 |
| packages fetched over http | 0; every http line in the log is an index file |
| tarball | 326,435,084 bytes, `ad7c07b760b8e510b621f73c263d248862bc5db065ce2b796b1b930bd2042672` |
| recorded before this run | `71ea76df6dcc4c5ed7cf20807872a93b82915de8f9062ec0b4051368211f8ca1` |
| package list | 412 packages, `4918887db3562d3179fea536999fb7149e25e466e28e1b51778c962913a19c9c` |
| the same list, read from the build the pool was captured from | `4918887db3562d3179fea536999fb7149e25e466e28e1b51778c962913a19c9c` |

So the two digests say different things and both are the point. Every
package the build installed came out of the pool, and the package list is
identical to the one recorded, to the character: the pinning holds. The
tarball is not the one recorded, and that difference is not packages.

A second measurement fell out of the evening by accident and is worth
keeping. The first attempt built against `/turnkey/fab` because an ssh
session carries `FAB_PATH` (see build-host.md), which meant the upstream
`common` and therefore no `removelists-final` entry for the pool: the
tarball came out at 606,186,229 bytes instead of 326,435,084, with the
hard linked pool inside it. The removelist line is load bearing, and a
build that loses it says so loudly rather than quietly.

## The proof, pending

**Pending. First confirmable on 2026-09-29.** The daily timer runs at
03:40 UTC; the two consecutive mornings are 2026-09-28 and 2026-09-29.
The reference they compare against was seeded on 2026-09-27 at 05:17 UTC
by the run above, and a drift run does not overwrite it, so the second
morning compares against the same reference as the first. A release that
rebuilds `core` before then drops the reference on purpose and the count
starts again.

The check is pinned to the pool for now by a systemd drop-in,
`/etc/systemd/system/keel-selfcheck.service.d/pool.conf`, and not by
`/srv/keel-pool/current`, because `current` would point the attended
release path at the pool too and that is the maintainer's call to make
deliberately, with `keel-pool current 2026-09-27`.

### The criterion needs an amendment, and here is the evidence

This note asks for `match`, meaning the tarball digest. Pinning alone
cannot produce it, and the measurement above is the proof: two builds of
`core` made 90 minutes apart installed the identical 412 packages, name
and version, and still packed different tarballs. The M0 gate measured
the same thing from the other side on 2026-09-26, 49 differing files out
of 33,684, every one of them install-time state: host keys, logs, the
initramfs, webmin state, a postfix pid. None of that is a package
version, and none of it is what this decision fixes.

So the criterion splits in two, and the maintainer should rule on the
split rather than have it assumed:

- **`packages=match` on two consecutive mornings proves this decision.**
  Confirmable 2026-09-29.
- **`status=match` on two consecutive mornings proves this decision and
  the install-time state work together**, which is part 3 of m0-gate.md
  and is not scheduled. Until then the daily unit keeps failing, which is
  honest: the layer is not reproducible yet, only its package set is.

Recording it any other way would mean either declaring victory on a
number that cannot go green, or quietly narrowing what the check
measures. The second dimension exists so that neither is necessary.
