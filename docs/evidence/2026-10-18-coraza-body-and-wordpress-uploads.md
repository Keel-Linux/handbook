# Evidence: Coraza and the request body, and media uploads in Keel WordPress 19.0-8

Date: 2026-10-18. The time zone is UTC.
Decisions: 0030, 0041, 0047, 0049, 0059, 0061. Issues: Keel-Linux/common#59
and Keel-Linux/keel-web#15. They came from the cross-site test of Keel
WordPress 19.0-6 (`2026-10-18-wordpress-nginx-cross-site.md`). The rule of
the maintainer, 2026-10-16, applies: a release test uses 3 CTs, 2 on BR1 and
1 on BR2, with the database pair across the 2 sites.

No secret is in this file. Output is trimmed. The passwords of the test are
random and are in no file of this repository.

## Result

| Image | sha512 (first 16) | keel | Result |
| --- | --- | --- | --- |
| `debian-13-keel-wordpress_19.0-8_amd64.tar.zst` | `58d045b3306ddb45` | 0.23.43 | PASS, every item below |

This is the image of the build `20261018T142951Z` of the image build per
merge (decision 0061). It passed the image gate (image-gate run 20). The
test ran on this file, and the Forgejo pre-release `testing-19.0-8-20261018`
on Keel-Linux/keel-wordpress holds the same file, signed by the main key and
the images key. Each key verifies the signature alone. The stable index and
keel are not changed.

| Item | Result |
| --- | --- |
| Media upload of 3 MiB and 32 MiB through Anubis and Coraza | 201 at the new holder after each of 4 failovers; before, 413 |
| Worker memory during an upload of 32 MiB | +12 to +16 MiB (RSS of the largest nginx worker) |
| Block editor save | a REST post with a JSON body and 3 blocks (paragraph with a link, image, code) answers 201 at the VIP |
| REST JSON post after each failover | 201, 4 of 4 |
| Failover with writes, 4 rounds (cut and `pct stop`, base and netem 250 ms ±25 ms, 1.5 % loss) | the first write came 1.47 to 1.66 s after the VIP; 0 acknowledged writes on the old holder after the fault; 0 of 10859 acknowledged ids lost |
| `keel diff` | exit 0 on the 3 CTs at the end |
| End | no netem, no test nft table; 10863 rows on both nodes; the GTID state is the same on both |

## The cause (Keel-Linux/keel-web#15)

The issue said that the front site was the limit, and that a body of 3 MB
made one worker use 1.4 GB. The measurement shows that the memory came from
Coraza, not from Nginx.

`keel-rules.conf` set `SecRequestBodyAccess On` and nothing else. Coraza
selects a body processor for a form only. For any other body, rule 901350 of
the Core Rule Set forces the URL encoded processor. So the whole body
became one argument, and the rules matched that argument again and again.
The cost is in the number of bytes, not in the number of arguments.

I measured this on the container of Keel WordPress 19.0-6 (2 GB, Coraza
0.21.0, Core Rule Set 4.25.1). The front limit was raised to 64 MB for the
test only. A guard killed the worker above 1.2 GB. The "after" column is the
final image, with the front limit of the layer.

| Body sent to the front site | Before | After |
| --- | --- | --- |
| `image/jpeg`, 1 MB | 30.4 s, worker at 800 MB | 403 in 0.28 s (rule 920420), +4 MB |
| `image/jpeg`, 3 MB | 74 s, worker above 1.2 GB, killed by the guard | 403 in 0.08 s, +1.5 MB |
| `image/jpeg`, 32 MB | not run | 403 in 0.56 s, +17 MB |
| `application/octet-stream`, 3 MB | not run | 403 in 0.18 s, +0 MB |
| URL encoded text form, 1.3 MB | 39.6 s | 413 in 0.19 s |
| URL encoded text form, 4 MB | answer 200 after 119 s | not run (same rule) |
| multipart with a file of 32 MiB | worker +126 MB | answer in 1.9 s, +4 MB |
| JSON, 3 MB | not run | 413 in 0.32 s |

An image sent with a raw body is refused by the policy of the Core Rule Set
anyway (rule 920420, the content type is not allowed). That is not a
regression: the media library of WordPress sends a multipart body, and the
test below uses it. The memory defect was in the time before the rule
answered.

### The fix

keel-overlay-coraza 0.1.4 (Keel-Linux/common#60, rules 10010 to 10013 in
`keel-rules.conf`):

1. A JSON body gets the JSON processor, and an XML body the XML processor.
   This closes Keel-Linux/common#59. The fields of the post are
   `json.content`, `json.title` and so on.
2. A form, JSON or XML body of more than 256 KiB is refused with 413. The
   rules need about 10 s of CPU for each MiB of such a body, so a big one
   is a cost for the machine. `SecRequestBodyLimit` counts the files of a
   multipart body too, so the limit is set with `ctl:requestBodyLimit` for
   these types only.
3. A body of any other type is not read.
4. A file in a multipart body is no argument. The limit does not count it.

