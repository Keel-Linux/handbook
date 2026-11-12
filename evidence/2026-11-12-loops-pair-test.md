# Loops 1.0.0-beta.15 on an LNMP pair in cloud advanced: the first pair test

Date: 2026-11-12 (UTC)

This file is the evidence of the first pair test of Loops (decision note
0086). It is a test by hand. The published LNMP image made the pair, and
the overlay of the prototype `keel-loops` put Loops on it by hand. No
`keel-loops` image exists. It is not a commissioning test (0075). The
nodes did not federate with a real server, and no public client reached
them.

The logs are in `repos/loops-hand-tests/t2/` of the Keel folder on the
workstation of the maintainer. Each claim names its log. No secret value
is in a log: a scan for an APP_KEY, a token and a private key found none.
The secrets were compared as "equal: yes or no" only.

## The questions

1. Do the install, the first boot hook and the shared secrets work on a
   pair?
2. Does the writer serve: a login, an upload, the transcode, the feed,
   the ActivityPub endpoints?
3. Do the nodes that do not serve answer 503 with the notice, and run no
   worker?
4. How long does a 20 MB video take to reach the other node, at the
   normal link and at 250 ms with loss?
5. What do a promote and a failover cost: the time, Redis, a browser
   session, an API token, a video in the queue, two open gates?
6. Does the old writer rejoin and not serve?
7. What do Coraza and Anubis do to the upload, the API and ActivityPub?
8. How much memory and CPU does a 4 GiB node use?

## The machines

| Item | Value |
|---|---|
| Topology | cloud advanced as the release tests: adv-primary CT 9391 and the Core witness CT 9393 on BR1, adv-replica CT 9392 on BR2. The coordinator approved this mapping of the 3 ids: keel-commission gives the nodes N, N+1, N+2 in the order of the contract |
| How it was made | `keel-commission` of Keel-Linux/.github `482feeb`, the contract of Keel-Linux/keel-lnmp `3251cb4`, pass `cloud_advanced`, `--keep` (`ca1/run.log`). 114 checks passed. The 3 screenshot checks failed: the browser of the workstation opened no DevTools port. The probable cause is the temporary folder of the run, which the test set inside the Keel folder (inferred, not checked) |
| Images | `debian-13-keel-lnmp_19.0-6_amd64.tar.zst`, sha256 `f8743dcb434f2ecea01b153e34b6cda028a9aac580cbd7236f2adcff5ef3f141`, on BR1 and BR2; witness `debian-13-keel-core_19.0-13_amd64.tar.zst` |
| Containers | 2 cores, 4096 MiB, 1024 MiB swap, 8 GB disk. BR1: Xeon E5-2630 v2. BR2: Xeon E5-2470 v2 |
| Packages | keel 0.23.96, keel-web 0.4.2, anubis 1.27.0-0+keel4, syncthing 2.1.6+keel1, coreruleset 4.25.1-0keel1, mariadb-server 1:11.8.6-0+deb13u1, php8.4-fpm 8.4.27-1~deb13u1, redis-server 5:8.0.2-3+deb13u3, ffmpeg 7:7.1.5-0+deb13u1 (`01-facts.log`, `20-build.log`) |
| Coraza | upgraded by apt from 0.1.4 to **keel-overlay-coraza 0.1.5** on both nodes before every test (`10-apt-coraza.log`). keel-web 0.4.4 was the candidate and was not installed |
| Mesh | VIP `fde4:fee2:c919::ffff:1`; RTT 9391 to 9392 over the mesh 3.3 to 6.5 ms. The clocks of both hosts were within 6 microseconds of NTP (`31-promote-old-gate.log`) |
| Loops | `v1.0.0-beta.15`, commit `0d2a881e`, built once on 9391 |
| Prototype | Keel-Linux/keel-loops `main` at `f7b3207` first, then the branch of Keel-Linux/keel-loops#1 at `7d174e8` (`proto-*.rev`). A later commit of that branch, `8be8ae6`, keeps the Redis of a standalone node; it did not run on a machine, and the path of a pair node is the same |
| Instance | name `Keel Loops t2`, url `https://loops.keel.test` (a name in `/etc/hosts` only), federation on |

## 1. Install, first boot hook, shared secrets

