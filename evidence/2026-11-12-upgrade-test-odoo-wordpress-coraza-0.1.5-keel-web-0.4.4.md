# Evidence: Odoo and WordPress after the upgrade to keel-overlay-coraza 0.1.5 and keel-web 0.4.4

Date: 2026-11-12. Site: BR1 (hw12-br1). This is the first upgrade test of decision 0090, done by hand.

## Question

Does the upgrade to keel-overlay-coraza 0.1.5 (stable) and keel-web 0.4.4
(testing) change an installed node of an application that is not Nextcloud?
We tested Odoo and WordPress.

## Machines

| CT | Template (published, stable) | sha256 | Mode |
|---|---|---|---|
| 9400 (pass 1) | debian-13-keel-odoo_19.0-18_amd64.tar.zst | 69cc3e16...afc9 | cloud_simple, role primary, one node |
| 9400 (pass 2) | the same template, a new CT | 69cc3e16...afc9 | simple (the default mode), Coraza and Anubis off |
| 9401 | debian-13-keel-wordpress_19.0-21_amd64.tar.zst | 7c8c6a07...69ce2 | cloud_simple, role primary, one node |

The sha512 of each template on BR1 is the same as the sha512 on
mirror.keellinux.org (log 00).

Each CT is unprivileged, 2 cores, bridge vtnet88 tag 5, nameserver
2606:4700:4700::1111. Odoo has 4 GiB of RAM, WordPress has 3 GiB.

We put `/etc/keel/instance.yaml` and three secret files into the stopped CT
before the first boot. The description declares `installation.mode:
cloud_simple`, the cloud_simple overlay column (coraza, anubis, crowdsec,
syncthing, wireguard enabled) and `database.server.role: primary`. The first
boot ran with no failed hook (logs 02 and 21).

Limits of this mode:

- The node is in no mesh: `keel mesh status` says "this node is in no mesh".
  WireGuard has no address. No pair exists, and no replica.
- The web request path is the cloud path: nginx with Coraza in the http
  block, then Anubis (`anubis@keel`), then the application server on
  `unix:/run/nginx/keel-app.sock`. The Coraza audit log shows each request
  twice, once on the front and once on the socket (`host_ip unix`).
- Each check sends a request that Coraza must refuse (XSS in the query
  string). Coraza refused it with 403 in each stage (rules 941100, 941110,
  941160, 941390, 949110).

## Method

The check scripts run inside each CT. They connect to the global IPv6
address of the CT on port 443 with the Host header of the application, so
the request goes through the front, Coraza and Anubis. The scripts read the
admin password from `/etc/keel/secrets/app_password`. No log shows a secret.

Stages:

- A: the image as published (keel-web 0.4.2, keel-overlay-coraza 0.1.4).
- B: `apt-get update` and `apt-get -y upgrade` from the stable suite.
- C: the `trixie-testing` suite turned on, then `apt-get install
  keel-web=0.4.4`.

`nginx_facts.sh` records versions, `nginx -t`, the nginx master and worker
PIDs, RSS and peak RSS (VmHWM). `sampler.sh` records the RSS of each worker
every 0.5 s during the checks.

In the cloud pass we did not send the untyped 10 MiB POST in stage A, on
purpose. In the simple pass Coraza is off, and we sent it in each stage.

## Packages

| Stage | Odoo CT 9400 | WordPress CT 9401 |
|---|---|---|
| B, stable | 10 packages: keel-overlay-coraza 0.1.4 to 0.1.5, keel-web 0.4.2 to 0.4.3, nginx 1.26.3-3+deb13u9 to deb13u10 (Debian security), apt, zlib1g, vim | 28 packages: the same Keel and nginx packages, and Debian security updates of PHP 8.4 (8.4.26 to 8.4.27), ImageMagick, libheif, apt, zlib1g, vim |
| C, testing | 1 package: keel-web 0.4.3 to 0.4.4 | 1 package: keel-web 0.4.3 to 0.4.4 |

The simulation (`apt-get -s install keel-web=0.4.4`) and the install name
only keel-web on each CT.

No conffile prompt came. dpkg installed the new versions of these
conffiles, which the operator did not change:
`/etc/nginx/coraza/keel-rules.conf` (stage B), and
`sites-available/default-anubis`, `sites-available/keel-default`,
`snippets/keel-web-acme.conf` (stage B, keel-web 0.4.3). keel-web 0.4.4
adds `/etc/nginx/conf.d/keel-web-scheme.conf`.

