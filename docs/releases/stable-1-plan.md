# Stable 1: the plan of the first stable release

Date: 2026-10-24. Status: approved by the maintainer on 2026-10-24, answers in
section 6. Execution is in steps. Nothing in this note was signed or made public. No
package was promoted, no file was signed, no tag or release was made.
Decisions: 0016, 0039, 0043, 0052, 0055, 0061, 0063. Text follows
`docs/writing.md`.

Scope: promote the Keel packages of the 5 images from `trixie-testing` to
`trixie`, then release as stable `keel-core`, `keel-web`, `keel-lnmp`,
`keel-lnpp` and `keel-ntfy`. The application images (WordPress, Odoo and
the others) are out. They wait for the real test of Syncthing.

No secret is in this note. A signing role is named by its purpose only.

## Facts of 2026-10-24

| Item | State |
| --- | --- |
| `trixie` | 6 packages: keel 0.23.21, confconsole 2.2.3+keel2, fab 1.1.1+keel2, inithooks 2.3.6+keel26, keel-archive-keyring 0.3.0, keel-transition 0.2.3 |
| `trixie-testing` | 54 packages, keel 0.23.49. Signed by the main role and the testing role |
| keel `main` | 0.23.51 (keel#222, the ntfy list). There is no 0.23.50 entry in the changelog. 0.23.51 is not in `trixie-testing` |
| keel#221 | open: filesync, 0.23.52. It is not in this release |
| keel-web `master` | 0.3.4 (depends on keel-overlay-syncthing). Not published. The images carry 0.3.3 |
| common#63 | open: keel-overlay-anubis 0.1.2. Not in this release |
| Stable pointers | `mirror.keellinux.org/layers/stable` answers 404. No stable release exists |
| Proxmox index | core 19.0-9, postgresql 19.0-5, redis 19.0-8, web 19.0-4 |

## 1. Packages to promote, and the evidence for each

### 1.1 The list

The list is the Keel packages that the 5 testing images install, from the
`.packages` files of the builds `20261020T174441Z` (core, run 32 of
image-gate) and `20261024T044821Z` (web, lnmp, lnpp, ntfy, run 35). It is
the packages of these images whose version differs in `trixie`. The count
is 46: 23 webmin packages and 23 others. In every image, the version
installed is the version in `trixie-testing` now.

Evidence keys:

| Key | File in `docs/evidence/` and what it covers |
| --- | --- |
| E1 | `2026-10-17-lnmp-19.0-4-cross-site.md`: LNMP 19.0-4 and LNPP 19.0-5 with keel 0.23.43, 3 CTs on 2 sites, netem, MariaDB pair |
| E2 | `2026-10-19-odoo-19.0-11-keel-0.23.49.md`: Odoo on LNPP with keel 0.23.49, PostgreSQL pair on 2 sites, netem. Earlier runs: `-10` (0.23.48), `-09` (0.23.46), `2026-10-18-odoo-19.0-7-cross-site.md` (0.23.45) |
| E3 | `2026-10-18-wordpress-nginx-cross-site.md`: WordPress on LNMP, keel 0.23.43 |
| E4 | `2026-10-18-coraza-body-and-wordpress-uploads.md`: the Coraza body processors |
| E5 | `2026-10-18-postgresql-first-boot-order.md`: inithooks 2.3.6+keel27 |
| E6 | `2026-10-15-cronapt-transition-release.md`: keel-transition 0.2.3 |
| E7 | `2026-10-14-keyring-0.3.0-trixie-security.md`: keel-archive-keyring 0.3.0 |
| E8 | `2026-10-13-step12-boot-checks.md`: Core, Web, MariaDB, PostgreSQL and Redis boot checks with keel 0.23.13 on hw12-br1 CTs 9051-9055 |
| G | Boot test of image-gate only: run 32 (core) and run 35 (web, lnmp, lnpp, ntfy). This is a pass or fail of the boot. It is not an evidence file |
| none | No evidence file and no boot test of this package alone |

| Package | In trixie now | Promote | Evidence |
| --- | --- | --- | --- |
| keel | 0.23.21 | 0.23.49 | E2 for PostgreSQL, VIP, etcd, mesh. E1 and E3 for MariaDB, but with 0.23.43. **No MariaDB test with 0.23.44 to 0.23.49** |
| inithooks | 2.3.6+keel26 | 2.3.6+keel27 | E5, and the first boot of every test since |
| confconsole | 2.2.3+keel2 | 2.2.3+keel15 | G only. **Flag: no test of the console.** The headless first boot of E1 to E3 does not use it |
| keel-core | none | 0.1.3 | E1, E2, E3 |
| keel-overlay-etcd 0.4.0, -vip 0.2.0, -wireguard 0.1.0, -crowdsec 0.1.0, -installer 0.2.0 | none | same | E1, E2. **Flag: no evidence file in the handbook names crowdsec 0.1.0 or installer 0.2.0. They have E8 and G only** |
| keel-web | none | 0.3.3 | E2: the file `-09` lists keel-web 0.3.3 |
| keel-overlay-nginx 0.1.0 | none | same | E1, E2, E3 |
| keel-overlay-coraza 0.1.4, libnginx-mod-http-coraza 0.21.0-0keel2, libcoraza1 1.8.0-0keel1, coreruleset 4.25.1-0keel1 | none | same | E4 |
| keel-overlay-anubis 0.1.1, anubis 1.27.0-0+keel3 | none | same | E2 (odoo -07 and -09, the WebSocket) |
| tkl-dhcpcd-ifupdown-glue 0.1.3+keel1, turnkey-conffile 1.1.2+keel1, turnkey-netinfo 1.1.1+keel2, turnkey-ssl 3.1.1+keel1, turnkey-sysinfo 1.1.0+keel2, turnkey-version 1.1.3+keel3 | none | same | **Flag: G only. No evidence file names them** |
| webmin 2.660.turnkey0 and 22 modules: authentic-theme, custom, fail2ban, fdisk, filemin, firewall, firewall6, logviewer, lvm, mount, mysql, net, passwd, postfix, postgresql, raid, software, sshd, systemd, updown, useradmin, xterm | none | same | **Flag: G only. They are TurnKey binaries that were copied and signed again (tracker#52)** |
| keel-archive-keyring 0.3.0, keel-transition 0.2.3 | same version | no action | E6, E7 |

The 46 arguments of `bin/promote`:

```
anubis=1.27.0-0+keel3 confconsole=2.2.3+keel15 coreruleset=4.25.1-0keel1
inithooks=2.3.6+keel27 keel=0.23.49 keel-core=0.1.3
keel-overlay-anubis=0.1.1 keel-overlay-coraza=0.1.4
keel-overlay-crowdsec=0.1.0 keel-overlay-etcd=0.4.0
keel-overlay-installer=0.2.0 keel-overlay-nginx=0.1.0
keel-overlay-vip=0.2.0 keel-overlay-wireguard=0.1.0 keel-web=0.3.3
libcoraza1=1.8.0-0keel1 libnginx-mod-http-coraza=0.21.0-0keel2
tkl-dhcpcd-ifupdown-glue=0.1.3+keel1 turnkey-conffile=1.1.2+keel1
turnkey-netinfo=1.1.1+keel2 turnkey-ssl=3.1.1+keel1
turnkey-sysinfo=1.1.0+keel2 turnkey-version=1.1.3+keel3
webmin=2.660.turnkey0 webmin-authentic-theme=2.660.turnkey0
webmin-custom=2.660.turnkey0 webmin-fail2ban=2.660.turnkey0
webmin-fdisk=2.660.turnkey0 webmin-filemin=2.660.turnkey0
webmin-firewall=2.660.turnkey0 webmin-firewall6=2.660.turnkey0
webmin-logviewer=2.660.turnkey0 webmin-lvm=2.660.turnkey0
webmin-mount=2.660.turnkey0 webmin-mysql=2.660.turnkey0
webmin-net=2.660.turnkey0 webmin-passwd=2.660.turnkey0
webmin-postfix=2.660.turnkey0 webmin-postgresql=2.660.turnkey0
webmin-raid=2.660.turnkey0 webmin-software=2.660.turnkey0
webmin-sshd=2.660.turnkey0 webmin-systemd=2.660.turnkey0
webmin-updown=2.660.turnkey0 webmin-useradmin=2.660.turnkey0
webmin-xterm=2.660.turnkey0
```

`bin/promote` refuses a package that is not at the named version in
`trixie-testing` (exit 3). It refuses a downgrade (exit 8). The versions
above are exact, so a publication to `trixie-testing` before the promotion
cannot change what moves.

### 1.2 Packages in `trixie-testing` that do not move

| Package | Reason |
| --- | --- |
| keel-overlay-syncthing 0.1.0, syncthing 2.1.6+keel1 | Application images wait for the Syncthing real test. No image of this release installs them |
| keel-mariadb 0.1.1 | The image `mariadb` is not in this release |
| keel-pve 0.1.0 | It runs on Proxmox hosts. No image installs it |
| tkl-installer 0.1.2+keel2 | Only the boot layer of the ISO installs it (decision 0052) |
| libcoraza-dev 1.8.0-0keel1 | Build only |
| fab 1.1.1+keel2 | It is in `trixie` already and is not in `trixie-testing` |

### 1.3 Not in `trixie-testing`, and it must stay out

- keel 0.23.51 is merged, built nowhere, and has no test on a real node.
  The maintainer chose keel 0.23.49 (answer 2), so it stays out.
- keel-web 0.3.4 is on `master`. It adds the Depends on
  keel-overlay-syncthing, which needs keel 0.23.52 (keel#221, not merged).
  Nobody must publish it to `trixie-testing` before the stable build ends.
- keel-overlay-anubis 0.1.2 (common#63, open) must not be published.

### 1.4 Evidence gaps that block the release

1. **keel-ntfy has no evidence file and no pre-release.** The CTs 9190 and
   9191 ran 19.0-2 on 2026-10-23 and ntfy-br1 is live, but the handbook
   has no file for it. Section 4 lists the test.
2. **MariaDB with keel 0.23.49 has no test.** E1 and E3 used 0.23.43. The
   changelog of 0.23.44 to 0.23.49 is about PostgreSQL and the witness, but
   a test that shows this does not exist.
3. **No tested image can become stable.** The images of the evidence files
   have the `trixie-testing` stanza on. Checked on the build host on
   2026-10-24: `keel.sources` of `debian-13-keel-ntfy_19.0-2` has
   `Enabled: yes` for `trixie-testing`. A stable image is a rebuild, so it
   has new bits, and section 4 runs on those bits.
4. **The bits of the same name already differ.** The lnmp 19.0-4 of E1 has
   sha512 `1ad070d9607af4d4`. The 19.0-4 of build `20261024T044821Z` has
   `a87f262316633c2d`. Both carry the name 19.0-4.
5. **The core layer of the web, lnmp, lnpp and ntfy images is not the core
   image that run 32 tested.** Build `20261020T174441Z` made core with
   sha256 `1642a977`. Build `20261024T044821Z` made core with sha256
   `70bf50c2`. The package lists are the same, the bytes are not. The
   stable build uses one core for all 5 images.
6. ~~**E8 is not in the handbook.**~~ E8 was added to
   `docs/evidence/2026-10-13-step12-boot-checks.md` on 2026-10-25.

## 2. Gaps

### 2.1 What the stable images need that `trixie` does not have

Of the 46 packages of section 1.1, 43 are not in `trixie` at all. The
other 3 are in `trixie` at an older version: keel, inithooks and
confconsole. A stable image installs from `trixie` alone, so the promotion
must come first.

An appliance on the stable track that runs keel 0.23.21 goes to 0.23.49 by
`apt upgrade`. Unattended upgrades take security only (decision 0039), so
no machine moves by itself. Section 4 has an upgrade test for it.

### 2.2 Which suite the image build reads

| Part | What it does |
| --- | --- |
| `bin/keel-image-ci` | Sets `KEEL_APT_TRACK=testing` (`KEEL_CI_APT_TRACK`, default `testing`). It builds the testing track only. 0061 says that it never touches stable |
| `common/conf/bootstrap_apt`, `conf/turnkey.d/keel-apt` | `KEEL_APT_TRACK` is `stable` when it is unset. `stable` writes `keel.sources` with `trixie` on and `trixie-testing` off |
| `keel-lnmp`, `keel-lnpp` `conf.d/main` | `keel-project-packages inithooks confconsole keel` fails when the installed version is not the candidate of `trixie`. With `trixie` at keel 0.23.21 every stable build of these two fails today |
| `keel-core`, `keel-web`, `keel-ntfy` | They have no such check. A stable build of them would pass with testing versions and hide the gap |
| `conf/pool.list` and `imageci_pool_refresh` | The capture pool reads `trixie-testing`. The refresh puts every package of `trixie-testing` in the current pool. The pin of the pool is 1001, so the highest version in the pool wins |
| `bin/keel-release` | Does not set the track. It uses the environment, so the procedure sets `KEEL_APT_TRACK=stable` |

What must change before the stable build:

1. **The promotion comes first.** The build reads the public
   `archive.keellinux.org` suite `trixie`. So the promotion is public before
   the images exist. Section 3 tests the upgrade before the public step.
2. **A frozen pool.** `keel-image-ci.timer` runs every 5 minutes and refreshes
   the current pool. A keel 0.23.51 or keel-web 0.3.4 in `trixie-testing`
   enters the current pool at pin 1001, and a stable build installs it
   although `trixie` does not have it. The stable build uses its own pool
   id (`KEEL_POOL_ID`), and a check compares the result with `trixie`.
3. **The hand tree is old.** On the build host `/turnkey/fab-keel` has
   common at `35648b5` (the tested one is `84ff6a2`), and `products/ntfy` does
   not exist. Its remotes point to GitHub. The stable build does not use it. It
   uses its own tree `/srv/keel-stable1`, made on 2026-10-24 with clones from
   `git.pop.coop`, like the tree of the image build per merge. The script
   `/srv/keel-stable1/sync REPO=SHA...` puts each checkout at an exact commit.
4. **A changelog entry in each product.** The lnmp and lnpp entries say
   "keel 0.23.42 from trixie-testing". The new entries say keel 0.23.49
   from `trixie`.
5. **Names.** The pre-releases already use `core_19.0-10`, `lnmp_19.0-4`,
   `lnpp_19.0-5` and `web_19.0-5` as asset names, with other bits. 0043
   makes a stable name immutable. The maintainer chose new numbers (answer 3).

### 2.3 Gaps in the release tooling and in the decisions

| Gap | Effect |
| --- | --- |
| Decision 0052: an official release has the ISO and the `.tar.zst`. buildtasks#9 (the ISO builder) is open and `keel-release` has no ISO step | The maintainer waived it for stable 1 (answer 1). 0052 has a dated note |
| 0043 names `SHA512SUMS`, the `stable/INDEX` files and `bin/keel-publish-github`. None exists in `keel-release`, `keel-publish-mirror` or `bin/` | The release has the per-file `.sha512` and `.asc` only. GitHub is a push mirror, so the release is on Forgejo only (answer 6) |
| No channel pointer exists. `keel-channel set stable` was never run | The first `set` creates `stable`. A client that reads the pointer gets its first answer |
| The Proxmox index has postgresql 19.0-5 and redis 19.0-8 | They stay in the index of a stable release unless a release drops them. The maintainer chose to drop them (answer 5) |
| The 23 webmin packages come from TurnKey and were signed again. tracker#52 lists 21 of them | The stable suite would hold third-party binaries. The maintainer accepted it (answer 4) |
| `master` of keel-web contains the keel-web 0.3.4 packaging | The tag goes on the commit that built the packages of the image (answer 7). The web release uses a branch `stable-1` from `14aea11`, which has 0.3.3 |

## 3. Procedure

Rules for the whole procedure: one step at a time, one person, and the
maintainer approves each step marked **gate**. Nobody publishes to
`trixie-testing` from the start of step 1 to the end of step 17.
The signing roles are the roles of decision 0055. A step names the role
only.

| Step | Action | Tool | Role |
| --- | --- | --- | --- |
| 1 | Stop `keel-image-ci.timer` on the build host. Wait for the build lock to be free. The backup is done: `/srv/keel-apt/backup-stable1/` holds `repo-db-before-promote.tgz` (db and dists) and `pages-head.txt` (`e635138`). The old `.deb` files of `trixie` are in `/srv/keel-apt/done/` | `systemctl`, `tar` | none |
| 2 | Merge the open decisions of section 6. Make one changelog PR for each of the 5 product repositories. Each PR passes its checks and merges. Add E8 to the handbook | PRs | none |
| 3 | Check `bin/promote` as a dry run with the 46 arguments. The output must show 46 lines, and "was none" for 43 of them | `bin/promote` | none (it reads the signing state only) |
| 4 | **gate.** Run `bin/promote --yes` with the same 46 arguments. It copies the packages and makes a commit in the Pages checkout | `bin/promote` | main |
| 5 | Test the upgrade before the archive is public. Use the loopback mirror of the build host through the maintainer tunnel. Section 4, item U. Run it on a private archive of the 46 files, with no signature of ours (see the evidence file `2026-10-24-stable-1-upgrade-private.md`) | `apt` | none |
| 6 | Push a branch `publish/DATE-promote-stable-1`. Open a PR. Wait for green checks. Merge with a merge commit | git, PR | none |
| 7 | **gate.** On the workstation, run `keel-publish-mirror --archive-only`. It must say that `trixie`, `trixie-testing` and `trixie-security` verify | `keel-publish-mirror` | none (the public host has no key) |
| 8 | Run `verify-repo https://archive.keellinux.org --dist trixie`. Compare the package list with section 1.1. In a clean trixie container with only the stable source, run `apt-get -s install keel-core keel-web` | `verify-repo`, `apt` | none |
| 9 | Make the frozen pool `stable-1` (below). Check it | `keel-stable`, `keel-pool` | none |
| 10 | Run `/srv/keel-stable1/sync` with the 6 commits (common `84ff6a2` and the merged changelog commit of each product, keel-web from the branch `stable-1`). Then run, in one session, `env KEEL_APT_TRACK=stable KEEL_POOL_ID=stable-1 KEEL_FAB_PATH=/srv/keel-stable1/fab KEEL_PRODUCTS=/srv/keel-stable1/products KEEL_LAYERS_DIR=/srv/keel-stable1/builds/layers KEEL_GIT_BASE=https://git.pop.coop/Keel-Linux keel-release --no-wait --date DATE --drop-from-index keel-postgresql --drop-from-index keel-redis core web lnmp lnpp ntfy`. It builds, stages, makes the templates, and signs the digests, the index and the MANIFEST | `keel-release` | main and images |
| 11 | Run the check of the stable packages (below) on the 5 `.packages` files | `keel-stable` | none |
| 12 | Run section 4 on the staged files. Write the evidence file. A failure stops the procedure. Fix, then build again with a new date | tests | none |
| 13 | **gate.** Move the stable pointer to the release: `keel-channel set stable DATE REV` | `keel-channel` | channel (the staging role) |
| 14 | **gate.** On the workstation, run `keel-publish-mirror DATE`. It installs the images, the layers, the index and the pointer, and verifies the public names | `keel-publish-mirror` | none |
| 15 | Check from a clean host: `sha512sum -c`, `sqv` with the main keyring and with the images keyring, `keel pull` and `keel verify` on the channel, and `pveam` on a Proxmox host | shell | none |
| 16 | **gate.** After a soak that the maintainer sets, tag the commit that built each image with `19.0-N` on Forgejo. Make a release that is not a pre-release, with the `.tar.zst`, `.sha512` and `.sha512.asc`. Do nothing on GitHub: it is a push mirror | Forgejo API | none |
| 17 | Commit the evidence file, update `STATUS.md`, and restart `keel-image-ci.timer` | git, `systemctl` | none |

Step 15 comes before step 16 because a tag and a stable release must not
change after they are public.

### The frozen pool (step 9)

The tool is `bin/keel-stable` of the apt tooling (apt#65).

1. Run `keel-stable freeze stable-1 --from 2026-10-08` with
   `--stable-index` set to `dists/trixie/main/binary-amd64/Packages` and
   `--testing-index` set to the file of `dists/trixie-testing`.
2. It copies the member list of the pool `2026-10-08`. It drops each Keel
   package that `trixie` does not have at that version. Debian packages stay.
3. It writes the index of the new pool. Run `keel-pool verify stable-1`.
4. Do not run `keel-pool current stable-1`. The image build per merge uses
   `current` and must go on in the testing track.

### The check of the stable packages (step 11)

Run `keel-stable check` with the same two indexes and the 5 `.packages`
files. It prints each package that one index names and that `trixie` does not
have at that version. The exit code must be 0. The packages keel-overlay-syncthing,
syncthing, keel-mariadb and keel-web 0.3.4 must not appear in any file.
Also check that each `keel.sources` has `Enabled: no` for `trixie-testing`.

## 4. Release test matrix

The rule of the maintainer (2026-10-16) is: 2 LXC on BR1 and 1 LXC on BR2,
the database pair across the sites, netem between the sites. BR3-THIN is
the third site when it is up. It is offline now, so the third CT is on BR2.
Netem: 250 ms with 25 ms jitter and 1.5 percent loss. Every run uses the
staged files of step 10 and records their sha512.

### Items for every image

| Item | What to run |
| --- | --- |
| C1 | `sha512sum -c`. `sqv` with the main keyring and with the images keyring. Both must accept |
| C2 | Stable track: `keel.sources` has `trixie-testing` off. `apt-get -s upgrade` shows nothing to install. `apt-cache policy` shows every Keel package from `trixie` |
| C3 | First boot headless from a spec on each CT. `systemctl --failed` is empty. `keel diff` exits 0 |
| C4 | The key audit of `keel-release` found no private key (exit 12 did not happen). Two CTs of one image have different SSH host keys and machine ids |
| U | Upgrade. Start a CT from the Core 19.0-9 template of the current index (keel 0.23.21). Run `apt upgrade` to the promoted set. Run `keel diff`. Then repeat on a PostgreSQL pair node of the test hosts if one is free. Step 5 did it on a private archive: `2026-10-24-stable-1-upgrade-private.md`. Run it again at step 12 against the public archive. A machine of an old pre-release image must run `apt-get install keel-core` or `keel-web` after the upgrade, because the public `trixie` removes them today |

### Items by image

| Image | What to run | Evidence that can be reused |
| --- | --- | --- |
| keel-core 19.0-N | 3 CTs form the mesh. etcd has 3 voters, 2 on BR1 and 1 on BR2. The VIP moves on a cut of the holder and on `pct stop`, with and without netem. Enable CrowdSec and WireGuard. Test the console (confconsole) by hand | E8 and E1 give the method and the numbers to compare. **None of them is a pass for these bits** |
| keel-web 19.0-N | The core items. nginx runs in simple. In a cloud mode, Coraza and Anubis run. The check page answers at the VIP and through Anubis. A WebSocket passes Anubis. A JSON body and an XML body pass Coraza. A failover with HTTP load under netem | E4 for the Coraza bodies and E2 for the WebSocket, if the overlay and library versions are the same. They are the same in this release |
| keel-lnmp 19.0-N | The web items. The MariaDB pair on BR1 and BR2 with the witness. Writes replicate. Cut of the holder, then `pct stop`, with netem. The old primary returns read only and rejoins by GTID with no reseed (keel#202). The reseed path works. The semi-sync timeout is 30 s and the read-only holder acts at 6 s (decisions 0031 and 0049) | E1 is the script and the numbers. The run is full (answer 8) |
| keel-lnpp 19.0-N | The web items. The PostgreSQL pair on BR1 and BR2 with the witness. Failover with writers under netem. The old primary rejoins by `pg_rewind` or by the reseed that keel picks (decision 0054). A `systemctl stop` of `postgresql@17-main` with an idle client takes under 5 s. The bootstrap has no hang | E2 is the same keel (0.23.49) on the same stack. The run is full all the same (answer 8) |
| keel-ntfy 19.0-N | ntfy is a node of one (decision 0063), so the pair rule does not fit. Run 3 standalone nodes: 2 CTs on BR1 and 1 CT on BR2, with one more CT of Core on BR2 as the sender. First boot headless. Port 80 serves only the ACME challenge and a 301 (19.0-2). The API answers on 443 only. The accounts and tokens work. `ntfy-client.service` is off. `keel notify` from the Core CT reaches each server across the sites under netem. An alert reaches the server after a cut of the link ends | The CTs 9190 and 9191 of 2026-10-23 ran 19.0-2, but no evidence file exists. keel 0.23.49 sends to one server (answer 2), so the test sends to each server in turn |

Item U is the one test that no earlier file covers. It checks that an
existing stable-track machine moves from 0.23.21 to 0.23.49 with its conffiles
and its drop-ins.

## 5. Rollback

| When | What to do |
| --- | --- |
| Before step 4 | Nothing changed. Stop. |
| After step 4, before step 7 | Nothing is public. In the Pages checkout, run `git reset --hard` to the HEAD of step 1. Put the `db` archive of step 1 back in `/srv/keel-apt/repo/db`. Check with `reprepro list trixie`, with the options that `bin/publish` uses |
| After step 7 | The archive is public. Run `reprepro remove trixie` for the 43 new names. Run `reprepro includedeb trixie` for keel 0.23.21, confconsole 2.2.3+keel2 and inithooks 2.3.6+keel26 from `/srv/keel-apt/done/`. Commit, merge, and run `keel-publish-mirror --archive-only`. The role is main. `bin/promote` cannot do it, because it refuses a downgrade (exit 8) |
| A machine that already took the new packages | It stays on the new version. The pin 990 never goes back (tracker#23). The fix is a forward fix: a higher version in `trixie-testing`, then a new promotion |
| After step 14 | Blobs and release revisions are immutable (decision 0016). No earlier stable pointer exists, so a pointer cannot move back. Publish a new date that drops the records with `keel-release --drop-from-index keel-core keel-web keel-lnmp keel-lnpp keel-ntfy`. Add a line to `WITHDRAWN.txt`, as on 2026-10-02. The old records core 19.0-9 and web 19.0-4 do not come back |
| After step 16 | A published tag and release must not change. A correction is a new `<rel>`. This is why step 16 is last |

## 6. Answers of 2026-10-24

The maintainer approved the plan with these answers.

1. Stable 1 ships the `.tar.zst` alone. The ISO comes in a later release
   (buildtasks#9). Decision 0052 has a dated note.
2. Stable 1 ships keel 0.23.49.
3. The new numbers are core 19.0-11, web 19.0-10, lnmp 19.0-5, lnpp 19.0-6
   and ntfy 19.0-3.
4. The TurnKey webmin packages go into `trixie`.
5. The release drops the records keel-postgresql 19.0-5 and keel-redis
   19.0-8 from the Proxmox index.
6. Nobody makes a GitHub release by hand. GitHub is a push mirror only.
   Nobody pushes or creates anything there. The release is on Forgejo.
7. The tag goes on the exact commit that built the packages of the image,
   not on a later commit. For keel-web this is a commit on the branch
   `stable-1` that starts at `14aea11`.
8. There are no reduced runs. All 5 images get the full matrix of section 4,
   with 2 LXC on BR1, 1 LXC on BR2 and netem. MariaDB and PostgreSQL get full
   runs too.

## 7. Note of 2026-10-25: the trixie-testing freeze is broken

After step 1 was done, publications to `trixie-testing` continued:

| Package | Version in plan (§1.1) | Version in trixie-testing now |
| --- | --- | --- |
| keel | 0.23.49 | 0.23.55 |
| keel-web | 0.3.3 | 0.3.4 |

`bin/promote keel=0.23.49` exits 3 because keel is not at 0.23.49 in
`trixie-testing`. Section 1.3 says that keel-web 0.3.4 must not be in
`trixie-testing` before the stable build ends, because it depends on
keel-overlay-syncthing and needs keel 0.23.52.

The publications after step 1 are the fixes for keel#224, keel#225 and
keel#228 (file replication, decision 0050). They are needed for the
application images (WordPress, Odoo) but not for the 5 base images of
this release.

The `repo-db-before-promote.tgz` backup of step 1 does not cover these
publications.

**What the maintainer must decide:**

- (a) Ship keel 0.23.55 instead of 0.23.49. The 46 arguments change, the
  evidence gaps grow (0.23.50 to 0.23.55 have no MariaDB test), and a
  new backup of the repo database is needed.
- (b) Restore `trixie-testing` to the state of step 1 (the backup),
  re-publish the 0.23.52-0.23.55 packages afterwards, and run the
  plan as written. keel-web 0.3.4 must also be removed.
- (c) A third option that the maintainer prefers.

## 8. Amendment of 2026-10-25: the maintainer chose option (a)

The maintainer chose option (a) on 2026-10-25: ship keel 0.23.55 and
keel-web 0.3.4, and add the Syncthing packages that keel-web 0.3.4
depends on. The stable release carries the file replication
infrastructure of decision 0050. The 5 base images run the Syncthing
service in the cloud modes, and an application that declares
`state.replicate` (decision 0068) has its paths replicated at once.

### 8.1 What changes in the promote list (§1.1)

| Package | Was | Becomes |
| --- | --- | --- |
| keel | 0.23.49 | 0.23.55 |
| keel-web | 0.3.3 | 0.3.6 (0.3.4 syncthing overlay, 0.3.5 lintian, 0.3.6 default replicate path 0068; keel-web#23) |
| keel-overlay-syncthing | not promoted (§1.2) | 0.1.0 |
| syncthing | not promoted (§1.2) | 2.1.6+keel1 |

The promote count goes from 46 to 48. The new arguments of
`bin/promote`:

```
anubis=1.27.0-0+keel3 confconsole=2.2.3+keel15 coreruleset=4.25.1-0keel1
inithooks=2.3.6+keel27 keel=0.23.55 keel-core=0.1.3
keel-overlay-anubis=0.1.1 keel-overlay-coraza=0.1.4
keel-overlay-crowdsec=0.1.0 keel-overlay-etcd=0.4.0
keel-overlay-installer=0.2.0 keel-overlay-nginx=0.1.0
keel-overlay-syncthing=0.1.0 keel-overlay-vip=0.2.0
keel-overlay-wireguard=0.1.0 keel-web=0.3.6
libcoraza1=1.8.0-0keel1 libnginx-mod-http-coraza=0.21.0-0keel2
syncthing=2.1.6+keel1
tkl-dhcpcd-ifupdown-glue=0.1.3+keel1 turnkey-conffile=1.1.2+keel1
turnkey-netinfo=1.1.1+keel2 turnkey-ssl=3.1.1+keel1
turnkey-sysinfo=1.1.0+keel2 turnkey-version=1.1.3+keel3
webmin=2.660.turnkey0 webmin-authentic-theme=2.660.turnkey0
webmin-custom=2.660.turnkey0 webmin-fail2ban=2.660.turnkey0
webmin-fdisk=2.660.turnkey0 webmin-filemin=2.660.turnkey0
webmin-firewall=2.660.turnkey0 webmin-firewall6=2.660.turnkey0
webmin-logviewer=2.660.turnkey0 webmin-lvm=2.660.turnkey0
webmin-mount=2.660.turnkey0 webmin-mysql=2.660.turnkey0
webmin-net=2.660.turnkey0 webmin-passwd=2.660.turnkey0
webmin-postfix=2.660.turnkey0 webmin-postgresql=2.660.turnkey0
webmin-raid=2.660.turnkey0 webmin-software=2.660.turnkey0
webmin-sshd=2.660.turnkey0 webmin-systemd=2.660.turnkey0
webmin-updown=2.660.turnkey0 webmin-useradmin=2.660.turnkey0
webmin-xterm=2.660.turnkey0
```

### 8.2 What changes in §1.2

The line "keel-overlay-syncthing 0.1.0, syncthing 2.1.6+keel1:
Application images wait for the Syncthing real test" is removed. Those
packages move to the promote list above.

### 8.3 What §1.3 said that is no longer true

- "keel#221, not merged": keel#221 merged on 2026-10-22 as keel 0.23.52.
- "keel-web 0.3.4 ... needs keel 0.23.52 (keel#221, not merged)":
  keel-web 0.3.4 is in `trixie-testing` and keel 0.23.55 satisfies
  keel (>= 0.15.0). The functional requirement (the file replication
  code of keel#221) is met by keel 0.23.52 and later.
- keel-overlay-anubis 0.1.2 (common#63) must still stay out.

### 8.4 Evidence for the new packages

| Fix | Version | Evidence |
| --- | --- | --- |
| keel#221: file replication | 0.23.52 | `2026-10-24-syncthing-0050-wordpress-odoo-cross-site.md` (handbook#133) |
| keel#224: undeclared syncthing | 0.23.53 | `2026-10-25-keel-0.23.54-pair-owner-and-undeclared-syncthing.md` |
| keel#225: ownership | 0.23.54 | same file |
| keel#228: boot resume | 0.23.55 | **pending**: the fix is in 0.23.55, tested in code review, not on a real node |
| keel-web 0.3.6: syncthing + default replicate | 0.3.6 | handbook#133 for 0.3.4 (the 10-24 image). 0.3.5 is a lintian override. 0.3.6 adds one manifest field (keel-web#23, 0068). Needs a build and boot test |
| keel-overlay-syncthing 0.1.0, syncthing 2.1.6+keel1 | — | handbook#133 |

The §1.4 evidence gaps change:

- Gap 2 ("MariaDB with keel 0.23.49 has no test") becomes: **MariaDB
  with keel 0.23.55 has no test.** The 10-24 and 10-25 evidence tested
  WordPress (LNMP, MariaDB) with keel 0.23.52 and 0.23.54. A test with
  0.23.55 is needed only for keel#228 (the boot-resume fix).
- **New gap: keel#228 real-node evidence.** The test must reboot a
  replica and confirm that file replication resumes. BR2 was offline on
  2026-10-25; a single-site test on BR1 can verify the fix. The full
  cross-site evidence runs when BR2 is back.

### 8.5 Images must be rebuilt

The images of run 32 (core) and run 35 (web, lnmp, lnpp, ntfy) carry
keel 0.23.52 and keel-web 0.3.4 from `trixie-testing`. They are testing
images. The stable build uses `KEEL_APT_TRACK=stable` and reads from
`trixie` after the promotion. The §1.4 items 3, 4 and 5 still apply:
the stable images are new bits and section 4 runs on those bits.

### 8.6 Decision 0068

Decision 0068, written on 2026-10-25, documents the application contract
for replication: what an application manifest declares (`base`,
`state.replicate`, `state.exclude`) and what the platform does with it
(database replication, file flip, ownership, boot resume). It adds a
default replicate path (`/var/www/keel-default`) to Keel Web. An
application inherits that path and adds its own.
