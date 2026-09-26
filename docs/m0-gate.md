# M0 gate: build unmodified 19.0 from the project forks

Brief section 9: "The project build of *unmodified* 19.0 reproduces upstream
artifacts before any change. Nothing else ships until this passes."

This note fixes what "reproduces" can mean today, the exact procedure, and
the allow-list of expected differences. First run: 2026-09-26, see
m0-gate-run-2026-09-26.md.

## What can and cannot be compared

Comparing our build byte for byte against the published 19.0 ISO is not
achievable and is not the gate. The published artifacts were built at an
unknown time, against apt archives whose contents have moved since, with no
build metadata published (`.manifest` and `.buildenv` are 404 on the mirror for
the 19.0 ISOs, checked 2026-09-22). Two facts from ../TKL/plan/06 bound what is
possible:

- From the same `root.patched`, the squashfs is bit-for-bit reproducible once
  `SOURCE_DATE_EPOCH` is set. The ISO is not yet, with the fab 1.1.1 package
  the build host installs: `isohybrid` writes a random MBR ID and xorriso
  keeps the mtimes of files copied at packing time (measured 2026-09-26:
  178 differing bytes between two packings). The fork of fab fixes both in
  `share/product.mk`; the gate is re-measured once that package is what the
  host installs.
- `root.patched` itself is not yet reproducible: package versions are not
  pinned and install-time state (host keys, logs, pids, webmin state) is
  written into the image.

So the gate is stated in three parts, in increasing strength:

1. **Equivalence gate (M0).** A build from the project forks produces an
   appliance whose package set and file tree match a build from the upstream
   repositories, made on the same host, within the documented allow-list of
   differences below. No change of ours may add a difference outside that
   list. Passed on 2026-09-26.
2. **Packing gate (M0).** With a fixed `SOURCE_DATE_EPOCH`, two runs from the
   same `root.patched` give identical squashfs and ISO hashes. Met on
   2026-09-26 for both, with fab 1.1.1+keel1 installed on the build host and a
   real tree (33,684 files): squashfs 47ed341d..., ISO ab615ac6..., identical
   over two packings. The 2026-09-22 squashfs figure was an empty tree and
   does not count; always check `mountpoint build/root.patched` and record
   sizes next to hashes.
3. **Full reproducibility (M2/M3).** Same commit plus same manifest gives the
   same bytes, including `root.patched`. Needs the package freeze and the
   install-time state work, both in ../TKL/plan/06.

## Procedure

Run on the project build host (TKLDev 19.0 VM). `postfix` must be stopped
(upstream bug, see ../TKL/plan/02, issue D; the chroot shares the host
network and `postfix-local` refuses to run when port 25 is taken) and the
trixie bootstrap has to exist locally, since the mirror does not publish it
(issue A). Builds take 5 to 6 minutes each and must not run concurrently,
for the same port 25 reason.

Upstream reference build:

```
export FAB_PATH=/turnkey/fab RELEASE=debian/trixie FAB_ARCH=amd64
export SOURCE_DATE_EPOCH=1700000000
tkldev-setup core
cd $FAB_PATH/products/core
make clean && make
sha256sum build/product.iso build/cdroot/live/10root.squashfs
deck build/root.patched
(cd build/root.patched && find . -xdev -type f | sort | xargs -d '\n' sha256sum) > /root/tree-upstream.sha256
chroot build/root.patched dpkg-query -W -f '${Package}\t${Version}\n' | sort > /root/pkgs-upstream.tsv
```

Fork build, in a separate `FAB_PATH` so the two trees never mix. The
organization's `tkldev-setup` (keel-linux/tkldev master) maps appliance
`core` to the repository `keel-core` and still checks it out as
`products/core`; the directory name must stay `core` because product.mk
takes `ISOLABEL` and turnkey.mk takes `HOSTNAME` from the directory
basename. The organization has no `bootstrap` repository, so copy the
bootstrap into the new tree before `tkldev-setup` runs, otherwise its local
bootstrap build fails on the missing clone:

