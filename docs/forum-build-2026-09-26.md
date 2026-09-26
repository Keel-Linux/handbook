# Forum build, 2026-09-26: keel-nodebb on LXC

First appliance built the Keel way (docs/forum.md), for the maintainer's
evaluation on the build host (docs/build-host.md). Repository:
`repos/keel-nodebb` (local, 14 commits on main, not pushed, not on GitHub
yet). Everything below was measured on the build host unless stated.

**State at 17:25 UTC, when this report was requested:** both layers are
built and verified; the rootfs was assembled and adapted for a container;
the container `forum` is defined with its spec and secrets in place, and its
first `lxc-start` failed before any first boot ran. The maintainer's side is
debugging the container start directly on the host; sections 5 to 7 record
what was reached. A final rebuild of the nodebb layer with the last recipe
commit (f9ee052) was running detached (`/root/layer-nodebb.out`) and
overwrites `/mnt/builds/layers/nodebb.*` when it finishes; the layer under
test in the container is the one from commit c85c359 (section 3).

## 1. Recipe summary

A fab product compatible with TurnKey Linux appliances, following the
turnkeylinux-apps `nodejs` and `redis` recipes for layout and conventions:

| Path | What |
| --- | --- |
| `Makefile` | `COMMON_OVERLAYS += overlay`, `nginx.mk`, `turnkey.mk`; a `bootstrap/post` hook that copies the build host's APT repository into the bootstrap and lists it as a `[trusted=yes] file:///srv/keel-apt/repo trixie-staging` source for the build only |
| `plan/main` | `turnkey/base`, `turnkey/nodejs-nginx`, nodejs, npm, redis-server, redis-tools, curl, inithooks, confconsole, keel |
| `conf.d/main` | NodeBB 4.11.2 from the release tarball pinned by sha256, dependencies with `npm install --omit=dev`, a build time `./nodebb setup` against a scratch Redis so the assets are compiled in the image, then flush and cleanup; Redis bound to `::1 127.0.0.1`; nginx site enabled; unit enabled; staging source removed |
| `overlay/etc/nginx/sites-available/nodebb` | `[::]:80` and `80` redirect to https (ACME path kept), `[::]:443` and `443` proxy to `http://[::1]:4567` with websocket headers |
| `overlay/etc/systemd/system/nodebb.service` | `Type=simple`, user nodebb, `node loader.js --no-daemon --no-silent`, `ConditionPathExists=/var/www/nodebb/config.json` |
| `overlay/usr/lib/inithooks/firstboot.d/40nodebb` | first boot: reads `APP_DOMAIN`, `APP_EMAIL`, `APP_PASS`, `APP_ADMIN_USER` (and `FQDN`) from the inithooks conf, runs `./nodebb setup <json> --skip-build`, patches `config.json` (`bind_address ::1`, `port 4567`, `trust_proxy`), starts the service; idempotent on `config.json` |
| `overlay/usr/lib/inithooks/lib/nodebb.sh` | the decisions, 9 pure functions, 100 percent under kcov (15 bats tests) |
| `overlay/usr/lib/inithooks/bin/nodebb.py` | the only dialog (libinithooks Dialog), called for an absent value when a terminal is attached |
| `overlay/etc/apt/sources.list.d/keel.sources`, `preferences.d/keel` | future `apt.keellinux.org` entry, `Enabled: no`, documented; origin pin from `bin/pin-file` |
| `overlay/etc/confconsole/services.txt` | IPv6 block first with `$ipaddr6`, IPv4 block second |
| `stacks/nodejs-nginx/` | the stack layer recipe (Makefile, plan, changelog) |
| `keel/instance.example.yaml` | the spec used for this boot (section 6) |
| `tests/boot-test.sh` | the appliance test of docs/org-plan.md section 1 |
| `tests/nodebb.bats`, `tests/coverage.sh` | unit tests and the coverage gate for the library |
| `.github/workflows/tests.yml` | `test-shell.yml` (threshold 95) and `test-appliance.yml` (appliance nodebb, parent nodejs-nginx) |
| `README.rst`, `LICENSE` (GPL-3.0-or-later), `COVERAGE.md`, `changelog` | as decisions 0003, 0006 and 0007 require |

Hook number: 40, as `40redis` in the redis appliance and `40tkldev`: after
`30rootpass` and the fence, before `80hub-services`.

## 2. NodeBB version and how it was verified

Read on 2026-09-26 in the NodeBB repository and documentation:

- `install/package.json` at tag v4.16.0 (latest release, 2026-09-16) declares
  `"engines": {"node": ">=22"}`; the same at v4.15.x, v4.14.x, v4.13.x,
  v4.12.0 and v4.11.3. Tags v4.11.0 to v4.11.2 declare `>=20`; v4.3.0 and
  earlier `>=18`. Debian 13 ships nodejs 20.19.2 (`apt-cache policy` on the
  host and in the core layer; madison: trixie 20.19.2, unstable 22 and 24, no
  backport). `src/prestart.js` `versionCheck()` only warns on a mismatch.
- The engines line is not the whole truth. The first build, pinned at
  v4.11.2 (released 2026-05-01), failed in `./nodebb setup` with
  `TypeError: webidl.util.markAsUncloneable is not a function` from
  `node_modules/undici`: v4.11.0 to v4.11.2 pin `"undici": "8.1.0"`, whose
  own `engines` is `node >= 22.19.0`. v4.10.3 and earlier pin `undici
  ^7.10.0` (`>= 20.18.1`); undici 7.30.0 loaded and served `fetch` on Node
  20.19.2 in the build tree. Decision: pin **v4.10.3** (released 2026-04-15,
  tag ca38bdc03768b8913822e6b676e94b6252dc81ff), the last release whose own
  dependency pins run on the archive's Node.js, and record the alternatives
  for the maintainer (section 10).
- Tarball `https://github.com/NodeBB/NodeBB/archive/refs/tags/v4.10.3.tar.gz`,
  5,299,106 bytes, sha256
  `093b29081970f30d7f3b3863833e606861da29c6cf9438616de3c6c6675906a7`,
  identical when downloaded on the agent host and on the build host (the
  same held for v4.11.2: 5,358,072 bytes, `32204fff...`). `conf.d/main` pins
  version and digest and checks `install/package.json` carries the version,
  the way the odoo 19 recipe pins `ODOO_VERSION` and its package digest
  (../TKL/plan/00 fact 12).
- Non-interactive setup: `src/cli/index.js` defines `setup [config]` with
  `--skip-build`; `src/cli/setup.js` parses the JSON, calls
  `install.setup()` and `build.buildAll()` unless `skip-build`;
  `src/install.js` `setupConfig()` copies from the initial config only the
  question names (`url`, `secret`, `database`, `redis:host`, `redis:port`,
  `redis:password`, `redis:database`, `admin:username`, `admin:password`,
  `admin:password:confirm`, `admin:email`), which is why `bind_address`,
  `port` and `trust_proxy` are patched into `config.json` afterwards.
  `secret` defaults to a generated UUID when absent, so it is not passed.
- Admin user: created by `install.setup()` from `admin:*`; when absent the
  installer generates a password and prints it. `./nodebb user` also exists
  (`create`, `reset`, `make admin`) for later changes.
- Running: docs.nodebb.org/configuring/running/ gives a systemd unit
  (`Type=forking`, `env node loader.js --no-silent`, `PIDFile`); the recipe
  uses `--no-daemon` and `Type=simple` instead so systemd owns the process.
- Redis: `src/database/redis.js` questions, defaults `127.0.0.1:6379`,
  database 0, no password. The Debian default binds `127.0.0.1 -::1`; the
  recipe writes `bind ::1 127.0.0.1` explicitly.
- Dependencies: `./nodebb` installs them itself when `node_modules` is
  missing (`src/cli/index.js`, `package-install.js`: copy
  `install/package.json`, `npm install`); the recipe does the same two steps
  explicitly so the build log shows them.

## 3. Layer chain

Decision: a stack layer `nodejs-nginx` on core, then `nodebb` on the stack,
as docs/forum.md planned. Justification: the stack is what keel-redis and a
keel-nodejs would share (nginx, Node.js, npm, Redis, all archive packages,
deterministic), and it keeps the npm fetched NodeBB tree, the one part that
depends on a registry, in its own layer. Directly on core would have saved
one build of about two minutes and lost the reuse.

bt-layer requires the product directory to carry the layer name, so the
stack recipe (`stacks/nodejs-nginx` in the repository) is copied to
`products/nodejs-nginx` on the host, and the appliance to `products/nodebb`.
SOURCE_DATE_EPOCH = 1790440581, the time of the recipe's last commit.

