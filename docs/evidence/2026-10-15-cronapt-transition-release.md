# Evidence: keel-transition 0.2.3 and inithooks 2.3.6+keel26, tested and promoted

Date: 2026-10-15, 23:40 to 2026-10-16 00:20 UTC.
Changes: Keel-Linux/keel-transition#9 and #10 (0.2.3), Keel-Linux/inithooks#47
(2.3.6+keel26), apt#34 (the publish commits), keel-transition#11 (the
upgrade note).
Approval: the coordinator ordered the publish and the promotion, under the
maintainer's delegation.

Machines:

- Build host: `root@2804:710:d0:5:bb3f:380a:f07b:7951`, `/srv/keel-apt/apt`.
- Test host: hw12-br1 (`2804:710:d0:2::12`). Test CTs 9082 (TurnKey 19.0)
  and 9083 (Keel PostgreSQL), both new, both removed after the test. CTs
  9054 and 9062 were not touched.

Output is trimmed.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| 1. Build and publish to trixie-testing | PASS | keel-transition 0.2.3 and inithooks 2.3.6+keel26. `keel-publish-mirror`: exit 0, 3 suites verify. |
| 2. `--apply` on TurnKey 19.0 | PASS | Both cron-apt actions read `security.sources`. It has Debian and Keel trixie-security. The dry run: exit 0. |
| 3. `--rollback` | PASS | Both actions are byte-identical to the originals. |
| 4. The upgrade path after 0.2.0 to 0.2.2 | PASS | 0.2.3 and `--apply` again fix both actions. |
| 5. First boot with inithooks 2.3.6+keel26 | PASS | The first boot ended in 20 s. A second reboot ran no first boot. The host key stayed the same. |
| 6. Promote to trixie | Done | keel-transition 0.2.3 and inithooks 2.3.6+keel26. keel stays 0.23.21. |
| 7. Appliances with the broken cron-apt | None found | See section 7. |

## 1. Build and publish

```
$ bin/build-package keel-transition main
build-package: done: keel-transition_0.2.3_amd64.changes in /srv/keel-apt/incoming
$ bin/build-package inithooks master
build-package: done: inithooks_2.3.6+keel26_amd64.changes in /srv/keel-apt/incoming
$ bin/publish
publish: committed in /srv/keel-apt/apt: publish trixie-testing: inithooks 2.3.6+keel26, keel-transition 0.2.3
$ /tmp/keel-apt-tooling/bin/keel-publish-mirror --archive-only     # workstation
keel-publish-mirror: https://archive.keellinux.org trixie verifies
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
keel-publish-mirror: https://archive.keellinux.org trixie-security verifies
EXIT=0
```

The sources were the GitHub mirror of `Keel-Linux/keel-transition` (main
6abd485) and `Keel-Linux/inithooks` (master 4257b48). Both heads were the
same as on git.pop.coop.

## 2. `--apply` on a TurnKey 19.0 appliance

TurnKey publishes 19.0 as ISO images only, and the Proxmox index has 18.x
only. The test CT is the root file system of the 19.0 core ISO:

```
$ sha256sum turnkey-core-19.0-trixie-amd64.iso
3d90e71a3ba646c7a3f544e87cb32f36a00fe2d91d2f1606a6f76ff3b04fcd73   # same as the .hash file of TurnKey
# live/10root.squashfs, mounted read-only, packed as a CT template
$ cat /etc/turnkey_version
turnkey-core-19.0-trixie-amd64
$ dpkg-query -W cron-apt inithooks turnkey-keys
cron-apt 0.13.0.1
inithooks 2.3.6
turnkey-keys 0.1
```

keel-archive-keyring and keel-transition came from trixie-testing, through
a source file for the install only, which was removed after it:

```
keel 0.23.29
keel-archive-keyring 0.3.0
keel-transition 0.2.3
```

Before:

```
$ grep -h sourcelist /etc/cron-apt/action-available.d/5-install.{default,alt}
dist-upgrade -y ... -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/security.sources.sources ...
upgrade -y ...      -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/security.sources.sources ...
$ ls -l /etc/cron-apt/action.d/5-install
/etc/cron-apt/action.d/5-install -> ../action-available.d/5-install.default
0cd180766d1c44226bd3a342a9fd08854bb59a09fadae1fde8b332f242075e01  5-install.default
2f38ec74d6795f05e708e4db79cfb681673535200e08bf3dd8e5c991c1bdc0ca  5-install.alt
```

