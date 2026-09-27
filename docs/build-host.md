# Build host

Date: 2026-09-26. The machine that runs the M0 gate (m0-gate.md) and, until
the self-hosted runner of ci-cd.md section 6 exists, every appliance build.

## 1. What it is

A TKLDev 19.0 virtual machine (Debian trixie, kernel 6.12.107+deb13-amd64,
8 processors, 59 GB root filesystem), reachable as
`root@2804:710:d0:5:bb3f:380a:f07b:7951` by key. `postfix` is inactive on
the host and has to stay so: the build chroot shares the host network and
`postfix-local` refuses to run when port 25 is taken (../TKL/plan/02, issue
D). For the same reason two builds never run at the same time.

Trees on the host:

| Path | Content | Rule |
| --- | --- | --- |
| `/turnkey/fab` | upstream reference tree (turnkeylinux/common, cdroots, products/core, bootstraps/trixie-amd64) | read-only for the project; only the reference build writes `products/core/build` |
| `/turnkey/fab-keel` | project tree, cloned by the organization's tkldev-setup from `https://github.com/keel-linux` | the tree every project build uses; `products/core` is the checkout of `keel-core` (the directory name must stay `core`, see m0-gate.md) |
| `/turnkey/buildtasks-keel`, `/turnkey/tklbam-profiles-keel` | project forks of buildtasks and tklbam-profiles | `BT_PATH` and `TKLBAM_PATH` for the project tree |
| `/root/keel-tkldev-setup` | the organization's tkldev-setup script (keel-linux/tkldev master) | the system copy in `/usr/bin` is upstream's and stays untouched |
| `/root/src/fab` | clone of `https://github.com/keel-linux/fab.git`, branch `pkg/keel1` | source of the installed fab package, section 2 |
| `/root/gate2.sh` | one packing run of gate 2 | section 4 |

Environment for a project build:

```
export FAB_PATH=/turnkey/fab-keel RELEASE=debian/trixie FAB_ARCH=amd64
export GIT_REMOTE_URL=https://github.com/keel-linux
export BT_PATH=/turnkey/buildtasks-keel TKLBAM_PATH=/turnkey/tklbam-profiles-keel
export SOURCE_DATE_EPOCH=1700000000   # for a reproducibility run; omit for a normal build
```

## 2. Which packages come from where

The build tools are Debian packages. Everything comes from the TurnKey
archive or from Debian except fab, which the project builds itself because
the host needs the fork's `share/product.mk` (the `SOURCE_DATE_EPOCH` handling
that the ISO half of the packing gate depends on).

| Package | Version on the host | Origin |
| --- | --- | --- |
| fab | 1.1.1+keel1 | project, built from keel-linux/fab branch `pkg/keel1`, installed from the local .deb and pinned (section 3) |
| deck | 2.1.1 | archive.turnkeylinux.org, trixie/main |
| pool | 1.2.1 | archive.turnkeylinux.org, trixie/main |
| turnkey-chroot | 1.1.2 | archive.turnkeylinux.org, trixie/main |
| debootstrap | 1.0.141 | Debian trixie |
| squashfs-tools | 1:4.6.1-1 | Debian trixie |
| xorriso | 1.5.6-1.2+b1 | Debian trixie |
| syslinux-utils | 3:6.04~git20190206.bf6db5b4+dfsg1-3.1 | Debian trixie |

Versioning follows BRIEF.md section 7: a package the project rebuilds from
an upstream version carries the `+keel1` suffix (then `+keel2` and so on) and
is held by a pin, never by an epoch. Until the project APT repository of
brief section 9 exists the package is installed from the file; the pin is
what keeps `apt-get upgrade` from putting upstream 1.1.1 back.

The fab source repository carries no `debian/changelog`; upstream generates
one at build time (the archive package says `1.1.1 UNRELEASED, undocumented`)
and ignores the file in `debian/.gitignore`. Branch `pkg/keel1` adds the
file, removes the ignore rule and adds `python3-setuptools` to
`Build-Depends` (pyproject.toml uses the setuptools backend and the build
fails without it). The branch is local to the host until it is pushed and
reviewed as a pull request; the diff is in m0-gate-run-2026-09-26.md.

The installed package has the same file list as upstream's 1.1.1; the
content differs only in `/usr/share/fab/product.mk` (and the version). The
`.deb` built on 2026-09-26 has sha256
`f4bf09be9535c01bbf7813c35ae482ee99105016780584671acb6da00b7859e5`.

