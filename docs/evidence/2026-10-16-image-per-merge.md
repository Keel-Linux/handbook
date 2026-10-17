# Evidence: one image build per merge

Date: 2026-10-16, 07:30 UTC, to 2026-10-17, 07:20 UTC.
Decision: 0061 (one image build per merge), and its amendment of
2026-10-17.

Changes, all merged with merge commits on green checks:

| Repository | Pull requests | What |
| --- | --- | --- |
| handbook | #92 | decision 0061 |
| .github | #26 | `bin/staged-release-verify`, `ULX_NO_UPGRADE`, the public staging keyring |
| image-gate (new) | #1 | `image-boot.yml`, lint and security gates |
| apt | #37, #38, #39, #40, #42 | `keel-image-ci`, `keel-release --staging --match-source`, the units, the fixes of the first runs |

Machines:

- Build host: `root@2804:710:d0:5:bb3f:380a:f07b:7951`. Tooling
  `/srv/keel-apt/apt`, CI tree `/srv/keel-ci`, timer
  `keel-image-ci.timer`.
- Runner VM: Keel-Linux-Runner (`2804:710:d0:5::bbba`), label
  `keel-lxc`, drop user `keel-image-drop`.

The subkey fingerprints are not written here. A signature check is
written as the count of `GOODSIG` status lines.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| 1. A real merge, from merge to image in testing | PASS | keel-lnpp#4 (keel#201 fix): 8 min 12 s |
| 2. Only the changed layer is built | PASS | core and web "tarball matches its manifest, not rebuilt"; lnpp built |
| 3. The same bits are promoted | PASS | the template in testing and in staging have the same inode and size |
| 4. Release signatures on the promoted build | PASS | MANIFEST: 1 GOODSIG with the main keyring, 1 with the images keyring |
| 5. The runner holds no key and cannot reach the build host | PASS | drop key: write only (`rrsync -wo`); shell and read refused |
| 6. No public index, no channel move | PASS | no `pve/` in staged or testing builds; `keel-channel` not run |
| 7. Failure handling | PASS | issues image-gate#2 to #11, one for each failure and set of heads |
| 8. Full build of the CI set | PARTIAL | 6 of 7 built; redis failed to build; lnmp fails its boot test |

## 1. A real merge, from merge to image in testing

