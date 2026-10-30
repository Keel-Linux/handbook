# Evidence: stable 1, the upgrade from the public `trixie` to the 48 packages, on a private archive

Date: 2026-10-25. The time zone is UTC. Plan: `docs/releases/stable-1-plan.md`,
section 4, item U, and section 8 (option a). Nothing was signed or made
public. No secret is in this file.

## Result

| Item | Result |
| --- | --- |
| The 48 files are the files of `trixie-testing` | PASS. The files are from the pool of the build host, after `bin/promote --yes` copied them to `trixie`. `dpkg-scanpackages` made a `Packages` file of them. The archive is not signed. The CT reads it as a `file:` source with `Trusted: yes` |
| Upgrade of a core CT | PASS. keel 0.20.0 to 0.23.55, inithooks +keel26 to +keel27, keel-overlay-installer 0.1.0 to 0.2.0, keel-overlay-vip 0.1.1 to 0.2.0 |
| Upgrade of a web CT | PASS. The same 4 packages, and keel-overlay-anubis 0.1.0 to 0.1.1 and keel-overlay-coraza 0.1.3 to 0.1.4 (6 upgraded) |
| `dpkg --audit` | empty on both CTs |
| `systemctl --failed` | empty on both CTs, after each stage |
| Conffile prompts | 0 on both CTs. The upgrade needed no answer |
| Second `apt-get -s dist-upgrade` | 0 to upgrade, 0 to install, 0 to remove on both CTs |
| `keel diff` | no drift on both CTs, after each stage |
| keel-core and keel-web after the upgrade | PASS. See "Stage C" |

## Method

The test hosts and CTs:

- Host: hw12-br1 (`root@2804:710:d0:2::12`). The new CTs 9240 (core) and
  9241 (web) were free before the test. Both were removed after it. No other
  CT was read or changed.
- The templates are `debian-13-keel-core_19.0-9_amd64.tar.zst` and
  `debian-13-keel-web_19.0-4_amd64.tar.zst` of the public Proxmox index.
- The CTs have a network on VLAN 5 with DHCP, so Debian and the public Keel
  archive are reachable.
- Storage: `local-lvm` (LVM thin provisioning).

The private archive:

1. The 48 `.deb` files were collected from the build host pool
   `/srv/keel-apt/repo/pool/main/`, after `bin/promote --yes` copied them
   from `trixie-testing` to `trixie` (commit `a992cbf`).
2. `dpkg-scanpackages` made a `Packages` file. `apt-ftparchive` made a
   `Release` file with `Origin: Keel Linux`, so the pin 990 of the image
   applies to it. The archive is not signed. The CT reads it as a `file:`
   source with `Trusted: yes`.
3. The tarball of the 48 debs (45 MB) was transferred from the build host to
   BR1, extracted, and pushed into each CT.

The three stages:

1. Stage A. Turn the `trixie-testing` source off (`Enabled: no`), as on a
   stable machine. Run `apt-get update` and `apt-get dist-upgrade` against
   the public `trixie`. This is the state of a stable machine today.
2. Stage B. Add the private archive. Run `apt-get -s dist-upgrade`, then
   `apt-get dist-upgrade`. Then run the checks of the result table.
3. Stage C. Install `keel-core` on the core CT and `keel-web` on the web CT.

## Output, trimmed

Stage A on the core CT (the public `trixie` today):

```
Removing keel-core (0.1.3) ...
Removing keel-overlay-etcd (0.2.0) ...
Unpacking keel (0.23.21) over (0.20.0) ...
Unpacking inithooks (2.3.6+keel26) over (2.3.6+keel23) ...
4 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.
```

Stage A on the web CT:

```
Removing keel-web (0.2.0) ...
Removing keel-core (0.1.3) ...
Removing keel-overlay-etcd (0.2.0) ...
Unpacking keel (0.23.21) over (0.20.0) ...
4 upgraded, 0 newly installed, 3 to remove and 0 not upgraded.
```

Stage B on the core CT:

```
Inst keel [0.23.21] (0.23.55 Keel Linux:trixie [all])
Inst inithooks [2.3.6+keel26] (2.3.6+keel27 Keel Linux:trixie [all])
Inst keel-overlay-installer [0.1.0] (0.2.0 Keel Linux:trixie [all])
Inst keel-overlay-vip [0.1.1] (0.2.0 Keel Linux:trixie [all])
4 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
audit rc 0, systemctl --failed empty
diff: no drift
```

Stage B on the web CT:

```
Inst keel [0.23.21] (0.23.55 Keel Linux:trixie [all])
Inst inithooks [2.3.6+keel26] (2.3.6+keel27 Keel Linux:trixie [all])
Inst keel-overlay-anubis [0.1.0] (0.1.1 Keel Linux:trixie [all])
Inst keel-overlay-coraza [0.1.3] (0.1.4 Keel Linux:trixie [all])
Inst keel-overlay-installer [0.1.0] (0.2.0 Keel Linux:trixie [all])
Inst keel-overlay-vip [0.1.1] (0.2.0 Keel Linux:trixie [all])
6 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
audit rc 0, systemctl --failed empty
diff: no drift
```

Stage C on the core CT:

```
Inst etcd-client, keel-overlay-etcd 0.4.0, keel-core 0.1.3
3 newly installed
audit empty, systemctl --failed empty, diff: no drift
```

Stage C on the web CT:

```
Inst etcd-client, keel-overlay-etcd 0.4.0, keel-core 0.1.3,
     syncthing 2.1.6+keel1, keel-overlay-syncthing 0.1.0, keel-web 0.3.6
6 newly installed
keel-web: the default site is enabled in place of Debian's default site
audit empty, systemctl --failed empty, diff: no drift
```

## Difference from the 46-package test of 2026-10-24

The test of 2026-10-24 (`2026-10-24-stable-1-upgrade-private.md`) used 46
packages with keel 0.23.49. This test uses 48 packages with keel 0.23.55.
The two new packages are keel-overlay-syncthing 0.1.0 and syncthing
2.1.6+keel1. Both `dist-upgrade` does not install them (they are new,
not upgrades). `apt-get install keel-web` installs them because keel-web
0.3.6 depends on keel-overlay-syncthing.

The keel upgrade is 0.23.21 to 0.23.55 (was 0.23.49). The additional
fixes (keel#224, keel#225, keel#228) are in the file replication code
and do not change the upgrade behaviour.

## Finding (same as the 46-package test)

An image of the old pre-releases (core 19.0-9, web 19.0-4) loses
`keel-core` and `keel-overlay-etcd` in stage A, before our change. The
public `trixie` has keel 0.23.21 and does not have `keel-core`, so apt
removes the two packages. The same happens in the web CT (3 packages).
This is the state of any machine of those images today.

The 48 packages do not bring the removed packages back by themselves:
`dist-upgrade` upgrades only what is installed. After stage B the machine
has no `keel-core`. The command `apt-get install keel-core` (core) or
`apt-get install keel-web` (web) installs them with no conflict, as stage C
shows.

For the release notes of stable 1: a machine of an old pre-release image
must run `apt-get install keel-core` or `apt-get install keel-web` after
the upgrade. The new images of stable 1 have both packages from the start.
