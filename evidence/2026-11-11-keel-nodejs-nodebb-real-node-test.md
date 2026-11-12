# keel-nodejs and NodeBB on lnpp: a real-node test of the prototype

Date: 2026-11-11 and 2026-11-12

This file is the evidence for the first real-node test of the Keel
Node.js package of note 0083 and of the NodeBB layer of note 0082. It is
a test of a local prototype on one node. Nothing was published: no apt
repository changed, no image was built, and no release was made. It is
not a commissioning test (0075).

## The questions

1. Does a `.deb` of the official Node.js 24 binary install, run, upgrade
   and come off with apt?
2. Does the build fail closed when the signature or the sha256 is not
   correct?
3. What does an upgrade of the package do to a running NodeBB?
4. Does NodeBB 4.16.7 run on the PostgreSQL 17 of lnpp in the layout of
   0082, section 4: code owned by root, and NodeBB writes only its own
   paths?
5. Do the first boot hook and `serve.py` of the layer work on a real node?

## The machine

| Item | Value |
|---|---|
| Container | CT 9385 on BR1, unprivileged, nesting=1, 2 cores, 4096 MiB, root disk 8 GB on `local-lvm`, host name `nodebb-test` |
| Network | `vtnet88`, tag 5, `--nameserver 2606:4700:4700::1111`. One global IPv6 address and one IPv4 address (DHCP). The node is not IPv6-only |
| Image | `debian-13-keel-lnpp_19.0-9_amd64.tar.zst`, sha512 `7a522c7e…cf4d`, the same as the published `.sha512` of mirror.keellinux.org |
| Debian | 13.7, keel 0.23.96, keel-web 0.4.2, PostgreSQL 17.11, nginx 1.26.3 |
| First boot | preseeded root and database passwords, written through `pct mount`; the host copy was removed |

## The package

| Item | Value |
|---|---|
| Repository | local `repos/keel-nodejs`, branch `main`, commit `43de5a4`, no remote |
| Name and version | `keel-nodejs` `24.22.3+keel1`, `amd64`. The test build `24.22.2+keel1` is test material only and is never published |
| Content | the official `node-v24.22.3-linux-x64.tar.xz` in `/usr/lib/keel-nodejs`; links `/usr/bin/node`, `npm`, `npx`; npm 11.19.1; no Corepack |
| Signature | `SHASUMS256.txt.asc` of 24.22.2 and 24.22.3 is signed by `5BE8A3F6C8A5C01D106C0AD820B1A390B168D356`, a key of `keys.list` of `nodejs/release-keys` at `481637f` |
| Tests | 48 bats tests, no network. Coverage of `debian/upstream`: 98.41 percent (124 of 126 lines), kcov. shellcheck: no finding. lintian: no tag, with overrides that give a reason each |
| `.deb` sha256 | 24.22.3+keel1 `2aa8941e…5d81`; 24.22.2+keel1 `8c8773cf…25cc` |

The tests show that the build stops on each of these: a key that is not
pinned, a key file that holds another key, a changed sum in the signed
text, a sum line outside the signed block, a pin that is not the signed
sum, a tarball with another content, an expired key, a revoked key, and
a Debian version that is not the pin plus `+keelN`.

## Results

The logs are in `repos/nodebb-hand-tests/` of the workstation. They hold
no password, no token and no key.

| Test | Result | Log |
|---|---|---|
| Install 24.22.2+keel1 from a local file repository (`[trusted=yes]`, unsigned, test only) | pass: `node -v` v24.22.2, npm 11.19.1, `npm config get prefix` `/usr/local`, man pages, `npm-cli.js` mode 0755 | `10-install-24.22.2.log` |
| NodeBB code, lock file, `npm ci` | pass: tarball sha256 checked; the lock file took 96 s, `npm ci` 26 s; `node_modules` 617 MB, 1271 packages, no git source | `20-nodebb-code.log` |
| `conf.d/main` of the layer on the node, PostgreSQL stopped as in a chroot | pass on the third run, 62 s, exit 0; `keel manifest validate nodebb` "resolved along core, web, lnpp, nodebb" | `30-layer-build.log`, `31-layer-build-2.log`, `32-layer-build-3.log` |
| First boot hook `45nodebb` on the writable node | pass, 5 s: role `nodebb` with a SCRAM verifier, `config.json` root:nodebb 0640, setup with the admin in the environment | `40-firstboot.log` |
| First start through `serve.py` | pass: HTTP 200 8 s after the start; `serve.py`, `loader.js`, `app.js` run as `nodebb` | `41-first-start.log` |
| Forum pages through nginx | pass: https and http (port 80, decision 0079) 200, title "Home | NodeBB", `/keel-health` 204, 4 default categories | `41-first-start.log`, `42-pages.log` |
| Admin login and a new topic through nginx | pass: login 200, topic created, a guest reads it | `47-forum-write.log` |
| Upgrade to 24.22.3+keel1 with `apt-get install --only-upgrade` while NodeBB runs | pass: the package upgrades, NodeBB answers 200 during and after it | `50-upgrade-24.22.3.log` |
| Restart of the unit after the upgrade | pass: `/proc/PID/exe` is the 24.22.3 binary (sha256 `a7ec1b37…`), a new topic passes | `51-restart.log` |
| `kill -9` of the worker `app.js` | pass: the loader starts a new worker, 200 after 4 s | `51-restart.log` |
| `kill -9` of `loader.js` | fail, then pass after the fix: the worker stayed and kept port 4567. Fixed in keel-nodebb `15151cc`: 200 after 2 s, no orphan, no EADDRINUSE | `51-restart.log`, `52-loader-kill.log` |
| Restart and stop of PostgreSQL | NodeBB itself ends; `serve.py` starts it again: 200 7 s after a restart, about 1 s after the start that follows a 20 s stop | `51-restart.log` |
| Removal of `keel-nodejs` while NodeBB runs | pass: no file of the package stays; the running NodeBB answers until it restarts | `60-remove.log` |
| Restart with no Node.js | `serve.py` stays active and tries again every 5 s (exit 127); nginx 502 | `60-remove.log` |
| Reinstall | pass: NodeBB serves again after 8 s with no action by hand | `60-remove.log` |
| Contract proofs of `tests/commission.yaml` | pass: the app proof logs in through nginx and refuses a wrong secret (403); the role `nodebb` logs in over TCP; the `seeded` query reads the admin | `70-contract-proofs.log` |
| Final overlay of keel-nodebb `70bc813` and a second run of `45nodebb` | pass: the secret and the 3 topics stay; a new topic passes | `80-final-overlay.log` |