## 3. The pin

`/etc/apt/preferences.d/keel-fab`:

```
Package: fab
Pin: version 1.1.1+keel1*
Pin-Priority: 1001
```

Priority 1001 wins over the archive's 999 even when the archive publishes a
higher version, so an upstream 1.1.2 will not be installed by accident; it
shows up in `apt-cache policy fab` and is picked up by rebuilding
(section 4) on a rebased branch. Checks:

```
dpkg -l fab                       # ii  fab  1.1.1+keel1  all
apt-cache policy fab              # Installed and Candidate 1.1.1+keel1, pin 1001
apt-get -s upgrade | grep fab     # nothing
grep -n ISOHYBRID_OPTS /usr/share/fab/product.mk
```

## 4. Rebuilding and reinstalling fab when the fork changes

Build dependencies (installed once, `apt-get build-dep -y ./` reads them from
`debian/control`): debhelper, dh-python, pybuild-plugin-pyproject,
python3-all, python3-setuptools, python3-debian.

```
cd /root/src/fab
git fetch origin
git checkout pkg/keel1
git rebase origin/master            # or merge; the branch only carries debian/
# bump debian/changelog: 1.1.1+keel2, distribution trixie, one line per change,
# maintainer "Keel Linux maintainers <admin@keellinux.org>"
apt-get build-dep -y ./
dpkg-buildpackage -us -uc -b
apt-get install -y ../fab_1.1.1+keel2_all.deb
sed -i 's/^Pin: version .*/Pin: version 1.1.1+keel2*/' /etc/apt/preferences.d/keel-fab
dpkg -l fab && apt-cache policy fab | head -4
```

When upstream releases a new fab, rebase onto the tag, set the version to
`<upstream>+keel1` and update the pin the same way. Once the project APT
repository exists the pin becomes an origin pin and the local install step
goes away; the build steps stay.

## 5. Packing gate with the project's fab

Procedure (m0-gate.md, gate 2), run from `/turnkey/fab-keel/products/core`
after a full build, with the environment of section 1 and
`SOURCE_DATE_EPOCH=1700000000`. `/root/gate2.sh <label> [epoch]` does one
run:

```
deck --ismounted build/root.patched || deck build/root.patched
rm -f build/stamps/cdroot build/stamps/root.sandbox build/product.iso
rm -rf build/cdroot
make
sha256sum build/product.iso build/cdroot/live/10root.squashfs
```

The `deck` line matters. `mksquashfs` reads `build/root.patched`, and
layering `root.sandbox` on that deck releases its mount, so a run that
removes the `root.sandbox` stamp without remounting first packs an empty
tree: the squashfs is 4,096 bytes (sha256 `8c339c02...` with the epoch), the
ISO 56,623,104 bytes, and `make` finishes in two seconds. Sizes to expect
for core are 385,646,592 bytes for the squashfs and 442,499,072 for the ISO.

Result, 2026-09-26, fab 1.1.1+keel1, same `root.patched` as the first gate
run (its squashfs hash is unchanged):

| Run | SOURCE_DATE_EPOCH | `build/product.iso` sha256 | `build/cdroot/live/10root.squashfs` sha256 |
| --- | --- | --- | --- |
| 1 | 1700000000 | ab615ac60ac19148a56adbc3506ac53da6733bda2760d759588c552263e6b22b | 47ed341d65f0f93bae6a304cabad839035d85b1f662616db63ca4f6fb8942801 |
| 2 | 1700000000 | ab615ac60ac19148a56adbc3506ac53da6733bda2760d759588c552263e6b22b | 47ed341d65f0f93bae6a304cabad839035d85b1f662616db63ca4f6fb8942801 |
| control | unset | df9ba299babe90036f756a4262b98e246c14c7686f5e5c13f7732add263cd28b | 4d9f6f5624509d1966657a7163d708e09aa7c147c3abe9803f7640ce788d2ba3 |

Runs 1 and 2: `cmp` reports no difference (0 bytes). The `make` log shows
`xorriso -as mkisofs ... --set_all_file_dates @1700000000` and
`isohybrid --id 1700000000`; without the variable both options are absent,
the build works, and the hashes differ from run to run as before. Gate 2 is
met for the squashfs and the ISO. What remains for full reproducibility is
`root.patched` itself (m0-gate.md, part 3).

