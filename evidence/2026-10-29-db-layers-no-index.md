# postgresql and redis layers on the stable 1 core, with no index

Date: 2026-10-29
Decision: 0072 (handbook#146, merge `eff9f6f`), option (c) of the
maintainer: postgresql and redis now, mariadb later on its own path.
Tooling: apt#72 (merge `3f04b1b`), `keel-release --no-index`.

## Result

| Item | Result |
| --- | --- |
| keel 0.23.61 in the pool `stable-1` | done, `keel-pool verify stable-1`: 621 members, 0 bad |
| Build, `--no-index` | postgresql 19.0-7 and redis 19.0-10, signed with main and images, no `pve/`, MANIFEST says `index none` |
| Stable package check | `keel-stable check` exit 0 on both `.packages` files |
| Release test, 2 CTs on BR1 + 1 on BR2, netem | pass |
| Bind address (keel#233) | the overlay address is bound with `listen: ["::1", "127.0.0.1"]` on both nodes |
| PostgreSQL pair, replication | streaming, `sync`, TLS, across BR1 and BR2 |
| Planned failover and failback, under netem | pass, 41 of 41 rows on both nodes, 0 lost |
| Redis boot and service | pass |
| Publication, `--no-channels` | exit 0 in 25 s |
| Proxmox index before and after | `6bb9c0fb8f3fd1cfa58da9d1aec52f85d454bf4c4da9ebc25174324534d890a5`, the same |
| Stable pointer before and after | `055bc0346ea413a15bd7429749e4824e6f7e7ec8ec8a6cb321353fc6b16c7613`, the same |
| Parent of both layers on the mirror | core `1c5dc3b1f5edece31b15e84576fa62dba0e38986d85913e4de059c58c984c7a7` |
| Build host and mirror | the same sha256 for each layer file |
| Appliance check | pass on keel-postgresql#22 and keel-redis#20, no change to branch protection |

## 1. The pool

The pool `stable-1` had keel 0.23.56. In 0.23.56, `bind_addresses` in
`keel/system/dbpair.py` returns the declared `listen` and the VIP only.
0.23.61 adds the overlay addresses (diff of the two packages on the build
host). The line in `dists/stable-1/files` was replaced, as in section 9.2
of the stable-1 plan:

```
< keel 0.23.56 all b4c1102f75043fbffa947e7274874b5c0145bd91343ecc18f2d6ec27b4272878 pool/main/k/keel/keel_0.23.56_all.deb
> keel 0.23.61 all 4aa318ba3de930430d20297e82920555ac827f76a5e6c958597867a4d8f6aaf5 pool/main/k/keel/keel_0.23.61_all.deb
pool stable-1: wrote the index of 621 packages
pool stable-1: 621 members, 0 bad
```

The sha256 of the `.deb` is the same in `/srv/keel-pool/pool`, in
`/srv/keel-apt/repo` and in `trixie` on archive.keellinux.org. The
`Depends` line of keel did not change. The new `Release` has sha256
`ce0e1f54e8b46a886cf28f5c656a81a7e1eeeceb4969e1acdf76bc609a010800`.
keel-mariadb is not in this pool. It is not part of this release.

## 2. The build

The stable 1 tree on the build host got the two products at the heads of
Git: keel-postgresql `d1d9766`, keel-redis `e9f1365`. common stays
`84ff6a2`. Neither 19.0-7 nor 19.0-10 was published before, so no
changelog entry was needed.

```
env KEEL_APT_TRACK=stable KEEL_POOL_ID=stable-1 \
    KEEL_FAB_PATH=/srv/keel-stable1/fab KEEL_PRODUCTS=/srv/keel-stable1/products \
    KEEL_LAYERS_DIR=/srv/keel-stable1/builds/layers \
    KEEL_GIT_BASE=https://git.pop.coop/Keel-Linux \
    keel-release --no-index --wait 3600 --date 2026-10-29 postgresql redis
```

The first run (22:08 UTC) built postgresql and stopped at redis:
`conf.d/main` did not find `/etc/redis/redis.conf.d/10-keel-bind.conf`.
The redis recipe needs its component in `unit.d/redis`, a clone that Git
ignores, and the stable 1 tree did not have it. The clone was added from
`git.pop.coop/Keel-Linux/unit-redis` at `v1.0.4`, commit `afc121c`. This is
the same commit as in the CI tree, and the published redis layer records
`units redis@1.0.4`. The second run, with `--resume` (22:20 UTC), finished:

```
keel-release: no-index: no pve/aplinfo.dat; the Proxmox index on the mirror stays as it is
keel-release: debian-13-keel-postgresql_19.0-7_amd64.tar.zst.sha512: signed
keel-release: debian-13-keel-redis_19.0-10_amd64.tar.zst.sha512: signed
keel-release: MANIFEST: signed
release 2026-10-29 staged in /srv/keel-release/2026-10-29, signed: yes subkey 03041024F4B2C0C2F42DDDEA04906EAB77513310 39DAE662C4726AC7A66C250BEF26DA5C869ECDC7
```

| File | sha256 |
| --- | --- |
| `layers/postgresql.manifest` | `73b887a40ecb62afdaa86aff80b9fec3e34e4af4bbbf741596f99c911cc12263` |
| `layers/postgresql.tar.zst` | `974c240ddccb0b13be91829b875f95abb0f76acf4076b78daff1f67ee569f38c` |
| `layers/redis.manifest` | `ed87f376d2e278f81ef47803bd91558fb6dff12dbc85ab1ec594233ca6290e19` |
| `layers/redis.tar.zst` | `214ac90593a05738e56d9f50bc80a11393afbbce20f3a5b99509f945ff41bc5b` |
| `images/debian-13-keel-postgresql_19.0-7_amd64.tar.zst` | `e39b11bb87f5df72d758afc0b6dcc265b427a73d5b6e8f19bfb954c4aaaa6646` |
| `images/debian-13-keel-redis_19.0-10_amd64.tar.zst` | `28244d24788fe1a9d683c0138e061ef730a9228801b3f62256695b97f52ba207` |

The MANIFEST has `index none`, no `index_base` and no `pve/` line. Both
layers have `parent_sha256 1c5dc3b1…` and keel 0.23.61. The core layer
keeps keel 0.23.56. `keel-stable check` with the `trixie` and
`trixie-testing` indexes and the two `.packages` files: exit 0. Neither
file has keel-mariadb, syncthing, keel-overlay-syncthing or keel-web.

## 3. The release test

CTs 9300 (A, postgresql) and 9301 (W, redis) on `hw12-br1`, CT 9302 (B,
postgresql) on `nfs1-br2`, from the two templates above (sha256 checked on
each host). All three: keel 0.23.61, 0 failed units after the first boot.
`installation.mode: cloud_advanced`. The mesh, etcd and the VIP come from
`keel` commands only.

### Mesh and etcd

```
created the mesh: this node is fd31:d04:4025::1/64 on wg0
joined the mesh: this node is fd31:d04:4025::b181/64 on wg0        # W, BR1
joined the mesh: this node is fd31:d04:4025::e280/64 on wg0        # B, BR2
etcd: 3 voter(s), 0 learner(s)   all healthy, leader keel-fd31-d04-4025--1
```

The first invite failed, because my shell quoting broke the token. The
next invites gave the token on standard input.

### Pair and bind address

`appliance.vip: fd31:d04:4025::ffff:1`. `keel vip pair fd31:d04:4025::e280`
on A: signed by both. `keel vip promote` on A: epoch 1. Then
`database.server` with `engine: postgresql`,
`listen: ["::1", "127.0.0.1"]`, on A as primary, then on B as replica. The
overlay address is not in `listen`, on purpose.

```
A: listen_addresses = '::1,127.0.0.1,fd31:d04:4025::1,fd31:d04:4025::ffff:1'
B: listen_addresses = '::1,127.0.0.1,fd31:d04:4025::e280,fd31:d04:4025::ffff:1'
```

`ss -ltn` showed 5432 on the four addresses on each node. With keel
0.23.56, the overlay address would be missing.

B refused to follow at first: each image ran its own `initdb`, so B held
transactions that A did not have. `keel spec apply --system-only
--destroy-local-database` on B, the documented step, reseeded it in 15 s:

```
A: keel|fd31:d04:4025::e280|streaming|sync|t        (pg_stat_replication, ssl)
A: synchronous_standby_names = FIRST 1 (keel)
B: pg_is_in_recovery t, walreceiver streaming from fd31:d04:4025::1
```

### Planned failover and failback, under netem

`tc qdisc replace dev eth0 root netem delay 250ms 25ms loss 1.5%` in CT
9302 (the egress of B). Overlay RTT from A to B: 230.6/251.2/276.8 ms
(min/avg/max). A synchronous commit took 2094 ms, including ssh and `pct
exec`.

| Step (UTC) | Result |
| --- | --- |
| 22:40:54, 21 writes on A | 21 rows on A and B; a write on B: `cannot execute INSERT in a read-only transaction` |
| 22:42:01, `keel vip promote` on B | released by A; epoch 2; promote 7 s; B writable after 9 s |
| A rejoins B | A is fenced, dumped, then reseeded from B with no flag (`the reseed is cheaper than the rewind: pg_rewind would copy about 32 MB, which is 274 s at 120 kB/s, and the reseed about 4 MB`); A streams from B 138 s after the promote |
| 10 writes on B | 31 rows on both nodes; B shows A `streaming`, `sync`; a write on A refused |
| 22:45:11, `keel vip promote` on A | released by B; epoch 3; promote 6 s; A writable after 8 s |
| B rejoins A | reseed with no flag, same reason (377 s at 87 kB/s for a rewind); B streams from A 42 s after the promote |
| 10 writes on A | 41 rows on both nodes: A-back 10, A-before 20, A-timed 1, B-after 10 |

After the test, `keel diff` on A and B: `no drift`. Failed units: 0 on
both. Netem was removed at 22:47 UTC.

### Redis

On W: `redis-server` active and enabled, `bind ::1 127.0.0.1`, 6379 on
both loopbacks. The default user may run `INFO` only: `GET` gives
`NOPERM`, by design (`20-keel-acl.conf`). `firstboot.d/35redispass` with a
test password (made in the CT and never printed):

```
Redis account 'admin' set from DB_PASS (32 characters), verified on [::1]:6379; a client with no secret is refused every key
SET keel-test ok -> OK; GET on 127.0.0.1 -> ok; after systemctl restart -> ok
no credential: NOPERM User default has no permissions to run the 'get' command
50-keel-secret.conf: root:redis 640, 1 user line
```

## 4. Publication

From the workstation, `bin/keel-publish-mirror --no-channels 2026-10-29`
(apt `3f04b1b`), exit 0 in 25 s. It printed "checking that the staged
Proxmox index was merged onto the one the mirror serves", then installed
release revision `2026-10-29/1`. `keel verify` checked the layers that the
mirror serves. The three archive tracks verify.

| Check | Before (22:47 UTC) | After (22:48 UTC) |
| --- | --- | --- |
| `releases.keellinux.org/pve/aplinfo.dat` | `6bb9c0fb…d890a5` | `6bb9c0fb…d890a5` |
| Index records | core, lnmp, lnpp, ntfy, web | the same |
| `layers/stable` | `055bc034…6c7613` | `055bc034…6c7613` |
| `layers/postgresql.manifest` | `0fa563bd…` (old parent) | `73b887a4…`, the same as the build host |
| `layers/redis.manifest` | `4aca7fc2…` (old parent) | `ed87f376…`, the same as the build host |

The two `.tar.zst` files of the layers and `core.manifest` have the same
sha256 on the mirror and on the build host. The build host record
`/srv/keel-release/published/pve/aplinfo.dat` is still `6bb9c0fb…`, from
release 2026-10-26: this publication recorded no index. The two templates
are on `mirror.keellinux.org/images/` (HTTP 200), and no index lists them.

## 5. The appliance gate

No PR was open on either repository. A PR with one empty commit on a
Keel-Linux branch ran the gate, and was closed without merge:
keel-postgresql#22 and keel-redis#20. Branch protection was not changed.

```
keel-postgresql run 17: the gate recorded published=true
  manifest says parent core, the caller declares core
  22:50:45 boot-test: postgresql boot test passed
keel-redis run 9: the gate recorded published=true
  manifest says parent core, the caller declares core
  22:50:37 boot-test: redis boot test passed
```

package, tests and appliance: success on both.

## 6. Clean up

CTs 9300, 9301 and 9302 are destroyed (`pct destroy --purge`). The
templates copied to `hw12-br1` and `nfs1-br2` are removed. The test did not
touch CTs 9310-9319. The pool backups `*.before-keel-0.23.61` stay on the
build host.

## Open

- mariadb: not in this release. Its promotion and its entry in the pool
  are another task.
- The stable 1 tree did not have `unit.d/redis`. `/srv/keel-stable1/sync`
  removes it with `git clean -ffdx -e /build`. A later sync of keel-redis
  must clone it again.
