# Evidence: trixie-testing signed by the testing key

Date: 2026-10-15, 20:00 to 22:45 UTC.
Decision: 0055 (one key per purpose, signed on the build host), step 6.
Changes: Keel-Linux/apt#31 (tooling), apt#32 and apt#33 (the publish
commits of the build host), Keel-Linux/common#54 (keel.sources).

Machines:

- Build host: `root@2804:710:d0:5:bb3f:380a:f07b:7951`. The publisher
  checkout is `/srv/keel-apt/apt`. The reprepro base is
  `/srv/keel-apt/repo`.
- Workstation: the tooling copy `/tmp/keel-apt-tooling`, which runs
  `keel-publish-mirror`. It was replaced with apt 533eec4 before the
  push. A backup of the old copy is in the session scratch directory.
- Test host: hw12-br1 (`2804:710:d0:2::12`), CT 9081, new, from the step
  12 PostgreSQL template. The CT was removed after the test. CTs 9054
  and 9062 were not touched.

Output is trimmed. The subkey fingerprints are written as `(main subkey)`
and `(testing subkey)`.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| 1. The decision: 2 signatures, not the testing key alone | Decided | Readers with the main keyring alone exist. The switch to the testing key alone stops their `apt update`. |
| 2. Measure with throwaway keys | PASS | reprepro 5.3 signs with 2 keys. apt 3.0.3 (sqv) accepts the suite with either keyring alone. gpgv alone exits 2. |
| 3. Tooling, apt#31 | PASS | CI green. 400 bats tests, kcov 99.71 percent. |
| 4. Re-sign on the build host | PASS | `git pull --ff-only`, then `reprepro export trixie-testing`. The InRelease of trixie and trixie-security did not change. |
| 5. Publish | PASS | `keel-publish-mirror --archive-only`: exit 0. The built-in verify passed for trixie, trixie-testing and trixie-security. |
| 6. Verify from outside | PASS | verify-repo: testing keyring exit 0, main keyring exit 0, security keyring exit 4. |
| 7. apt-get update, CT 9081 | PASS | Signed-By testing: exit 0. Signed-By main: exit 0. Signed-By security: exit 100, as it must. |
| 8. Packages | PASS | trixie-testing has keel 0.23.29. trixie has keel 0.23.21. Nothing was promoted. |

## 1. Why 2 signatures

The task was to sign trixie-testing with the testing key alone. These
readers of the suite have the main keyring alone today:

- the keel.sources of a testing-track appliance. The step 12 PostgreSQL
  template has the trixie-testing stanza enabled, with
  `Signed-By: /usr/share/keyrings/keel-archive-keyring.gpg` (seen in CT
  9081). keel 0.23.29 is in trixie-testing only, so the pair CTs read
  that suite too;
- the `keel-pve` source on the Proxmox hosts (`lib/source.sh` of
  keel-pve writes `Suites: trixie-testing` with the main keyring);
- the CI containers of `Keel-Linux/.github`, which trust the keyring of
  the image.

A suite signed by the testing key alone stops the `apt update` of each
of them. So trixie-testing gets 2 signatures, by main and by testing, as
the images role did. The main key goes from the suite when no reader has
the main keyring alone. `docs/layout.md` of apt gives that order.

## 2. Measure with throwaway keys

2 throwaway ed25519 keys, A and B, on the workstation. `SignWith: A B` in
a scratch reprepro configuration:

```
$ reprepro -b repo includedeb trixie-testing hello.deb
Exporting indices...
$ grep -c "BEGIN PGP SIGNATURE" repo/dists/trixie-testing/Release.gpg
1
$ gpg --verify repo/dists/trixie-testing/InRelease
gpg: Good signature from "mainA <mainA@example.invalid>" [ultimate]
gpg: Good signature from "testB <testB@example.invalid>" [ultimate]
apt keyring A only: exit 0
gpgv keyring A only: exit 2
sqv keyring A: exit 0
apt keyring B only: exit 0
gpgv keyring B only: exit 2
sqv keyring B: exit 0
```

`apt` is `apt-get update --error-on=any` with `signed-by` of one keyring.
apt reads the suite with either key. gpgv alone exits 2 for the
signature that it has no key for. So `bin/verify-repo` now reads the
status lines of gpgv. Of the other gpgv readers, keel-transition checks
trixie only by default, and keel-wordpress checks trixie-staging.