## Package contents

`keel-web` 0.4.3 and 0.4.4 differ only in the new conffile
`/etc/nginx/conf.d/keel-web-scheme.conf` and the changelog. The maintainer
scripts, the state hooks and `/usr/lib/keel-web/http-mode` are the same
(log 18). The archive pool has no 0.4.2 and no coraza 0.1.4 any more, so we
did not compare those.

## nginx reload

| Stage | Odoo | WordPress |
|---|---|---|
| B | `nginx -t` ok. Master PID 3092 to 9631: the Debian nginx package upgraded the binary. dpkg ran the `nginx-reload` trigger. Rules 10014 and 10015 are in the loaded file | `nginx -t` ok. Master PID 3222 to 16308, the same way |
| C | `nginx -t` ok. Master PID 9631 stays. Workers are new (reload by the `nginx-reload` trigger of keel-web) | `nginx -t` ok. Master PID 16308 stays. Workers are new |

keel-overlay-coraza and keel-web each activate `nginx-reload`
(`activate-noawait`) in their `.triggers` file. In stage B the nginx binary
upgrade also restarted nginx. Thus stage B does not show which package did
the reload. Two more measurements close this:

- Stage C: keel-web alone reloads nginx (same master, new workers).
- `apt-get install --reinstall keel-overlay-coraza=0.1.5` on CT 9400 with
  nginx already at deb13u10: master 9631 stays, workers 14031 and 14032
  become 18907 and 18908 (log 17). Thus coraza 0.1.5 alone also reloads
  nginx, and its rules go live with no nginx update in the same run.

## Results: Odoo (CT 9400)

| # | Check | A | B | C | Logs |
|---|---|---|---|---|---|
| 1 | GET /web/login | 200 pass | 200 pass | 200 pass | 10, 13, 15 |
| 2 | Coraza probe (XSS in query) | 403 pass | 403 pass | 403 pass | 10, 13, 15 |
| 3 | Admin login, form POST /web/login | 303 to /odoo, pass | pass | pass | 10, 13, 15 |
| 4 | GET /odoo, web client, uid 2 | 200 pass | 200 pass | 200 pass | 10, 13, 15 |
| 5 | JSON-RPC create a contact with a 100 KiB HTML note | 200 pass | 200 pass | 200 pass | 10, 13, 15 |
| 6 | JSON-RPC create a contact with a 300 KiB HTML note | 200, stored (307807 chars) | 200 | 200 | 10, 13, 15 |
| 7 | Read back the 100 KiB note | same length, pass | pass | pass | 10, 13, 15 |
| 8, 9 | Multipart attachment 20 MiB, size and sha1 | 200, 20971520 bytes, sha1 same, pass | pass | pass | 10, 13, 15 |
| 10 | Multipart: text field 300 KiB and a small file | 200 (6.4 s) | **413, rule 10015** (0.01 s) | **413** | 10, 13, 15 |
| 11 | Multipart: text field 200 KiB and a small file | 200 (4.6 s) | 200 (4.2 s) | 200 (4.3 s) | 10, 13, 15 |
| 12 | CSV import, 307 KiB file part (base_import) | 200 pass | 200 pass | 200 pass | 10, 13, 15 |
| 13 | PDF report base.report_irmodulereference | 200, PDF 266 KB, pass | pass | pass | 10, 13, 15 |
| 14 | Websocket /websocket (bus), subscribe | 101, held open, pass | 101 pass | 101 pass | 10, 13, 15 |
| 16, 17 | Untyped POST 10 MiB, no login | not sent | 403 in 0.08 s, rules 920340, 949110 | 403 in 0.08 s | 13, 15 |
| - | Browser User-Agent gets the Anubis challenge | not checked | not checked | 200, challenge page | 16 |
| - | Peak RSS of an nginx worker | 84 MB | 94 MB | 98 MB | 10, 13, 15 |

In the first stage A run, check 12 gave 500. The cause was a wrong field
name in the test script (`import_id`, Odoo 18 wants `id`). The second
stage A run uses `id` and passes. The two runs are in log 10.

After stage C we sent multipart bodies with several text parts and no
login to `/web/binary/upload_attachment` (log 17):

