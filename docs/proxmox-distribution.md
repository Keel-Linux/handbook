# How templates reach Proxmox VE, and what Keel has to do

Verified 2026-09-25 against pve-manager `PVE/APLInfo.pm` (master) and the
live TurnKey index.

## How it works today

`pveam update` fetches template indexes from a list that is hardcoded in
`PVE::APLInfo::get_apl_sources`: `download.proxmox.com/images/aplinfo-pve-9.dat`
and `releases.turnkeylinux.org/pve/aplinfo.dat`. For each source it downloads
`<file>.gz` and `<file>.asc`, verifies the signature with `sqv` against
`/usr/share/doc/pve-manager/trustedkeys.gpg` (a keyring shipped inside the
pve-manager package), parses the file, and stores it under
`/var/lib/pve-manager/apl-info/<host>`. `load_data` then reads only the files
of those hardcoded hosts, so a file dropped into that directory by anyone else
is ignored. There is no configuration file to add a source.

The index is a plain text file of records separated by blank lines:

```
Package: turnkey-ansible
Version: 18.0-1
Type: lxc
OS: debian-12
Section: turnkeylinux
Architecture: amd64
Location: http://mirror.turnkeylinux.org/turnkeylinux/images/proxmox/debian-12-turnkey-ansible_18.0-1_amd64.tar.gz
Infopage: http://www.turnkeylinux.org/ansible
ManageUrl: http://__IPADDRESS__/
sha512sum: 2317b91a...
Description: TurnKey Ansible
 TurnKey Ansible - Radically simple IT automation platform
```

TurnKey's index lists 111 packages today, all 18.0 on debian-12; no 19.0
container is listed, consistent with the empty debian-13 directory on the
mirror. Each `Location` is a single monolithic tarball; `pct create` and the
web UI only know that shape.

## Consequently, three things, in order

1. **Produce the index.** Done, unsigned until the key exists: `bt-aplinfo`
   in buildtasks (`docs/aplinfo.md` there) takes the templates `keel assemble`
   writes, builds one record per template (name, version and architecture
   from the file name, sha512 from the file, Description from the product's
   `pve-description` or README title), validates each record the way
   `PVE::APLInfo` reads it, and writes `aplinfo.dat` and a reproducible
   `aplinfo.dat.gz`. With `BT_GPGKEY` set it also writes `aplinfo.dat.asc`
   (`gpg --detach-sign --armor`, verified in the tests with `sqv`); without
   it, the run prints a warning that pveam refuses an unsigned index, which
   is the state until the replacement signing subkey of 0005 is on the build
   host. To be served at `https://releases.keellinux.org/pve/aplinfo.dat{.gz,.asc}`
   over IPv6.
2. **A package for the Proxmox host, `keel-pve`,** until (3) exists: installs the
   project keyring, fetches and verifies our index with the same `sqv` call
   pveam uses, and downloads a chosen template into the storage's `vztmpl`
   content, where `pveam list`, `pct create` and the web UI already pick up
   local templates. This is also where the layered model meets Proxmox: the
   package can `keel pull` the layers and assemble the single tarball Proxmox
   expects, so the user still gets the download savings while Proxmox sees a
   normal template. What it cannot do: appear in the "Templates" download
   dialog next to TurnKey, because that list is the hardcoded sources.
3. **Upstream inclusion.** Being listed like TurnKey means a change in
   pve-manager: our host in `get_apl_sources` and our public key in
   `trustedkeys.gpg`, submitted to the Proxmox developers. Realistic only once
   the project is public, the index has been stable for a while, and the key
   custody policy exists. It is the goal, and (1) plus (2) are what make the
   request credible.

## Open points

- The web UI download dialog will not show Keel templates before (3);
  documentation for (2) must say so plainly.
- Proxmox verifies with `sqv` (Sequoia), so the project key must be a plain
  OpenPGP key without unusual algorithms; check that when the key is created.
- Template file name: `debian-13-keel-<app>_<version>-<revision>_<arch>.tar.zst`,
  settled with bt-aplinfo. pveam accepts `.tar.zst`: pve-storage
  `PVE/Storage.pm` defines `VZTMPL_EXT_RE_1` as `.tar`, `.tar.gz`, `.tar.xz`,
  `.tar.zst` or `.tar.bz2`, and `PVE::APLInfo` derives the template name from
  `Location` with that regex (verified 2026-09-26; details in buildtasks
  `docs/aplinfo.md`).