The apply:

```
$ keel-transition --apply
apply-exit=0
  create  /etc/apt/sources.list.d/security.sources  deb822, Debian, Signed-By .../debian-archive-keyring.gpg; Keel trixie-security, Signed-By .../keel-security-keyring.gpg
  update  /etc/cron-apt/action-available.d/5-install.default reads /etc/apt/sources.list.d/security.sources, the original kept in /var/lib/keel/transition/cron-apt/5-install.default
  update  /etc/cron-apt/action-available.d/5-install.alt reads /etc/apt/sources.list.d/security.sources, the original kept in /var/lib/keel/transition/cron-apt/5-install.alt
  rename  /etc/apt/sources.list.d/security.sources.sources to security.sources.sources.disabled-by-keel
  ...
  purge   turnkey-keys  dpkg -P, its files kept in /var/lib/keel/transition/turnkey-keys.tar for --rollback
```

After:

```
$ grep -h sourcelist /etc/cron-apt/action-available.d/5-install.{default,alt}
dist-upgrade -y ... -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/security.sources ...
upgrade -y ...      -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/security.sources ...
$ cat /etc/apt/sources.list.d/security.sources      # comments removed
Types: deb
URIs: http://security.debian.org/debian-security
Suites: trixie-security
Components: main non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb
URIs: https://archive.keellinux.org
Suites: trixie-security
Components: main
Signed-By: /usr/share/keyrings/keel-security-keyring.gpg
```

The dry run of the install action, with the source list option of
`/etc/cron-apt/action.d/5-install` and `-s` in place of `-y`:

```
$ apt-get update --error-on=any -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/security.sources -o Dir::Etc::sourceparts=nonexistent
Hit:1 http://security.debian.org/debian-security trixie-security InRelease
Get:2 https://archive.keellinux.org trixie-security InRelease [1,927 B]
Get:3 https://archive.keellinux.org trixie-security/main amd64 Packages [730 B]
upd-exit=0
$ apt-get -s dist-upgrade -o APT::Get::Show-Upgraded=true -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/security.sources ...
Conf linux-image-amd64 (6.12.111-1 Debian-Security:13/stable-security [amd64])
Conf openssl (3.5.7-1~deb13u3 Debian-Security:13/stable-security [amd64])
sim-exit=0
$ apt-cache policy        # with the same options
 990 https://archive.keellinux.org trixie-security/main amd64 Packages
     release o=Keel Linux,a=stable-security,n=trixie-security,l=Keel Linux security,c=main,b=amd64
 500 http://security.debian.org/debian-security trixie-security/main amd64 Packages
     release v=13,o=Debian,a=stable-security,n=trixie-security,l=Debian-Security,c=main,b=amd64
```

What the old action does after a transition, on the same CT:

```
$ apt-get -s dist-upgrade -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/security.sources.sources -o Dir::Etc::sourceparts=nonexistent
W: Unable to read /etc/apt/sources.list.d/security.sources.sources - RealFileExists (2: No such file or directory)
sim-exit=0
```

apt exits 0 with only a warning. So cron-apt installs no update, and
nothing tells the operator.

## 3. `--rollback`

```
$ keel-transition --rollback
rollback-exit=0
  remove   /etc/apt/sources.list.d/security.sources  Debian's source this tool wrote
  rename   /etc/apt/sources.list.d/security.sources.sources from security.sources.sources.disabled-by-keel, byte for byte
  restore  /etc/cron-apt/action-available.d/5-install.default from /var/lib/keel/transition/cron-apt/5-install.default, byte for byte
  restore  /etc/cron-apt/action-available.d/5-install.alt from /var/lib/keel/transition/cron-apt/5-install.alt, byte for byte
$ sha256sum -c cronapt.before
5-install.alt: OK
5-install.default: OK
$ ls /var/lib/keel/transition/cron-apt
ls: cannot access '/var/lib/keel/transition/cron-apt': No such file or directory
```

## 4. The upgrade path after 0.2.0 to 0.2.2

0.2.0 is the first version that sets `security.sources.sources` aside. It
was published in trixie-testing only. trixie had 0.1.1 until this
promotion. 0.2.1 and 0.2.2 were never published.

The test made the state that 0.2.0 to 0.2.2 leave: `--apply`, then the
original actions put back and the kept copies removed.