| Body | Result |
|---|---|
| one text part 250 KiB | 303 (5.3 s), not refused |
| two text parts 150 + 150 KiB | 413, rule 10015 |
| ten text parts 30 KiB each, 300 KiB | 413, rule 10015 |
| eight text parts 30 KiB each, 240 KiB | 303, not refused |
| two text parts 100 + 100 KiB and a file of 5 MiB | 303, not refused |

Rule 10015, as shipped in 0.1.5, uses `ARGS_COMBINED_SIZE`: it adds all
text parts (and the query arguments). It does not look at one part only.

## Results: Odoo, simple mode (CT 9400, pass 2)

In stage A, `nginx -T` has no `coraza on`, `anubis@keel` is inactive and
the site is `keel-default`. After stages B and C this is the same
(logs 31, 32, 33).

| # | Check | A | B | C |
|---|---|---|---|---|
| 1, 3, 4 | Login page, admin login, web client | pass | pass | pass |
| 2 | XSS in the query | 200 (Coraza off, as expected) | 200 | 200 |
| 5, 6, 7 | JSON-RPC notes 100 KiB and 300 KiB, read back | 200 pass | pass | pass |
| 8, 9 | Multipart attachment 20 MiB, size and sha1 | pass | pass | pass |
| 10, 11 | Multipart text field 300 KiB, 200 KiB | 200, 200 | 200, 200 | 200, 200 |
| 12 | CSV import | 200 pass | pass | pass |
| 13 | PDF report | 200, PDF | 200, PDF | 200, PDF |
| 14 | Websocket /websocket | 101 pass | 101 pass | 101 pass |
| - | Several text parts (as above) | all 303 | all 303 | all 303 |
| 16, 17 | Untyped POST 10 MiB, no login | 400 from Odoo, 0.05 s | 400 | 400 |
| - | Peak RSS of an nginx worker | 9 MB | 11 MB | 11 MB |

In simple mode the upgrade changed no result.

## Results: WordPress (CT 9401)

| # | Check | A | B | C | Logs |
|---|---|---|---|---|---|
| 1 | GET /wp-login.php | 200 pass | 200 pass | 200 pass | 23, 25, 27 |
| 2 | Coraza probe (XSS in query) | 403 pass | 403 pass | 403 pass | 23, 25, 27 |
| 3 | Admin login, form POST | 302 to /wp-admin/, pass | pass | pass | 23, 25, 27 |
| 4, 5 | Editor and media pages, nonces | 200 pass | 200 pass | 200 pass | 23, 25, 27 |
| 6, 7 | Publish a post (REST JSON), read it | 201, text found, pass | pass | pass | 23, 25, 27 |
| 8 | Media form upload, PNG 5.6 MiB (multipart) | 200, success, pass | pass | pass | 23, 25, 27 |
| 9 | Media form upload, ZIP 20 MiB (multipart) | 200, success, pass | pass | pass | 23, 25, 27 |
| 10 | Post with a 300 KiB body, REST JSON (block editor) | 201 | 201 | 201 | 23, 25, 27 |
| 11 | Post with a 300 KiB body, urlencoded (as classic post.php) | 413 from Coraza (nginx error log), no rule id in the audit log | 413 | 413 | 23, 25, 27, 29 |
| 12 | Post with a 300 KiB body, multipart text part | 403, rule 941180, 4.7 s | **413, rule 10015**, 0.01 s | **413** | 23, 25, 27 |
| 13 | Media upload with a 300 KiB text field (synthetic) | 200 | **413, rule 10015** | **413** | 23, 25, 27 |
| 14 | admin-ajax heartbeat (urlencoded) | 200 pass | 200 pass | 200 pass | 23, 25, 27 |
| 15 | Logout page without nonce | 403, page of WordPress, no Coraza rule | same | same | 23, 25, 27 |
| 16, 17 | Untyped POST 10 MiB, no login | not sent | 403 in 0.08 s, rules 920340, 949110 | 403 in 0.08 s | 25, 27 |
| - | Browser User-Agent gets the Anubis challenge | not checked | not checked | 200, challenge page | 28 |
| - | Peak RSS of an nginx worker | 81 MB | 80 MB | 79 MB | 23, 28 |
| - | Several text parts, as for Odoo | not sent | not sent | 250: 302, 150+150: 413, 10x30: 413, 8x30: 302, 100+100 and file: 302 | 29 |

In each stage of both cloud CTs, a 300 KiB JSON body passes (Odoo check 6,
WordPress check 10) and a 300 KiB urlencoded body gets 413 (WordPress
check 11). Rule 10012 names both types. The upgrade does not change this.

