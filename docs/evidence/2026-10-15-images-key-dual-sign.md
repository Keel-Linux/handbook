# Evidence: the image artifacts signed by main and images

Date: 2026-10-15, 16:20 to 17:45 UTC.
Decision: 0055, step 4 (images).
Approval: the coordinator gave this task. It allows publication of image
and index artifacts. It does not allow a keel release.

Keys (public fingerprints only):

| Role | Primary | Signing subkey |
| --- | --- | --- |
| main | `AD0964BE3F09DED469A3B6B2148E951314703180` | `03041024F4B2C0C2F42DDDEA04906EAB77513310` |
| images | `E71DB9C3CA6AC18075395CC3ED3A709C4F3E2F3C` | `39DAE662C4726AC7A66C250BEF26DA5C869ECDC7` |

Machines:

- Build host: `root@2804:710:d0:5:bb3f:380a:f07b:7951`. Tooling:
  `/srv/keel-apt/apt` at apt 03c30c6.
- Public host: `popsolutions@keellinux.org`.
- Test host: BR3-THIN (`root@2804:710:d0:c::1:1`), Proxmox VE 9.2.2,
  sqv 1.3.0. CT 9081 was made for the test and is removed. CT 9071 (the
  etcd witness of the other agent) did not change. BR1 and BR2 did not
  change.

Output is trimmed. No secret is in this file.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| 1. Signers changed, 1 PR for each repository | DONE | apt#30 and buildtasks#24 merged. keel#176 open, see section 1 |
| 2. How Proxmox verifies `aplinfo.dat.asc` | MEASURED | `pveam` has 2 fixed sources and the pve-manager keyring. An admin adds no key file. Keel uses `keel-pve` and `/usr/share/keyrings/keel-images-keyring.gpg` |
| 3. Re-sign of the current artifacts | PASS | release 2026-10-11: `.sha512.asc`, `aplinfo.dat.asc`, `MANIFEST.asc` each have 2 signatures. `aplinfo.dat` did not change |
| 4. Publication | PASS | `keel-publish-mirror --no-channels 2026-10-11`: exit 0. The APT archive did not change |
| 5. sqv on BR3-THIN, published files | PASS | main alone: exit 0. images alone: exit 0. Both: exit 0. Security key alone: exit 1. pve-manager keyring: exit 1 |
| 6. Tampered `aplinfo.dat` | PASS | sqv exit 1 with main or images. keel-pve 0.1.0 and 0.1.2: exit 3, nothing stored |
| 7. keel-pve list and download | PASS | keel-pve 0.1.0 and 0.1.2: index verified, 4 templates. `pveam list local` shows the template |
| 8. `keel verify --release-manifest` in a CT | PASS | keyring 0.2.0 (main only): exit 0. Main alone, images alone: exit 0. Security alone: exit 8. Tampered MANIFEST: exit 8. Tampered listed file: exit 7 |
| 9. `keel pull` and `keel verify` of a `.hash` file in a CT | PASS | main alone, images alone: `ok`. Security alone: exit 8. Changed file: BADSIG, exit 7 |

## 1. The signers and the verifiers

| Artifact | Signer | Change | Verifier |
| --- | --- | --- | --- |
| template `.sha512` | `keel-release` | apt#30: main and images in 1 `.asc` | no reader. keel-pve uses the sha512 of the signed index |
| `pve/aplinfo.dat` | `keel-release` | apt#30 | keel-pve with sqv (keel-pve#4, merged before this task) |
| release `MANIFEST` | `keel-release` | apt#30 | `keel verify --release-manifest` (keel#176, new) |
| layer `.hash` | `bt-layer`, `generate-signature` | buildtasks#24: `BT_GPGKEY_ALSO` | `keel verify` (keel#176). `keel pull` copies the file into the cache |
| `aplinfo.dat` by `bt-aplinfo` | `bt-aplinfo` | buildtasks#24: `BT_GPGKEY_ALSO` | as above |

`keel-release` gives `bt-aplinfo` no key and clears `BT_GPGKEY`. So the
published files come from `keel-release` only. buildtasks#24 is for a
build that signs with buildtasks directly.

The pull requests:

