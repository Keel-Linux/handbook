# Nextcloud 35, third test by hand: the nginx memory under Coraza, and the scheme behind Anubis

Date: 2026-11-12 (UTC)

This file is the evidence for the places marked "(third test)" in
decision note 0087. It is a test by hand on the LNMP pair of the second
test. No image was built. It is not a commissioning test (0075).

## The questions

1. Why did one nginx worker grow to 3.5 GB in the second test? Can any
   Keel application hit it?
2. What is the smallest fix, and does it break Nextcloud?
3. What is the smallest change of keel-web that passes the scheme of the
   client to an application behind Anubis (option B of 0087)?
4. Does the session-only Redis user alone keep the Redis password out of
   `nextcloud.log` at log level 2?

## The machines

The pair of the second test (`2026-11-12-nextcloud-35-cloud-advanced-pair.md`):
CT 9381 (holder of the VIP) and the Core witness CT 9383 on BR1, CT 9382
on BR2; keel 0.23.96, keel-web 0.4.2, coreruleset 4.25.1-0keel1,
keel-overlay-coraza 0.1.4, libnginx-mod-http-coraza 0.21.0-0keel2,
libcoraza1 1.8.0-0keel1. CT 9381 has 4096 MiB of memory and 1024 MiB of
swap. The client is the witness 9383, through the VIP. For question 4,
CT 9380 of the first test.

The logs are in `repos/nextcloud-hand-tests/t3/` (and `t1/` log 60) of
the Keel folder on the workstation of the maintainer.

## The first conditions again (logs 01, 02)

The plugin of the prototype and the front file were taken away on 9381,
as in the run of the second test. A sampler on 9381 logged the RSS of
each nginx worker every 0.5 s, and killed a worker over 2.5 GB (it did not
have to).

| Run | Request | Client result | Biggest worker |
|---|---|---|---|
| E1 | PUT of 100 MiB with no Content-Type, through the VIP, Anubis and the app server | no answer in 75 s | 59 MB to 2.48 GB |
| E3 | the same PUT straight to the app socket on 9381 (one Coraza only) | no answer in 70 s | 33 MB to 2.17 GB, then 2.32 GB |

In both runs the worker grew in two steps: about 1.4 to 1.6 GB while the
body came in (about 20 s), a flat part, then 0.8 GB more about 40 s later.
Four minutes after E3 the worker still used CPU (1 min 52 s of CPU) and
held 2.3 GB of anonymous memory. Coraza had written the body to a file
(`/tmp/body…`, besides nginx's own `/var/lib/nginx/body/…`), so the
memory is not the body buffer. Coraza wrote no audit entry. While the
worker works, it serves no other connection.

## The cause (logs 03, 06)

The rules of keel-overlay-coraza 0.1.4 in
`/etc/nginx/coraza/keel-rules.conf`:

| Rule | What it does |
|---|---|
| 10012 | a form, JSON or XML body: body limit 262144 (256 KiB) |
| 10013 | a Content-Type outside that list and multipart: no body inspection (`ctl:requestBodyAccess=Off`) |
| global | `SecRequestBodyAccess On`, `SecRequestBodyLimit 134217728`, `SecRequestBodyInMemoryLimit 131072`, `SecRequestBodyLimitAction Reject`; no `SecResponseBodyAccess` |

Rule 10013 tests `REQUEST_HEADERS:Content-Type`. A request with no
Content-Type gives that rule no value to test, so it does not match, and
rule 10012 does not match either. The body of such a request keeps body
inspection on, up to the global limit of 128 MiB, and the Core Rule Set
reads it with no body processor.

E4 (log 03): a POST of 10 MiB to `/` with no Content-Type and **no
login**, through the front: no answer in 110 s, one worker at 1.29 GB with
1 min 49 s of CPU. The request needs nothing of the application, so every
site of keel-web with Coraza on is open to it. Coraza is on in the cloud
modes only (the manifest of web), so WordPress, Odoo and every other
application in cloud simple and cloud advanced are exposed.

For comparison (log 06): a POST of 250 KB as a form (passed, 302) took
11.7 s, and the same text with no Content-Type 3.6 s (403, rule 920340).
A body of the size that rule 10012 allows costs seconds, not minutes.

The response side is not the cause: Coraza does not read response
bodies here, and four GETs of 100 MiB grew no worker (second test, log
47). The GET that ended with 504 in the second test waited for a worker
that was busy in the rules.

## The fix (logs 04, 05, 07)

Two plugins were tested on 9381, each in `/etc/coreruleset/plugins/`:

| Variant | Rule | 10 MiB, no type | 100 MiB, no type | 250 KB, no type | DAV PUT 100 MiB, no type |
|---|---|---|---|---|---|
| none | | no answer, 1.29 GB | | | |
| A | body limit 262144 when there is no Content-Type | 413 in 0.14 s, +14 MB | | 403 in 6.3 s, +180 MB | 201 in 2.3 s |
| B | no body inspection when there is no Content-Type | 403 in 0.13 s | 403 in 1.0 s | | 201 in 1.9 s |

With variant B no worker passed 93 MB. Rule 920340 ("content but no
Content-Type") still refuses such a request, from the headers. Variant B
is the same treatment that rule 10013 gives a type outside the list. The
test rule was taken away from 9381 after the runs.

## Nextcloud and the rule set (logs 05, 08)

- A DAV PUT of 100 MiB with `Content-Type: application/octet-stream` got
  403 from rule 920420 ("content type is not allowed by policy"), with the
  plugin of the prototype. The plugin now removes rule 920420 for a DAV
  PUT too: 201 in 1.9 s.
- A POST of 10 MiB with that type outside the DAV paths: still 403.

## The scheme behind Anubis (logs 09, 10)

A debug header on the route of 9381 showed what the server of the
application receives behind Anubis:
`xfp=https addr=unix:/run/nginx/keel-app.sock scheme=http https= xrip=<client>`.
The front sets `X-Forwarded-Proto` to its own `$scheme`, and `$https` is
empty on the app socket. The try of the second test compared
`$server_addr` with `unix:`, which is wrong; the value is
`unix:/run/nginx/keel-app.sock`.

The change tested: a `map` in the http context that gives
`$keel_web_https` = `on` for `$server_addr|$http_x_forwarded_proto` =
`unix:/run/nginx/keel-app.sock|https`, and `$https` everywhere else; the
route sets `fastcgi_param HTTPS $keel_web_https if_not_empty;` after
`fastcgi_params`.

| Request | Redirect |
|---|---|
| `/` on 443 through Anubis | `https://nc.test/login` |
| `/` on 80 through Anubis | `http://nc.test/login` |
| `/` on 443 with `X-Forwarded-Proto: http` from the client | `https://nc.test/login` |
| `/` on 80 with `X-Forwarded-Proto: https` from the client | `http://nc.test/login` |
| `/` on the loopback, port 80 | `http://nc.test/login` |
| PROPFIND through the front | 207 |

Port 80 keeps `http://` links, as 0079 asks. A header of the client
changes nothing, because the front sets the header itself.

## The Redis password at log level 2 (CT 9380, `t1/` log 60)

At log level 2, with the session-only user in `session.save_path`, Redis
stopped once: 3 new lines of `nextcloud.log` held `auth[pass]`, and each of
them held the current password of the session user. So the session user
alone does not keep its password out of the log; it only limits what the
password opens. Log level 3 stays. The session password of CT 9380 was
changed after the run.

## Not tested here

A real desktop or mobile client, multipart uploads of other applications
(WordPress media) with large files, the fix inside keel-overlay-coraza
itself (only as a plugin), and the change of keel-web as a package (only
as a file on 9381).