| Layer | Type | Parent | Built from | root.patched | pack | tar.zst bytes | sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| core | rootfs | none | keel-core 24c82ee, common b60dd23, 2026-09-24 (existing, not rebuilt) | 309 s | 95 s | 326,418,793 | e08e8224aeea1abb605b0e359d345f459d2e04d413e6a08c5e57f5b7858c9e19 |
| nodejs-nginx | delta | core | `stacks/nodejs-nginx` at 351d19e | 240 s (stamps: root.build 214 s, root.patched 21 s) | 52 s | 148,864,072 | f791777f1fdf387c7b30880ca24d4d53f991e78c5fce2e3eb3abd184c43832e1 |
| nodebb | delta | nodejs-nginx | recipe at c85c359 (third attempt; see section 8) | 198 s | 62 s | 165,333,228 | c199a86042bcde87640585ca04e9ed595213195da37fa5bf6f9fc94a05554fa2 |

`keel verify --layers-dir /mnt/builds/layers` (keel 0.1.0, 2 s): core, lamp,
nodejs-nginx, nodebb all `unverified: hash file present, not signed`, exit 8,
as expected without a trusted key; no mismatch, chain resolved.

Stack layer content checked in `nodejs-nginx.rootfs`: nginx 1.26.3-3+deb13u9,
nodejs 20.19.2+dfsg-1+deb13u3, npm 9.2.0~ds1-3, redis-server 5:8.0.2-3+deb13u2;
`snippets/ssl.conf` carries the Mozilla intermediate cipher list (the fix of
section 8, item 1). Uppers: root.build 723 MiB, root.patched 44 MiB.
Manifest: `build_overlays turnkey.d/tkl-bashlib turnkey.d/systemd-chroot
nginx`, `build_conf turnkey.d/hostname turnkey.d/zz-ssl-ciphers nginx`.

nodebb layer content checked in `nodebb.rootfs`: `/var/www/nodebb` 663 MiB
(node_modules from `npm install --omit=dev`, 834 packages in 3 min, plus
`build/public` compiled at build time), no `config.json`, no
`keel-staging.list`, no `/srv/keel-apt`, `/etc/turnkey_version`
`turnkey-nodebb-19.0-trixie-amd64`, `nodebb.service` enabled. Uppers:
root.build 96 MiB, root.patched 707 MiB. Two of the three project packages
were still at the upstream version in this layer (section 4).

## 4. How the project packages got in

1. `/root/keel-apt-tools` (the apt tooling, identical to repos/apt by md5)
   published the four packages waiting in `/srv/keel-apt/incoming` with
   `KEEL_APT_PAGES=/root/keel-apt-pages bin/publish --unsigned-staging`
   (the Pages checkout has to be a git repository, so a scratch one was
   created; nothing was pushed). reprepro now lists in `trixie-staging|main|amd64`:
   confconsole 2.2.3+keel1, fab 1.1.1+keel1, inithooks 2.3.6+keel1, keel 0.1.0.
   The repository base is `/srv/keel-apt/repo` (db, dists, pool).
2. The appliance `Makefile` appends to `bootstrap/post`, after turnkey.mk's
   `bootstrap_apt`: copy `dists/` and `pool/` into
   `$O/bootstrap/srv/keel-apt/repo`, write
   `/etc/apt/sources.list.d/keel-staging.list` with
   `deb [trusted=yes] file:///srv/keel-apt/repo trixie-staging main`, run
   `apt-get update`. The copy is needed because fab-chroot shares the host's
   network but not its filesystem. `fab-plan-resolve` then resolves
   inithooks, confconsole and keel from the plan to the staging versions and
   `fab-install` upgrades the two core packages and installs keel.
3. `conf.d/main` removes the list file, `/srv/keel-apt` and the apt lists,
   and checks that `keel.sources` (overlay) carries `Enabled: no`. The image
   therefore has the three packages installed and no source that could serve
   them; `/etc/apt/sources.list.d/keel.sources` documents the future signed
   entry and `/etc/apt/preferences.d/keel` pins origin `Keel Linux` at 1001.
4. `keel` 0.1.0 was also installed on the build host from
   `/srv/keel-apt/done` (dpkg), for `keel verify`, `pull` and `assemble`.