```
export FAB_PATH=/turnkey/fab-keel RELEASE=debian/trixie FAB_ARCH=amd64
export SOURCE_DATE_EPOCH=1700000000
export GIT_REMOTE_URL=https://github.com/keel-linux
export BT_PATH=/turnkey/buildtasks-keel TKLBAM_PATH=/turnkey/tklbam-profiles-keel
mkdir -p $FAB_PATH/bootstraps && cp -a /turnkey/fab/bootstraps/trixie-amd64 $FAB_PATH/bootstraps/
tkldev-setup core
cd $FAB_PATH/products/core
make clean && make
sha256sum build/product.iso build/cdroot/live/10root.squashfs
deck build/root.patched
(cd build/root.patched && find . -xdev -type f | sort | xargs -d '\n' sha256sum) > /root/tree-keel.sha256
chroot build/root.patched dpkg-query -W -f '${Package}\t${Version}\n' | sort > /root/pkgs-keel.tsv
```

`deck build/root.patched` is required: after a full build the deck's
mount is released when `root.sandbox` is layered on it and the directory
reads as empty. Compare:

```
diff /root/pkgs-upstream.tsv /root/pkgs-keel.tsv
diff /root/tree-upstream.sha256 /root/tree-keel.sha256 | grep '^[<>]' | awk '{print $3}' | sort -u
```

Packing gate, from the fork tree once the build is done:

```
sha256sum build/product.iso build/cdroot/live/10root.squashfs
rm -f build/stamps/cdroot build/product.iso && rm -rf build/cdroot && make
sha256sum build/product.iso build/cdroot/live/10root.squashfs
```

The package diff must be empty. The file diff must contain only paths on the
allow-list below; anything else is a finding to investigate before M1 starts.

## Allow-list of expected differences (frozen 2026-09-26)

Observed on the first run: 49 of 33,684 regular files, 412 packages
identical, symlinks identical. Every entry is install-time state (clock,
process id, random source, Perl hash order). Entries and what may differ:

| Path pattern | Allowed difference |
| --- | --- |
| `/etc/ssh/ssh_host_*` | generated host keys |
| `/var/log/*` | log content |
| `/var/cache/*` | ldconfig aux-cache and similar caches |
| `/boot/initrd*` | initramfs built without the epoch inside the chroot |
| `/etc/webmin/config`, `/etc/webmin/miniserv.conf`, `/etc/webmin/*/config` | line order only; the files must be identical after `sort` |
| `/etc/webmin/miniserv.pem` | generated TLS key and certificate |
| `/etc/webmin/webmincron/crons/*.cron` | file name and `id=` line (time-based ids); the other lines must match pairwise |
| `/var/webmin/module.infos.cache` | line order and the `mtime_/usr/share/webmin` value |
| `/var/webmin/webmin.log.time` | timestamp |
| `/etc/aliases.db` | Berkeley DB header bytes (creation time, log sequence number) |
| `/var/lib/postfix/master.lock`, `/var/spool/postfix/pid/master.pid` | pid of the postfix master run during configuration |

Not on the list, although the first draft of this file expected them:
`/etc/machine-id` and `/var/lib/dbus/machine-id` (written by the bootstrap,
identical when both trees use the same bootstrap), `/var/lib/dpkg/*`
(turnkey.mk removes dpkg.log; the status file carries no dates),
`/var/lib/apt/lists/*` (empty in the image), `/etc/ssl/private/*`
(identical). A run with a different bootstrap on either side will show the
machine-id files differ; that is a change of the run's premise, not of this
list, and has to be stated in the run report.

Any other path, or a non-ordering difference in the webmin files, is a
finding.

## Dependencies, resolved on 2026-09-26

The first run needed three things that are now in place:

- `tkldev-setup` on keel-linux/tkldev master maps an appliance to `keel-<app>`
  when `GIT_REMOTE_URL` points at the organization (decision 0006 names
  appliances `keel-<app>` and leaves infrastructure unprefixed).
- The `core` repository exists in the organization as `keel-core`, together
  with `common`, `buildtasks`, `cdroots` and `tklbam-profiles`, all of which
  `tkldev-setup core` clones.
- The trixie bootstrap is copied into the fork tree by hand, since the
  organization has no `bootstrap` repository and the mirror does not publish
  the tarball.

What still blocks the ISO half of the packing gate: the build host installs
fab from apt (upstream 1.1.1). The fork's `share/product.mk` (keel-linux/fab
master, merge e79be43 and later) passes `--set_all_file_dates
@$(SOURCE_DATE_EPOCH)` to xorriso and `--id $(SOURCE_DATE_EPOCH)` to
isohybrid; the project has to build and install that package on the host
(the APT repository of brief section 9, M0) and re-run the packing gate.