## 3. Tooling, apt#31

- `conf/distributions`: `SignWith` of trixie-testing names
  `AD0964BE3F09DED469A3B6B2148E951314703180` (main) and
  `9B3CFC527FAD0EA5298D84ED05B5A6FE7E3BA58A` (testing).
- `bin/publish` gives each key the refusals (exit 4 and 5) and the expiry
  alert.
- `bin/verify-repo` checks trixie-testing against the testing keyring
  when no `--keyring` is given. 1 good signature by the keyring and no bad
  signature pass.
- `conf/pool.list`: the layer builds read trixie-testing with the testing
  keyring.

CI: tests and security green. Merge commit 533eec4.

## 4. Re-sign on the build host

```
$ git status -sb
## main...origin/main [ahead 2]       # the publish commits of 0.23.27 and 0.23.29
```

The 2 local publish commits went to main first, through apt#32, so that
the pull could fast-forward.

```
$ git pull --ff-only
533eec4 Merge pull request 'feat: trixie-testing is signed by the main key and the testing key' (#31) ...
$ grep "^SignWith" conf/distributions
SignWith: AD0964BE3F09DED469A3B6B2148E951314703180
SignWith: AD0964BE3F09DED469A3B6B2148E951314703180 9B3CFC527FAD0EA5298D84ED05B5A6FE7E3BA58A
SignWith: D97E853FBDBB24492002067BA92969F1BF3B71C6
SignWith: 33516A960EC47DC1DB403ECC9DA966DE8C77FDE9
```

Before:

```
4c73042af12ef36cdc1e8f1932979562f5bf5f267165f0abf1349165a624da4d  repo/dists/trixie/InRelease
0347e9d7702af75c92b773a709fcb6436dec9ead740459d0a6204c4938bbda90  repo/dists/trixie-testing/InRelease
89f0255f893a0934f8828932319c14edf4923ad1cde5212dbe0924e1073f9532  repo/dists/trixie-security/InRelease
Date: Thu, 15 Oct 2026 20:02:30 UTC                                 # trixie-testing Release
Package: keel / Version: 0.23.29                                    # trixie-testing Packages
```

The refusals and the expiry alert of `bin/publish`, then the export of
the one suite:

```
$ bash -c ". lib/common.sh; . lib/publish.sh; publish_check_signing trixie-testing"
signing subkey (main subkey) expires on 2028-09-26, in 711 days
signing trixie-testing with subkey (main subkey) of AD0964BE3F09DED469A3B6B2148E951314703180
signing subkey (testing subkey) expires on 2029-10-13, in 1093 days
signing trixie-testing with subkey (testing subkey) of 9B3CFC527FAD0EA5298D84ED05B5A6FE7E3BA58A
check-exit=0
$ reprepro -b /srv/keel-apt/repo --confdir /srv/keel-apt/apt/conf export trixie-testing
Exporting trixie-testing...
```

After:

```
4c73042af12ef36cdc1e8f1932979562f5bf5f267165f0abf1349165a624da4d  repo/dists/trixie/InRelease          # same
26ce422c146d83796e4aeaf802c20a2a9786d783c46eeaff3ee8a54565368ef0  repo/dists/trixie-testing/InRelease  # new
89f0255f893a0934f8828932319c14edf4923ad1cde5212dbe0924e1073f9532  repo/dists/trixie-security/InRelease # same
Date: Thu, 15 Oct 2026 22:31:17 UTC
$ gpg --status-fd 1 --verify repo/dists/trixie-testing/InRelease
GOODSIG (main subkey)
VALIDSIG (main subkey) AD0964BE3F09DED469A3B6B2148E951314703180
GOODSIG (testing subkey)
VALIDSIG (testing subkey) 9B3CFC527FAD0EA5298D84ED05B5A6FE7E3BA58A
```

The publisher functions copied the tree and committed it:

```
a265f7e publish trixie-testing: signed by the main key and the testing key
 dists/trixie-testing/InRelease   | 12 +++++++-----
 dists/trixie-testing/Release     |  2 +-
 dists/trixie-testing/Release.gpg | 10 ++++++----
```

That commit goes to main through apt#33.