Result in the layer built from c85c359: `keel 0.1.0` installed from the
staging source, but `inithooks 2.3.6` and `confconsole 2.2.3` unchanged.
`build/root.spec` explains it: `inithooks # bootstrap plan/main` and
`confconsole # bootstrap plan/main` (a package the parent already carries is
resolved at the parent's version) against `keel # plan/main` (new, installed).
Fix in commit f9ee052: `conf.d/main` runs `apt-get install -y --only-upgrade
inithooks confconsole` from the same file source before removing it, and
fails the build unless both versions end in `+keel1`. The rebuild with that
commit was running when this report was written; its result replaces the
nodebb row of section 3.

## 5. Container network

`tests/boot-test.sh nodebb --keep`, run from `/turnkey/fab-keel/products/nodebb`
at 17:16 UTC (log `/root/boot-test-1.log`):

- `keel pull nodebb --source /mnt/builds/layers`: core, nodejs-nginx and
  nodebb fetched, 640,616,093 bytes, cache `/var/cache/keel/layers` (611 MiB).
- `keel assemble nodebb --rootfs /var/lib/lxc/forum/rootfs`: core 1 member;
  nodejs-nginx 2 members, 31 whiteouts, 835 opaque directories; nodebb 2
  members, 32 whiteouts, 10 opaque directories. Rootfs 2.1 GB. verify 3 s,
  pull plus assemble 32 s.
- Container adaptation (what bt-container does to an ISO rootfs, 62 s):
  `purge-pkgs` (tkl-installer, live-boot, live-tools,
  live-boot-initramfs-tools removed; di-live absent), `tklpatch-apply`
  patches/headless and patches/container, `aptconf-tag` and `build-tag
  proxmox` (marker `/var/lib/turnkey-info/inithooks.service/lxc`, so the
  inithooks unit does not run at boot, ../TKL/plan/00 addendum),
  `30rootpass` made executable again so the spec's root password applies.
- `/etc/keel/instance.yaml` written from `keel/instance.example.yaml`;
  `/etc/keel/secrets/root_password` and `app_password` generated with
  `openssl rand -base64 18`, mode 0600, root. They live only in the rootfs.
- LXC config `/var/lib/lxc/forum/config`: `common.conf` and `nesting.conf`
  includes, `lxc.rootfs.path = dir:/var/lib/lxc/forum/rootfs`, macvlan in
  bridge mode on the host's `eth0` (`lxc.net.0.type = macvlan`,
  `lxc.net.0.macvlan.mode = bridge`, `lxc.net.0.link = eth0`, hwaddr
  `02:bc:24:11:00:xx` derived from the name), apparmor `generated` with
  nesting allowed, the configuration ../TKL/tools/iso-to-lxc.sh boots TKLDev
  with. The address was to come by SLAAC from 2804:710:d0:5::/64;
  `ip6table_nat` was loaded on the host for the init fence (plan/00 fact 4).
- `lxc-start -n forum` failed: `wait_on_daemonized_start: 829 No such file or
  directory - Failed to receive the container state`, `The container failed
  to start`. No `/var/log/lxc/forum.log` exists (lxc 6.0.4-4+deb13u4 installed
  on the host today, `lxc-net.service` enabled). Not diagnosed further from
  this side at the maintainer's request; the next step is
  `lxc-start -n forum -F -l DEBUG -o /var/log/lxc/forum.log`.

## 6. First boot

Not reached: the first boot runs after `lxc-start`, as
`lxc-attach -n forum -- keel spec apply --spec /etc/keel/instance.yaml
--non-interactive` (writes `/etc/inithooks.conf`, so the headless `29preseed`
finds it and does nothing) followed by
`lxc-attach -n forum -- /usr/lib/inithooks/run` with a 900 s timeout, then a
count of `successfully completed` lines in `/var/log/inithooks.log`
(`tests/boot-test.sh`, `first_boot`). The hooks that will run on this
container: 00declarative (no-op), 01ipconfig (no-op, `managed_by: host`),
05autogrow-fs, 09hostname (`forum`), 10randomize-*, 10regen-sshkeys,
15regen-sslcert, 29preseed (no-op), 29sudoadmin, 29tagid, 30rootpass,
30turnkey-init-fence, 35postfix-unprivileged, 40nodebb, 80hub-services
(`SKIP`), 85secalerts (`SKIP`), 95secupdates (`SKIP`), 97, 98finalize.

## 7. Checks over IPv6

Not reached. The script does, from the host: `curl -6 http://[ADDR]/`
expecting `307` to https (or `200` when the request carries a trusted
`X-Forwarded-Proto: https`), then `curl -6 -k https://[ADDR]/` until `200`
and the `<title>` of the forum page, then `lxc-attach -- keel diff --spec
/etc/keel/instance.yaml` accepting exit 0 or 13 (a declared field inspect
cannot observe), never 14.

## 8. What failed and how it was fixed