## The build host is not a public server (2026-09-26)

It builds the appliances and it is where the signing subkey goes
(decision 0005), so nothing on it is exposed to the network except SSH.
The temporary mirror that served
`http://[2804:710:d0:5:bb3f:380a:f07b:7951]:8080/` for internal evaluation
was retired on 2026-09-26, when mirror.keellinux.org started serving the
same content: nginx now listens on `[::1]:8080` and `127.0.0.1:8080` only
(`/etc/nginx/sites-available/keel-releases`, kept in git as
`repos/apt/infra/build-host/nginx-keel-internal.conf`), and the header it
sends reads `internal, build host, not a public mirror`. Checked from a
workstation the same day: the port does not answer.

What that block serves, to the loopback:

| Path | Tree |
| --- | --- |
| `/release/` | `/srv/keel-release`, what `bin/keel-release` stages, including `selfcheck/` |
| `/layers/` | `/mnt/builds/layers`, the bt-layer outputs |
| `/apt/` | `/srv/keel-apt/repo`, the reprepro tree |
| `/pve/` | `/srv/keel-www/pve` |

The public services VM reaches it only through a forward that the
maintainer's own session opens, because the VM pulls and neither machine
holds a key on the other:

```
ssh -N -L [::1]:18080:[::1]:8080 root@2804:710:d0:5:bb3f:380a:f07b:7951
ssh -6 -R 18080:[::1]:18080 popsolutions@keellinux.org 'wget -6 http://[::1]:18080/release/...'
```

`repos/apt/bin/keel-publish-mirror` does both ends and verifies the public
names afterwards. TurnKey's hardening sets `AllowTcpForwarding no`; the
first end needs it, so `/etc/ssh/sshd_config.d/00-keel-release.conf` sets
`AllowTcpForwarding local`, which allows `-L` and keeps `-R` refused. The
file has to sort before `turnkey.conf`, since sshd uses the first value it
obtains for a keyword.

## The release path

```
ssh root@2804:710:d0:5:bb3f:380a:f07b:7951 'TERM=dumb /srv/keel-apt/apt/bin/keel-release core'
./bin/keel-publish-mirror --unsigned-staging <date>       # from a workstation
```

`/srv/keel-apt/apt` is the checkout of the apt tooling repository on this
host. `/etc/keel-apt.conf` holds the paths specific to this machine, today
only `KEEL_BT_APLINFO`, because `bt-aplinfo` lives on branch
`feat/bt-aplinfo` of keel-linux/buildtasks and is checked out as a git
worktree at `/turnkey/buildtasks-aplinfo` so the 19.x tree the builds use
is untouched. Drop that line when the branch is merged.

`/turnkey/buildtasks-keel/config/common.cfg` is the host's own copy of
`config.example/common.cfg` and is not in git. Three of its lines were
changed on 2026-09-26 so the environment can override them (`BT_BUILDS`,
`BT_PRODUCTS`) and so the host stops claiming a key that is not ours: the
example ships `BT_GPGKEY=26147592087C0EDE42143B637761DEBABBCFBA7C`, which
is TurnKey's, and `bin/generate-signature` uses it to write a `.hash` file
that tells the reader to verify with the TurnKey release key and contains
no signature at all. `BT_GPGKEY` is now empty unless the caller sets one,
`keel-release` calls `bt-layer` with it cleared, and the digests and
signatures a release publishes are written by `keel-release` itself.

Measured on 2026-09-26: a first `keel-release core` reused the layer built
on 2026-09-24 (its tarball still matched its manifest), verified it,
assembled the template and staged nine artifacts; a second run with
`--force` produced the same template byte for byte
(`e08e8224aeea1abb605b0e359d345f459d2e04d413e6a08c5e57f5b7858c9e19`, which
is also the layer's own digest, since `core` is a single rootfs layer and
`keel assemble` repacks it deterministically). A run started while the
self check held the lock exited 4 without touching anything.

## Daily reproducibility self check