keel-lnpp#4, "fix: a preset disables postgresql-common's WAL archival
(keel#201)", changes the overlay of the lnpp layer. Build
`20261016T182304Z`, record `/srv/keel-ci/records/20261016T182304Z`:

| Step | Time (UTC) | From the merge |
| --- | --- | --- |
| Merge on git.pop.coop (`merged_at`) | 18:21:59 | 0 s |
| Poll sees the new head (`detected`) | 18:23:04 | 1 min 05 s |
| Build starts | 18:23:06 | 1 min 07 s |
| Build ends (lnpp only) | 18:28:30 | 6 min 31 s |
| Staged release pushed to the runner VM | 18:28:36 | 6 min 37 s |
| Boot test run 8 dispatched | 18:28:36 | 6 min 37 s |
| Run 8 ends: success | 18:30:06 | 8 min 07 s |
| Promoted, signed by main and images | 18:30:11 | 8 min 12 s |

The boot test: <https://git.pop.coop/Keel-Linux/image-gate/actions/runs/8>.

## 2. Only the changed layer is built

From the build log of `20261016T182304Z`:

    keel-release: core: tarball matches its manifest, not rebuilt
    keel-release: web: tarball matches its manifest, not rebuilt
    keel-release: building layer lnpp on web

## 3. and 4. The promoted build

`/srv/keel-ci/testing/20261016T182304Z/MANIFEST`, header (the `signed`
line is left out):

    release 2026-10-16
    revision 1
    appliances lnpp
    channel testing
    build 20261016T182304Z
    staged_manifest_sha256 d273010d22104cc440d68f524052f8e0ea5061b855f6defeafb3cfcca1da2e96
    tested_by https://git.pop.coop/Keel-Linux/image-gate/actions/runs/8
    source keel-lnpp 74fd1df249e204e3070fd34e8dc134c9ca7b8be8
    (one source line for each watched repository)

Checks on the build host:

    MANIFEST.asc with the main keyring alone:   GOODSIG 1
    MANIFEST.asc with the images keyring alone: GOODSIG 1
    sha512sum -c images/*.sha512: debian-13-keel-lnpp_19.0-4_amd64.tar.zst: OK
    inode and size, testing and staged template:
    1708366 283839359 testing/.../debian-13-keel-lnpp_19.0-4_amd64.tar.zst
    1708366 283839359 staged/.../debian-13-keel-lnpp_19.0-4_amd64.tar.zst

The promotion checked the staged MANIFEST against the digest that run 8
checked, and the staging signature and every digest again, on the build
host's own copy. Nothing came back from the runner.

## 5. The drop user on the runner VM

From the build host, with the drop key:

    rsync push to keel-image-drop:      push-ok
    rsync --delete with an empty tree:  delete-ok
    ssh ... id:                         rrsync error: SSH_ORIGINAL_COMMAND does not run rsync
    rsync pull of a file:               rrsync error: reading from write-only server is not allowed
    runner9: touch incoming/x:          Permission denied

The Forgejo token on the build host belongs to `keel-image-bot`, a
collaborator with write access to `Keel-Linux/image-gate` only. Branch
protection lets only the Owners team merge to `main` there. An issue in
the private repository `Keel-Linux/apt` with that token: HTTP 404.

## 7. Failures found, and what they caused

| Issue | Cause | Result |
| --- | --- | --- |
| image-gate#2, #7, #8 | stable track: the project package check of each appliance refused keel 0.23.29 from trixie-testing | apt#38 (each appliance on its own), apt#42 (testing track); closed |
| image-gate#3 to #6 | `git clean` could not remove `build/root.patched`, where fab leaves its deck mounted | apt#39; closed |
| (none) | 13 GB of deck trees under `/srv/keel-ci/src` | apt#40: unmount and remove after each build |
| image-gate#9 | the redis layer fails to build (`bt-layer` status 2) | open |
| image-gate#10, #11 | the lnmp boot test: "appliance.name: lnmp is not an installed appliance under /usr/share/keel" | open, a defect of the lnmp boot test or of keel |

## 8. Full build of the CI set, testing track

Build `20261016T154336Z` (after apt#42): build 15:43:37 to 16:14:37 UTC,
31 min for 7 layers. Built: core, web, lnmp, lnpp, mariadb, postgresql.
Failed: redis. Run 7 booted core and web, then failed on lnmp (item 7),
so nothing of that build was promoted.

## Measured limits

- **Runner queue.** Run 6 of build `20261016T105401Z` waited 86 min for
  a free `keel-lxc` runner and then took 3 min. The time to testing
  depends on the queue, not on the build.
- **Disk.** On 2026-10-17 07:20 UTC the build host had 6.6 GB free (95
  percent used). The poll does not start a build below 8 GB, so the next
  build waits until space is freed. The CI tree uses about 10 GB
  (`builds` 6.2 GB, `staged` 3.1 GB, `testing` 0.6 GB). The hand-build
  trees use 37 GB (`/turnkey/fab-keel/products` 16 GB,
  `/srv/keel-release` 14 GB, `/mnt/builds` 7.6 GB).

## What testing means here, and what keel is in it

The promoted builds are on the build host only, in
`/srv/keel-ci/testing/`, with `latest-<appliance>` links. No Proxmox
index was written and no channel pointer moved. The public stable index
did not change. The images carry the keel package of `trixie-testing`
(0.23.29 at the time of build `20261016T105401Z`). No build of keel
`main` entered an image, and this flow released no keel package.
