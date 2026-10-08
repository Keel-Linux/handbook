# 0052: Every release ships both formats, and the container drops what only a machine needs

Date: 2026-10-10
Status: **decided by the maintainer, 2026-10-10**: every release of every
appliance ships the `.tar.zst` and the ISO from the same build, and a
release is published only when both pass their checks. How the container
variant is made lighter, and how the ISO is proven to boot, were proposed
from the release tooling as it stands, and the five points the proposal
left open were approved by the maintainer the same day as recommended;
they are part of the decision below (sections 2, 3, 6 and 8). Nothing here
is built. It amends 0043.

## What was decided

The maintainer, 2026-10-10:

- **Every release of every appliance ships both formats from the same
  build**: the `.tar.zst` LXC container template, and a bootable `.iso` for
  people who run virtual machines.
- **The extra time is small.** Both come from the same root filesystem;
  only the extraction and assembly step differs.
- **A release is not complete, and is not published, unless both artifacts
  pass their checks.**

And, approving the proposal's five open points as recommended:

- **A separate boot layer per appliance**, used only by the ISO (section 2).
- **The ISO must boot under UEFI** before the first two-format release
  (section 3).
- **The boot check also installs to disk** once that is automated
  (section 6).
- **Unsigned testing pre-releases may ship the `.tar.zst` alone** until the
  ISO builder exists; official releases may not (section 8).
- **The 990 pin (tracker#23) is confirmed before the first ISO** (section
  8).

## Why (brief section 10)