`keel-selfcheck.timer` runs `/srv/keel-apt/apt/bin/keel-selfcheck` once a
day at 03:30 UTC with up to 30 minutes of jitter. It rebuilds `core` with
`SOURCE_DATE_EPOCH=1700000000`, the epoch of the packing gate, into its own
`BT_BUILDS` tree (`/srv/keel-selfcheck/builds`, never `/mnt/builds`), and
compares the tarball digest with the one recorded in
`/srv/keel-release/selfcheck/reference`. The result is
`/srv/keel-release/selfcheck/reproducibility.json` and a one line `STATUS`,
which the mirror serves and `keel-publish-mirror` carries to
`https://mirror.keellinux.org/selfcheck/` with each publication.

Since 2026-09-27 it measures two things and needs both to be green for a
`match`: the digest of the tarball, and the digest of the package list of
the rebuilt layer, which is what the pinning of decision 0012 holds. The
reference file gained a fourth field for the second digest, `STATUS` gained
`packages=<status>` and `reproducibility.json` gained `packages`,
`expected_packages_sha256`, `actual_packages_sha256` and `pool`.

It takes the same lock `keel-release` takes and also looks for a build
started by hand (`bt-layer`, `fab-chroot`, `mksquashfs`, `debootstrap`);
when either says a build is going it skips, says why and records
`"status": "skipped"`, because two builds must never run at once on this
host. Drift exits 1, so the unit fails and `systemctl --failed` shows it.

First real run, 2026-09-26 19:31 UTC: **drift**, and it is the expected
drift. `core` rebuilt at epoch 1700000000 in 450 seconds gives sha256
`76e76e4b12f4ffb3718ce207458420191d783710a1bbcc20bba0d97bfae351b0`; the
layer published on 2026-09-24 records
`e08e8224aeea1abb605b0e359d345f459d2e04d413e6a08c5e57f5b7858c9e19`. That is
exactly part 3 of m0-gate.md: `SOURCE_DATE_EPOCH` makes the squashfs and the
ISO reproducible from one `root.patched`, but `root.patched` itself is not,
because package versions are not pinned and install-time state is written
into the image. The check does not fix that; it measures it every day and
says so in one line, so the day the package freeze lands the number becomes
`match` and any later regression is visible the next morning.

## The captured package pool

`/srv/keel-pool` holds the `.deb` files a release was built from (decision
0012), captured by `/srv/keel-apt/apt/bin/keel-pool` and not in git. One
shared file store, `pool/main/<prefix>/<name>/`, and one index per pool id
under `dists/<id>/`, whose `files` names every member with its sha256.
`current` names the pool a build is pointed at; `/etc/keel-apt.conf` can
override it with `KEEL_POOL_ID`.

```
keel-pool current 2026-09-27
keel-pool capture core --rootfs /srv/keel-selfcheck/builds/layers/core.rootfs
keel-pool verify
```

`keel-release` and `keel-selfcheck` point a build at it by hard linking the
pool into the tree the build starts from, `/turnkey/fab-keel/bootstraps/
trixie-amd64` for `core` and `<parent>.rootfs` for a child layer, with
`/etc/apt/sources.list.d/keel-pool.sources` reading it over a `file:` URI
and `/etc/apt/preferences.d/keel-pool` pinning it at 1001. They take the
three paths back out of the build tree afterwards, and
`common/removelists-final/turnkey` takes them out of the image. Hard links,
so pointing a build costs no disk: `/srv` and `/turnkey` are the same
filesystem here, and `keel-pool point` copies instead and says so when they
are not.

Measured on 2026-09-27: 411 of the 412 packages of `core` are 272 MiB on
disk, captured in 80 seconds. The one that cannot be captured is
`turnkey-core-19.0`, which fab builds inside the chroot; it is recorded in
`dists/<id>/gaps`.

## The build environment is not the operator's environment (2026-09-27)

An ssh session to this host carries `FAB_PATH=/turnkey/fab` in its
environment. The release tooling used to fall back to it, so
`keel-release` run over ssh built against the **upstream** `common` and the
upstream bootstrap, while the daily timer, which systemd starts with a
clean environment, built against `/turnkey/fab-keel`. Two builds of the
same layer then differ for a reason nothing records: the layer in
`/mnt/builds` records `common_commit b60dd230`, which is not the project
common. Fixed in the tooling (`KEEL_FAB_PATH` and its four siblings no
longer read the build variables); a machine that needs another path says so
in `/etc/keel-apt.conf`. Anything built over ssh before that date was built
against the upstream tree.

Rebuilding this machine from a fresh Debian 13, and what on it is not in
git: docs/infra-recovery.md.