- **apt#30**, merged (03c30c6). `release_signing_subkeys` gives main,
  then images. `release_sign` writes 1 `.asc` with both. A main-only
  signature is not current when both must sign, so `--sign-only` adds the
  images signature. The expiry alert checks both subkeys. CI green.
- **keel#176**, open. `signature.verify_by_any` reads the gpgv status
  lines one signature at a time. gpgv exits 2 when one of 2 signatures has
  no key, so the exit code is not read. The keyrings are
  `/usr/share/keyrings/keel-archive-keyring.gpg` and
  `keel-images-keyring.gpg`. A missing file is skipped. Version 0.23.28.
  It merges after keel#175 (0.23.27) of the other agent. The first CI run
  had 1 red job, `tests / vip`: etcd timeouts under netem, in code that
  this PR does not change. It is run again before the merge. keel#151 is
  replaced by keel#176.
- **buildtasks#24**, merged (a43e6a3). The first CI run failed the
  coverage gate (98.99 percent of 99 in `generate-signature`). The fix
  made the line that kcov did not count into 2 lines, and the second run
  was green.

This task publishes no keel release. keel#176 goes out in the next keel
release of the other agent, or in a later one.

## 2. How Proxmox VE 9 verifies the index

`/usr/share/perl5/PVE/APLInfo.pm` on BR3-THIN:

```
sub get_apl_sources {
    host => "download.proxmox.com", ... file => 'aplinfo-pve-9.dat',
    host => "releases.turnkeylinux.org", ... file => 'aplinfo.dat',
...
my $trustedkeyring = "/usr/share/doc/pve-manager/trustedkeys.gpg";
my $cmd = "/usr/bin/sqv --keyring $trustedkeyring $sigfn $tmp";
```

- The sources are in the code. There is no configuration for a custom
  source.
- The keyring belongs to pve-manager (`dpkg -S`). An upgrade replaces it.
- So an admin cannot add a Keel key file for `pveam`. This task did not
  change `APLInfo.pm` or `trustedkeys.gpg`.

The Keel path is `keel-pve`. It runs the same sqv command with
`/usr/share/keyrings/keel-archive-keyring.gpg` and, from 0.1.2,
`/usr/share/keyrings/keel-images-keyring.gpg`. Both files come from
`keel-archive-keyring` 0.3.0. These are the files that an admin installs:

```
# /etc/apt/sources.list.d/keel.sources, as the keel-pve README says
Suites: trixie-testing
Signed-By: /usr/share/keyrings/keel-archive-keyring.gpg
$ apt-get install keel-pve
Setting up keel-archive-keyring (0.3.0) ...
Setting up keel-pve (0.1.0) ...
```

`keel-pve download` puts the template in the `vztmpl` content of the
storage, and `pveam list` and `pct create` use it from there.

## 3. Re-sign of release 2026-10-11

Release 2026-10-11 is the one that the live index comes from
(`published/pve/FROM`: `release 2026-10-11`, sha256 `05edd2dd...4c4688`).

A backup of the old signatures and MANIFEST is in
`/srv/keel-release/.backup-2026-10-11-pre-images` on the build host.

`--sign-only` names the template from the changelog of the product. That
changelog is at 19.0-10 now. A copy that starts at the 19.0-9 entry gives
the staged name. The base of the index is the 2026-10-10 index, which the
MANIFEST records as `index_base` (`095e6728...15e4d8e`). So the MANIFEST
header stays the same.

```
$ KEEL_PRODUCTS=/var/tmp/img-products KEEL_PUBLISHED_DIR=/var/tmp/img-base \
    bin/keel-release --date 2026-10-11 --sign-only --drop-from-index keel-mariadb core
keel-release: signing subkey 03041024F4B2C0C2F42DDDEA04906EAB77513310 expires on 2028-09-26, in 711 days
keel-release: signing subkey 39DAE662C4726AC7A66C250BEF26DA5C869ECDC7 expires on 2029-10-13, in 1094 days
keel-release: pve/aplinfo.dat: already the index of these templates merged onto the published one, not written again
keel-release: debian-13-keel-core_19.0-9_amd64.tar.zst.sha512: signed
keel-release: aplinfo.dat: signed
keel-release: MANIFEST: signed
exit=0

$ diff backup/MANIFEST 2026-10-11/MANIFEST
< signed yes subkey 03041024F4B2C0C2F42DDDEA04906EAB77513310
> signed yes subkey 03041024F4B2C0C2F42DDDEA04906EAB77513310 39DAE662C4726AC7A66C250BEF26DA5C869ECDC7
< 228 965c4e77...ec5bde images/debian-13-keel-core_19.0-9_amd64.tar.zst.sha512.asc
> 390 8656c7e2...9ae728 images/debian-13-keel-core_19.0-9_amd64.tar.zst.sha512.asc
< 228 6de58c84...1feb pve/aplinfo.dat.asc
> 390 857ab00a...1ee4 pve/aplinfo.dat.asc
```

