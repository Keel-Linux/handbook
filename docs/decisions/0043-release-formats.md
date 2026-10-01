# 0043: Release formats

Date: 2026-10-01
Status: **proposed**, waiting on the maintainer. Nothing here is built
except the first fix it depends on (Keel-Linux/buildtasks#16, the machine-id
of the ISO and the images made from it, tracker#24). Decided parts of 0005,
0012, 0016 and 0039 are restated only where this note builds on them.

The maintainer's requirements, 2026-10-01:

- Keel releases are published in **every format TurnKey Linux shipped**,
  not only the Proxmox `.tar.zst`: the ISO, the VMware formats and the
  others;
- **Docker is out.** The project ships system containers only;
- images are also published as **GitHub Releases** on each appliance
  repository. The first was published by hand on 2026-10-01:
  [keel-core `testing-19.0-3-step4-20260930`](https://github.com/Keel-Linux/keel-core/releases/tag/testing-19.0-3-step4-20260930),
  the `.tar.zst` and its `.sha512`, marked unsigned and not for production.
  Uploads happen from the build host or an attended step, **never from the
  CI runner**.

## What TurnKey ships, measured on 2026-10-01

Read from `releases.turnkeylinux.org` and `mirror.turnkeylinux.org` (curl,
read only), the TurnKey page "Supported virtualization platforms and build
types" (`www.turnkeylinux.org/docs/builds`) and the `bt-*` scripts of
Keel-Linux/buildtasks, branch `19.x`.

| Format | Script | Output | Last published by TurnKey |
| --- | --- | --- | --- |
| Hybrid ISO, BIOS and UEFI, live or installed with `tkl-installer` | `bt-iso` (fab's `product.iso`, `isohybrid`), `bin/iso-release` | `turnkey-core-19.0-trixie-amd64.iso` | 19.0, the only 19.0 format published so far |
| Proxmox VE and LXC template | `bt-container` (patches `headless`, `container`: kernel purged) | `debian-12-turnkey-core_18.1-1_amd64.tar.gz` | 18.x |
| OVA, VMware and VirtualBox | `bt-vm`, `bin/vm-bundle` (LVM disk, grub, `ovftool`) | `turnkey-core-15.0-stretch-amd64.ova` | 15.x |
| VMDK in a zip, with a `.vmx` | `bt-vm`, `bin/vm-bundle` | `turnkey-core-15.0-stretch-amd64-vmdk.zip` | 15.x |
| qcow2, OpenStack, headless | `bt-openstack`, `bin/openstack-bundle` (patches `headless`, `cloud`, `openstack`, extlinux) | `turnkey-core-15.0-stretch-amd64-openstack.qcow2` | 15.x |
| Xen domU tarball, headless | `bt-xen` (patches `headless`, `xen`) | `turnkey-core-15.0-stretch-amd64-xen.tar.bz2` | 15.x |
| Docker image | `bt-docker`, `bt-qemu-docker` (`docker push` to Docker Hub) | `turnkey/core` on the Docker index | not on the mirror |
| AWS AMI | `bt-ec2` (registers an AMI in AWS; no file) | an AMI id | through the TurnKey Hub |
| OpenStack AMI style tarball, Open Telekom Cloud qcow2 | `bt-openstack-ami`, `bt-otc` | `-openstack.tar.gz`, `-openstack.qcow2` | not on the mirror |
| Raw disk image (ARM boards) and its qcow2 | `bt-img`, `bt-prepqemu` | `.img.xz`, `.qcow2` | not on the mirror |
| Bootstrap | `bt-bootstrap` | `bootstrap-trixie-amd64.tar.gz` | bookworm (Keel publishes trixie, `docs/releases-host.md`) |

Also in the tree: `bt-optimized` (runs `bt-vm` and `bt-container`; the
OpenStack, Xen and Docker lines are commented out), `bt-bugfix`,
`bt-bugfix-single` and `bt-iso-patched` (re-release a patched ISO),
`bt-iso-list`, and Keel's own `bt-layer`, `bt-layer-measure` and
`bt-aplinfo`.

What this shows: **TurnKey itself stopped publishing the VM, OpenStack and
Xen builds after 15.x.** `releases.turnkeylinux.org/turnkey-core/` lists
`.ova`, `-vmdk.zip`, `-openstack.qcow2` and `-xen.tar.bz2` hashes for 14.2
and 15.0, has no 16.x or 17.x entry, and lists only the ISO and the Proxmox
template for 18.0 and 18.1 (WordPress 18.2 the same);
the `ova/`, `vmdk/`, `xen/` and `openstack/` directories on the mirror are
empty. Their documentation still describes all of them. The code shows the
same age: `bt-vm` knows guest OS ids up to bullseye only and stops with
"vm_guestos could not be determined" on trixie, `bin/vm-bundle` reads the
kernel version with a pattern written for 4.19, and both OVA and VMDK need
`ovftool`, VMware's proprietary tool, which is not in Debian.

## What Keel publishes today

- **The Proxmox template** `debian-13-keel-<app>_<ver>-<rel>_amd64.tar.zst`,
  made by `keel assemble` from the layer chain `bt-layer` builds, staged by
  `keel-release` (Keel-Linux/apt `lib/release.sh`) in
  `/srv/keel-release/<date>/`, published by `keel-publish-mirror` (apt
  `lib/mirror.sh`) to `mirror.keellinux.org/images/` with a `.sha512` and a
  detached `.sha512.asc` (or a `.sha512.UNSIGNED` note).
- **The Proxmox index** `releases.keellinux.org/pve/aplinfo.dat{,.gz,.asc}`,
  cumulative (tracker#11), and the release `MANIFEST` and its signature in
  `releases.keellinux.org/meta/<date>/`.
- **The layers** in `mirror.keellinux.org/layers/` with the `stable` and
  `testing` channel pointers of 0016.
- **No ISO and no VM image.** buildtasks has the scripts, but none is wired
  into `keel-release`, and every one of them starts from an ISO
  (`iso-download`, `tklpatch-extract-iso`) that Keel never built.

Signing (0005): the release key's signing subkey is on the build host,
passphrase protected; a release is attended because the maintainer types
the passphrase and the agent forgets it after ten minutes. `keel-release`
does everything that needs no key first and signs last, and
`keel-release --sign-only <date>` signs what is staged without rebuilding.

## Decision proposed

### 1. The formats

| TurnKey format | Keel | Why |
| --- | --- | --- |
| Proxmox / LXC `.tar.gz` | **kept**, as today's `.tar.zst` | the primary format; Proxmox VE reads zstd templates |
| Hybrid ISO | **kept** | bare metal, and any hypervisor that installs from an ISO (Hyper-V, XenServer, KVM) |
| OVA | **kept** | VMware and VirtualBox import by double click; built without `ovftool` |
| VMDK zip with `.vmx` | **kept, last** | the same disk as the OVA; for old VMware products and KVM users who want a ready disk |
| OpenStack qcow2 | **kept as one qcow2** | KVM, libvirt, Proxmox VM and OpenStack read the same file; see "headless" below |
| Xen `.tar.bz2` | **dropped** | Xen HVM boots the qcow2 or the ISO, and the template is already a root filesystem tarball for PV; TurnKey stopped in 15.x |
| Docker | **dropped** | system containers only (maintainer, 2026-10-01): the template is the container format |
| `bt-qemu-docker` | **dropped** | Docker |
| AWS AMI (`bt-ec2`) | **not now** | not a file: needs an AWS account and a key there; the qcow2 imports into EC2 with `vmimport` if someone asks |
| OpenStack AMI tarball, Open Telekom Cloud | **dropped** | the qcow2 covers both |
| ARM raw image (`bt-img`, `bt-prepqemu`) | **not now** | Keel is amd64 only today |

So a release of one appliance is **four files**: `.tar.zst`, `.iso`,
`.qcow2`, `.ova`, and a fifth, `-vmdk.zip`, once the other four are proven.

**Headless.** TurnKey's qcow2, Xen and container builds are headless: no
console at first boot, random passwords written to the log. Keel's qcow2 is
**not** headless: it boots to the same first boot screens as the ISO and
the template on Proxmox, because that is what Proxmox VE and libvirt users
see, and the headless path of Keel is still open (inithooks#31). An
OpenStack image with cloud metadata is a later variant, decided when
someone needs it.

### 2. Which appliances

- **Core and Web** first, in all four formats, because they are what Phases
  1 and 3 deliver (tracker#46) and what everything else is built on.
- **The others** (mariadb, postgresql, redis, wordpress, lamp, and the
  appliances 0034 brings) keep the template only, and get the other formats
  one by one, each after its boot test passes in that format. A format is
  never published for an appliance whose first boot was not run in it.

### 3. Names

TurnKey's Proxmox naming, for every format, because it is the one Keel
already publishes and `bt-aplinfo` parses:

    debian-13-keel-<app>_<ver>-<rel>_amd64.tar.zst
    debian-13-keel-<app>_<ver>-<rel>_amd64.iso
    debian-13-keel-<app>_<ver>-<rel>_amd64.qcow2
    debian-13-keel-<app>_<ver>-<rel>_amd64.ova
    debian-13-keel-<app>_<ver>-<rel>_amd64-vmdk.zip

`<ver>-<rel>` is the appliance version and revision from the product's
changelog, as `release_version` reads it today (for example `19.0-3`). A
testing build adds a `+<label>-<date>` suffix to `<rel>`, as the first
GitHub pre-release did (`19.0-3+step4-20260930`); a stable name has none.

### 4. One root filesystem, many wrappers

**Every format is made from the template**, the `.tar.zst` `keel assemble`
writes, and from nothing else: unpack it, reset what must be per machine
(section 7), and wrap it. No `apt` runs between the template and a wrapper.

The alternative is TurnKey's: build the ISO with fab from the product and
derive the VM images from the ISO. For Keel that would produce a second root
filesystem for the same `<ver>-<rel>`, built at another time from other
package versions, and the derived builds then run `apt-get upgrade` and
patches in a chroot (`update-pkgs`, `patches/vm`), which re-runs package
postinsts: systemd's writes a machine-id, and CrowdSec's registers the
machine (tracker#47). Since 0016 a Keel release is the bytes its layers
name; one name, one set of bytes, in every format.

What a wrapper adds is only what the template does not need: the ISO's
cdroot and boot loader (fab's `cdroot` step: the squashfs of the rootfs,
isolinux and GRUB EFI, `xorriso`, `isohybrid`), and for the VM disk a
partition table, a filesystem and GRUB. The kernel, `grub-pc`,
`tkl-installer` and `open-vm-tools` come from the layers' plans, so they
are in the template already and tested there.

**Built on the build host, never on the runner.** Every wrapper needs root:
loop devices, `kpartx`, mounts, `grub-install`. The CI runner is an
unprivileged LXC user without sudo on the public services VM
(`docs/ci-cd.md` section 6), and is not to hold anything that is
published. What the runner does is test the code: `tests/machine-id` makes
small ISOs from a few files, and the boot checks keep reading what the
mirror serves. The build host also lacks tools today (measured 2026-10-01:
`qemu-img`, `kpartx`, `zip` and `extlinux` are missing; `xorriso`,
`mksquashfs`, `parted` and `grub-install` are there), which is part of the
work.

The OVA is written without `ovftool`: an OVA is a tar of the `.ovf`
descriptor, its `.mf` manifest and a `streamOptimized` VMDK, and
`qemu-img convert -O vmdk -o subformat=streamOptimized` writes the disk.
The descriptor is a template in buildtasks, tested by importing it with
VirtualBox's `VBoxManage import` on a test machine.

### 5. Where the files go

The split stays the one `docs/releases-host.md` describes and TurnKey uses:
the bytes on `mirror.keellinux.org`, what describes and signs them on
`releases.keellinux.org`.

```
mirror.keellinux.org/images/
  <app>/<ver>-<rel>/debian-13-keel-<app>_<ver>-<rel>_amd64.{tar.zst,iso,qcow2,ova}
                                     immutable: written once, never replaced
  debian-13-keel-<app>_<ver>-<rel>_amd64.tar.zst
                                     the flat name the Proxmox index points
                                     at today, a hard link to the file above

releases.keellinux.org/
  pve/aplinfo.dat{,.gz,.asc}         unchanged: the Proxmox index, stable only
  meta/<date>/MANIFEST{,.asc}        unchanged: the release MANIFEST
  <app>/<ver>-<rel>/                 one directory per appliance release, as
                                     releases.turnkeylinux.org/turnkey-core/18.1-bookworm-amd64/
    SHA512SUMS, SHA512SUMS.asc       every file of that release (section 6)
    <name>.changelog                 the product changelog
    <name>.packages                  the package list the layers captured (0012)
  stable/INDEX, stable/INDEX.asc     per channel: one line per appliance,
  testing/INDEX, testing/INDEX.asc   "<app> <ver>-<rel> <sha512 of its SHA512SUMS>"
```

A channel index changes only in a release, so it is signed with the
release key in the attended step and needs no expiry: images are not an
update path, `apt` is (0039), and 0016's expiry exists to stop a mirror
freezing an updater. The index is what the download page reads to say
"the current stable Core is 19.0-3", and the digest of `SHA512SUMS` in it
ties the line to the files.

`testing/` holds only signed builds. **An unsigned build never goes to
either host**: the hosts serve nothing unsigned except the staging archive,
and the header says so (`docs/releases-host.md` section 5). Unsigned test
images go to GitHub pre-releases only (section 8).

### 6. Checksums and signatures

- `SHA512SUMS` per appliance release, in `sha512sum` format, one line per
  file, so `sha512sum -c SHA512SUMS` works in a directory of downloads.
- `SHA512SUMS.asc`, a detached armoured signature by the release key, made
  in the attended step by `keel-release`'s signing phase, beside the
  signatures it already makes. Verifiable with `gpg --verify` and with
  `sqv`, which is what Proxmox and apt use.
- The per-file `.sha512` and `.sha512.asc` of the template stay, because
  the Proxmox index and existing instructions use them.
- The release `MANIFEST` lists every file with its size and sha256, as it
  does for the templates today, and `keel-publish-mirror` refuses any file
  whose digest differs.

### 7. What each format's first boot must make for itself

Nothing that identifies a machine may be in an image, because every machine
made from it would share it. The table says where each item is removed and
where it is made.

| Identity | Template (LXC, Proxmox) | ISO, live and installed | qcow2, OVA, VMDK |
| --- | --- | --- | --- |
| `/etc/machine-id` (and with it the DHCP DUID and IAID, the journal, MariaDB `server_id`) | emptied by `bt-layer` (buildtasks#15); systemd makes it at boot | emptied by `bt-iso` before fab squashes the rootfs, checked in the ISO (buildtasks#16, tracker#24; on the real Core squashfs: an empty 0444 file and the D-Bus link); `tkl-installer` copies the squashfs as it is and has no machine-id step, so the empty file is what makes each install unique | emptied when the wrapper is made, by the same `bin/reset-machine-id` |
| SSH host keys, TLS and snakeoil pairs | none in a layer: `layer_audit_keys` refuses one (keel-core#8); `keel-host-keys.service` makes the missing ones and replaces published ones at every boot (inithooks#30), `10regen-sshkeys` and `15regen-sslcert` at first boot | the same packages and hooks; the ISO check must also run the key audit, since fab's ISO path does not call it today (follow-up) | the same, from the template |
| CrowdSec LAPI and CAPI credentials, bouncer key | removed by keel-core's `conf.d/main`, CAPI registration suppressed in the build (tracker#47); `keel apply` registers on the first enable (keel 0.13.0) | the same: `conf.d/main` runs in the fab build of every format | the same, and no `apt` in the wrapper, so no postinst registers again |
| WireGuard keys | the build fails if `/etc/wireguard` is not empty or a `wg-quick@` unit is enabled (keel-core#16); keel makes the pair at the first converge (keel#49) | the same | the same |
| etcd member, Anubis key, MariaDB accounts | made by keel from the spec when enabled (keel#58, keel#62) | the same | the same |

The disk wrappers add one item of their own: the filesystem and LVM UUIDs
are made when the disk is created, so they are the same on every VM made
from one image, as with every cloud image. Nothing in Keel reads them as an
identity; they are recorded here so that nothing starts to.

### 8. GitHub Releases

Each appliance repository (`keel-core`, `keel-web`, `keel-wordpress`, ...)
carries its own releases.

- **Tags.** `<ver>-<rel>` for a signed stable release (`19.0-3`), on the
  commit of the product the layers were built from. `testing-<ver>-<rel>-<date>`
  for a testing build (`testing-19.0-3-20261001`), and
  `testing-<ver>-<rel>-<label>-<date>` for a named test image, which is
  the shape of the first one (`testing-19.0-3-step4-20260930`). Testing
  releases are marked pre-release.
- **Assets.** GitHub refuses an asset of 2 GiB or more. The template is
  386 MB (`keel-core` 19.0-3) and a Core ISO 445 MB, its squashfs 388 MB
  (measured on the build host, 2026-10-01), so the ISO, qcow2 and OVA are
  expected well below 1 GiB for Core and Web; every format of section 1 is attached
  while it fits. A format that does not fit is left out of that release
  and its body links to it on `mirror.keellinux.org`; no file is ever split.
- **Checksums.** Today the `.sha512` of each file. Once signing exists,
  the same `SHA512SUMS` and `SHA512SUMS.asc` as on
  `releases.keellinux.org`, byte for byte.
- **Consistency.** `releases.keellinux.org` is the source of truth and
  GitHub a second copy. A release is uploaded to GitHub only after
  `keel-publish-mirror` has installed it, from the same staged files, and
  the upload checks every asset against the signed `MANIFEST` first and
  GitHub's own asset digest (the API reports a sha256 per asset) after. The
  release body names the `MANIFEST` URL. Stable releases are created
  **immutable** (GitHub's immutable releases), so an asset cannot be
  replaced later; a correction is a new `<rel>`.
- **Where the upload runs.** `bin/keel-publish-github <date>` in
  Keel-Linux/apt, beside `keel-publish-mirror`, run by the maintainer in
  the attended release from a machine where `gh` is logged in to the
  organization, or from the build host with a fine-grained token limited to
  `contents: write` on the appliance repositories, readable by root only.
  Not a reusable workflow: a workflow runs on the runner, and the runner
  must neither hold the files nor a token that can publish them.
  Unsigned testing images are uploaded the same way, marked
  "not signed, not for production" in the title and the body, as the first
  one was.

### 9. Order of work

1. **buildtasks: the machine-id of the ISO and the images made from it**
   (tracker#24). `bin/reset-machine-id`, `bin/iso-machine-id-check`, the
   reset in `bt-iso` and `bin/rootfs-cleanup`: buildtasks#16, which accompanies this
   note.
2. **tracker#23, the pin.** A pin of 1001 downgrades any package that is
   newer in the image than in the archive. An ISO or VM user runs
   `apt upgrade` on day one, so no new format is published before either
   every package of an image is in the archive first, or the pin is 990.
3. **The key audit on the ISO** (section 7): `bin/iso-machine-id-check`
   becomes the image check and also runs `layer_audit_keys` over the
   squashfs.
4. **`bt-image`** in buildtasks: template in, `.iso` and `.qcow2` out, with
   the reset and the checks, tested with fake templates like
   `tests/layer`. The ISO first, because the qcow2 and the OVA reuse its
   root filesystem steps.
5. **`keel-release`**: build the wrappers after `keel assemble`, add them
   to `MANIFEST`, write `SHA512SUMS` per appliance and sign it in the
   existing signing phase. `--sign-only` keeps working.
6. **`keel-publish-mirror`**: the per-appliance directories, the flat hard
   links, the channel indexes; refuse what `MANIFEST` does not list.
7. **Boot tests** for each format on the test machines: the ISO installed
   with `tkl-installer` and booted twice (two machine-ids, two key sets),
   the qcow2 on KVM, the OVA imported in VirtualBox.
8. **The OVA**, then the VMDK zip.
9. **`keel-publish-github`**, then the download page on keellinux.org.

### 10. What blocks the first publication

- items 1 to 7 above, for the formats other than the template;
- the attended steps already listed in tracker#1, in particular keel-core#8
  (every published image still carries the shared keys until the chain is
  rebuilt and published);
- the attended signing of the release (0005).

## The attended step, as it will be

Everything before it is built and staged by the agent on the build host
without a key. The maintainer then:

1. on the build host: `keel-release --sign-only <date>` and types the
   passphrase once. It signs the template digests, the index, every
   `SHA512SUMS`, the channel indexes and `MANIFEST`; seconds, well inside
   the ten minutes the agent keeps the passphrase;
2. on his workstation: `keel-publish-mirror <date>`, which opens the
   tunnel, pulls the staged files to the public host and verifies them
   against `MANIFEST`. Under 2 GiB per appliance in four formats, so
   Core and Web are under 4 GiB: 10 to 20 minutes, unattended once
   started;
3. `keel-publish-github <date>`: the same files to the two repositories'
   releases, a few minutes.

About **30 minutes** in all, of which the passphrase is under one minute
and the rest can run while he does something else.

## Open questions for the maintainer

1. **The ISO from the template** (section 4) rather than fab's own ISO
   build: recommended, because one release is then one set of bytes.
2. **qcow2 with console first boot**, not headless (section 1).
3. **Drop Xen, Docker, the AMI and the ARM images** (section 1).
4. **The GitHub upload credential** (section 8): from his workstation in
   the attended step (recommended), or a root-only fine-grained token on
   the build host.
5. **Testing images unsigned on GitHub only**, never on the project's
   hosts (section 5).
6. **Immutable stable releases on GitHub** (section 8).
