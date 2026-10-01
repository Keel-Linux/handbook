# 0043: Release formats

Date: 2026-10-01
Status: **decided by the maintainer, 2026-10-01**: Keel publishes two
formats, the ISO and the `.tar.zst`. The decision is under "Decision";
what was proposed and not taken is under "Resolved". Nothing here is built
except the first fix it depends on (Keel-Linux/buildtasks#16, the
machine-id of the ISO, tracker#24). Decided parts of 0005, 0012, 0016 and
0039 are restated only where this note builds on them.

The maintainer's requirements, 2026-10-01, before the proposal:

- Keel releases are published in **every format TurnKey Linux shipped**,
  not only the Proxmox `.tar.zst`: the ISO, the VMware formats and the
  others;
- **Docker is out** as a format of its own. The project ships system
  containers only;
- images are also published as **GitHub Releases** on each appliance
  repository. The first was published by hand on 2026-10-01:
  [keel-core `testing-19.0-3-step4-20260930`](https://github.com/Keel-Linux/keel-core/releases/tag/testing-19.0-3-step4-20260930),
  the `.tar.zst` and its `.sha512`, marked unsigned and not for production.
  Uploads happen from the build host or an attended step, **never from the
  CI runner**.

The evidence below led the maintainer to cut the list to two files rather
than rebuild TurnKey's whole set.

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

## Decision

### 1. Two formats

A release of one appliance publishes **two files**, the same root
filesystem in two wrappers:

| File | Covers | Made by |
| --- | --- | --- |
| `.iso`, hybrid, BIOS and UEFI | VMware, VirtualBox, Proxmox VE virtual machines, Hyper-V, KVM, bare metal: boot it and install with `tkl-installer`, or run it live | `bt-iso` on the build host |
| `.tar.zst` | Proxmox VE containers and LXC, as today; Docker through `docker import` (section 2) | `bt-layer` and `keel assemble` on the build host, as today |

Nothing else is published: no OVA, VMDK or qcow2 download, no Xen tarball,
no Docker image format, no AMI, no ARM image. TurnKey itself stopped
publishing the VM, OpenStack and Xen builds after 15.x (above), and every
hypervisor among them installs from the ISO.

Both formats go to **Core and Web** first, since they are what Phases 1 and
3 deliver (tracker#46). The other appliances keep the `.tar.zst` and get
the ISO one by one, each after its first boot was run from that ISO. A
format is never published for an appliance whose first boot was not run in
it.

### 2. Docker, from the same `.tar.zst`

`docker import` reads the template as it is:

    docker import debian-13-keel-core_19.0-3_amd64.tar.zst keel/core:19.0-3

zstd is read since **Docker Engine 23.0**: its release notes list "Add
support for pulling `zstd` compressed layers"
([moby/moby#41759](https://github.com/moby/moby/pull/41759), in
`pkg/archive`), and `docker import` decompresses through that same
`archive.DecompressStream` (`daemon/images/image_import.go` at `v23.0.0`;
`pkg/archive` in 20.10.24 has no zstd). An older Engine needs
`zstd -d` first and imports the plain `.tar`.

**The appliance expects systemd as PID 1**, which Docker does not give a
container by default. Two ways to run it:

    docker run -d --name core --privileged --cgroupns=host \
        -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
        --tmpfs /run --tmpfs /run/lock --tmpfs /tmp \
        keel/core:19.0-3 /sbin/init

or, without `--privileged`, the [Sysbox](https://github.com/nestybox/sysbox)
runtime, which runs systemd in an ordinary container:

    docker run -d --runtime=sysbox-runc --name core keel/core:19.0-3 /sbin/init

Then `docker exec -it core keel-init` runs the first boot.

**Said plainly: on Docker, first boot and services are not guaranteed the
way they are on LXC.** Docker manages networking, `/etc/hosts`,
`/etc/resolv.conf` and the hostname itself, which the first boot screens,
`keel network` (0018) and the WireGuard overlay expect to own; nftables,
CrowdSec's bouncer and WireGuard need capabilities and kernel modules a
container may not have; and `--privileged` gives the container the host.
The Docker path is documented and best effort. **Keel's own tests use
system containers only** (LXC, as `docs/ci-cd.md` describes); nothing is
tested on Docker, and a defect seen only there is not a release blocker.

### 3. AWS and OpenStack: converted locally, later

Neither file is uploaded to a cloud as it is. The `.tar.zst` is a
container root filesystem: it has no kernel and no boot loader, and both
clouds import virtual machine disks (AWS `ec2 import-image`: VMDK, VHD,
OVA or raw; OpenStack Glance: qcow2, raw or ISO, among others). The ISO
can be installed by hand into a VM there, which stays the manual
alternative.

The plan is a **local conversion in keel**: `keel assemble --format raw|qcow2`
takes the same layers, adds a kernel, GRUB and a cloud datasource client,
resets the machine identity (section 8), and writes a disk the user
uploads with the cloud's own tools (`aws ec2 import-image`, `openstack image
create`). Keel publishes no cloud image and holds no cloud account.

**This is its own later phase**, validated on real AWS and OpenStack
accounts before it is announced, and **not built now**.

### 4. Names

TurnKey's Proxmox naming, which Keel already publishes and `bt-aplinfo`
parses:

    debian-13-keel-<app>_<ver>-<rel>_amd64.tar.zst
    debian-13-keel-<app>_<ver>-<rel>_amd64.iso

`<ver>-<rel>` is the appliance version and revision from the product's
changelog, as `release_version` reads it (for example `19.0-3`). A testing
build adds `+<label>-<date>` to `<rel>`, as the first GitHub pre-release
did (`19.0-3+step4-20260930`); a stable name has none. `bt-iso` writes
`turnkey-<app>-<ver>-<codename>-<arch>.iso` today; the release step
renames it.

### 5. One root filesystem

**The ISO is made from the template**, the `.tar.zst` `keel assemble`
writes: unpack it, reset what must be per machine (section 8), and add
fab's `cdroot` (the squashfs of the rootfs, isolinux and GRUB EFI,
`xorriso`, `isohybrid`). No `apt` runs in between. A separate fab ISO
build would be a second root filesystem for the same `<ver>-<rel>`, built
at another time from other package versions; since 0016 a Keel release is
the bytes its layers name, so one name is one set of bytes in both files.
The kernel, `grub-pc` and `tkl-installer` come from the layers' plans and
are in the template already.

Until that builder exists, `bt-iso` builds the ISO from the product with
the machine-id reset of buildtasks#16, which is proven on a real Core ISO
(445 MB, its squashfs 388 MB, 2026-10-01). It is the fallback, not the
release path.

**Built on the build host, never on the runner.** The ISO needs root for
fab's decks and mounts. The CI runner is an unprivileged LXC user without
sudo on the public services VM (`docs/ci-cd.md` section 6) and holds
nothing that is published. It runs the code's tests: `tests/machine-id`
makes small ISOs from a few files.

### 6. Where the files go

The bytes on `mirror.keellinux.org`, what describes and signs them on
`releases.keellinux.org`, as `docs/releases-host.md` and TurnKey split them:

```
mirror.keellinux.org/images/
  <app>/<ver>-<rel>/debian-13-keel-<app>_<ver>-<rel>_amd64.{tar.zst,iso}
                                     immutable: written once, never replaced
  debian-13-keel-<app>_<ver>-<rel>_amd64.tar.zst
                                     the flat name the Proxmox index points
                                     at today, a hard link to the file above

releases.keellinux.org/
  pve/aplinfo.dat{,.gz,.asc}         unchanged: the Proxmox index, stable only
  meta/<date>/MANIFEST{,.asc}        unchanged: the release MANIFEST
  <app>/<ver>-<rel>/                 one directory per appliance release
    SHA512SUMS, SHA512SUMS.asc       both files of that release (section 7)
    <name>.changelog                 the product changelog
    <name>.packages                  the package list the layers captured (0012)
  stable/INDEX, stable/INDEX.asc     per channel: one line per appliance,
  testing/INDEX, testing/INDEX.asc   "<app> <ver>-<rel> <sha512 of its SHA512SUMS>"
```

A channel index changes only in a release, so it is signed with the
release key in the attended step and needs no expiry: images are not an
update path, `apt` is (0039), and 0016's expiry exists to stop a mirror
freezing an updater. The download page reads it to say "the current stable
Core is 19.0-3".

`testing/` holds only signed builds. **An unsigned build never goes to
either host**: they serve nothing unsigned except the staging archive, and
the header says so (`docs/releases-host.md` section 5). Unsigned test
images go to GitHub pre-releases only (section 9).

### 7. Checksums and signatures

- `SHA512SUMS` per appliance release, in `sha512sum` format, so
  `sha512sum -c SHA512SUMS` works in a directory of downloads.
- `SHA512SUMS.asc`, a detached armoured signature by the release key, made
  in the attended step by `keel-release`'s signing phase. Verifiable with
  `gpg --verify` and with `sqv`, which Proxmox and apt use.
- The per-file `.sha512` and `.sha512.asc` stay, because the Proxmox index
  and existing instructions use them.
- The release `MANIFEST` lists both files with size and digest, and
  `keel-publish-mirror` refuses any file whose digest differs.

### 8. What each format's first boot makes for itself

Nothing that identifies a machine may be in a published file.

| Identity | `.tar.zst` (LXC, Proxmox, Docker) | ISO, live and installed |
| --- | --- | --- |
| `/etc/machine-id` (the DHCP DUID and IAID, the journal, MariaDB `server_id`) | emptied by `bt-layer` (buildtasks#15); systemd makes it at boot | emptied before the squashfs is made and checked in the ISO (buildtasks#16, tracker#24; on the real Core squashfs: an empty 0444 file and the D-Bus link); `tkl-installer` copies the squashfs as it is and has no machine-id step, so the empty file is what makes each install unique |
| SSH host keys, TLS and snakeoil pairs | none in a layer: `layer_audit_keys` refuses one (keel-core#8); `keel-host-keys.service` makes the missing ones and replaces published ones at every boot (inithooks#30); `10regen-sshkeys` and `15regen-sslcert` at first boot | the same packages and hooks; the ISO check must also run the key audit, which fab's ISO path does not call today |
| CrowdSec LAPI and CAPI credentials, bouncer key | removed by keel-core's `conf.d/main`, CAPI registration suppressed in the build (tracker#47); `keel apply` registers on the first enable (keel 0.13.0) | the same: `conf.d/main` runs in every fab build |
| WireGuard keys | the build fails if `/etc/wireguard` is not empty or a `wg-quick@` unit is enabled (keel-core#16); keel makes the pair at the first converge (keel#49) | the same |
| etcd member, Anubis key, MariaDB accounts | made by keel from the spec when enabled (keel#58, keel#62) | the same |

The later cloud conversion (section 3) must apply the same resets to the
disk it writes; its filesystem UUIDs are made per conversion, so they
differ between users but not between VMs made from one upload.

### 9. GitHub Releases

Each appliance repository (`keel-core`, `keel-web`, `keel-wordpress`, ...)
carries its own releases.

- **Tags.** `<ver>-<rel>` for a signed stable release (`19.0-3`), on the
  commit of the product the layers were built from.
  `testing-<ver>-<rel>-<date>` for a testing build
  (`testing-19.0-3-20261001`), and `testing-<ver>-<rel>-<label>-<date>`
  for a named test image, the shape of the first one
  (`testing-19.0-3-step4-20260930`). Testing releases are marked
  pre-release.
- **Assets.** The ISO and the `.tar.zst`, each with its `.sha512`, and,
  once signing exists, the same `SHA512SUMS` and `SHA512SUMS.asc` as on
  `releases.keellinux.org`, byte for byte. GitHub refuses an asset of
  2 GiB or more; the Core template is 386 MB and the Core ISO 445 MB, so
  both fit with room. A file that ever does not fit is left out of that
  release and its body links to the mirror; no file is split.
- **Consistency.** `releases.keellinux.org` is the source of truth and
  GitHub a second copy. A release is uploaded to GitHub only after
  `keel-publish-mirror` installed it, from the same staged files; the
  upload checks every asset against the signed `MANIFEST` first and
  GitHub's own asset digest (the API reports a sha256 per asset) after,
  and the release body names the `MANIFEST` URL. Stable releases are
  created **immutable** (GitHub's immutable releases), so an asset cannot
  be replaced; a correction is a new `<rel>`.
- **Where the upload runs.** `bin/keel-publish-github <date>` in
  Keel-Linux/apt, beside `keel-publish-mirror`, run in the attended
  release from a machine where `gh` is logged in to the organization, or
  from the build host with a fine-grained token limited to
  `contents: write` on the appliance repositories, readable by root only.
  **Never a workflow**: a workflow runs on the runner, which must hold
  neither the files nor a token that can publish them. Unsigned testing
  images are uploaded the same way, marked "not signed, not for
  production" in the title and the body, as the first one was.

### 10. Order of work

1. **buildtasks#16**: the machine-id of the ISO (tracker#24), merged after
   review.
2. **tracker#23, the pin.** A pin of 1001 downgrades any package newer in
   the image than in the archive, and an ISO user runs `apt upgrade` on
   day one. No ISO is published before every package of an image is in
   the archive first, or the pin is 990.
3. **The key audit on the ISO**: `bin/iso-machine-id-check` becomes the
   image check and also runs `layer_audit_keys` over the squashfs.
4. **The ISO from the template** in buildtasks (section 5), tested with
   fake templates like `tests/layer`, and proven by installing a Core ISO
   with `tkl-installer` twice on the test machines (two machine-ids, two
   key sets).
5. **`keel-release`**: build the ISO after `keel assemble`, add it to
   `MANIFEST`, write `SHA512SUMS` per appliance and sign it in the existing
   signing phase. `--sign-only` keeps working.
6. **`keel-publish-mirror`**: the per-appliance directories, the flat hard
   links, the channel indexes; refuse what `MANIFEST` does not list.
7. **`keel-publish-github`**, then the download page on keellinux.org,
   with the Docker instructions of section 2.
8. **Later, its own phase**: `keel assemble --format raw|qcow2` for AWS and
   OpenStack (section 3), validated on real accounts.

### 11. The attended step

Everything before it is built and staged by the agent on the build host
without a key. The maintainer then:

1. on the build host: `keel-release --sign-only <date>`, typing the
   passphrase once. It signs the template digests, the index, every
   `SHA512SUMS`, the channel indexes and `MANIFEST`: seconds, well inside
   the ten minutes the agent keeps the passphrase;
2. on his workstation: `keel-publish-mirror <date>`, which pulls the staged
   files to the public host and verifies them against `MANIFEST`. Core and
   Web in both formats are under 2 GiB: about 10 minutes, unattended once
   started;
3. `keel-publish-github <date>`: the same files to the two repositories'
   releases, a few minutes.

About **20 minutes** in all, of which the passphrase is under one minute.

## Resolved (maintainer, 2026-10-01)

The proposal of the same day published the template, the ISO, a qcow2 and
an OVA, then a VMDK zip, and dropped Xen, Docker, the AMI and the ARM
images. The maintainer decided:

- **Only the ISO and the `.tar.zst` are published.** The ISO covers
  VMware, VirtualBox, Proxmox VMs and bare metal, so the OVA, VMDK and
  qcow2 downloads are dropped with Xen, the Docker image formats, the AMIs
  and ARM.
- **Docker through `docker import` of the `.tar.zst`**, with the systemd
  caveat of section 2; still no Docker in Keel's own tests.
- **AWS and OpenStack by local conversion** (`keel assemble --format
  raw|qcow2`), a later phase validated on real accounts; the ISO install
  stays the manual alternative.
- **GitHub Releases as proposed**: the tags, the two files with their
  `.sha512` and the signed `SHA512SUMS`, uploaded only from the build host
  or an attended step.

The proposal's open questions are answered by this or no longer arise: the
ISO from the template (section 5, kept), the qcow2 first boot (no qcow2),
the dropped formats (above), the upload credential (section 9: either
place, never the runner), unsigned testing images on GitHub only (section
6, kept), immutable stable releases (section 9, kept).