The scratch copies of the changelog and the base are removed.

## 4. Publication

Before the publication, the `InRelease` files of `trixie`,
`trixie-testing`, `trixie-security` and `trixie-staging` on the build
host and on `archive.keellinux.org` had the same sha256. So the APT tree
that the publication pulls is the published one.

```
$ bin/keel-publish-mirror --no-channels 2026-10-11
keel-publish-mirror: checking every staged file against the MANIFEST
keel-publish-mirror: checking that the staged Proxmox index was merged onto the one the mirror serves
keel-publish-mirror: publishing the blobs and release revision 2026-10-11/1
published release 2026-10-11 ..., signed: yes
390 8656c7e2...9ae728 https://mirror.keellinux.org/images/debian-13-keel-core_19.0-9_amd64.tar.zst.sha512.asc
1761 05edd2dd...4c4688 https://releases.keellinux.org/pve/aplinfo.dat
390 857ab00a...1ee4 https://releases.keellinux.org/pve/aplinfo.dat.asc
keel-publish-mirror: https://archive.keellinux.org trixie verifies
keel-publish-mirror: https://archive.keellinux.org trixie-testing verifies
keel-publish-mirror: https://archive.keellinux.org trixie-security verifies
exit=0
```

After the publication, the 3 `InRelease` files still have the same
sha256 (`4c73042a...`, `cf90f91d...`, `89f0255f...`). The channel
pointers did not change.

## 5. sqv on BR3-THIN, the published files

The files come from the public names:

```
4c7f5c9e...93f3a5  MANIFEST
3c0161f7...d27     MANIFEST.asc
05edd2dd...4c4688  pve/aplinfo.dat
857ab00a...1ee4    pve/aplinfo.dat.asc
8656c7e2...9ae728  images/debian-13-keel-core_19.0-9_amd64.tar.zst.sha512.asc
signed yes subkey 03041024F4B2C0C2F42DDDEA04906EAB77513310 39DAE662C4726AC7A66C250BEF26DA5C869ECDC7
rel/pve/aplinfo.dat.asc: 2 signature packets, issuers 04906EAB77513310 EF26DA5C869ECDC7
rel/MANIFEST.asc: 2 signature packets, issuers 04906EAB77513310 EF26DA5C869ECDC7
rel/images/...sha512.asc: 2 signature packets, issuers 04906EAB77513310 EF26DA5C869ECDC7
```

The command has the shape that `PVE::APLInfo` uses:
`sqv --keyring RING SIG FILE`.

| File | main alone | images alone | main and images | security alone |
| --- | --- | --- | --- | --- |
| `pve/aplinfo.dat` | exit 0, `AD0964BE...3180` | exit 0, `E71DB9C3...2F3C` | exit 0, both | exit 1 |
| `...tar.zst.sha512` | exit 0 | exit 0 | exit 0 | exit 1 |
| `MANIFEST` | exit 0 | exit 0 | exit 0 | exit 1 |

With one keyring, sqv also prints, and still exits 0:

```
Missing key 39DAE662C4726AC7A66C250BEF26DA5C869ECDC7, which is needed to verify signature.
AD0964BE3F09DED469A3B6B2148E951314703180
```

With the pve-manager keyring `/usr/share/doc/pve-manager/trustedkeys.gpg`
the index gives exit 1, because no Keel key is in it.

## 6. Tampered index

`Version: 19.0-9` changed to `Version: 19.0-99`, same `.asc`:

```
$ sqv --keyring /usr/share/keyrings/keel-archive-keyring.gpg t/aplinfo.dat.asc t/aplinfo.dat
Verifying signature:
           Message has been manipulated
exit=1
$ sqv --keyring /usr/share/keyrings/keel-images-keyring.gpg t/aplinfo.dat.asc t/aplinfo.dat
           Message has been manipulated
exit=1
```