1. **layer-lib did not run zz-ssl-ciphers for a nginx stack.** `layer_child_conf`
   looked for the `ZZ_SSL_CIPHERS` mark in the conf scripts the child runs; the
   apache conf reads it there, but nginx carries the mark in an overlay file
   (`overlays/nginx/etc/nginx/snippets/ssl.conf`), so a stack built on core
   would have kept the literal `'ZZ_SSL_CIPHERS'` as its cipher list and nginx
   would not start. Fixed in the buildtasks fork, branch
   `fix/layer-ssl-ciphers-overlay` (one commit: `layer_needs_ssl_ciphers`
   also scans the child's overlays; bt-layer passes the overlays path and
   list; two cases added to tests/layer, 42 of 42 paths; kcov layer-lib
   195/195, bt-layer 99/100, the one uncovered line pre-existing). Applied on
   the host's `/turnkey/buildtasks-keel` with `git am`; not pushed. The stack
   manifest shows `build_conf turnkey.d/hostname turnkey.d/zz-ssl-ciphers
   nginx` and the built `ssl.conf` carries the Mozilla intermediate list.
2. **NodeBB 4.11.2 does not run on Node 20** despite `engines >= 20`
   (section 2). Fixed by pinning 4.10.3.
3. **The Redis started by the first failed build outlived it.** The chroot
   shares the host's network and pid space; `systemctl start redis-server`
   through the systemd-chroot shim started a real redis-server on the host's
   `::1:6379` and `127.0.0.1:6379`. When the build aborted, `make clean` removed
   its data directory but not the process. The second build's NodeBB then
   connected to that stale instance and failed with `MISCONF Redis is
   configured to save RDB snapshots, but it's currently unable to persist to
   disk`; the second build's own Redis had logged `Could not create server TCP
   listening socket ::1:6379: bind: Address already in use`. The stale process
   refused SIGTERM (Redis will not exit while its final save fails) and was
   removed with SIGKILL. Fixed in the recipe: the build time setup uses a
   plain `redis-server` process as user redis, `--save "" --appendonly no
   --dir /tmp --daemonize yes`, on port 16379, shut down with `shutdown
   nosave`; nothing of it can collide with, or survive on, the build host.
4. **kcov counts a backslash continued command on its first line only**, so
   multi line `python3 -c` bodies in `lib/nodebb.sh` read as uncovered (72
   percent). Rewritten as single lines; 100 percent (43/43). Same quirk hit
   the bt-layer fix, which is why its call is on one line.
5. **`bin/publish` expects a git checkout for the Pages tree** and the copy of
   the tooling on the host is not one; a scratch repository
   `/root/keel-apt-pages` was created for it (nothing is pushed from there).
6. **`BT_PRODUCTS` in the host's buildtasks-keel config pointed at the upstream
   tree** (`/turnkey/fab/products`); set to `/turnkey/fab-keel/products`.
7. **`lxc-start` failed** on the assembled and adapted rootfs (section 5),
   before any first boot. Under the maintainer's investigation on the host.
8. **The naming changed twice during the build**: apex, then
   forum.keellinux.org. The recipe now takes the public proxy that terminates
   TLS as `app.options.trusted_proxy` (`APP_TRUSTED_PROXY`), rendered at
   first boot into `/etc/nginx/conf.d/nodebb-proxy.conf` (`geo` of trusted
   addresses, `map` to `$nodebb_scheme`, `set_real_ip_from`); a request from
   2804:710:d0:5::13 with `X-Forwarded-Proto: https` is proxied on port 80,
   every other port 80 request is redirected to https. `nodebb_proxy_conf`
   refuses a value nginx would not accept and the hook runs `nginx -t`.

## 9. Timings and sizes

| Step | Time | Size |
| --- | --- | --- |
| stack layer root.patched | 240 s | uppers 723 + 44 MiB |
| stack layer pack (zstd -19) | 52 s | 148,864,072 bytes |
| nodebb layer root.patched (attempt 3) | 198 s (npm install 3 min of it) | uppers 96 + 707 MiB |
| nodebb layer pack | 62 s | 165,333,228 bytes |
| keel verify (4 layers) | 3 s | |
| keel pull (3 layers, local directory) | with assemble, 32 s | 640,616,093 bytes |
| keel assemble | with pull, 32 s | rootfs 2.1 GB |
| container adaptation (bt-container steps) | 62 s | |
| first boot, checks | not reached | |

Failed attempts: attempt 1 (v4.11.2, undici) failed after the 3 min npm
install; attempt 2 (stale Redis) the same. Warm chain for a NodeBB user with
core and the stack cached: one 165 MB download.

## 10. What is left

- **Container start**, then the first boot, the HTTP checks and `keel diff`
  (sections 5 to 7), and the numbers they produce.
- **Final layer**: the rebuild from f9ee052 (project packages upgraded in
  conf.d) replaces the nodebb row; re-run `tests/boot-test.sh nodebb --keep`
  on it, since the container under test carries inithooks 2.3.6 and
  confconsole 2.2.3 from the archive, not the +keel1 builds.
- **ACME and TLS**: `tls.acme.enabled: false` inside the appliance; TLS for
  forum.keellinux.org terminates on the public services VM
  (2804:710:d0:5::13), which reverse proxies to the container over IPv6 on
  port 80. The appliance's own certificate is the regenerated self signed
  one; enabling ACME later needs the AAAA record and the confconsole
  Let's Encrypt path.
- **DNS**: forum.keellinux.org has no record yet; the spec keeps
  `managed_by: host` with SLAAC and should move to a static address once
  the record exists (comment in `keel/instance.example.yaml`).
- **Key**: nothing here is signed. The project packages came from the
  unsigned staging distribution, the layers carry unsigned `.hash` files
  (`unverified`), and `keel.sources` stays disabled until the subkey is
  rotated and apt.keellinux.org serves the signed `trixie` distribution.
- **NodeBB version**: 4.10.3 is five months behind the latest release
  because of the archive's Node.js 20. Options for the maintainer: stay on
  4.10.x until Debian 14; take Node.js 22 from outside the archive (forum.md
  says all from the archive); or wait for a 4.x release that pins an undici
  compatible with 20 (unlikely, the engines line moved to 22 in 4.11.3).
- **Pushes**: the keel-nodebb repository (14 commits) is local only; the
  buildtasks fix branch `fix/layer-ssl-ciphers-overlay` is local and applied
  on the host's checkout with `git am`; `/root/keel-apt-pages` holds the
  staging publish commit and must never be pushed.
- **A `keel apply` hook**: the boot test runs `keel spec apply` by hand
  before `inithooks/run`; the keel package should ship a firstboot hook that
  does it, so a container with `/etc/keel/instance.yaml` boots declaratively
  without an operator step.
- **Host hygiene**: the container patch leaves `30rootpass` disabled for
  Proxmox; the boot test re-enables it, which belongs in a Keel container
  patch, not in a test.

## Container start, first boot and public switch (coordinator, 17:19 to 17:35 UTC)

- `lxc-start` failed with "Failed to receive the container state"; the debug
  log said "Cannot use generated profile: apparmor_parser not available".
  The build host had the apparmor kernel module but not the `apparmor`
  package. Installed it; the container started with the generated profile,
  macvlan bridge on eth0, SLAAC address 2804:710:d0:5:7f14:2160:4aa0:6cfa.
- Inside the image: keel 0.1.0 present, but inithooks 2.3.6 and confconsole
  2.2.3 from upstream (the parent layer's packages win in apt's resolver, as
  the builder found; the rebuild with an explicit upgrade is running). So no
  00declarative hook: the first boot was driven by `keel spec apply` writing
  /etc/inithooks.conf (11 variables) and then `/usr/lib/inithooks/run`
  headless. Every hook completed, RUN_FIRSTBOOT=false, nodebb, nginx and
  redis active, NodeBB on [::1]:4567 with url https://forum.keellinux.org.
- The build host cannot reach its own macvlan containers (known macvlan
  bridge limitation); the workstation and the public VM can: HTTP answers
  307 to HTTPS, correct behind a TLS-terminating proxy.
- Public VM: the prepared proxy block in /etc/nginx/sites-available/keel-forum
  was enabled with the container address; nginx reloaded. From the
  workstation, https://forum.keellinux.org answers 200 with the title "Keel
  Linux forum" over IPv6 with a valid certificate. Admin user `admin`
  (admin@keellinux.org, uid 1) exists; its password is the `app_password`
  secret under /etc/keel/secrets in the container.
- `keel diff` inside the container after first boot: 5 same, 4 drift,
  1 unknown. The drifts are findings, not failures: `network.ipv6.method`
  declared `auto` but observed `dhcp` (inspect cannot tell SLAAC from DHCPv6
  in ifupdown's `inet6 dhcp`, and the hook writes `dhcp` for both: the
  vocabulary needs one term or inspect needs the distinction); `tls.acme`
  declared with domains while acme is disabled for this boot (the spec should
  not declare domains when disabled, or diff should treat disabled as
  nothing); `security.updates` declared `skip` but observed `force` (the
  upstream 95secupdates hook enables unattended security updates regardless;
  the spec value SKIP only skips the interactive prompt: the field's
  semantics must be documented and probably renamed); `instance.fqdn`
  unknown because /etc/hosts has no fully qualified entry (09hostname does
  not write one; the apply phase should).
- Left: ACME inside the appliance (TLS terminates on the public VM for
  now), the rebuilt nodebb layer with the +keel1 packages and its boot test,
  pushing the keel-nodebb repository, the diff findings above as issues.

## Validation of the rebuilt layer, and the two proxy fixes (18:00 to 18:20 UTC)

The container `forum` was left untouched throughout: a second container,
`forum2`, was assembled from the rebuilt layer on the same build host, with
its own macvlan hwaddr (`02:bc:24:11:00:f2`) and hostname.

### The two fixes, now in the sources

Both were diagnosed and applied live earlier in the day and existed in no
repository. They are the two halves of one failure, and fixing either alone
still leaves the loop.

1. **The appliance tested the trust against the wrong address.**
   `/etc/nginx/conf.d/nodebb-proxy.conf`, written at first boot by
   `firstboot.d/40nodebb` (logic in `lib/nodebb.sh`), declared
   `geo $nodebb_trusted_proxy`, which reads `$remote_addr`. The same file
   sets `set_real_ip_from` with `real_ip_header X-Forwarded-For`, and the
   realip module runs in the post read phase, before any geo or map variable
   is evaluated. By the time the trust test ran, `$remote_addr` already held
   the address the proxy had put in `X-Forwarded-For`: the visitor, not the
   proxy. The geo block never matched, `$nodebb_scheme` stayed `http`, and
   every request to port 80 was answered with a 307 to https, which the TLS
   terminating proxy sent straight back. Now `geo $realip_remote_addr
   $nodebb_trusted_proxy`, with a comment in the rendered file and in the
   shipped default saying why, and a test asserting the old form is absent.

2. **The public VM connected from the wrong source address.** The VM has the
   static `2804:710:d0:5::13`, which DNS points at and the appliance trusts,
   and a SLAAC address `2804:710:d0:5:be24:11ff:feeb:ed35` that the kernel
   picks for outgoing connections. `proxy_bind 2804:710:d0:5::13;` before
   `proxy_pass` in `/etc/nginx/sites-available/keel-forum` fixes it. No
   brackets: nginx rejects a bracketed literal in `proxy_bind`. Written up in
   docs/releases-host.md section 3.1. Carrying it into
   `/usr/local/sbin/keel-provision` is prepared but **not installed**; see
   that document's pending list.

Pull request: keel-linux/keel-nodebb#1, three commits.

### What the layer actually contained

The layer published at 17:23 (sha256 `40e3f4da`, 122,535,134 bytes, parent
nodejs-nginx `f791777f`) does carry `inithooks 2.3.6+keel1`, `confconsole
2.2.3+keel1` and `keel 0.1.0`, and therefore the `00declarative` hook. It is
also the output of a **failed build**, and two defects come from that.

- `conf.d/main`'s `apt-get install -y --only-upgrade inithooks confconsole`
  met a dpkg conffile prompt on `/etc/confconsole/services.txt`, which the
  appliance overlay replaces and which is a conffile of confconsole. Conf
  scripts run with stdin closed, dpkg read end of file at the prompt, left
  confconsole `install ok unpacked`, apt exited 100 and `root.patched`
  failed with `make: *** Error 100`. The build log at
  `/mnt/builds/layers/nodebb.log` ends on that line.
- `bt-layer` packed and exported the tree anyway. Line 155 of `bt-layer` is
  `make build/stamps/root.patched ... | tee -a "$log" || true`, so a failed
  build is published as a layer. Because `root.patched` never finished, fab
  never removed the build overlays: the layer carries
  `/usr/local/bin/systemctl` and `/usr/local/bin/service`, the
  systemd-chroot shims, which `core.rootfs` and `nodejs-nginx.rootfs` do not
  have. On the first attempt at booting `forum2`, `10regen-sshkeys` called
  the shim and looped forever, 5,000 log lines in three minutes.

The recipe fix (keep the conffile non interactively, and check the dpkg
state as well as the version, since a half configured package reports the
new version either way) is in the pull request. The `bt-layer` half is a
buildtasks change and is not. A clean rebuild needs write access to the
build host's product tree, which this run did not have, so `forum2` was
assembled from the published layer with the two shims removed by hand and
confconsole reconfigured by the container adaptation; that is what the rest
of this section validates.

### First boot, driven by the hook chain alone

No `keel spec apply`. The spec was written to `/etc/keel/instance.yaml` and
`INITHOOKS_DECL` in `/etc/default/inithooks` was pointed at it, because
`00declarative` reads `/etc/inithooks.yaml` by default and the keel package
puts the spec somewhere else. That mismatch is a finding, not a fix: one of
the two packages should agree with the other.

`inithooks.service` did not start by itself. The headless patch's unit
carries `ConditionPathExists=!/var/lib/turnkey-info/inithooks.service/lxc`
and `build-tag proxmox` writes exactly that marker, while no
`inithooks-lxc.service` exists in this image. So the chain was started once
with `lxc-attach -n forum2 -- /usr/lib/inithooks/run`, which is the hook
chain and nothing else.

```
INFO: [00declarative] running
[00declarative] /etc/keel/instance.yaml applied to /etc/inithooks.conf
INFO: [00declarative] successfully completed
...
INFO: [40nodebb] running
INFO: [40nodebb] successfully completed
```

20 hooks completed successfully. `29preseed` reported `failed - exit code 1`:
its first line is `[[ -n "$_TURNKEY_INIT" ]] && exit 0` under `bash -e`, and
a `&&` list whose own status is non-zero ends the script, so that hook always
exits 1 when `_TURNKEY_INIT` is unset. It is a harmless no-op either way
(`00declarative` had already written the conf), but it is noise in every
boot log. `nodebb`, `nginx` and `redis-server` all active;
`/etc/inithooks.conf` wiped after the boot, as it should be.

### Checks over IPv6, from the public services VM

Container address **`2804:710:d0:5:deea:cbca:f115:6172`**. The build host
still cannot reach its own macvlan containers, so every request came from
the VM, with `--interface` standing in for `proxy_bind`.

| request | layer as built | with the fix |
| --- | --- | --- |
| trusted source, `X-Forwarded-For` present, `X-Forwarded-Proto: https` | 307 to https | 200, `<title>Home \| NodeBB</title>` |
| trusted source, no `X-Forwarded-For` | 200 | 200 |
| SLAAC source, both headers | 307 | 307 |
| trusted source, no proxy headers | 307 | 307 |
| `https://[addr]/` direct, self signed | 200 | 200 |