## Facts found

1. **gpgv exits 0 for an expired key and for a revoked key.** Only its
   status lines (`EXPKEYSIG`, `REVKEYSIG`) show it. The build reads them.
2. **dh_fixperms sets every `*.js` file to 0644.** The first build had a
   `/usr/bin/npm` that could not run. The package now excludes its tree
   from dh_fixperms and sets the modes itself.
3. **An upgrade of the package does not restart NodeBB.** The package has
   no maintainer script. After the upgrade, `/proc/PID/exe` of the loader
   and of the worker shows `(deleted)`: they run the old binary until a
   restart. The node has no needrestart. This is open point 5 of 0083.
4. **npm 11.19 runs no install script of a dependency unless it is
   approved.** `esbuild`, `cbor-extract` and `@parcel/watcher` ran no
   script, and NodeBB works.
5. **The native modules of NodeBB are tied to the Node.js line.**
   `cbor-extract` ships `node.abi137.glibc.node`. ABI 137 is Node.js 24.
   An apt upgrade that moves to another line can break such a module.
6. **The writable list of 0082, section 4, is not complete.**
   `nodebb-plugin-emoji` removes and writes `build/emoji` in its own
   directory under `node_modules` at the first start of a node. The layer
   gives `nodebb` that directory and allows it in the unit.
7. **`./nodebb setup` copies the favicon into `uploads/system` and makes
   no directory for it.** The hook makes it.
8. **The GitHub tarball of NodeBB gives modes 0664 and 0775** when tar
   runs as root. The layer removes the group write bit.
9. **NodeBB takes its setup answers from `NODEBB_ADMIN_*` variables**, and
   the other answers from an existing `config.json`. So no password goes
   on a command line.
10. **NodeBB 4.16.7 runs on PostgreSQL 17.11.** 0082 had this as "not
    verified". The upstream CI tests PostgreSQL 18.
11. The first requests in the first seconds after a start gave a short
    page (686 bytes) and 404 on `/api/config`. Ten seconds later both
    were complete.

## Defects of the test method

- A call as `bash conf.d/main` ignores the `-e` of the shebang, so the
  first run went on after a failure. The script now sets `-e` itself.
- The first emoji fix (`38d6853`) replaced `build/` of the plugin with a
  link and so removed its code. `a7c93aa` and `5ac313a` replaced it.
- The CT ran the check page of lnpp, so `userdel keel-check` failed. A
  chroot has no running process. `keel_check` stays in the database of
  the CT from its own first boot of lnpp.
- `bc` is not in the image, so the duration of the apt upgrade is not
  measured.

## Not tested

- A build of the layer with `bt-layer`, an image, an ISO, and the
  commissioning of 0075. The main session builds the images.
- A pair: `cloud_simple`, `cloud_advanced`, the replica notice, a promote,
  the replication of the uploads, netem.
- An IPv6-only node.
- Anubis and Coraza in front of NodeBB. No Coraza exclusion is written.
- A login in a browser over plain HTTP. The session cookie has `Secure`,
  so such a login cannot keep its session.
- A change of the active plugins and the build that `serve.py` then runs.
- A change of the Node.js line, and BR2.

## Questions for the maintainer

1. Package name (0083 open point 1): A `keel-nodejs` for every line, or B
   one name for each line, for example `keel-nodejs-24`?
2. Place of the tree (open point 2): is `/usr/lib/keel-nodejs` with links
   in `/usr/bin` correct?
3. Restart (open point 5): does the package stay with no maintainer
   script, so that the operator or the layer restarts the application?
4. Shared secret: does keel render `nodebb_secret` into the first boot?
   Without it, a login does not survive a promote.
