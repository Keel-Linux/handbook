# Evidence: stable 1, the upgrade from the public `trixie` to the 46 packages, on a private archive

Date: 2026-10-24. The time zone is UTC. Plan: `docs/releases/stable-1-plan.md`,
section 4, item U. Nothing was signed or made public. No secret is in this
file.

## Result

| Item | Result |
| --- | --- |
| The 46 files are the files of `trixie-testing` | PASS. The `InRelease` of `trixie-testing` has 2 good signatures, one of the main role and one of the testing role. The sha256 of each of the 46 `.deb` files is the sha256 in its `Packages` file |
| Upgrade of a core CT | PASS. keel 0.23.21 to 0.23.49, inithooks +keel26 to +keel27, keel-overlay-installer 0.1.0 to 0.2.0, keel-overlay-vip 0.1.1 to 0.2.0 |
| Upgrade of a web CT | PASS. The same 4 packages, and keel-overlay-anubis 0.1.0 to 0.1.1 and keel-overlay-coraza 0.1.3 to 0.1.4 |
| `dpkg --audit` | empty on both CTs |
| `systemctl --failed` | empty on both CTs, after each stage |
| Conffile prompts | 0 on both CTs. The upgrade needed no answer |
| Second `apt-get -s dist-upgrade` | 0 to upgrade, 0 to install, 0 to remove on both CTs |
| `keel diff` | exit 0, no drift, on both CTs, after each stage |
| keel-core and keel-web after the upgrade | **Finding.** See "Finding" |

## Method

The test hosts and CTs:

- Host: hw12-br1 (`root@2804:710:d0:2::12`). The new CTs 9200 (core) and 9201
  (web) were free before the test. Both were removed after it. No other CT was
  read or changed.
- The templates are `debian-13-keel-core_19.0-9_amd64.tar.zst` and
  `debian-13-keel-web_19.0-4_amd64.tar.zst` of the public Proxmox index. The
  `sha512sum -c` of each file with the public `.sha512` gave OK.
- The CTs have a network on VLAN 5 with DHCP, so Debian and the public Keel
  archive are reachable.

The private archive:

1. The 46 `.deb` files of the plan were downloaded from the public archive
   `trixie-testing`, and checked as in the first row of the result.
2. `dpkg-scanpackages` made a `Packages` file. `apt-ftparchive` made a
   `Release` file with `Origin: Keel Linux`, so the pin 990 of the image
   applies to it. The archive is not signed. The CT reads it as a `file:`
   source with `Trusted: yes`. We signed nothing. The tar of the archive has
   sha256 `92523bd753cde635` (first 16).

The two stages, in `upg.sh` and `upg2.sh` (the scripts are in the PR text of
the apt tooling and in this file):

1. Stage A. Turn the `trixie-testing` source off, as on a stable machine. Run
   `apt-get update` and `apt-get dist-upgrade` against the public `trixie`.
   This is the state of a stable machine today.
2. Stage B. Add the private archive. Run `apt-get -s dist-upgrade`, then
   `apt-get dist-upgrade`. Then run the checks of the result table.
3. Stage C. Install `keel-core` on the core CT and `keel-web` on the web CT.

## Output, trimmed

Stage A on the core CT (the public `trixie` today):

```
Unpacking keel (0.23.21) over (0.20.0) ...
Unpacking inithooks (2.3.6+keel26) over (2.3.6+keel23) ...
4 upgraded, 0 newly installed, 2 to remove and 0 not upgraded.
remove keel-core:all 0.1.3
remove keel-overlay-etcd:all 0.2.0
```

Stage B on the core CT:

```
Inst keel [0.23.21] (0.23.49 Keel Linux private upgrade test:stable [all])
Inst inithooks [2.3.6+keel26] (2.3.6+keel27 ...)
Inst keel-overlay-installer [0.1.0] (0.2.0 ...)
Inst keel-overlay-vip [0.1.1] (0.2.0 ...)
4 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
audit rc 0
diff: 2 same, 0 drift, 0 unknown, 11 not declared, 1 not compared; no drift
```

Stage B on the web CT: the same, with `keel-overlay-anubis` 0.1.0 to 0.1.1 and
`keel-overlay-coraza` 0.1.3 to 0.1.4 (6 upgraded).

Stage C:

```
core CT:  Inst etcd-client, keel-overlay-etcd 0.4.0, keel-core 0.1.3
web CT:   Inst etcd-client, keel-overlay-etcd 0.4.0, keel-core 0.1.3, keel-web 0.3.3
diff: 2 same, 0 drift, 0 unknown, 12 not declared, 1 not compared; no drift
```

## Finding

An image of the old pre-releases (core 19.0-9, web 19.0-4) loses
`keel-core` and `keel-overlay-etcd` in stage A, before our change. The
public `trixie` has keel 0.23.21 and does not have `keel-core`, so apt removes
the two packages. The same happens in the web CT (3 packages). This is the
state of any machine of those images today.

The 46 packages do not bring the removed packages back by themselves:
`dist-upgrade` upgrades only what is installed. After stage B the machine
has no `keel-core`. The command `apt-get install keel-core` (core) or
`apt-get install keel-web` (web) installs them with no conflict, as stage C
shows.

For the release notes of stable 1: a machine of an old pre-release image must
run `apt-get install keel-core` or `apt-get install keel-web` after the
upgrade. The new images of stable 1 have both packages from the start.

## What this test does not cover

- A PostgreSQL pair or a MariaDB pair node. The pair test of the plan covers
  that, on the images of stable 1.
- The services of the overlays. etcd, the VIP and Coraza stay off in a simple
  installation, and the test does not start them.