The second row is why the bug survived the first build: with no
`X-Forwarded-For` the realip module does nothing, `$remote_addr` stays the
proxy's address and the old geo block happened to match. The third row is
fix 2 in one line: from the wrong source address the trust fails whatever
the appliance does.

`keel diff --spec /etc/keel/instance.yaml` inside `forum2`: 5 same, 4 drift,
1 unknown, 6 not declared, 3 not compared, exit 14. The four drifts are the
same four the coordinator recorded for `forum` (`ipv6.method` auto against
observed dhcp, `tls.acme` domains declared while acme is disabled,
`security.updates` skip against force, `instance.fqdn` unknown because
`/etc/hosts` carries no fully qualified name). Nothing new.

### confconsole Instance menu: not present

`ls /usr/lib/confconsole/plugins.d/Instance` exits 2: there is no such
directory. The plugins are the five upstream ones. `keelcli` does not exist
in the image, so there is no non-interactive path to exercise either.
`confconsole 2.2.3+keel1`'s changelog is the IPv6 networking work and the
tests, and mentions no Instance plugin: it has not been written yet. Brief
section 6 still wants it, and `keel diff` and `keel spec apply` are the
library calls it would sit on.

### Timings and sizes

| Step | Time | Size |
| --- | --- | --- |
| keel pull plus keel assemble (local layers directory) | 33 s | cache 571 MiB, rootfs 2.1 GB |
| container adaptation (bt-container steps) | 32 s | |
| removing the two build shims | 0 s | |
| lxc-start to a global IPv6 address | 4 s | |
| first boot, whole hook chain | 12 s | |
| HTTP checks from the public VM | 2 s | |

`forum2` is left running at `2804:710:d0:5:deea:cbca:f115:6172` with the
fixed library installed. It has no DNS record and no server block on the
public VM; reach it by address. `forum` was not touched.

### Still wrong after this section

Filed as keel-linux/keel-nodebb#2. In short: `bt-layer` publishes failed
builds; the layer of 2026-09-26 must be rebuilt and replaced; `00declarative`
and the keel package disagree on where the spec lives; a Keel container has
no inithooks unit that runs at boot; `29preseed` always exits 1; the
confconsole Instance menu does not exist.