keel-web 0.3.2 (Keel-Linux/keel-web#16 and #17) includes
`/etc/nginx/keel-front.d/*.conf` in the front server, and keel-wordpress
(Keel-Linux/keel-wordpress#26 and #27) puts `client_max_body_size 64m;`
there. 64 MB is the limit of PHP.

Tests. The suites marked "red first" were run and failed before the fix.
The 6 tests of common and the test of `site.bats` first ran after the fix,
in the job of the pull request:

| Repository | Tests |
| --- | --- |
| common | 6 in `tests/overlay-web.bats`, run by the job `packages / web` on a booted container (all 6 passed in the job): the processor of each type, a body of another type, the limit on both sides, a multipart file of 32 MiB, a script in a multipart field |
| keel-web | 3 in `package.bats` (red first), 1 in `site.bats` (a real `nginx -t` with a file in `keel-front.d`, and a body of 2 MB; passed in the job) |
| keel-wordpress | 3 for the hook, 2 for the front file, 1 for the image check, 3 for the exclusion (red first, except the replica test of the hook) |

### What the test on the platform found

The unit tests passed and the platform found 2 more defects. Both are fixed
and they are in the image of this test.

1. **keel-web 0.3.1 set `client_max_body_size 1m;` in the front server.**
   Nginx refuses a second `client_max_body_size` in the same server. The
   file of keel-wordpress made the Anubis state hook fail with "directive is
   duplicate" and roll back. The hook rolled back on the first CT of the
   first image of this test (19.0-7, not published). keel-web 0.3.2 sets
   none, and the front keeps the default of 1 MB until a file sets another.
   `site.bats` now runs `nginx -t` with such a file.
2. **The first boot hook left `wp-content/uploads/2026/10` to root.**
   wp-cli runs as root in the hook, and WordPress makes the directory of the
   month at the installation. The web user could not move a file into it, and
   the REST API answered 500 `rest_upload_unknown_error`. No upload had
   reached this point before, because the front answered 413 first. The hook
   gives the tree to the web user before it starts the web server.

The exclusion of the REST API for Coraza changed too. With the JSON
processor, rule 941180 and others (941160, 942190, 932235 for a code block)
still read the HTML comments of the blocks in `json.content`. So the
exclusion stays, and it is now narrow. It removes the Core Rule Set rules
from `json.content`, `json.title` and `json.excerpt` only. Before it removed
them from all the arguments and all the argument names of a JSON write to
`/wp-json/`.

| Request at the VIP, after the fix | Status |
| --- | --- |
| a post with 3 blocks (paragraph with a link and `&`, image, code with `SELECT` and a pipe) | 201 |
| the same post with a text of SQL injection in `slug` | 403 |
| a JSON body of 400 KB | 413 |

## The test

BR1 is hw12-br1, BR2 is nfs1-br2. BR3-THIN is offline, so the test cuts the
CT of the primary and never the whole site.

| | BR1, witness | BR1, pair node | BR2, pair node |
| --- | --- | --- | --- |
| WordPress | 9137 `wp7-w` | 9138 `wp7-b`, replica at installation | 9139 `wp7-c`, primary at installation |

All 3 nodes use `cloud_advanced` with Anubis and Coraza enabled, keel-web
0.3.2 and keel-overlay-coraza 0.1.4. The test replaced the CTs 9134 to 9136
of the 19.0-6 test, which are removed. The mesh has 3 etcd voters, all
healthy. At the first boot the 3 CTs complete with no failed unit. The
harness is the one of the 19.0-6 test, with one more step.

### Failover rounds

Writers ran on both pair nodes, as in the 19.0-6 test. Times are in seconds
after the fault. After each fault, at the new holder and through Anubis and
Coraza, the test did a login, a REST post with a JSON body, a post with
wp-cli, and the uploads below.

| Round | Fault | Network | VIP left the old holder | VIP landed | First write after the VIP | Acks on the old holder after the fault | Acked ids missing on the survivor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cut of C (the holder) | base | +12.55 | +20.87 | 1.55 s | 0 | 0 of 3400 |
| 2 | `pct stop` of B (the holder) | base | stopped | +18.67 | 1.47 s | 0 | 0 of 2627 |
| 3 | cut of C (the holder) | netem | +11.78 | +22.04 | 1.59 s | 0 | 0 of 3067 |
| 4 | `pct stop` of B (the holder) | netem | stopped | +21.01 | 1.66 s | 0 | 0 of 1765 |

The netem profile on the BR2 CT is `delay 250ms 25ms loss 1.5%`. Overlay
ping from W to C: 230 / 253 / 280 ms (min / avg / max), 0 of 30 lost. The
old holder returned read only after rounds 1 and 3, "diverged" by 1
transaction as in the 19.0-6 test, and was reseeded with
`--destroy-local-database`. After rounds 2 and 4 it replicated by itself.
A cut in which the old primary took no write ended with "rejoined: no errant
GTID", with no reseed.

### Uploads

A multipart POST to `/wp-json/wp/v2/media` through the front site of the
holder (Anubis and Coraza), logged in as the administrator with a nonce. The
file is a ZIP of random bytes (accepted by WordPress as a valid type) or a
PNG. Memory is the largest RSS of an nginx worker, sampled every 0.1 s. The
last 2 rows run from W against the VIP.

| Round, holder | File | Status | Time | Worker before / peak (kB) |
| --- | --- | --- | --- | --- |
| 1, B | ZIP 3 MiB | 201 | 0.34 s | 58112 / 68528 |
| 1, B | ZIP 32 MiB | 201 | 2.11 s | 68776 / 81584 |
| 1, B | PNG 3 MiB | 201 | 2.76 s | 81604 / 81604 |
| 2, C | ZIP 3 MiB | 201 | 0.53 s | 48844 / 55924 |
| 2, C | ZIP 32 MiB | 201 | 2.95 s | 56572 / 72424 |
| 2, C | PNG 3 MiB | 201 | 2.92 s | 72428 / 72428 |
| 3, B (netem) | ZIP 3 MiB | 201 | 0.52 s | 57856 / 61864 |
| 3, B (netem) | ZIP 32 MiB | 201 | 2.17 s | 62432 / 78876 |
| 3, B (netem) | PNG 3 MiB | 201 | 2.63 s | 78876 / 78892 |
| 4, C (netem) | ZIP 3 MiB | 201 | 0.50 s | 51320 / 62272 |
| 4, C (netem) | ZIP 32 MiB | 201 | 2.16 s | 62492 / 75108 |
| 4, C (netem) | PNG 3 MiB | 201 | 2.15 s | 71464 / 71532 |
| end, W to the VIP | ZIP 32 MiB, PNG 3 MiB | 201, 201 | 2.84 s, 2.12 s | (W does not carry the request) |

The peak is 12 to 16 MiB above the start for a body of 32 MiB. WordPress made
the thumbnails of the PNG files. The table samples the nginx workers only.
The cgroup of each CT covers all processes, Anubis and PHP-FPM included. Its
`memory.peak` for the whole test, from the first boot to the end, was 1012 MB
(9137), 982 MB (9138) and 1084 MB (9139), with a limit of 2147 MB. The count
includes the page cache. `oom_kill` is 0 on the 3 CTs.

## Limits that stay open

- **The witness has a failed unit.** `keel-database-follow.service` on W
  fails with "this node declares no appliance.vip". The path unit starts it
  when the file `/var/lib/keel/vip` changes. The same unit failed on the CT
  9134 of the 19.0-6 test, so it is not new. It is a defect of keel for a
  node with no pair (Keel-Linux/keel#211). It does not touch
  WordPress.
- **256 KiB for a form, JSON or XML body is a regression against 19.0-6.**
  In 19.0-6 a JSON write to `/wp-json/` went through up to the 1 MB limit of
  the front site. Now a block editor save of more than 256 KiB of text is
  refused with 413. Measured at the VIP, logged in, with a block post of
  about 200 KB, 400 KB, 900 KB and 1.2 MB: 201, 413, 413, 413. This is about
  40000 words for the first limit, but the block markup counts too. A check
  on the holder, with a rule in `keel-wordpress-before.conf` that sets
  `ctl:requestBodyLimit=1048576` for a JSON write to `/wp-json/`, gave 201,
  201, 201 and 413. So a later `ctl` overrides the cap, and the file was put
  back after the check. Other layers can be affected: Odoo sends base64 fields
  inside JSON-RPC bodies. This is not tested, and the Odoo CTs were not
  touched. Keel-Linux/common#61 holds the options. The 19.0-8 pre-release
  says so.
- **A media file with a raw body.** A REST upload with a raw body and an
  image type is refused by rule 920420 of the Core Rule Set. The
  media library, the block editor and the mobile apps send multipart. No
  change is made.
- **The three layers lnmp, lnpp and odoo.** They were rebuilt in the same
  build because keel-web changed. Only WordPress was tested across the sites
  for this change. The image gate booted each of them.
- **The checks of a pull request did not see the defect of keel-web 0.3.1.**
  The job `appliance` of a repository that depends on Web boots the
  published layer, not the layer of the merge. Only a test on the platform
  found it. `site.bats` of keel-web now covers it.

## Pull requests and issues

| Repository | What |
| --- | --- |
| common#60 | keel-overlay-coraza 0.1.4: the body processors and the body limits |
| keel-web#16, #17 | keel-web 0.3.1 and 0.3.2: `keel-front.d` in the front site |
| keel-wordpress#26, #27 | the front limit, the narrow exclusion, the owner of the uploads tree, keel-web 0.3.2 |
| apt#52, #53 | the publication of keel-overlay-coraza 0.1.4, keel-web 0.3.1 and keel-web 0.3.2 to trixie-testing. The job `tests` of apt#52 failed once, and the log of this private repository was not readable. The commit had no code change (only the pool and the index), the run before it on the same code passed, and the second run passed. The cause of the first failure is not known |
| this change | the evidence |

keel-web 0.3.1 is not in any image that was published. The CTs 9137, 9138
(BR1) and 9139 (BR2) stay running for the maintainer.