```
== as 0.2.2 left it
sourcelist=/etc/apt/sources.list.d/security.sources.sources
== keel-transition 0.2.3, then --apply again
reapply-exit=0
  update  /etc/apt/sources.list.d/security.sources  deb822, Debian, ...; Keel trixie-security, ...
  update  /etc/cron-apt/action-available.d/5-install.default reads /etc/apt/sources.list.d/security.sources, ...
  update  /etc/cron-apt/action-available.d/5-install.alt reads /etc/apt/sources.list.d/security.sources, ...
sourcelist=/etc/apt/sources.list.d/security.sources        # 5-install (default)
sourcelist=/etc/apt/sources.list.d/security.sources        # 5-install.alt
rollback-exit=0, both actions OK against the originals
```

The fix cannot come through cron-apt, because the broken action reads no
source. The upgrade path is manual, as root:

1. `apt-get update`
2. `apt-get install keel-transition` (0.2.3 is in trixie now)
3. `keel-transition --apply`

keel-transition#11 adds these steps to its README.

## 5. First boot with inithooks 2.3.6+keel26

CT 9083 is new, from the step 12 PostgreSQL template. Its `35pgsqlpass`
is still the old hook (common#55 is not in an image yet), so this tests
inithooks#47 alone. `RUN_FIRSTBOOT` was set to `false` before the first
start, inithooks 2.3.6+keel26 was installed from trixie-testing, and
`RUN_FIRSTBOOT` was set to `true` again before the reboot.

```
$ dpkg-query -W inithooks
inithooks 2.3.6+keel26
$ pct reboot 9083
first boot ended after 20 s
INFO: [35pgsqlpass] running
ERR: [35pgsqlpass] failed - exit code 1
INFO: [98finalize] running
INFO: [98finalize] successfully completed
SHA256:1kyhHxhs0dMwT1Iq5J+cfSSMUi9ZF/gImSZ3YiOeyxA    # ED25519 host key
"Running firstboot scripts": 1
$ pct reboot 9083
RUN_FIRSTBOOT=false
"Running firstboot scripts": 1
SHA256:1kyhHxhs0dMwT1Iq5J+cfSSMUi9ZF/gImSZ3YiOeyxA    # the same
passwd -S root: P
```

The old hook now fails at once instead of waiting on the console, and the
first boot ends. The reboot after it runs no first boot hook.

## 6. Promote to trixie

```
$ bin/promote keel-transition=0.2.3 inithooks=2.3.6+keel26
would copy from trixie-testing into trixie:
  keel-transition 0.2.3 all (was 0.1.1)
  inithooks 2.3.6+keel26 all (was 2.3.6+keel5)
$ bin/promote --yes keel-transition=0.2.3 inithooks=2.3.6+keel26
promoted into trixie: keel-transition inithooks
6bd6d2b promote trixie: keel-transition 0.2.3, inithooks 2.3.6+keel26
$ keel-publish-mirror --archive-only
... trixie verifies / trixie-testing verifies / trixie-security verifies
EXIT=0
$ curl -6 -fsS https://archive.keellinux.org/dists/trixie/main/binary-amd64/Packages
Package: inithooks        Version: 2.3.6+keel26
Package: keel             Version: 0.23.21
Package: keel-transition  Version: 0.2.3
```

keel was not promoted. It stays 0.23.21 in trixie until the real-node
matrix.

## 7. Appliances with the broken cron-apt

- The Keel CTs on hw12-br1 (124, 125, 9003, 9004, 9051, 9052, 9053, 9055)
  have no keel-transition. Their install action reads
  `/etc/apt/sources.list.d/security.sources`, which common writes. CT 241
  has no cron-apt action. 9054 and 9062 were not read.
- The access log of the public host has 20 downloads of
  `keel-transition_0.2.0_all.deb`, from 2026-10-02 to 2026-10-08. The
  sources are 127.0.0.1 (the mirror path of the CI runner), the
  Keel-Linux-Runner VM (8500, which runs throwaway CI containers), and 2
  addresses of the BR1 network that this test could not map to a machine.
- No appliance with the broken action was found. An appliance that ran
  0.2.0 and that this check did not reach takes the manual path of
  section 4.

## Cleanup

CTs 9082 and 9083 are destroyed. The TurnKey ISO, its root file system and
the CT template made from it are removed from hw12-br1.