## What changed

1. Rule 10015 refuses a multipart body whose text parts are more than
   256 KiB in total, with 413, in about 0.01 s. Several medium parts can
   add up to more than 256 KiB. Before, Coraza scanned the text in
   4 to 6 s and then sent it on (Odoo) or refused it with 403 by rule
   941180 (WordPress block markup `-->`).
2. The untyped 10 MiB POST with no login is refused with 403 in 0.08 s
   (CRS 920340). No worker went over 98 MB.
3. keel-web 0.4.4 adds the map `$keel_web_https`. No Odoo or WordPress file
   uses the variable. nginx evaluates a map only when a directive reads its
   variable. Each check gave the same result in stage B and in stage C.

## Normal use and rule 10015

- Odoo: the web client sends records as JSON-RPC (check 6, 300 KiB, 200 in
  each stage). Files go as file parts (checks 8 and 12, pass). This
  database has no `website` and no `mail` module, so no website form and no
  chatter were tested. A website form with a textarea of more than 256 KiB
  is a normal use that rule 10015 refuses. That is inferred, not measured.
- WordPress: the block editor saves as REST JSON (check 10, pass). The
  classic editor sends urlencoded and was refused at 300 KiB before the
  upgrade too (check 11). The media form sends small text fields and a file
  part (checks 8 and 9, pass). Only a multipart text part of more than
  256 KiB, or text parts that add up to more, get the new 413 (checks 12
  and 13, log 29). We know of no core WordPress screen that sends one. A
  plugin form can.
- In simple mode, the default mode, Coraza is off and rule 10015 does not
  apply (pass 2).

## Not tested

- A pair, a mesh, a VIP and a failover. These nodes are one-node
  cloud_simple primaries with no mesh.
- A browser that solves the Anubis challenge. Our client has a
  non-browser User-Agent, and Anubis let it through to the socket without a
  challenge.
- The untyped 10 MiB POST on coraza 0.1.4 (stage A), on purpose.
- The PDF path through nginx. `report.url` is `http://127.0.0.1:8069`, so
  wkhtmltopdf reads Odoo directly, not through nginx.
- Odoo modules website and mail, WordPress plugins.
- WordPress in simple mode. Only Odoo had a simple pass. The keel-web
  diff and the Odoo pass make the same result for WordPress likely. That is
  inferred, not measured.

## Notes for the promotion

- With `trixie-testing` turned on, every newer package of testing is a
  candidate. `/etc/apt/preferences.d/keel` pins `o=Keel Linux` at 990 for
  both suites, and our own pin of 100 for `n=trixie-testing` had no effect.
  Today keel-web is the only package installed on these CTs that is newer
  in testing.
- The stable upgrade also takes Debian security updates (nginx, PHP,
  ImageMagick). They change the stage B results together with the Keel
  packages.
- cron-apt runs on these images each day at 16:02 UTC. The tests ended
  before that time.
- At the end, `trixie-testing` is `Enabled: no` again on both CTs, our pin
  file is removed, and both CTs are stopped (log 40). Each CT keeps
  keel-web 0.4.4 and keel-overlay-coraza 0.1.5. The cloud Odoo CT of pass 1
  was destroyed to make pass 2.

## Logs

The logs are on the workstation of the coordinator in
`repos/upgrade-test-2026-11-12/`, numbered:
00 host and templates, 01-04 Odoo create and baseline facts, 10 Odoo A,
11-12 Odoo B upgrade and postinst, 13 Odoo B checks, 14 Odoo C install,
15-16 Odoo C checks, 17 rules 10014/10015, several text parts and the
coraza reinstall, 18 package diff, 20-22 WordPress create and facts,
23 WordPress A, 24-25 WordPress B, 26-27 WordPress C, 28 WordPress peaks and
Anubis, 29 WordPress several text parts, 30-33 Odoo simple pass, 40 cleanup.

## Result for the promotion

`keel-web` 0.4.4 changed no result on Odoo or WordPress. The test of
decision 0090 passes for `keel-web` 0.4.4. `keel-nodejs-24` is a new
package, and no published image installs it.

`keel-overlay-coraza` 0.1.5 went to `trixie` before this test, as a
security correction (0090 item 3). The test shows one change that the
change record of 0.1.5 does not say clearly: rule 10015 adds all the text
parts of a multipart body. The maintainer gets this result.