1. **Why the current approach is not enough.** 0043 decided the two
   formats but phased the ISO in: Core and Web first, every other appliance
   "one by one". In practice no ISO has been published at all
   (Keel-Linux/buildtasks#9 is open), so a person who runs VMs has nothing
   to download, and the format that is published carries what only a VM
   needs. Jeremy Davis of TurnKey Linux measured our images against his:
   decompressed, the root filesystems are about the same size (TurnKey's
   935 MB, Keel's 951 MB), and ours carries a kernel it never boots as a
   container, `linux-image-amd64` and the versioned kernel package, about
   100 MB decompressed.
2. **Whether it can be made to work.** It can. The kernel, the initrd, the
   boot loaders and the installer are a separable set: TurnKey's own
   `patches/container` in buildtasks already purges most of it for its
   Proxmox build, and common's `plans/boot` already guards its boot
   packages with `CHROOT_ONLY`. Keel's layers are content addressed, so the set can live
   in a layer of its own that only the ISO uses (section 2).
3. **Why this is better.** A container user downloads and stores no kernel
   (every host that pulls the Core layer pays for it today, 0047), a VM user
   gets an image of the same release instead of none, and a release is one
   thing in two wrappers, checked the same way, rather than a container
   release with an ISO promised later.

## The sizes, measured honestly

A `.tar.zst` is a zstd compressed tar; the ISO is a squashfs inside an ISO
9660 image, with boot files around it. **The files are never compared with
each other.** What can be compared is the root filesystem each one unpacks
to, and the compressed size of the same format across releases.

Jeremy's figures are his own measurement of the two projects' root
filesystems, decompressed: TurnKey 935 MB, Keel 951 MB.

Measured for this note on the Core template published on 2026-10-08
(`debian-13-keel-core_19.0-9_amd64.tar.zst`, 360,255,317 bytes, the same
bytes as `layers/core.tar.zst`), streaming it through `zstd -dc | tar -tv`
and attributing each file to its package by the `dpkg` file lists inside
it. The total is the sum of the tar members' sizes, 903.6 MB, which is not
a `du` figure (no block rounding, hard links counted once) and is why it
differs from Jeremy's 951 MB; the shares below are of that 903.6 MB.

| What | Packages or paths | Unpacked |
| --- | --- | --- |
| Kernel | `linux-image-6.12.111+deb13-amd64`, `linux-image-amd64`, `linux-base` | 107.9 MB |
| Initrd, not owned by a package | `/boot/initrd.img-6.12.111+deb13-amd64` | 43.1 MB |
| Boot loaders | `grub-common`, `grub-pc`, `grub-pc-bin`, `grub2-common`, `os-prober`, `syslinux`, `syslinux-common`, `isolinux`, `efivar`, and the generated `/boot/grub/unicode.pf2` (2.4 MB) | 23.7 MB |
| Installer and disk tools | `tkl-installer`, `lvm2`, `dmsetup`, `libdevmapper-event1.02.1`, `parted`, `libparted2t64`, `dosfstools`, `mtools`, `fdisk`, `eject`, `hdparm`, `webmin-fdisk`, `webmin-lvm`, `webmin-mount`, `webmin-raid` | 10.3 MB |
| Hardware and guest services | `qemu-guest-agent`, `acpid`, `acpi-support-base`, `jitterentropy-rngd`, `ntpsec` | 4.8 MB |
| Initramfs tooling and live boot | `initramfs-tools`, `-core`, `-bin`, `live-boot`, `live-boot-initramfs-tools`, `live-tools`, `klibc-utils`, `libklibc`, `busybox`, `cpio`, `dracut-install` | 2.1 MB |
| Firmware | `firmware-linux-free` (no non-free firmware is installed) | 0.1 MB |
| **All of it** | | **about 192 MB, 21%** |

So the container variant of Core unpacks to about 712 MB, before whatever
else only these packages pulled in is autoremoved. Its compressed size is
measured at the first build and recorded, not predicted here. The kernel
alone is the 100 MB Jeremy named; with the initrd it is 151 MB.

## Decision

### 1. Two artifacts per appliance release, from one build

Every run of `keel-release` for an appliance stages both:

| File | For | Contains |
| --- | --- | --- |
| `debian-13-keel-<app>_<ver>-<rel>_amd64.tar.zst` | Proxmox VE containers, LXC, Docker through `docker import` (0043, section 2) | the appliance's layer chain, without the boot set |
| `debian-13-keel-<app>_<ver>-<rel>_amd64.iso` | VMware, VirtualBox, Proxmox VE VMs, Hyper-V, KVM, bare metal; live or installed with `tkl-installer` | the same chain, plus the appliance's boot layer (section 2), squashed, with the boot files |

Names are 0043's, section 4. "The same build" means one run, one captured
package pool (0012), one product commit per layer: the ISO's root
filesystem is the template's root filesystem plus one layer, never a
second build of the appliance.

### 2. The boot set lives in a layer of its own

**The rule: the container variant drops what only a VM or bare metal
needs, and the ISO keeps it.** The boot set is the table above: the kernel
and its meta package, initramfs-tools and the initrd, firmware, GRUB, the
syslinux family and the boot loader tooling, `tkl-installer` and the disk
tools it and the Webmin disk modules need, and the guest and hardware
services that do nothing in a container (`qemu-guest-agent`, `acpid`,
`jitterentropy-rngd`, `ntpsec`). The list is the plans', not a removal
list: what goes in it is decided by moving lines between plans, and the
container check (section 5) fails if any of it is found in a template.

**Decided: the boot set leaves every layer for a boot layer per
appliance, used only by the ISO**, rather than staying in the layers and
being stripped from the template at assembly. Stripping would leave the
kernel in every layer download, run `apt` between assembly and the
template, and break 0016's "the bytes its layers name" for the template.

How it is made, from the tooling as it stands:

- **`common/plans/turnkey/base` no longer includes the boot set.** Its
  `#include <boot>`, `grub-pc`, `tkl-installer`, `efivar`, `lvm2`, `eject`,
  `jitterentropy-rngd`, `ntpsec`, `fdisk`, the Webmin disk modules,
  `qemu-guest-agent` and `acpi-support-base` move to a new plan,
  `plans/turnkey/machine`, which includes `<boot>`. Every layer chain is
  then built without them, so the Core layer, and every layer above it,
  shrinks for everyone who pulls it.
- **A boot layer per appliance**, `<app>-boot`, built by `bt-layer` with
  the appliance's top layer as its parent and `plans/turnkey/machine` as
  its plan: a small delta (about 192 MB unpacked, by the table) that
  installs the boot set, writes the initrd and carries the dpkg state that
  goes with it. It is per appliance, not one shared layer, because a delta
  carries `/var/lib/dpkg/status`, which differs on every parent.
- **It is a published layer like any other**: manifest, `.packages`,
  pinned to the same pool, checked by `keel verify`, scanned by the key
  scan, and staged under `layers/`. So 0016's rule holds for both files: a
  release is the bytes its layers name, the template naming the chain and
  the ISO the chain plus `<app>-boot`.
- **`keel assemble` gains no format logic for this.** The template is
  `keel assemble <app>` as today; the ISO's root filesystem is
  `keel assemble <app>-boot` into a scratch directory, which the ISO step
  squashes. The extraction and assembly step is what differs, as the
  maintainer put it; the build adds one `bt-layer` run per appliance.
- TurnKey's `patches/container` is not used: it purges after the fact,
  which leaves the kernel in the layers below and runs `apt` between
  assembly and the template, which 0043, section 5, rules out.

### 3. The ISO step

After `keel assemble`, in `release_one` (Keel-Linux/apt `lib/release.sh`),
for each appliance:

1. build or reuse `<app>-boot` (current when its tarball matches its
   manifest, like every layer), stage it, scan it;
2. assemble the chain plus `<app>-boot` into the work directory; reset what
   must be per machine (0043, section 8; buildtasks#16's machine-id reset);
3. make the cdroot from Keel-Linux/cdroots, copy the kernel and initrd from
   that root, `mksquashfs` it into `live/10root.squashfs` with the release's
   `SOURCE_DATE_EPOCH`, and write the ISO with `xorriso` and `isohybrid`,
   as fab's `cdroot` and `product.iso` targets do today;
4. run the ISO checks of section 5, then the boot test of section 6.

This is buildtasks#9 ("produce an ISO from an assembled rootfs"), which
already requires that "a test boots it". It is built on the build host,
never on the runner (0043, section 5): it needs root for the assembly, the
squashfs and the loop mounts.

**UEFI is not wired today.** fab's `product.iso` target uses
`run-genisoimage` (El Torito with `isolinux.bin`) and `isohybrid` without
`-u`; `run-genisoimage-uefi` exists in `share/product.mk` but expects an
`efi.img` nothing builds, and cdroots carries only `isolinux`. 0043's
"hybrid, BIOS and UEFI" is therefore a target, not a property of the
current path. The ISO step adds a GRUB EFI image (`grub-efi-amd64-bin`'s
`grub-mkstandalone` into a FAT `efi.img`, or the method of
`JedMeister/tkl-gen-iso`, which buildtasks#9 says to read first) and calls
`xorriso` with `-eltorito-alt-boot -e efi.img -isohybrid-gpt-basdat`.
Secure Boot (a signed shim) is not in scope; the test runs OVMF with it
off.

**Decided: UEFI is a gate from the first release with both files.** No
two-format release is published before the ISO boots under UEFI as well as
BIOS (section 6). Hyper-V generation 2 machines boot UEFI only, current
VMware defaults to UEFI, and Proxmox VE offers OVMF beside SeaBIOS; a BIOS
only ISO would fail many of the people it is for.

### 4. Signatures, listings and where the files go

Both variants are treated the same:

- **The same key and secret scan.** `keel-release`'s `lib/keyscan.sh`
  reads a tarball stream, which covers the template and every layer,
  `<app>-boot` included, as `release_refuse_key_files` already does. For
  the ISO, the scan reads the squashfs as a tar stream (`sqfs2tar` from
  `squashfs-tools-ng`, or `tar` over a read only mount) and the cdroot
  tree, so what is checked is what is published and not the tree it was
  made from. A hit removes the ISO and fails the release with exit 12,
  like a template. `bin/iso-machine-id-check` runs as well (0043, section
  10, step 3).
- **Signed and listed.** Each file has its `.sha512` and `.sha512.asc` (or
  `.sha512.UNSIGNED` in an unsigned build), both are in the appliance
  release's `SHA512SUMS` and `SHA512SUMS.asc`, and the release `MANIFEST`
  lists both with size and digest. The signing phase signs the ISO digest
  beside the template digest; `--sign-only` refuses to sign an appliance
  whose ISO is not staged and checked, as it does for a template today.
- **Published together.** Both go to `mirror.keellinux.org/images/<app>/
  <ver>-<rel>/` and to the GitHub release of the appliance repository,
  pre-release or not (0043, sections 6 and 9). `keel-publish-mirror` and
  `keel-publish-github` refuse an appliance release that `MANIFEST` lists
  with one of the two files only; the one exception, unsigned testing
  pre-releases before the ISO builder exists, is section 8.
- **The Proxmox index lists only the `.tar.zst`.** `bt-aplinfo` runs over
  the templates as today; the ISO has no `aplinfo.dat` record.
- **The `MANIFEST` also records each artifact's unpacked root filesystem
  size**, so the honest comparison of the section above is printed by the
  release itself.

### 5. The checks each artifact must pass

| Check | `.tar.zst` | ISO |
| --- | --- | --- |
| Layers match their manifests, `keel verify` | yes, the chain | yes, the chain and `<app>-boot` |
| Key and secret scan | yes | yes, over the squashfs and the cdroot |
| Empty machine-id | `bt-layer` (buildtasks#15) | `iso-machine-id-check` (buildtasks#16) |
| No boot set inside | yes: no `linux-image-*`, `/boot/vmlinuz*`, `/boot/initrd*`, `grub-*`, `tkl-installer` in the dpkg state or the tree | not applicable |
| Boots to the first boot screen | the appliance's LXC boot test (keel-core `tests/boot-test.sh` and its siblings) | the QEMU boot test, section 6 |

**Every check is a gate.** A failure in either column stops the release
of that appliance before the signing phase; nothing of it is signed,
staged for publication or uploaded. With `all`, the run stops at that
appliance with its exit code, as `release_main` does today for any failure
of `release_one`, and `--resume` continues once it is fixed.

### 6. Proving the ISO boots

**The boot test runs on the build host, in `keel-release`, after the ISO
is written and before anything is signed.** Not on the CI runner: the
runners are unprivileged LXC users (`docs/ci-cd.md`, section 6;
`docs/infra/keel-lxc-2.md`) with no `/dev/kvm`, and they hold nothing that
is published. CI keeps testing the ISO builder's code with small fake
images, as `tests/machine-id` does.

For each ISO, two boots with `qemu-system-x86_64` (`qemu-system-x86` and
`ovmf` from Debian), 2 GiB of memory, the ISO as a CD-ROM, a blank 8 GiB
virtio disk, user mode networking with IPv6:

| Boot | Firmware | Passes when |
| --- | --- | --- |
| BIOS | SeaBIOS, QEMU's default | the boot menu appears, the default live entry boots, and the first boot screen (inithooks' root password dialog) is on the console within 5 minutes |
| UEFI | OVMF (`OVMF_CODE_4M.fd`), Secure Boot off | the same |

How it is observed: the cdroot's boot entries also write the kernel
console to the first serial port, which the test reads, and a QMP
`screendump` of the first virtual console is taken at the first boot
screen in each firmware. The two screenshots are staged with the release
(`<name>.screens/`, as `bt-iso` already does for TurnKey's ISOs), so the
images reach the maintainer with their screens.

**What it proves:** the ISO boots under both firmwares and reaches the same
first boot as the container, with the machine's own identity made at that
boot. **What it does not prove on its own:** the installed path, which
0043 required (`tkl-installer` twice, two machine-ids, two key sets).

**Decided: the boot check also installs to disk once that is automated.**
Then every release's boot test runs `tkl-installer` to the blank virtio
disk, driven by QMP key presses, reboots from that disk and reaches the
first boot screen again, under both firmwares, and the install is a gate
like the live boot. Until it is automated, the install is run by hand at
each appliance's first ISO and whenever `tkl-installer` or the boot layer
changes, and the live boot test is the gate.

If the build host's VM does not expose `/dev/kvm` (not recorded in
`docs/build-host.md`), QEMU runs under TCG, which is slower; the timeout is
then raised, never the test dropped.

### 7. Time

Per appliance, on top of today's release: one `bt-layer` run for
`<app>-boot` (a package install and an initrd), one extra `keel assemble`,
one `mksquashfs` of about 0.9 GB, one `xorriso`, and two QEMU boots. These
are estimates in minutes, not measurements; the first release that builds
both records the real figures in `STATUS.md`. The attended step (0043,
section 11) stays the same shape, with twice the digests to sign, which is
seconds.

### 8. Before the first ISO: testing builds and the pin

- **Testing builds.** Until the ISO builder exists (buildtasks#9), unsigned
  testing builds may go to GitHub pre-releases as the `.tar.zst` alone,
  marked "not signed, not for production" as 0043, section 9, has it, and
  saying in the title and body that the ISO is missing. **Official releases
  may not**: a signed release, and any release on the mirror or on
  `releases.keellinux.org`, carries both files or is not published.
- **The pin (tracker#23).** The archive pin is lowered from 1001 to 990,
  and that is confirmed on a built image, before the first ISO is
  published, as 0043, section 10, step 2, allowed. An ISO install runs
  `apt upgrade` on day one, and a pin above 1000 can downgrade packages
  that are newer in the image than in the archive.

## What changes in 0043

| 0043 | Now |
| --- | --- |
| Section 1: both formats for Core and Web first, other appliances one by one, each after its first boot ran from the ISO | **Every appliance, every release, both files.** The last rule holds by construction: the boot test of section 6 runs every appliance's first boot from its ISO before it is published |
| Section 2: Docker through `docker import` of the `.tar.zst` | **Unchanged**, with a lighter template; still best effort, still not tested |
| Section 3: AWS and OpenStack by `keel assemble --format raw\|qcow2`, a later phase | **Unchanged as a plan.** The conversion no longer "adds a kernel, GRUB": it assembles the chain plus `<app>-boot`, which has them, and adds only the cloud datasource client. Still later, still validated on real accounts |
| Section 4: names | Unchanged |
| Section 5: the ISO is made from the template, which already carries the kernel, `grub-pc` and `tkl-installer` | **The ISO is made from the same chain plus `<app>-boot`**; the template no longer carries the boot set. Still one root filesystem per release, still no `apt` between assembly and wrapping |
| Section 6: layout | Unchanged; `<name>.packages` is written for each file, and the boot layers sit in `layers/` with the others |
| Section 7: checksums and signatures | Unchanged, now applied to both files from the first release; per-file `.sha512` and `.sha512.asc` for the ISO too |
| Section 8: identity per format | Unchanged; the key audit on the ISO is section 4 here |
| Section 9: GitHub Releases | Unchanged; both assets on every release. The Core template is 360 MB and 0043 measured a Core ISO of 445 MB (built by `bt-iso`, with the boot set); both files are far below GitHub's 2 GiB, and each is compared only with its own format |
| Section 10: order of work | Replaced by "How it is carried out" below |
| Section 11: the attended step | Unchanged in shape |

## How it is carried out

1. **tracker#23**: the pin at 990, confirmed before the first ISO
   (section 8).
2. **common**: split `plans/turnkey/base` into the base and
   `plans/turnkey/machine`; `conf/turnkey.d/container-units` keeps its
   masks, which become harmless where `ntpsec` is absent.
3. **buildtasks#9**: the ISO from an assembled root filesystem, with BIOS
   and UEFI boot, the ISO checks, and the QEMU boot test, tested with fake
   layers like `tests/layer`; then the automated install to disk (section
   6).
4. **apt**: `lib/release.sh` builds and stages `<app>-boot`, assembles and
   checks the ISO, adds it to `MANIFEST`, `SHA512SUMS` and the signing
   phase; `lib/keyscan.sh` reads a squashfs; `keel-publish-mirror` and
   `keel-publish-github` refuse a release with one file.
5. **The conf/appliances list**: each appliance gains its `-boot` line.
6. **First release with both**: Core and Web, then every appliance in the
   next run of `keel-release all`, recording sizes and times.

Done when a run of `keel-release all` on the build host stages, for every
appliance, a template with no boot set and an ISO that booted to its first
boot screen under BIOS and UEFI, both scanned, both signed, both listed;
and both reach the mirror and the GitHub release together.

## Consequences

- No official release is published with one file (section 8 has the
  testing exception). A defect that breaks only the
  ISO blocks the container too, and the other way round.
- Every layer is rebuilt once without the boot set, and every published
  template changes its digest; the Proxmox index records change with it.
- A container's root filesystem unpacks to about 192 MB less on every
  Core based chain; how much smaller the `.tar.zst` download gets is the
  compressed share of that, measured at the first build. A host that holds
  several appliances saves it once, on the Core layer.
- The build host needs `qemu-system-x86`, `ovmf`, `xorriso`,
  `squashfs-tools` and `squashfs-tools-ng`, and enough disk for a second
  assembled root per appliance during a run.
- Twice the artifacts per release on the mirror and on GitHub; the ISO is
  the larger of the two.

## What this amends

- **0043**: sections 1, 5, 7, 9 and 10 as tabled above; sections 2, 3, 4,
  6, 8 and 11 unchanged in what they decide.
- **0047**: "one `.tar.zst` and one ISO per application release" becomes a
  rule for every release, not a target.
- **0016**: unchanged; the ISO is now also the bytes its layers name,
  through the published `<app>-boot` layer.
- **0012**: unchanged; the boot layer is pinned to the release's pool like
  the others.
- **0036**: `common` gains `plans/turnkey/machine`; what is common and what
  is an appliance does not change.
