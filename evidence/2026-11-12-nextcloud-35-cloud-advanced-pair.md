# Nextcloud 35 on an LNMP pair in cloud advanced: the second test by hand

Date: 2026-11-11 and 2026-11-12 (UTC)

This file is the evidence for the places marked "(second test)" in
decision note 0087. It is a test by hand. The published LNMP image made
the pair, and the first boot hook of the prototype `keel-nextcloud`
installed Nextcloud on it by hand. No `keel-nextcloud` image exists. It
is not a commissioning test (0075).

## The questions

1. Does the design of 0087 work on a real pair across two sites: one
   Redis on each node, only the writer serves, the values of the pair
   from shared secrets?
2. What happens at a failover: the time, the sessions, the app
   passwords, an upload in progress, the locks, the Syncthing folder?
3. What does the front of keel-web (Anubis and Coraza) do to WebDAV and
   to the sync clients?
4. What do 250 ms of RTT between the sites cost?

## The machines

| Item | Value |
|---|---|
| Topology | cloud advanced as in the release tests: adv-primary CT 9381 and the Core witness CT 9383 on BR1, adv-replica CT 9382 on BR2 |
| How it was made | `keel-commission` of Keel-Linux/.github `482feeb`, the contract of Keel-Linux/keel-lnmp `3251cb4`, pass `cloud_advanced`, `--keep`. Result: PASS, 117 checks (`ca1/run.log`) |
| Images | `debian-13-keel-lnmp_19.0-6_amd64.tar.zst`, sha256 `f8743dcb434f2ecea01b153e34b6cda028a9aac580cbd7236f2adcff5ef3f141`, the same on BR1 and BR2; witness `debian-13-keel-core_19.0-13_amd64.tar.zst` |
| Packages | keel 0.23.96, keel-web 0.4.2, anubis 1.27.0-0+keel4, syncthing 2.1.6+keel1, coreruleset 4.25.1-0keel1, keel-overlay-coraza 0.1.4, mariadb-server 1:11.8.6-0+deb13u1, php8.4-fpm 8.4.27-1~deb13u1, redis-server 5:8.0.2-3+deb13u3 |
| Containers | 2 cores, 4096 MiB, 8 GB disk each |
| Mesh | VIP `fd23:2b45:279c::ffff:1`; RTT 9381 to 9382 over the mesh 3.5 to 6.7 ms (mean 4.6 ms) |
| Nextcloud | 35.0.2, the tarball of the first test (same sha256) |
| Prototype | Keel-Linux/keel-nextcloud, local repository, commits `d271fff`, `14d44df`, then the gate of `2af0c6f` and `cbf7190` (the overlay files were copied into the nodes) |

The logs are in `repos/nextcloud-hand-tests/t2/` of the Keel folder on
the workstation of the maintainer. Each section names its log. The
shared secrets were made on 9381 in a root-only file and went to 9382
by a pipe between the two hosts. A scan inside each container found no
secret value in any log (`scan-t2.log`).

## A stand-in for the replicated path

The LNMP image has no manifest of Nextcloud, so Syncthing replicates
only the default path of Web, `/var/www/keel-default`. The test did not
change a manifest of keel. It put the data directory of Nextcloud inside
that replicated folder, as a stand-in for the path of the manifest
(`/var/lib/nextcloud/data`):

- Nextcloud refuses a data directory whose path goes through a symbolic
  link: "Following symlinks is not allowed" (log 21).
  `/var/www/keel-default` is a link to `/usr/share/keel-web/default-site`,
  so the test used the real path `/usr/share/keel-web/default-site/ncdata`.
