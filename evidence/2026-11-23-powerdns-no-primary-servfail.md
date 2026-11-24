# Evidence: SERVFAIL when no primary is visible, variant A of decision 0045 (PowerDNS 5.1)

Date: 2026-11-23 and 2026-11-24. Site: BR2, the Keel test VM (nested
Proxmox VE, VM 101). Status: laboratory test, run 2, for decision 0045
(second round, handbook#201, proposed, at commit `79d021c`). On
2026-11-23 the maintainer chose variant A of section 7: a DNS server
that sees no primary answers SERVFAIL. The note says that variant A must
be tested before the note is accepted. This file gives that test. It
does not change the note.

Run 1 is `evidence/2026-11-23-powerdns-5.1-standby-and-failover-record.md`.
Run 2 uses the method, the build steps and the scripts of run 1. This
file states each change.

## Questions

1. Does the LUA form of section 7 and section 10 E
   (`backupSelector='empty'` and a Lua error) answer SERVFAIL only when
   no address is up, and the correct addresses in all other cases? Is
   this true for A and AAAA, and does each answer validate (DNSSEC on)?
2. With `minimumFailures=1` (the default, the value of the note): how
   long does a switch take when the old primary refuses or answers 404,
   and when it is powered off (10 runs each)? Is there a time with two
   addresses, or with SERVFAIL while one node is the primary?
3. A validating resolver is in front of 3 DNS servers, with netem
   between them: 250 ms, jitter and loss. While at least one server
   gives the primary, does the client get an answer? How long does the
   resolver keep a SERVFAIL after the first server gives the new
   primary? The limit is 60 s.
4. The first query after a `pdns` start gets SERVFAIL (run 1). Does
   this harm variant A? What must the note say?

## Short answers

| Pass condition of section 7 | Result |
| --- | --- |
| 1. SERVFAIL when no address is up, and the addresses that are up in all other cases | **PASS.** 504 answers in 14 states: 168 SERVFAIL, each in a state with no address up. 336 NOERROR answers with the correct addresses, and `delv` gave "fully validated" for all 336. A, AAAA, the apex and `www`. |
| 2. While at least one DNS server gives the primary, the resolver gives an answer, not SERVFAIL (case 7) | **Unbound: PASS. BIND: PASS. Knot Resolver: FAIL.** Unbound gave no SERVFAIL. It gave no reply to 1 to 11 of each 128 fresh queries, because of its `discard-timeout` (1900 ms). BIND answered all 1250 queries of this case. Knot Resolver 5.7.5 (forward mode) gave SERVFAIL in 7 of 9 runs, to 1.6 % to 6.3 % of the queries of a phase. |
| 3. After the gap of a move, the resolver gives the new primary no later than 60 s after the first DNS server gives it (case 15) | **PASS** for all 3 resolvers, in 7 runs. The worst time was 39.3 s, from the positive cache of the old address (TTL 60 s). The SERVFAIL hold was at most 5.1 s (Unbound), 1.9 s (BIND) and 0.7 s (Knot Resolver). |

- **Item 2.** With `minimumFailures=1`, each server gave the new primary
  only at its next check of the new primary. On dns1 and dns2, which
  checked every 5 s, that was 0.03 s to 5.0 s after the new primary
  answered 200. On dns3, some checks ran every 10 s, and the time went
  up to 9.5 s. Run 1 measured 5.5 s to 13.9 s with `minimumFailures=2`,
  with a different method (item 2).
  - **SERVFAIL while one node is the primary: yes.** A server answers
    SERVFAIL until its next check of the new primary: at most 4.7 s on
    dns1 and dns2, and 9.1 s on dns3.
  - **Two addresses: yes, in 3 of 60 switches.** Twice, the powered-off
    old primary stayed next to the new primary for 1.3 s to 1.9 s.
    Once, the old primary, which answered 404 (the replica), stayed next
    to the new primary for 4.6 s.
  - In all switches, a server gave the old address for up to 9.5 s after
    the old node stopped as primary. Variant A does not change this. It
    is the age of the last check result.
- **Item 4.** After a `pdns` restart, the query that starts the checks
  gets SERVFAIL. The next query, 0.13 s to 0.17 s later, got the
  correct answer in 8 of 10 cases. In 2 of 10 cases (the same restart,
  A and AAAA, with one candidate powered off), the server gave
  SERVFAIL for 5.3 s. Through the 3 resolvers at 250 ms, a restart of
  one server or of all 3 servers gave no SERVFAIL to the client
  (378 queries). On the first query after setup, with all 3 servers
  cold and no netem, Unbound gave SERVFAIL to the client.
- **Does this send the choice back to B?** By the rule of section 7,
  yes for case 7: Knot Resolver kept a SERVFAIL while one server gave
  the primary. The rule then sends the choice to the maintainer with
  variant B. Unbound, the resolver that section 10 K names, and BIND
  passed all 3 conditions. The facts for the choice are in the section
  "The choice between A and B" below.

## Where and with what

All work ran inside the BR2 test VM (`keel-pve-br2`, Proxmox VE 9.2.31,
kernel 7.0.14-30-pve, 4 vCPU, 12 GiB). The VM had no guest before the
test. The test made 8 unprivileged CTs (`nesting=1`) from the Proxmox
template `debian-13-standard_13.6-1`, on the VM bridge `vmbr0`. Each CT
got a private IPv4 address by DHCP and a ULA address by SLAAC. The tests
used only these addresses. This file names the CTs by role.

| CT | Role | Software |
| --- | --- | --- |
| 9401 | build | trixie, the build of `pdns` |
| 9411 | dns1: PostgreSQL writer and PowerDNS | PostgreSQL 17.12-0+deb13u1, `pdns-server` 5.1.5-2~bpo13+1 (this build) |
| 9412 | dns2: PostgreSQL hot standby and PowerDNS | the same |
| 9413 | dns3: PostgreSQL hot standby and PowerDNS | the same |
| 9421 | web-a, the primary at the start | nginx 1.26.3-3+deb13u11, self-signed certificate |
| 9422 | web-b, the replica at the start | the same |
| 9441 | client: direct probe of the DNS servers | `dig` and `delv` 9.20.30-1~deb13u1 |
| 9451 | resolver and its client | Unbound 1.26.2-0+deb13u1, BIND 9.20.30-1~deb13u1, Knot Resolver 5.7.5-1 |

- **The build.** The test built `pdns` 5.1.5-2 of forky again as
  `5.1.5-2~bpo13+1`, with the steps of run 1. `apt-get source` took
  the source through a forky `deb-src` line. `mk-build-deps` installed
  the build dependencies from trixie. The build ran with the tests on
  and took 20 min 40 s. The 3 smoke tests printed `success`. The meson
  test printed "No errors detected", `Ok: 1`, `Fail: 0`. Lintian did
  not run in run 2.
- **The packages are not the same files as in run 1.** The sha256 sums
  are different: `pdns-server`
  `693564829193bfcf4522e6e2d408c98081c13d3fe33b4a06dcd39b924ea6e7f6`,
  `pdns-backend-pgsql`
  `c6d0d14700c02438e88a45eb7f180f3c62b5c41c95f887c5b47182b3252e4f87`,
  `pdns-tools`
  `740c5dcf2df138a70342fe11679fee66bd84947112d10d6b7666b7a8e2a71956`.
  The packages stayed on the VM, and the cleanup deleted them.
- **PowerDNS and PostgreSQL** use the files of run 1: the same
  `pdns.conf` (`lua-health-checks-interval=5`, the check timeout 2 s,
  `lua-health-checks-expire-delay=86400`), and asynchronous streaming
  replication with a slot per standby. Each PowerDNS reads only its
  local PostgreSQL. `pg_is_in_recovery()` was true on both standbys.
- **The zone** `example.test` is signed live: one CSK, ECDSA P-256
  (algorithm 13), NSEC. The DS record is
  `example.test. IN DS 61819 13 2 102f1ed2...0dca17`. The client and the
  resolvers used this DS as a static trust anchor.
- **The web nodes.** The primary answers `200` with the body
  `keel-primary fd00:db8::ffff:1` on `/.well-known/keel/primary`. The
  other node answers `404` with the body `replica`.
- The test passwords came from `openssl rand` on the VM. No password and
  no private key is in this file or in the logs. No production DNS
  server got a query.

## The record

The renderer of section 10 E is not built. The test wrote the record by
hand, for the apex and `www`, A and AAAA, with `pdnsutil`. The stored
content of each of the 4 records is the text of section 10 E. Only the
host of the URL, the 2 addresses and the token are different (a script
compared the database rows with the note):

```
www.example.test. 60 IN LUA A ";local r = ifurlup('https://www.example.test/.well-known/keel/primary', {'<web-a IPv4>', '<web-b IPv4>'}, {stringmatch='keel-primary fd00:db8::ffff:1', selector='all', backupSelector='empty', failOnIncompleteCheck='true'}) if #r == 0 then error('no primary') end return r"
```

The AAAA record lists the ULA addresses of web-a and web-b. The record
does not set `minimumFailures`, so the value is the default, 1.

- **The Lua form works.** `#r` gives the number of addresses that
  `ifurlup` returns. When the number is 0, `error('no primary')` makes
  the server answer SERVFAIL. The pdns log has one line for each such
  answer, for example: `Lua record (www.example.test|A) reported:
  [string "local r = ifurlup('https://www.example.test/...."]:1: no
  primary`.
- When an address is up, the record returns it, and the answer is
  signed.

## Item 1: the answer in each state

**Method.** For each state, the script set the check answer of web-a
and web-b, and waited 22 s. Then the client asked each of the 3 servers
for `www` and the apex, A and AAAA, 3 times (`+norec +dnssec`). For
each NOERROR answer, `delv` with the static anchor checked the answer
from that server. 14 states, 504 answers.

| State | web-a | web-b | Each server, each name and type |
| --- | --- | --- | --- |
| S1 (3 times) | 200 | 404 | web-a, fully validated |
| S2 | 404 | 200 | web-b, fully validated |
| S3 | refuses (nginx stopped) | 200 | web-b, fully validated |
| S4 | powered off (`pct stop`) | 200 | web-b, fully validated |
| S10 | 200 | powered off | web-a, fully validated |
| S9 | 200 | 200 | web-a and web-b, fully validated |
| S5 | 404 | 404 | SERVFAIL |
| S8 | 200 with a wrong body (`maintenance`) | 404 | SERVFAIL |
| S6 | refuses | refuses | SERVFAIL |
| S7 | powered off | powered off | SERVFAIL |
| S11, `prohibit` | 200 | 404 | dns1, dns2: web-a, fully validated. dns3 (no path to the web nodes, fast error): SERVFAIL |
| S11, `blackhole` | 200 | 404 | dns1, dns2: web-a, fully validated. dns3 (no path, timeout): SERVFAIL |

- The rcode is SERVFAIL, not NOERROR with no data. A NODATA answer
  would stay in a resolver cache for the negative TTL of the SOA.
- S9 is not a state of a real pair: 2 nodes never answer 200 at the
  same time (section 10 B). The test shows that the record gives each
  address that is up.
- **Pass condition 1: PASS.**

## Item 2: switch times with `minimumFailures=1`

**Method.** One run has 2 switches. First the old primary (web-a) fails.
Then the script sets web-b to 200 through `pct exec`, 1.6 s to 2.7 s
later, as a pair that moves its primary. After 30 s, web-a comes back
as the replica (404). After 15 s, the fail-back: web-b turns 404, and
web-a turns 200 about 2 s later. The client asked each server for `www`
A and AAAA every 0.25 s, with no netem. 10 runs for each way to fail:
nginx stopped (refused), a 404, and `pct stop` (powered off). That is
30 runs, 60 switches, and 360 series (server and type).

The table gives the time from the moment when the new primary answered
200, to the first answer of a server that gives the new primary only,
for each series. Run 1 changed both nodes at the same time. Thus this
time is the one to compare with run 1.

| Switch (10 runs each) | New primary only, from its first 200 | Median | SERVFAIL after the new primary answered 200, max | Runs with 2 addresses |
| --- | --- | --- | --- | --- |
| web-a refuses, then web-b 200 | 0.10 s to 9.32 s | 3.16 s | 8.92 s | 0 |
| web-a 404, then web-b 200 | 0.03 s to 6.32 s | 4.09 s | 4.79 s | 0 |
| web-a powered off, then web-b 200 | 0.17 s to 5.55 s | 3.21 s | 4.91 s | 2 |
| fail-back after "refused" | 0.16 s to 9.52 s | 2.25 s | 9.07 s | 1 |
| fail-back after "404" | 0.28 s to 7.36 s | 1.29 s | 4.65 s | 0 |
| fail-back after "powered off" | 0.08 s to 7.12 s | 2.67 s | 4.36 s | 0 |

All times above 5.0 s in this table were on dns3. On dns1 and dns2,
the maximum was 5.02 s, and the SERVFAIL after the first 200 was at
most 4.74 s.

From the start of the act, the times were: refused 3.7 s to 14.1 s, 404
3.5 s to 10.1 s, powered off 6.9 s to 12.3 s (`pct stop` took 4.6 s to
6.3 s). Run 1 (`minimumFailures=2`) measured 7.6 s to 14.4 s and 14.2 s
to 18.9 s from the start of the act.

- **One failed check marks an address down.** The pdns log shows a
  DOWN line at the first failed check. This confirms the expectation of
  section 7: a switch is about one check interval shorter than with 2.
- **SERVFAIL while the new primary is up.** A server learns that web-b
  is up only at its next check of web-b. Until then, it sees no address
  up and answers SERVFAIL. In the test, each switch had a real gap of
  about 2 s with no primary, so every server had a SERVFAIL time. Its
  length was about one check interval: 4.5 s to 5.1 s for a 404, and up
  to 10.3 s on a server with the 10 s period.
- **The 10 s period.** dns3 checked at 10 s intervals 544 times, and
  at 5 s intervals 2855 times. dns1 and dns2 checked at 5 s intervals
  only. Run 1 found the same on dns3, and its cause: the next check is
  due at `lastStatusUpdate + interval`, in whole seconds.
- **2 addresses, powered off (2 runs, dns3).** The check of the old
  primary waited for its 2 s timeout. Before it ended, a check marked
  web-b up. For 1.3 s and 1.9 s, dns3 gave both addresses. The old node
  was off, so a client could not write to it.
- **2 addresses, fail-back after "refused" (1 run, dns3, A only).**
  web-b had turned 404 (the replica). dns3 had not checked web-b again,
  because of the 10 s period. For 4.6 s, dns3 gave web-a and web-b.
- **The old address after the old node stops as primary.** In all
  switches, a server gave the old address for up to 9.5 s (median 1.5 s
  to 3.2 s). In the 404 switches, that address is the replica. Variant
  A does not change this time. Variant B has the same time.

## Item 3: a validating resolver behind netem

### The setup

The resolver CT runs 3 validating resolvers. Each has the static DS of
`example.test` as its trust anchor, and lists the 3 DNS servers on IPv4:

- **Unbound** on port 53: `stub-zone` for `example.test`, `trust-anchor`,
  `local-zone: "test." nodefault` (Unbound blocks `.test` by default).
- **BIND** (`named`) on port 5300: `static-stub` for `example.test`,
  `trust-anchors` with `static-ds`, `dnssec-validation yes`.
- **Knot Resolver** (`kresd`) on port 5301: `policy.FORWARD` for
  `example.test`, and `trust_anchors.add`. Forward mode validates. Stub
  mode does not validate in 5.7.5. Forward mode is not the mode of a
  public resolver, which iterates from the root.

**netem.** The resolver CT delays its packets to the 3 DNS servers by
250 ms ±25 ms (normal distribution) and drops 1 % of them. Each DNS
server CT drops 1 % of its packets to the resolver. The round trip is
thus about 250 ms, with about 2 % loss. Measured with `dig`: 192 ms to
277 ms. One run of each kind used 2 % loss in each direction. The direct
probe of the client CT did not pass through netem. The VM kernel loaded
`sch_prio`, `cls_u32` and `sch_netem` for the test. The cleanup unloaded
them.

### How long each resolver keeps a SERVFAIL

| Resolver | Default | Source |
| --- | --- | --- |
| Unbound 1.26.2 | 5 s, a constant (`NORR_TTL`), with no setting. Unbound does not replace a good answer that has not expired. | `util/data/msgparse.h`, `iterator/iterator.c` (`error_response_cache`) |
| BIND 9.20.30 | 1 s (`servfail-ttl`, maximum 30 s) | `bin/named/config.c` |
| Knot Resolver 5.7.5 | no SERVFAIL cache found in `lib/cache/api.c` | measured only |

Measured (the gap runs below): from the time when the first DNS server
gave web-b, to the first answer with web-b from the resolver, after a
gap longer than the TTL: Unbound 0.3 s to 5.1 s, BIND 0.1 s to 1.9 s,
Knot Resolver 0.1 s to 0.7 s.

### Pass condition 2: one server gives the primary (case 7)

**Method.** web-a 200, web-b 404. Phase 0: all 3 servers see web-a.
Phase 1: dns2 and dns3 have a `prohibit` route to the web nodes, so
they answer SERVFAIL, and only dns1 gives web-a. Phase 2: only dns2
gives web-a. In each phase, every 1 s, the script removed the name
from the cache of each resolver, and then asked each resolver once
(`dig +time=12 +tries=1`). The infra cache of each resolver stayed.
Thus each query is a new resolution, as after the end of the TTL.

| Run | Loss | Phase | Unbound | BIND | Knot Resolver |
| --- | --- | --- | --- | --- | --- |
| cond2-loss1 | 1 % | 0 | 51/51 | 51/51 | 51/51 |
| | | 1 | 128/129, 1 no reply | 129/129 | 125/129, 4 SERVFAIL |
| | | 2 | 117/128, 11 no reply | 128/128 | 126/128, 2 SERVFAIL |
| cond2-loss1b | 1 % | 0 | 52/52 | 52/52 | 52/52 |
| | | 1 | 127/128, 1 no reply | 128/128 | 126/128, 2 SERVFAIL |
| | | 2 | 123/128, 5 no reply | 128/128 | 120/128, 8 SERVFAIL |
| cond2-loss2 | 2 % | 0 | 52/52 | 52/52 | 52/52 |
| | | 1 | 127/128, 1 no reply | 128/128 | 124/128, 4 SERVFAIL |
| | | 2 | 124/129, 5 no reply | 129/129 | 123/129, 6 SERVFAIL |
| diag, only dns2 | 1 % | | 119/120, 1 no reply | 120/120 | 113/120, 7 SERVFAIL |
| diag, `+time=5 +tries=2` | 1 % | | 120/120 | 120/120 | 120/120 |
| udiag, `discard-timeout` 1900 | 1 % | | 115/120, 5 no reply | 120/120 | 116/120, 4 SERVFAIL |
| udiag, `discard-timeout` 0 | 1 % | | 120/120 | 120/120 | 120/120 |
| kdiag (Knot Resolver only) | 1 % | | | | 116/120, 4 SERVFAIL |

Each count is the number of answers with web-a. Each answer had the AD
flag, except in cond2-loss1, where the AD flag was not recorded (a
parser defect, corrected for the later runs).

- **Unbound gave no SERVFAIL.** It gave no reply to some queries. The
  cause is `discard-timeout` (default 1900 ms): Unbound drops the reply
  to a client that waits longer, and the resolution continues. With the
  setting at 0, the same case gave 120/120, and the slowest answer took
  3.7 s. Phase 0 had no drop. Thus the servers that answer SERVFAIL
  make the resolution slower than 1.9 s: Unbound asks them again
  (`outbound-msg-retry`, default 5) before it asks the good server. A
  stub that waits 5 s and asks again (`+time=5 +tries=2`) got 120/120.
- **BIND answered every query** of this case (1250 queries).
- **Knot Resolver gave SERVFAIL** in 7 of 9 runs, to 1.6 % to 6.3 % of
  the queries of a phase. Its debug log shows one such query: SERVFAIL from dns3, SERVFAIL
  from dns3 again, a timeout from dns2 (a lost packet), SERVFAIL from
  dns3, and then the end of the request with state FAIL. In forward
  mode, a SERVFAIL marks the server as broken only for that attempt
  (`lib/selection.c`, `KR_SELECTION_SERVFAIL`). In iteration mode, Knot
  Resolver first retries with TCP and other workarounds. Iteration mode
  was not tested.
- **Pass condition 2: PASS for Unbound and BIND, FAIL for Knot Resolver
  5.7.5 in forward mode.**

### Pass condition 3: the gap of a move (case 15)

**Method.** The client asked each resolver for `www` A every 1 s, with
no flush, for the whole run. After 75 s, web-a turned 404 (the old
primary fails). After a gap of 20 s or 90 s, web-b turned 200. The
direct probe gave the time when the first DNS server gave web-b.

| Run | Gap | First server gives web-b, after web-b 200 | Unbound | BIND | Knot Resolver |
| --- | --- | --- | --- | --- | --- |
| gap20-loss1-r1 | 21.8 s | 3.41 s | 1.3 s | 1.3 s | 0.3 s |
| gap20-loss1-r2 | 22.0 s | 1.74 s | 36.7 s | 23.9 s | 34.7 s |
| gap20-loss1-r3 | 21.7 s | 2.66 s | 37.1 s | 28.6 s | 39.3 s |
| gap90-loss1-r1 | 92.1 s | 1.94 s | 5.0 s | 1.9 s | 0.4 s |
| gap90-loss1-r2 | 92.6 s | 4.34 s | 0.3 s | 0.9 s | 0.4 s |
| gap90-loss1-r3 | 92.5 s | 4.90 s | 5.1 s | 0.1 s | 0.1 s |
| gap90-loss2-r1 | 92.5 s | 3.34 s | 0.6 s | 1.3 s | 0.7 s |

The resolver columns give the time from the first server with web-b to
the first answer of the resolver with web-b. After that answer, each
resolver gave web-b at each query. Each answer had the AD flag, except
in gap20-loss1-r1 (not recorded).

- **All servers answered SERVFAIL** from 4.0 s to 7.4 s after web-a
  failed, until the end of the gap.
- **The resolvers kept the old address of web-a** until its TTL ended,
  44.0 s to 62.5 s after web-a failed. In the 20 s gaps, the cache did
  not end before web-b came. This, not a SERVFAIL, gave the times of
  23.9 s to 39.3 s. With a gap of about 2 s, this time can reach about
  58 s. The TTL of 60 s sets this limit, for variant A and variant B.
- **The SERVFAIL hold of variant A** was at most 5.1 s (Unbound), 1.9 s
  (BIND) and 0.7 s (Knot Resolver). Unbound gave up to 4 SERVFAIL
  answers after the first server gave web-b, the last one 4.0 s after.
  BIND gave 1, 0.6 s after. Knot Resolver gave none.
- In the gap, Unbound gave no reply to 9 to 15 queries per 90 s gap
  (`discard-timeout`). All of them were before the first server gave
  web-b.
- **Pass condition 3: PASS** for all 3 resolvers.

## Item 4: the first queries after a `pdns` start

**On one server** (dns3, `systemctl restart pdns`, a query on the
loopback every 0.1 s):

| State | Runs | Result |
| --- | --- | --- |
| web-a 200, web-b 404 | 3 x (A, AAAA) | 1 SERVFAIL (the first query, 0.16 s to 1.25 s after the restart), then web-a 0.13 s to 0.17 s later |
| web-a powered off, web-b 200 | run 1, A and AAAA | 1 SERVFAIL, then web-b 0.13 s later |
| web-a powered off, web-b 200 | run 2, A and AAAA | SERVFAIL for 5.3 s (30 and 32 answers), then web-b |

- The first query starts the checks of its name and type, and gets
  SERVFAIL (`failOnIncompleteCheck`). With variant A, an address with
  no check result yet counts as down. Thus an address that answers fast
  makes the record correct after one check, also while the check of
  the other address waits for its timeout.
- In run 2 of the powered-off state, the pdns log has no check of web-b
  until 5 s after the first query. Only the check of web-a ran (a
  timeout at 2 s). The cause is not known.

**Through the resolvers** (netem 1 %, the name flushed every 0.5 s):

| Act | web-a 200, web-b 404 | web-a off, web-b 200 |
| --- | --- | --- |
| restart dns3 only | 32/32 for each resolver | 32/32 for each resolver |
| restart dns1, dns2 and dns3 at the same time | 31/31 for each resolver | 31/31 for each resolver |

Each answer had the correct address and the AD flag.

**All servers cold, fast path.** Right after the setup, the 3 servers had
not checked `www` yet. The first query to Unbound, with no netem, got
SERVFAIL: "all the configured stub or forward servers failed". Each
server answered SERVFAIL to the query that started its checks. The
query to BIND 1 s later got web-a. With 250 ms between the resolver and
the servers, the checks ended before the retries, and no client got
SERVFAIL.

**What this means for variant A.** One cold server costs nothing: the
resolver asks another server. All servers cold for one name at the same
time can give one SERVFAIL to a client, and Unbound then keeps it for
5 s. A cold server with a candidate that times out can give SERVFAIL for
about 5 s.

## The choice between A and B

The rule of section 7: "If condition 1 fails, or if the resolver keeps a
SERVFAIL for longer than the limits of conditions 2 or 3, the choice
goes back to the maintainer with variant B." Knot Resolver failed
condition 2. Thus the choice goes back to the maintainer. The facts:

| Fact | Variant A (measured here) | Variant B (run 1) |
| --- | --- | --- |
| A server with no path to the nodes (case 7) | SERVFAIL. Unbound and BIND gave the correct answer. Knot Resolver (forward) gave SERVFAIL to up to 6.3 % of the queries of a phase. Unbound gave no reply within 1.9 s to up to 8.6 % (`discard-timeout`). | Both addresses, fast. A client can get the replica. |
| No primary at all (the gap) | SERVFAIL. Each resolver gave the new primary 0.1 s to 5.1 s after the first server. | Both addresses. A client can get the replica, which refuses writes. |
| The old address after a switch | Up to 9.5 s, the age of the last check | The same |
| A cold server | SERVFAIL until the first results | Both addresses for about 5 s (with `minimumFailures=2`) |

The resolvers of real clients are not known. Unbound and BIND are the
resolvers of many operators. Public resolvers iterate from the root, not
in forward mode.

## What the note can say (proposals, the note is not changed)

1. Section 7: the Lua form works as written (condition 1 measured). The
   record keeps `minimumFailures` at its default of 1 (measured).
2. Section 7: a switch takes one check interval after the new primary
   answers 200, at most 5.0 s, and 9.5 s on a server whose checks run
   every 10 s.
3. Section 7 and section 10 B: variant A does not stop a server from
   giving the replica for up to one check interval after a switch. The
   sentence "a server never gives the replica" is true only when the
   server sees no primary.
4. Section 10 J: the DNS server terms with `minimumFailures=1`, and the
   SERVFAIL hold of the resolvers: Unbound 5 s, BIND 1 s.
5. Section 10 K: test the resolvers of the main client networks, not
   only Unbound. Knot Resolver in forward mode failed case 7 here.
6. Section 7: restart the DNS servers one at a time. At each `pdns`
   start, run the warm-up query for each failover name at once, not
   only every 5 minutes.

## Sentences of 0045 that the results confirm or contradict

This section quotes the note at handbook#201, commit `79d021c`.

**Confirmed:**

- Section 7: "The record uses `backupSelector='empty'` (5.1) and Lua
  code that raises an error when the result is empty. The 5.1.5 code
  turns an error of a LUA record into SERVFAIL". True for A and AAAA,
  `www` and the apex, signed.
- Section 7: "With 1, one failed check marks an address down, so a
  switch is expected to be one check interval shorter than the measured
  times." True: from the first 200 of the new primary, 0.03 s to 5.0 s
  on dns1 and dns2, and up to 9.5 s on dns3 (the 10 s period).
- Section 7, variant A: "a resolver asks another server". True for
  Unbound and BIND.
- Section 7, variant A: "In the gap of a move, when no node answers as
  the primary, all servers answer SERVFAIL." True, from 4.0 s to 7.4 s
  after the old primary failed.
- Section 7: with `failOnIncompleteCheck`, later queries before the
  first result "get SERVFAIL (not tested)". True. With variant A, the
  record is correct after the first check result of an address that is
  up.

**Contradicted or limited:**

- Section 7, variant A: "a server never gives the read-only replica
  because it cannot see the primary". True when the server sees no
  primary. After a switch, a server gave the old primary, then the
  replica, for up to 9.5 s. Once, one server gave both nodes for 4.6 s.
- Section 7, variant A: "a resolver can keep a SERVFAIL for up to 5
  minutes (RFC 2308, section 7.1)". The 3 resolvers kept it for at
  most 5.1 s.
- Section 10 B: "With variant A of section 7 (the decision) it answers
  SERVFAIL, and the resolver asks another server (not tested)." True
  for Unbound and BIND. Knot Resolver 5.7.5 in forward mode gave
  SERVFAIL to up to 6.3 % of the queries of a phase.

## What failed or went wrong in the test

- The CT disks were slow (I/O pressure 60 % to 75 %). The first package
  installs took about 25 min. `force-unsafe-io` for `dpkg` was set in
  the build CT and the DNS CTs.
- Unbound did not start at first: `named` and `kresd` had taken port
  53 after their install. The script stopped them and started the 3
  resolvers on their own ports.
- The AD flag was not recorded in cond2-loss1 and gap20-loss1-r1. The
  parser read the EDNS line, which also has "flags:". cond2-loss1b ran
  again with the correction.
- The first start of cond2-loss1 stopped at once: a shell function had
  the name `cut`, which hid the `cut` command. Its partial output was
  deleted, and the run started again.
- `pveam update` refreshed the appliance index of the VM
  (`/var/lib/pve-manager/apl-info/`), as in run 1.

## What was not tested

- A real Keel pair, the check address of `keel`, and a real gap of a
  move. The gap here is a fixed 2 s, 20 s or 90 s.
- Knot Resolver in iteration mode, and public resolvers.
- A resolver that iterates from the root through a real delegation.
- Lintian on the run 2 build.
- Stubs other than `dig` (glibc, systemd-resolved, browsers).
- The public IPv6 prefix and public IPv4.

## Logs and scripts

The logs and the scripts are kept outside the handbook, in the Keel
working directory `repos/evidence-0045-2026-11-23/run2/`: the build log,
the probe output and the pdns, nginx and resolver logs of each run, the
analysis scripts and their output, and the VM state before and after
the test.

## Cleanup

On 2026-11-24 the test destroyed its 8 CTs (`pct destroy --purge`). It
removed its files from the VM, the template that it had downloaded, and
the 3 netem modules (`rmmod`). The VM state after the cleanup is the
same as before the test, except the date. The output after the cleanup:

```
== pct list
== qm list
== /etc/pve/lxc
== template cache
debian-13-keel-core_19.0-13_amd64.tar.zst
debian-13-keel-nextcloud_19.0-3_amd64.tar.zst
debian-13-keel-nextcloud_19.0-4_amd64.tar.zst
== lsmod netem, prio, u32
no-netem-module
no-prio-u32
== storage
local:iso/debian-13-keel-nextcloud_19.0-3_amd64.iso
local:iso/debian-13-keel-nextcloud_19.0-4_amd64.iso
local:vztmpl/debian-13-keel-core_19.0-13_amd64.tar.zst
local:vztmpl/debian-13-keel-nextcloud_19.0-3_amd64.tar.zst
local:vztmpl/debian-13-keel-nextcloud_19.0-4_amd64.tar.zst
== links
lo, eth0, vmbr0
```

The 3 Keel images and the 2 ISO files were there before the test. The
test changed no firewall, bridge, storage or cluster setting of the VM.