The loopback mirror of the build host, before the push:

```
$ bin/verify-repo http://[::1]:8080/apt --dist trixie-testing                         exit=0  (testing keyring)
$ bin/verify-repo ... --keyring keys/keel-archive-keyring.asc                         exit=0
$ bin/verify-repo ... --keyring keys/keel-testing-keyring.asc                         exit=0
$ bin/verify-repo ... --keyring keys/keel-security-keyring.asc                        exit=4
```

## 5. Publish

```
# workstation
$ /tmp/keel-apt-tooling/bin/keel-publish-mirror --archive-only
keel-publish-mirror: https://archive.keellinux.org trixie verifies
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
keel-publish-mirror: https://archive.keellinux.org trixie-security verifies
EXIT=0
```

## 6. Verify from outside

The keyrings come from a fresh clone of Keel-Linux/keel-keys. The
verifier is apt 533eec4 on the workstation.

```
public trixie/InRelease          4c73042a...a624da4d   # same as before
public trixie-testing/InRelease  26ce422c...65368ef0   # the new file of the build host
public trixie-security/InRelease 89f0255f...0f9532     # same as before

$ verify-repo https://archive.keellinux.org --dist trixie-testing
verify-repo: InRelease and Release.gpg: good signatures with .../keys/keel-testing-keyring.asc
keel 0.23.29 all
exit=0
$ verify-repo ... --dist trixie-testing --keyring keel-keys/keys/keel-trixie-testing.asc     exit=0
$ verify-repo ... --dist trixie-testing --keyring keel-keys/keys/keel-trixie-main.asc        exit=0
$ verify-repo ... --dist trixie-testing --keyring keel-keys/keys/keel-trixie-security.asc
verify-repo: signature check failed for https://archive.keellinux.org/dists/trixie-testing
exit=4
$ verify-repo https://archive.keellinux.org --dist trixie
keel 0.23.21 all
exit=0
```

## 7. apt-get update in CT 9081

CT 9081 has apt 3.0.3, sqv 1.3.0 and keel-archive-keyring 0.3.0 (0.2.0
in the template, upgraded from trixie). Each run reads 1 sources file
with the trixie-testing stanza alone, and its own lists directory:

```
== Signed-By keel-testing-keyring.gpg
Get:1 https://archive.keellinux.org trixie-testing InRelease [2,127 B]
Get:2 https://archive.keellinux.org trixie-testing/main amd64 Packages [15.6 kB]
update-exit=0
== Signed-By keel-archive-keyring.gpg
Get:1 https://archive.keellinux.org trixie-testing InRelease [2,127 B]
Get:2 https://archive.keellinux.org trixie-testing/main amd64 Packages [15.6 kB]
update-exit=0
== Signed-By keel-security-keyring.gpg (must fail)
W: OpenPGP signature verification failed: ... Missing key (main subkey) ... Missing key (testing subkey) ...
E: The repository 'https://archive.keellinux.org trixie-testing InRelease' is not signed.
update-exit=100
```

`apt-cache policy keel` with the testing keyring: candidate 0.23.29, from
`trixie-testing/main`.

The full sources of the CT, with the trixie-testing stanza of common#54
(`Signed-By: /usr/share/keyrings/keel-testing-keyring.gpg`):

```
Hit:4 https://archive.keellinux.org trixie InRelease
Get:5 https://archive.keellinux.org trixie-testing InRelease [2,127 B]
update-exit=0
```

0 `W:` and 0 `E:` lines.

## 8. What did not change

- trixie: InRelease byte-identical, keel 0.23.21. Nothing was promoted.
- trixie-security: InRelease byte-identical.
- trixie-testing: the same Packages, keel 0.23.29. Only the Release
  date and the signatures changed.

## Before the main key goes from trixie-testing

The main key stays in `SignWith` of trixie-testing until each reader has
the testing keyring:

1. Images built from common#54 replace the step 12 templates, and the
   appliances on the testing track get the new stanza.
2. The `keel-pve` source names `keel-testing-keyring.gpg`, or names
   `trixie` once keel-pve is promoted.
3. The CI containers of `Keel-Linux/.github` trust the testing keyring.
4. Then remove the main key from `SignWith`, re-sign, and test every
   reader again with a suite signed by the testing key alone.
