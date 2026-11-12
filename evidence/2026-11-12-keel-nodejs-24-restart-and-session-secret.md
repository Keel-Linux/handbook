# keel-nodejs-24, the restart of NodeBB on a new Node.js, and the session secret in the database

Date: 2026-11-12

This file is the evidence for the second real-node test of the prototype,
after the answers of the maintainer of 2026-11-12 to the questions of
`2026-11-11-keel-nodejs-nodebb-real-node-test.md`:

1. One binary package for each Node.js line: `keel-nodejs-24`.
2. `/usr/lib/keel-nodejs` with links in `/usr/bin`.
3. The package has no maintainer script. The application layer restarts
   its service.
4. The NodeBB session secret: the database carries it (answer A of the
   coordinator). No change of keel.

It is a test of a local prototype on one node. Nothing was published. It
is not a commissioning test (0075).

## The machine

CT 9385 on BR1, the machine of the first test, with NodeBB 4.16.7 on the
PostgreSQL 17.11 of keel-lnpp 19.0-9 and 4 topics from the first test.

## The code

| Part | Commit |
|---|---|
| keel-nodejs, package `keel-nodejs-24` | `0522ad3` (Keel-Linux/keel-nodejs#1) |
| keel-nodebb, layer | `ef609a8` on the node; `403d5a7` and `aa628d7` change the documents and the boot test only (Keel-Linux/keel-nodebb#23) |

| `.deb` | sha256 |
|---|---|
| `keel-nodejs-24_24.22.3+keel1_amd64.deb` | `467553af…4b54` |
| `keel-nodejs-24_24.22.2+keel1_amd64.deb`, test material only, never publish | `018b09c5…2466` |
| `keel-nodejs-26_26.0.0+test1_all.deb`, an empty package of a later line, test material only | `722f2a47…be27` |

The package `keel-nodejs-24` passes 49 bats tests, coverage 98.41 percent
of `debian/upstream`, shellcheck, and lintian with no tag. It has
Provides `keel-nodejs` and Conflicts `keel-nodejs, nodejs, npm`.

## Results

The logs are in `repos/nodebb-hand-tests/` of the workstation. They hold
no password, no secret value and no token. A secret shows only as the
first 12 hex digits of its sha256.

| Test | Result | Log |
|---|---|---|
| The overlay of `ef609a8` and a second run of `45nodebb` | pass: the table `keel_nodebb_secret` has one row of 64 characters, owner `nodebb`, no right for PUBLIC; the row and `config.json` hold the same value | `100-phase2-overlay.log` |
| Where the secret is | pass: in the environment of `app.js`, and `/proc/PID/environ` is mode 0400, owner `nodebb`; `config.json` is 0640 root:nodebb; 0 of 42 processes have it in their arguments; 0 lines of the journal of this boot hold it | `101-secret-env.log` |
| A session made before a restart works after it | pass: login 200, uid 1 before and after `systemctl restart nodebb` | `101-secret-env.log` |
| NodeBB takes the secret from the environment, not from `config.json` | pass: with another value in the row and the same `config.json`, the session of step b is refused (uid 0); with the first value back, it works again (uid 1) | `101-secret-env.log` |
| `keel-nodejs` 24.22.3+keel1 replaced by `keel-nodejs-24` 24.22.2+keel1 | pass: apt removes `keel-nodejs` and installs `keel-nodejs-24`; the path unit runs 2 times (removal, install); NodeBB serves on v24.22.2 with a new process 7 s after apt ends | `110-lines-and-restart.log` |
| Upgrade `keel-nodejs-24` 24.22.2+keel1 to 24.22.3+keel1 | pass: the path unit runs 1 time; a new process 8 s after apt ends; its binary is the new one (sha256 `a7ec1b37…`, no `(deleted)`); a new topic passes | `110-lines-and-restart.log` |
| apt simulation of `keel-nodejs-26` | pass: `Remv keel-nodejs-24`, `Inst keel-nodejs-26` | `110-lines-and-restart.log` |
| `dpkg -i` of `keel-nodejs-26` while line 24 is installed | pass: dpkg refuses, "conflicting packages - not installing keel-nodejs-26" | `110-lines-and-restart.log` |
| `apt-get install keel-nodejs-26` | apt removes line 24 with no question; NodeBB stops, and `serve.py` tries again every 5 s (exit 127) | `110-lines-and-restart.log` |
| `apt-get install keel-nodejs-24` again | pass: apt removes line 26; NodeBB serves with a new process 6 s after apt ends | `110-lines-and-restart.log` |
| CI of keel-nodebb#23 at `403d5a7` | `tests`, `python`, `commission` and `package` pass on the runners; `appliance` fails because `https://mirror.keellinux.org/layers/nodebb.manifest` answers 404 (task 18810) | Forgejo tasks 18808 to 18814 |

## Facts found

1. **keel renders a manifest secret that the spec declares.**
   `secrets.nodebb_secret` of a spec becomes `KEEL_SECRET_NODEBB_SECRET`
   in the conf of the first boot (`keel/spec/secretstore.py`). The first
   test report said that keel renders only three secrets. That was wrong.
2. **keel has no general path that gives one generated value to both
   nodes of a pair.** `shared: true` is only validated. Only the Anubis
   key and the replication credential have such a path, each written for
   itself. The NodeBB layer does not need one: the database carries its
   secret. This is a known gap of keel, not work of this test.
3. **NodeBB reads the environment before `config.json`.** `app.js` calls
   `nconf.argv().env()` before it loads the file. The test of the
   refused session proves that NodeBB uses the value of the environment.
4. **A path unit sees the binary that dpkg puts in place.** dpkg writes
   the new file and renames it over `/usr/lib/keel-nodejs/bin/node`.
   `PathChanged=` starts the restart unit at the removal and at the
   install.
5. **apt removes the package of the other line with no question.** An
   operator who installs `keel-nodejs-26` stops NodeBB. The layer names
   its line in its plan, so only a deliberate act of an operator does
   this.
6. The CI check `appliance` cannot pass before a nodebb layer is
   published. Its parent check was never reached: the mirror has no
   nodebb layer at all.

## Defects of the test method

- `secret-check.sh` counted the processes with `ps -eo args | grep`, and
  that grep held the secret in its own arguments: it counted 1.
  `argv-check.py` read the secret from a pipe and skipped itself: 0.
- Step d of `secret-check.sh` gave the secret to `psql -c` as an
  argument, for less than one second, to put the first value back.
- The rerun of `45nodebb` on this CT made a new secret, because the CT
  had no row. So the sessions of the first test ended one time.
- The packages of repository C stay in `/srv/keel-local` of the CT.

## Not tested

- A promote of a pair: a login that survives it is a claim of the design,
  not a result. It needs the pair test of the commissioning (0075).
- A replica: its first boot writes `config.json` only and never writes
  the row.
- A build of the layer with `bt-layer`, an image, BR2, an IPv6-only node.
- The CI job `build` of keel-nodejs#1 on `keel-lxc`.