- The folder of keel takes the owner of the parent directory
  (`copyOwnershipFromParent`), and the parent here is root's. So the
  files arrived on 9382 as `root:root` (log 23). For the test they were
  given to `www-data` by hand once. The path of the manifest is owned by
  `www-data` in the image, so the real design gets `www-data`, as the
  WordPress folders do (keel#225). After the first failover keel
  restored the owner on 68 entries (log 36).
- `custom_apps` was not replicated in this test.

## The first boot hook of the prototype (logs 21, 22, 25)

| Node | Result |
|---|---|
| 9381, primary | code 0, 29 s; schema, install, the password of the administrator from the environment, the settings of the node, the cron mode; `instanceid` made from the shared secret; the gate emptied Redis and opened the site |
| 9382, replica, first run | refused: `occ config:import` cannot start while the data directory has not arrived ("Your data directory is invalid") |
| 9382, after the fix | code 0, 1 s; a whole `config.php` written with no `occ`; nothing written to the database; the gate closed; `occ status` works; every URL 503; the cron unit does not start (`ConditionResult=no`) |

Two defects of the prototype were found here and fixed in `14d44df`:
the replica path above, and the install log, which the install wrote
into the data directory before the log setting came.

## The front of keel-web: Anubis and Coraza (logs 27, 28, 29, 31)

A client on the witness, through the VIP, with an app password:

| Request | Result |
|---|---|
| `/status.php`, `/` with curl | 200, 302 |
| `/` | 302 to **`http://`**`nc.test/login` on a request to port 443 |
| `/login`, browser user agent | 200, the Anubis challenge page |
| PROPFIND, PUT | **403**: Coraza, rule 911100 ("Method is not allowed by policy"); then rule 920340 for a PUT with no Content-Type |
| PUT and GET of 100 MiB, before the rule-set plugin | timed out after 60 s, and a 504 |

**The container ran out of memory.** One worker of nginx, which served
the PUT and the GET of 100 MiB while the rule set read the body, grew to
3.5 GB of RSS. The container (4096 MiB) had 31 MiB free and full swap,
load 28, and MariaDB did not answer (log 30). The worker was an old one
that later reloads had asked to stop. `kill -9` of that one process
gave the memory back (567 MiB used).

The test then added two files, which are now in the prototype:

- `/etc/coreruleset/plugins/keel-nextcloud-before.conf`: on the DAV paths
  only, the DAV methods are allowed, and the body of a DAV PUT is not
  read (`ctl:requestBodyAccess=Off`), and rule 920340 does not apply to
  that PUT.
- `/etc/nginx/keel-front.d/60-keel-nextcloud.conf`: the paths of the sync
  clients go from the front to the app socket with no Anubis.

| Request, after both files | Result |
|---|---|
| PROPFIND, user agent `Mozilla/5.0 (Linux) mirall/3.15.0` (desktop), before the front file | 200 with the Anubis page, no DAV answer; the same for the Android and iOS agents |
| the same, after the front file | 207 |
| PUT 100 MiB | 201 in 12.7 s through Anubis; 201 in 2.0 s past Anubis; GET returns the same sha256 |
| `/login`, browser agent | 200, the Anubis challenge (the browser keeps it) |

A fix for the scheme was tried and did not work: the route trusted
`X-Forwarded-Proto` on requests from the app socket only (log 42).
`overwriteprotocol = https` makes the redirect on 443 correct, and it
also sends port 80 to `https://` while the certificate is self-signed
(0079).

## The unplanned failover (logs 30, 32, 33)

The memory starvation above made a real failover, which was not planned:

| Time (UTC) | Event |
|---|---|
| 00:10:06 | 9381: "no renewal the majority confirmed for 6 s: this node may be cut off" |
| 00:10:55 | 9382: "drained and promoted"; owner restored on 6 entries; folder primary |
| 00:11:00 | 9382: the gate emptied Redis and opened the site |
| 00:11:44 | 9381: read only; its gate closed the site |
| 00:12:47 | 9382: read only for 2 s (lease doubt); its gate closed at 00:12:48 |
| 00:14:56 | 9382: "the replica did not connect within 30 s, so this node takes writes without it"; read_only off; its gate opened again |
| 00:14:59 | 9382: VIP "dropped, no renewal the majority confirmed for 15 s" |
| 00:15 to 00:19 | 9381: replica of 9382, fence cleared at 00:16:00. 9382: writable, gate open, but no node carried the VIP; the cron unit ran on 9382 at 00:15:06 |
| 00:19:12 | 9381: "drained and promoted", VIP epoch 5; its gate opened at 00:19:15 |
| 00:19:17 | 9382: read only; its gate closed |

After it the two nodes had the same GTID position
(`0-1963892930-2979`), and 9382 replicated from 9381 with no error.
For about 5 s (00:19:12 to 00:19:17) both databases may have taken
writes; the test did not measure which writes came in that window. This
is a behaviour of keel under a starved node. It is recorded here for
the keel maintainers and is not a defect of Nextcloud.

## The planned failover (log 36)

The client on the witness logged in with a cookie (browser login, curl
agent), started a PUT of 200 MiB at 2 MB/s, and asked the VIP each
second for `status.php`, PROPFIND with the app password, and the files
page with the cookie. 9381 was then stopped hard (`pct stop`).

| Time (UTC) | Event |
|---|---|
| 00:21:56.4 | `pct stop 9381` started (it returned at 00:22:00.1) |
| 00:22:07 to 00:22:17 | no answer from the VIP |
| 00:22:19 to 00:22:30 | 503 from 9382 (its gate closed) |
| 00:22:30 | 9382: the gate emptied Redis and opened the site |
| 00:22:31.8 | 200, 207, files page 200 with the old cookie |
| 00:22:38 | 9382: keel logs "drained and promoted", the folder primary, the owner restored on 68 entries |

- The service came back 35 s after the stop started.
- The browser session of 9381 works on 9382 with the same cookie, and
  the app password works: same `secret`, the token in the replicated
  database, an empty Redis.
- **The gate opened 8 s before keel finished the role change.** A PUT at
  00:22:35 wrote a file while the folder was still receive-only. The gate
  of the prototype then opened on `read_only = 0` only. Later commits make
  it also wait for `role=primary` in the role file and for the VIP on a
  local interface (see "The gate: zero time with two open gates").
- The upload in progress broke at the client after 35 MB (code 000). No
  partial file was left (PROPFIND of the path: 404). A new PUT to the same
  path: 201, so no lock was left.
- A file uploaded before the failover was served by 9382 (GET 200).

## Back to the first node (logs 37, 38, 39, 40)

- 9381 started again: read only, gate closed, "fenced". Its role file
  still said `role=primary` (no demote ran after the hard stop), so the
  role file alone cannot open the gate. It replicated from 9382 and had
  caught up about 80 s after its start; the file uploaded after the
  failover had reached it.
- `keel vip promote` on 9381: its gate emptied Redis and opened 8 s after
  the command started.
- **A stale cache was not seen.** 9382, back to replica, still held 24
  Redis keys from its time as writer. With its gate timer stopped,
  9382 was promoted and the route opened by hand with no flush: the
  site served the newest value of the setting (theming name), as after
  the flush. The flush stays as a precaution; this probe did not show the
  risk.
- **A stale lock was not seen.** No lock key was in Redis during a slow
  PUT of 50 MiB: nginx buffers the whole body before PHP runs
  (`fastcgi_request_buffering on`), so Nextcloud takes its lock after the
  body arrived. After a promote in the middle of that PUT, no lock key was
  left.

## Syncthing (logs 23, 35)

- The data directory was made after Syncthing watched the folder. The
  watcher did not report it, and the rescan interval is 3600 s; a manual
  scan sent 72 files in about 10 s.
- After that, a new file uploaded through the VIP was on 9382 after
  about 5 s, owned by `www-data`, with no manual scan.

## 250 ms between the sites (log 41)

netem put 125 ms on eth0 of 9381 and of 9382 (ping over the mesh
254.6 ms). The requests went from 9381 to its own front on the loopback,
so only the replication of the database and Syncthing crossed the slow
link. Semi-sync stayed on (`Rpl_semi_sync_master_yes_tx` 97 during the
run).

| Request | 0 ms | 250 ms |
|---|---|---|
| `status.php` | 0.03 s | 0.03 s |
| PROPFIND depth 1 | 0.07 to 0.90 s | 0.32 to 0.33 s |
| PUT 1 KiB | 0.14 to 0.59 s | 2.41 to 2.47 s |
| MKCOL | 0.11 to 0.13 s | 1.64 to 1.65 s |

The first run at 0 ms includes a cold cache. Each commit waits for the
replica, so a write that commits several times pays the RTT several
times. The VIP did not move during the run.

## The gate: zero time with two open gates (logs 43 to 46)

The pass criterion of the coordinator: no time at which the gates of
both nodes are open. A monitor on each node logged the gate mark,
`read_only`, the VIP on `wg0` and the role file, every 0.5 s (log 44)
and then every 0.2 s (log 45), during `keel vip promote` to 9382 and
back. The clocks of both containers come from their hosts.

| Gate version | Promote to 9382 | Promote back to 9381 |
|---|---|---|
| `2af0c6f`: timer of 5 s, conditions `read_only = 0`, `role=primary`, VIP on a local interface (log 44) | old gate closed 00:43:51.4, new gate opened 00:43:56.5: no overlap | new gate opened 00:44:36.617, old mark still there until 00:44:36.686: **about 70 ms with two open gates** (FAIL) |
| `cbf7190`: the same, plus a pass at each address event (`ip monitor address`) (log 45) | old gate closed 00:47:48.65, 0.25 s after the VIP left; new gate opened 00:47:53.62: no overlap, 5.0 s with both closed | old gate closed 00:48:29.03, 0.4 s after the VIP left; new gate opened 00:48:31.69: no overlap, 2.7 s with both closed |

With `cbf7190` the time with two open gates was zero in both directions.
keel moves the VIP itself with no overlap (log 44: it left 9381 at
00:43:48.7 and was on 9382 at 00:43:49.3), and the new holder opens only
after the VIP, `read_only` and the role file agree, seconds later.

**A writable node with no VIP** (log 46). On the holder 9381 the VIP was
removed from `wg0` by hand (`ip address del`). The gate closed within
0.3 s (00:49:56.5). keel put the VIP back within about 0.3 s, and the
gate opened again (with a flush) at 00:49:56.8. A client on the witness,
one probe per second, saw no change: the window was shorter than the
probe step. The case of the unplanned failover (4 minutes with no
holder) could not be made by hand while keel restores the VIP, so it is
not reproduced; with the VIP condition the gate is closed in it, by its
rule. What a client gets when no node carries the VIP: no answer at the
VIP (no node has the address), and 503 at each node.

## The memory of nginx under Coraza (logs 30, 47, 48)

The facts of the defect:

| Item | Value |
|---|---|
| Container | 4096 MiB of memory, 1024 MiB of swap (9381) |
| Coraza | `coraza on` for every server of nginx (`/etc/nginx/conf.d/keel-coraza.conf`), so a request through the front is read twice: by the front and by the app server behind Anubis |
| Rules in use | `SecRequestBodyAccess On`, `SecRequestBodyLimit 134217728` (128 MiB), `SecRequestBodyInMemoryLimit 131072`, `SecRequestBodyLimitAction Reject`; no `SecResponseBodyAccess` line; the Core Rule Set 4.25.1 |
| What grew | one worker of nginx, 3.5 GB of RSS, started at 23:55:22. It served the run of 00:05: a PUT of 100 MiB that the client stopped after 60 s with no answer (the PUT of 1 KiB just before it was refused by rule 911100), and a GET of 100 MiB that ended with 504 |
| Effect | 31 MiB free, swap full, load 28, MariaDB did not answer, keel moved the VIP |

With the plugin of the prototype (no body access for a DAV PUT) on 9381,
through the VIP (log 47):

| Step | RSS of the biggest worker |
|---|---|
| before | 66 MB |
| after one PUT of 100 MiB (201, 2.3 s) | 87 MB |
| after four GETs of 100 MiB (200, 1.1 to 1.2 s each) | 87 MB |

With body access turned on again for the DAV PUT (the methods still
allowed), a PUT of 10 MiB of random bytes with
`Content-Type: application/octet-stream` was refused with 403 in 0.14 s
by rule 920420 ("content type is not allowed by policy") and anomaly
rule 949110; the worker grew by 9 MB (log 48). So with body inspection a
binary upload is refused, and the growth to 3.5 GB was not reproduced
in this step. Its exact cause is not isolated. The plugin was put back
after the step.

## Not tested here

- The `keel-nextcloud` image, its build, and the manifest paths with
  Syncthing (only the stand-in path above).
- `custom_apps` on Syncthing, an app installed on a pair, an `occ upgrade`
  on a pair.
- A real desktop or mobile client (only their user agents), the Login
  Flow v2, chunked uploads at a failover, CalDAV and CardDAV.
- A failover at 250 ms RTT, lossy profiles, and a site cut by the
  network instead of a stopped container.
- Large data, and the scale-out of 0081.
- The third site (BR3 is down; the witness is on BR1).