keel-pve, with the tampered index on a local HTTP server
(`KEEL_PVE_INDEX_URL`):

```
keel-pve 0.1.0: the index signature does not verify against /usr/share/keyrings/keel-archive-keyring.gpg; nothing stored   exit=3
keel-pve 0.1.2: the index signature does not verify against /usr/share/keyrings/keel-archive-keyring.gpg; nothing stored   exit=3
```

## 7. keel-pve against the published index

keel-pve 0.1.0 is the version in `trixie-testing`. keel-pve 0.1.2 is
Keel-Linux/keel-pve main, run from the checkout. It is not published.

```
$ keel-pve update                                   # 0.1.0, main keyring only
Missing key 39DAE662C4726AC7A66C250BEF26DA5C869ECDC7, which is needed to verify signature.
index updated from https://releases.keellinux.org/pve/aplinfo.dat: 4 templates, signature verified
exit=0
$ keel-pve available
keel-core        19.0-9     debian-13-keel-core_19.0-9_amd64.tar.zst         Keel Linux Core
keel-postgresql  19.0-5     debian-13-keel-postgresql_19.0-5_amd64.tar.zst   keel-postgresql
keel-redis       19.0-8     debian-13-keel-redis_19.0-8_amd64.tar.zst        keel-redis
keel-web         19.0-4     debian-13-keel-web_19.0-4_amd64.tar.zst          Keel Web
$ keel-pve download local keel-core
already present and verified: local:vztmpl/debian-13-keel-core_19.0-9_amd64.tar.zst
$ pveam list local
local:vztmpl/debian-13-keel-core_19.0-9_amd64.tar.zst        343.57MB

$ keel-pve update                                   # 0.1.2, both keyrings
index updated from https://releases.keellinux.org/pve/aplinfo.dat: 4 templates, signature verified
exit=0
$ KEEL_PVE_KEYRING=.../keel-images-keyring.gpg KEEL_PVE_IMAGES_KEYRING=/nonexistent.gpg keel-pve update
index updated from https://releases.keellinux.org/pve/aplinfo.dat: 4 templates, signature verified
exit=0
```

The first download of the template ran before the re-sign, with
keel-pve 0.1.0 (3 min 25 s, `downloaded and verified`).

## 8. keel verify of the release MANIFEST in a CT

CT 9081 on BR3-THIN, from `debian-13-keel-core_19.0-9`. It has keel
0.20.0 and keel-archive-keyring 0.2.0. keel of keel#176 (0.23.28, commit
1850960, the same tree as 48212cb) runs from a copy of the source with `PYTHONPATH`. The CT has no
network. The files of section 5 are copied in with `pct push`.

```
### keyring 0.2.0: main file only, images file missing
$ keel verify --release-manifest /root/rel/MANIFEST
/root/rel/MANIFEST: signed by AD0964BE3F09DED469A3B6B2148E951314703180
images/debian-13-keel-core_19.0-9_amd64.tar.zst: not present, not checked
images/debian-13-keel-core_19.0-9_amd64.tar.zst.sha512: ok
images/debian-13-keel-core_19.0-9_amd64.tar.zst.sha512.asc: ok
pve/aplinfo.dat: ok
pve/aplinfo.dat.asc: ok
pve/aplinfo.dat.gz: ok
exit=0
### keyring 0.3.0 installed (dpkg -i)
/root/rel/MANIFEST: signed by AD0964BE3F09DED469A3B6B2148E951314703180, E71DB9C3CA6AC18075395CC3ED3A709C4F3E2F3C
exit=0
### --keyring keel-archive-keyring.gpg    -> signed by AD0964BE...3180, exit=0
### --keyring keel-images-keyring.gpg     -> signed by E71DB9C3...2F3C, exit=0
### --keyring keel-security-keyring.gpg
unverified: /root/rel/MANIFEST: no good signature by a key of the keyrings
exit=8
### MANIFEST changed (revision 1 -> 2), main alone and images alone
unverified: /root/t/MANIFEST: BADSIG, the file changed after it was signed
exit=8
### pve/aplinfo.dat changed, images alone
pve/aplinfo.dat: mismatch: size 1762, MANIFEST says 1761; sha256 ccda7888..., MANIFEST says 05edd2dd...
exit=7
### keel 0.20.0 of the template
Error: unrecognized arguments: --release-manifest /root/rel/MANIFEST
exit=1
```