**Result: pass, after 3 defects (2 fixed in Keel-Linux/keel-loops#1).**

The plan packages came from Debian 13. Steps 1 to 9 of `conf.d/main` ran
on 9391 as root, with the memory set to 6144 MiB for the build and back to
4096 MiB after it (`20-build.log`). The test copied the built tree to 9392
by a pipe between the hosts, with the same sha256 (`21-copy.log`).

- **Defect: step 7 of `conf.d/main` stops the build.** `systemctl
  is-enabled loops-horizon.service` prints `static` and exits 0 for a
  unit with no `[Install]` section, so the check `exit 1` runs
  (`20-build.log`). Fixed: the check compares the word.
- The hook ran by hand after the pairing, as root with the options in the
  environment. `/etc/default/inithooks` sets `INITHOOKS_CONF` again, so an
  `INITHOOKS_CONF` of the caller has no effect. The first run took the
  defaults (`23-hook-primary.log`). The second run took the options:
  code 0, 4.5 s, federation on, 1 administrator.
- The primary hook made 3 rows in `keel_settings`: `app_key`,
  `activitypub_key`, `passport_key`. The declared `app_key` replaced the
  row of the first run. Row and declared secret: equal.
- `app_key` is a shared secret (`shared: true`). The test made it on 9391
  in a root-only file and sent it to 9392 by a pipe, as a stand-in for
  keel (`22-secrets.log`).
- **Defect: the replica hook wrote an old APP_KEY.** The hook of 9392 ran
  at 08:05:11, code 0, 12.5 s. The replica was then 90 to 127 s behind the
  primary and had 75 of 100 tables. It caught up at 08:06:45, about 150 s
  after the migrations of the primary (`25-replica-catchup.log`). The key
  pairs were equal, the APP_KEY was not (`24-hook-replica.log`). The gate
  wrote the rows again when 9392 first served: then all keys were equal.
  Fixed: a read-only server takes the declared shared APP_KEY first.
- Modes on both nodes: `.env` 0600, the two Passport keys and the
  ActivityPub private key 0600, the ActivityPub public key 0644, owner
  `www-data`.

**The replicated path of the manifest.** The spec of both nodes changed
from `appliance.name: lnmp` to `loops`, and `keel spec apply
--system-only` ran (`27-spec-loops.log`). keel made a second Syncthing
folder for `/var/www/loops/storage/app/public`, send-only on 9391 and
receive-only on 9392. **Defect of keel:** the first apply on each node
ended with code 16: "write .../.stfolder ... failed: Is a directory".
Syncthing 2.1.6 had made `.stfolder` as a directory when keel restarted
it, before keel wrote its marker file. The second apply ended with code 0.
`keel diff` also says that it cannot infer `database.server` on a node
with MariaDB and Redis ("2 database servers") (`27-spec-loops.log`).

## 2. The writer serves

**Result: pass.** A client on the witness asked the VIP (`43-writer-serves.log`,
`44-activitypub.log`).

| Step | Result |
|---|---|
| Registration (`POST /api/v1/auth/register/email`) | **403**, "Mail service not configured": Loops refuses each registration while `MAIL_MAILER=log` in production. The test user `keelt2` was made with `tinker` |
| Web login (`POST /login` with the XSRF cookie) | 200, then `GET /api/v1/account/info/self` with the session cookie 200 |
| Personal access token | `GET /api/v1/account/info/self` 200 |
| Upload of a clip of 5 s, 3.7 MB (ffmpeg on 9391) | 200 in 0.37 s through the front and Anubis |
| Transcode | 13 s; `720p.mp4` H.264 720x1280, 5.0 s, 1.1 MB, and a thumbnail |
| The video plays | `GET` of the 720p file 200 `video/mp4`; a range request 206 |
| Feed | `/api/v1/feed/for-you`, `/feed/local`, `/feed/account/ID`, `/feed/account/self` show the video. `/api/web/feed` (no login) gave an empty list |
| WebFinger, `/ap/actor`, the actor, outbox, followers, nodeinfo, host-meta | 200 with the right types; the actor id, its inbox and its key id are under `https://loops.keel.test/ap/users/ID` |
| `POST /ap/inbox` with no signature | 401 "Missing signature header" |
| `POST /ap/inbox` and the user inbox, signed (Cavage, rsa-sha256) with a new key, `keyId` on a host that does not exist | **202** `{"status":"accepted"}`. Loops checks the signature in a queue job (`ProcessInboxActivityWithVerification`). No failed job and no log line came at level `warning` |

## 3. The nodes that do not serve

**Result: fail with the prototype, pass after the fix.**

| Request on 9392 (replica) | Prototype `f7b3207` (`30-gate-old.log`) | Branch of keel-loops#1 (`32-deploy-fix1.log`, `60-rejoin.log`) |
|---|---|---|
| `/`, `/up`, `/explore`, `/api/v1/feed/for-you` | **200** with the notice (HTML, also on the API) and `Retry-After: 30` | **503**, the notice, `Retry-After: 30` |
| `/up` | **200** (the notice) | 503 |
| `/storage/...` (media) | served | 503 |
| WebFinger | (not asked) | 503 |
| `/keel-loops-up` (loopback only) | did not exist | 200, the same body as `/up` of the writer but for the render time; 403 from the mesh address |
| Horizon, scheduler | inactive | inactive at rest; see the exception below |

**An exception: Horizon after a close.** The gate stops the workers with
no wait. At the promote of 08:48, Horizon on the closed, read-only node
ran for 55 s more to finish a transcode. It wrote a full `720p.mp4` into
the receive-only folder, and its update of the database failed. The
scheduler stopped at once (`50-promote.log`, `52-queue-at-switch.log`).

## 4. Media to the other node

**Result: pass. Slow at 250 ms with loss.** (`46-media-sync.log`, `47-media-netem.log`)

A watcher on 9392 logged each file the first time it had its final name,
every 0.5 s. Each clip had new content, so Syncthing could not take blocks
from a file that it had.

| Link | File | Written on 9391 | On 9392 | Time |
|---|---|---|---|---|
| normal, RTT about 4 ms | original, 20.3 MB | 08:35:56.13 | 08:36:08.95 | **12.8 s** |
| 250 ms ±25 ms, 2% loss | original, 20.1 MB | 08:40:34.95 | 08:43:33.24 | **178 s** |
| 250 ms ±25 ms, 2% loss | 720p, 10.1 MB | 08:41:48.54 | 08:44:54.92 | 186 s |

- netem: `delay 125ms 12ms distribution normal loss 1%` on `eth0` of 9391
  and of 9392 (ping over the mesh 220 to 284 ms, mean 252 ms). The upload
  came from 9391 to its own front, so only the replication crossed the
  slow link. The VIP did not move. netem was removed at 08:45:12, and
  `tc qdisc show dev eth0` then showed `noqueue` on both nodes.
- The sha256 of each file was the same on both nodes.
- Syncthing sent a 48-byte `720p.mp4` while ffmpeg still wrote it, and the
  full file later: Loops writes the transcode to its final name.
- A directory that the upload made after Syncthing watched the folder was
  sent with no manual scan.
- **Files of the last seconds before a failover stay behind.** 9392 wrote
  a thumbnail and a partial `720p.mp4` about 1 s before it stopped. They
  never reached 9391. After the failover the folder of 9391 is send-only,
  and it still "needs" those 2 files and does not fetch them
  (`52-queue-at-switch.log`).

## 5. Promote and failover

**Result: pass for the gate; the sessions and the queue are lost.**
(`31-promote-old-gate.log`, `33-promote-new-gate.log`, `50-promote.log`,
`52-queue-at-switch.log`, `53-failover.log`)

A monitor on each node logged the gate, the workers, `read_only`, the VIP
and the role file every 0.2 s. A client on the witness asked the VIP
every 0.5 to 1 s.

| Switch | Gate | VIP left the old writer | Old site closed | New site open | Client: no 200 | Two open gates |
|---|---|---|---|---|---|---|
| promote 9391 to 9392, 08:09 | prototype | 08:09:20.76 | 08:09:22.85: **2.1 s with `read_only` 1** while it served; Horizon blocked the mark for 1.8 s | 08:09:27.93 | not probed | none |
| promote 9392 to 9391, 08:14 | branch | 08:14:45.69 | 08:14:45.50 (journal) | 08:14:51.83 | 08:14:45.93 to 08:14:51.91, **6.0 s** | none |
| promote 9391 to 9392, 08:47 | branch | 08:48:02.57 | 08:48:03.60 | 08:48:07.17 | 08:48:03.32 to 08:48:07.69, **4.4 s** | none |
| failover: `pct stop 9392`, 08:50:47.4 | branch | (stop) | (stop) | 08:51:20.94 | 08:50:48.07 to 08:51:21.66, **34 s** after the stop started | none |

- At the failover keel put the VIP on 9391 at 08:51:08.8, `read_only` went
  to 0 at 08:51:11.1, and the role file said `role=primary` at
  08:51:18.5. The gate opened 2.4 s later. It waited for all three.
- At the promote of 08:48, the old writer stayed open for about 1.0 s
  after the VIP left, with `read_only` 1. The VIP was already on the other
  node, so no client of the VIP reached it.
- **Redis.** A key put in the Redis of 9391 before the promote of 08:14
  was gone after the gate opened. A restart of `keel-loops-serve` on the
  writer closed the site for 4.1 s and emptied Redis, 31 keys to 0
  (`54-gate-restart.log`).
- **The browser session** was lost at each switch: `/api/v1/account/info/self`
  with the cookie gave 401 on the new writer. The session is in the Redis
  of the old writer.
- **The API token** worked at once on the new writer (200).
- **A video in the queue at the switch stays in "processing".** At the
  promote, Horizon on the old writer finished the transcode 55 s after the
  close (it stops with no wait), with a read-only database, so the row
  was not updated. The new writer had a partial `720p.mp4` of 524 KB. At
  the failover, the job was in the Redis of the stopped node. Both videos
  kept `status` 1 and `has_processed` 0. The scheduler of Loops has no task
  that starts the transcode again (`52-queue-at-switch.log`).

## 6. The old writer comes back

**Result: pass.** (`60-rejoin.log`)

`pct start 9392` at 08:53:54. The node booted with `read_only` 1 and
`role=primary` still in its role file, so the gate stayed closed. keel
kept a dump, rejoined it by GTID with no errant transaction at 08:55:02,
and wrote `role=replica` at 08:55:04. Replication: both threads running,
0 s behind. The workers stayed inactive, and the site answered 503 with
`Retry-After: 30`. The site of 9391 stayed open. The two gates were never
open at the same time.

## 7. Coraza and Anubis (cloud mode)

**Result: fail with the prototype, pass after the fix, with open points.**
(`49-front-config.log`, `70-front-matrix.log`, `71-front-fix.log`,
`72-front-media.log`, `73-upload-sizes.log`, `74-coraza-summary.log`)

Before the fix, the front of keel-web had no body limit of its own, so
nginx took 1 MiB. An upload of 3.7 MB got **413** from the front. Every
ActivityPub POST got **403** from Coraza: rule **920420** ("Request content
type is not allowed by policy", `application/activity+json`) and the
anomaly rule 949110.

Each path class with each user agent, before the fix:

| Path | Browser agent | `okhttp/4.12.0`, `CFNetwork`, Mastodon `http.rb`, curl |
|---|---|---|
| `/`, `/up` | Anubis challenge | pass |
| `/.well-known/webfinger`, `/.well-known/nodeinfo` | pass | pass |
| `/nodeinfo/2.1`, `/ap/users/ID` | Anubis challenge | pass |
| `POST /ap/inbox` | 403 (rule 920420) | 403 (rule 920420) |
| `/api/v1/...`, `POST /oauth/token` | Anubis challenge | pass |
| a video file under `/storage/` | Anubis challenge, no cookie | pass |

The fix of Keel-Linux/keel-loops#1:

- `keel-front.d/60-keel-loops.conf`: `client_max_body_size 64m`, and these
  paths go to the app socket with no Anubis: `/.well-known/webfinger`,
  `/.well-known/nodeinfo`, `/.well-known/host-meta`, `/nodeinfo/`, `/ap/`,
  `/storage/`. `/api/` and `/oauth/` keep Anubis. `/embed` was not tested.
- `coreruleset/plugins/keel-loops-before.conf`: rule 920420 does not apply
  to a POST to an inbox path (id 10121).

After the fix, with a browser agent: the actor 200
`application/activity+json`, nodeinfo 200, the video file 200
`video/mp4` and a range 206, the unsigned inbox POST 401, the signed one
202. `/`, `/api/` and `/oauth/` still give the challenge to a browser.

| Upload through the front, Coraza 0.1.5 | Result | Rule |
|---|---|---|
| valid video, 40.2 MB | 200, 1.7 s | none |
| a file that is not a video, 52.4 MB | 422 from Loops (type), 3.6 s | none |
| 73.4 MB | 413 from nginx, 0.15 s | none (the body limit) |
| clip of 3.7 MB with a text part of 300 KiB | 413, 0.43 s | **10015** |

The biggest nginx worker grew from 65 MB to 80 MB during these uploads.
Rule 920350 (Host is an address) logged the probes on the loopback only.
One `GET /keel-health` on each node was blocked by rules 941100, 941110,
941160, 941390 and 949110 (cross-site scripting). The test did not send
it, and the cause is not explained (`74-coraza-summary.log`).

**CrowdSec banned the witness.** After 6 answers 401 from `/ap/inbox`,
CrowdSec on 9391 banned `fde4:fee2:c919::1e2e` for 4 h
(`LePresidente/http-generic-401-bf`). That is the address of the witness
on the mesh. The witness lost the VIP and the primary, and etcd had 2
healthy voters of 3. The whitelist of CrowdSec names `127.0.0.1`, `::1`
and the private IPv4 ranges, not the ULA prefix of the mesh. The test
removed the decision with `cscli decisions delete`; etcd had 3 voters
again within 15 s (`45-crowdsec.log`). Later, 54 answers 401 from the
API to the same address on 9392 made no decision (`51-crowdsec-after-switch.log`);
the test did not find why.

## 8. Memory and CPU on a 4 GiB node

**Result: pass.** (`80-resources.log`)

| State | Container used | Horizon cgroup | Other |
|---|---|---|---|
| writer, idle, 60 s | 1390 MiB | 761 MiB; 0.6 s CPU in 60 s | MariaDB 182 MiB RSS |
| writer, transcode of a 30 s clip, 1080x1920, 20 MB | peak 1900 MiB | peak 1.27 GB (`memory.peak`); 67 s CPU in 45 s of transcode | ffmpeg 488 MiB |
| writer, transcode of a 58 s clip, 40 MB | peak 1980 MiB | peak 1218 MiB | transcode 129 s |
| replica, idle, 30 s | 551 MiB | no workers | MariaDB 157 MiB, etcd 67 MiB |

The 2 cores were busy during a transcode. `keel vip tend` used 17 to 30 %
of one core on the idle writer (`top`).

## Defects found

In Keel:

1. The gate of the prototype: the notice answered 200, the gate read
   `read_only` only, it kept its state with no answer, it wrote the mark
   after Horizon stopped, it did not empty Redis. Fixed in
   Keel-Linux/keel-loops#1.
2. Step 7 of `conf.d/main` stops every build. Fixed in keel-loops#1.
3. The replica hook takes an old APP_KEY row while the replica lags.
   Fixed in keel-loops#1.
4. The front of keel-loops: no body limit, rule 920420 against every
   ActivityPub POST, Anubis on the federation paths and the media. Fixed
   in keel-loops#1.
5. keel: the first `keel spec apply` of a new replicated path fails (code
   16) when Syncthing made `.stfolder` as a directory first. Not fixed.
6. CrowdSec of the cloud modes bans a node of the mesh, and etcd loses a
   voter. Not fixed.
7. keel: `keel diff` cannot infer `database.server` when Redis runs next
   to MariaDB. Not fixed.

In Loops upstream (for the maintainer to report in his words):

1. A video whose transcode job is lost stays in `status` 1 and
   `has_processed` 0. No scheduled task starts the job again.
2. The transcode writes the 720p file to its final name while ffmpeg
   writes it, so another process can read a partial file.
3. `UserRegisterVerifyController::verifyEmailVerification` and
   `claimUsername` call `$this->preflightCheck($request)` and drop the
   error that it returns, so those two checks have no effect there. Found
   by reading the code of beta.15; not exploited.

## Inferred, not measured

- The signed delivery with an unknown key was dropped in its queue job:
  no failed job and no log line, but the job itself was not traced.
- The real mobile applications send the agents of their HTTP libraries
  and pass Anubis. Only the agents were tested.
- Mastodon copies a remote video to its own storage, so it fetches with
  its server agent. Not tested with a real server.

## Not tested

- An image of `keel-loops`, its build on the build host, the first boot
  of an image (the hook ran by hand after the pairing).
- A real federated server, a real mobile application, a browser.
- A failover at 250 ms, a cut of the link in place of a stopped container.
- The scheme of links behind Anubis: `meta.path` of an API answer was
  `http://` (keel-web 0.4.2; 0.4.4 has `$keel_web_https`).
- Registration with a mail service.
- The third site: BR3 is down, so the witness is on BR1.

## What the test did by hand that a release does not do

- It removed the CrowdSec decision against the witness on 9391 with
  `cscli decisions delete`, in the middle of the test.
- It changed `appliance.name` of both specs from `lnmp` to `loops`.
- It ran the first boot hook by hand after the pairing.

## What is left on the hosts

| Host | Left |
|---|---|
| BR1 | CT 9391 (writer now) and CT 9393 (witness), running |
| BR2 | CT 9392 (replica), running |

Each of the two Loops nodes holds `/root/loops-secrets/` (APP_KEY,
administrator and test user passwords, an API token, the hook options),
`/root/clips/`, the pushed scripts and tarballs, `/root/loops-tree.tar`
(9391 and 9392), and keel's rejoin dump in `/var/backups/keel/mariadb/` on
9392. The witness holds `/root/loops-secrets/` (the test user password, the
token, a cookie jar), `/root/clips/` and the client scripts. The witness also has the line
`fde4:fee2:c919::ffff:1 loops.keel.test` in `/etc/hosts`. Both Loops
nodes have `appliance.name: loops` in their spec, the old file in
`/root/instance.yaml.lnmp`. No netem is left. No file was left on the
hosts outside the containers. Remove the 3 containers when this evidence
is merged.