## 9. keel pull and keel verify of a layer `.hash` file in a CT

The release publishes `core.tar.zst.sha256` and no `.hash` file. So the
`generate-signature` of buildtasks#24 made a `.hash` file for the
published `core.tar.zst` on the build host, in a scratch directory, with
`BT_GPGKEY` = main and `BT_GPGKEY_ALSO` = images. It is not published.

```
INFO [generate-signature]: l/core.tar.zst.hash is signed by AD0964BE3F09DED469A3B6B2148E951314703180 E71DB9C3CA6AC18075395CC3ED3A709C4F3E2F3C (release@keellinux.org) and verifies
   This file also carries a signature by each key below. A good signature by
   any one of them is enough (Keel Linux decision 0055):
```

In CT 9081, `core.tar.zst` (sha256 `6f0a5590...72fca56`, from
`mirror.keellinux.org/layers/`), `core.manifest` and the `.hash` file:

```
$ keel pull --source /root/src-layers --cache-dir /root/cache core
core: fetched (360255317 bytes)
$ ls /root/cache
core-6f0a5590...72fca56.manifest
core-6f0a5590...72fca56.tar.zst
core-6f0a5590...72fca56.tar.zst.hash
$ keel verify --layers-dir /root/cache --keyring .../keel-archive-keyring.gpg
core: ok: hash file signed by AD0964BE3F09DED469A3B6B2148E951314703180      exit=9
$ keel verify --layers-dir /root/cache --keyring .../keel-images-keyring.gpg
core: ok: hash file signed by E71DB9C3CA6AC18075395CC3ED3A709C4F3E2F3C      exit=9
$ keel verify --layers-dir /root/cache --keyring .../keel-security-keyring.gpg
core: unverified: signature present, not verified: no good signature by a key of the keyrings   exit=8
$ keel verify --layers-dir /root/cache
core: ok: hash file signed by AD0964BE3F09DED469A3B6B2148E951314703180, E71DB9C3CA6AC18075395CC3ED3A709C4F3E2F3C   exit=9
### 1 word of the signed text changed
core: mismatch: hash file: BADSIG, the file changed after it was signed   exit=7
```

Exit 9 is `NOT_IMPLEMENTED` for the packages half of `keel verify`, after
every layer passed.

## Main stays

This task did not remove a main signature. Every signature that main
made stays valid. Before the publisher signs with images alone, all of
these must be true:

1. keel-pve 0.1.2 is published, and every Proxmox host that reads the
   Keel index has it. keel-pve 0.1.0 reads only the main keyring.
2. Every Proxmox host and every appliance has keel-archive-keyring 0.3.0
   or later. The template `debian-13-keel-core_19.0-9` ships 0.2.0, which
   has no images keyring. New templates must ship 0.3.0.
3. A keel release with keel#176 is published, and every appliance that
   checks a `.hash` file or a release MANIFEST has it. keel 0.20.0 of the
   template has no `--release-manifest`.
4. Each verifier is measured again with a file that images signed alone.
   This task measured only files that both keys signed.
5. `release_index_live` of `keel-release` accepts images (apt#28). It has
   this already.
6. Then `release_signing_subkeys` gives the images subkey alone, in a new
   apt pull request, and the handbook records the date.

The 4 templates of the live index other than `keel-core 19.0-9`, and the
MANIFESTs of releases 2026-10-02 to 2026-10-10, still have main alone.
Their release directories hold older indexes, so a re-publication of them
would be refused at the index check. Their next release signs them with
both keys. A main signature stays valid until main is revoked.

## Notes

- keel-pve 0.1.0, and 0.1.2 with one keyring, print the sqv line
  `Missing key ..., which is needed to verify signature.` on stderr for the
  signature that it cannot check. The exit code is 0. With both keyrings,
  keel-pve 0.1.2 prints nothing.
- The 2026-10-12 and 2026-10-13 staged releases are unsigned
  pre-releases. This task did not sign or publish them.
