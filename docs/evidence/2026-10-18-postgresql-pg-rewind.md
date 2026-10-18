# Evidence: the old PostgreSQL primary rejoins with pg_rewind (keel 0.23.45)

Date: 2026-10-18. The time zone is UTC. Decision: 0054, amendment of
2026-10-18 (the maintainer answered "sim" to the question in
`evidence/2026-10-18-odoo-nginx-cross-site.md`). Rule of the maintainer,
2026-10-16: a release test uses 3 CTs, 2 on BR1 and 1 on BR2, with the
database pair across the 2 sites.

No secret is in this file. Output is trimmed. Test passwords are random.

## Result

| Image | sha512 (first 16) | keel | Result |
| --- | --- | --- | --- |
| `debian-13-keel-postgresql_19.0-7_amd64.tar.zst` | `aa077e09852bb14d` | 0.23.45 | PASS, every case. The cost on the poor link is under "Open" |

The image is the one that the image gate built and passed: build
20261018T213935Z, `image-gate` run 26. It is not a hand build. The
build host made it after keel 0.23.45 reached `trixie-testing`.

| Case | Link | Result |
| --- | --- | --- |
| (a) The holder is cut for 90 s with no writer | base | The old primary rejoins by `pg_rewind`: streaming 15.9 s after the heal, the rewind 9.5 s. No copy of the holder, no divergence record, no alert |
| (b) The holder is cut while it takes writes | base | The rewind discards 1 write that the sync standby never received. 0 of 1048 acknowledged writes are lost. Old and new primary hold the same ids afterwards |
| (c) `pg_rewind` is impossible on the old primary | base | keel falls back. The divergence is recorded 14.3 s after the heal and the node stays read only. The confirmed reseed streams 16.9 s after it starts |
| (d) A second failover in a row | base | Case (b) ran 80 s after the heal of case (a), and the VIP fence of the first node was clear. The VIP landed 20.07 s after the cut and the first write came 2.00 s later |
| (a) with netem, the source on BR2 | 250 ms ±25 ms, 1.5 % loss | The rewind takes 1246.5 s. Streaming 1257.2 s after the heal. See "Open" |
| (b) with netem, the source on BR1 | 250 ms ±25 ms, 1.5 % loss | Streaming 32.0 s after the heal. 0 of 974 acknowledged writes are lost. 1 unacknowledged write is discarded |
| (c) with netem | 250 ms ±25 ms, 1.5 % loss | The reseed streams 144.1 s after it starts |
| End | | `keel diff` shows no drift on W, B and C. Both pair nodes hold 2023 rows of the test table |


## What changed

Every pull request merged with every check green, merge commits only.

| PR | What |
| --- | --- |
| handbook#113 | Decision 0054, amendment of 2026-10-18: the rule of the rewind and the fallback |
| keel#213 | keel 0.23.45. `keel/system/dbpgrewind.py`, the grants of the replication role, `wal_keep_size` in the pair drop-in, the tests and the pair case (e) of the network namespace test |
| apt#56 | keel 0.23.45 in `trixie-testing` only. `trixie` stays at 0.23.21 |

The rule that keel follows, in order:

1. The old primary returns, and keel fences it: a standby that follows
   nobody. keel keeps a dump of it first, as before.
2. keel reads the settings of the running server (`wal_log_hints` or
   data checksums, `full_page_writes`) and asks the holder whether it is
   a primary. A holder that is a standby is not promoted yet: keel
   changes nothing, records nothing and asks again at the next run.
3. keel stops the old primary cleanly and runs `pg_rewind --progress`
   against the holder. `pg_rewind` only reads the holder.
4. keel writes the follow drop-in and `standby.signal`, starts the
   server, and the standby streams on the new timeline.
5. If `pg_rewind` fails before it prints `need to copy`, it changed
   nothing. keel starts the server again as the fenced standby, records
   the divergence, and asks again after 10 minutes. The reseed with
   `--destroy-local-database` is the fallback.
6. If `pg_rewind` fails after `need to copy`, the data directory is half
   copied. keel marks it unusable. Only the confirmed reseed replaces it.
   The reseed works when the half copy does not start.

## Defects that the tests found

The tests were written first. The real nodes and the network namespace
test found 8 more problems, 6 in keel and 2 in the test. All 8 are fixed
in keel#213.

| Found by | Defect | Fix |
| --- | --- | --- |
| netns pair case (a) | The follow of a new primary runs before the apply that makes the role `repl`. The grants failed with `role "repl" does not exist` and failed the follow | The grants check that the role exists, run after the commit alone, and never fail the follow |
| CI bandit | The grants built with an f-string raised B608 | The statement is written out in full |
| real nodes | A dry run (`pg_rewind --dry-run`) reads as much as the run does. On the 250 ms link both took about 20 minutes | No dry run. One run with `--progress`. The line `need to copy` marks the start of the copy |
| real nodes | After a rewind the walreceiver starts at the start of its segment, and an idle holder sends nothing. The received position stayed below the holder's flush position, so the VIP fence of the node never cleared and the next failover did not happen | The fence clears when the replayed position, or the received one, reaches the holder's position |
| real nodes | The holder was still a standby for a few seconds after the VIP landed. keel recorded a divergence and sent an alert, and the next run rewound the node | keel waits for the holder to be promoted, with no record and no alert |
| real nodes | A rewind killed in its copy left a server that does not start. `keel spec apply --destroy-local-database` refused: "the server is not answering" | The plan goes straight to the reseed for a copy marked unusable |
| netns | One failover creates one more timeline file of the same WAL segment. `pg_rewind` copies every one of them | The test cluster has 1 MB segments. The cost is measured on real nodes |
| netns | The test read the log of the follow too early | The test reads the log after the follow ended |

## The cost on a poor link

`pg_rewind` copies every WAL file of the new primary from the segment of
the fork on, in full, through SQL (`pg_read_binary_file`). A WAL file is
16 MB, and each failover makes one more file of the same segment, one for
each timeline. The relation files that changed are small. On a link of
250 ms and 1.5 % loss, one TCP stream carries about 47 kB/s.

The cost depends on the direction of the pull, because the test puts
netem on the BR2 CT only (its egress). A node on BR1 that pulls from
the BR2 holder waits for data that leaves BR2 slowly. A node on BR2 that
pulls from the BR1 holder receives fast.

| Case | Source of `pg_rewind` | Time |
| --- | --- | --- |
| base, node on BR2 | BR1 | rewind 9.5 s, streaming 15.9 s after the heal |
| base, node on BR1 | BR2 | rewind 6.5 s, streaming 13.2 s after the heal |
| netem, node on BR2 | BR1 | streaming 32.0 s after the heal |
| netem, node on BR1 | BR2 | rewind 1246.5 s, streaming 1257.2 s after the heal |
| netem, reseed of the node on BR1 (case c) | BR2 | streaming 144.1 s after the start of the apply |

In the slow case the source holds 3 WAL files of the segment of the
fork: `000000040000000000000004`, `000000040000000000000005` and
`000000050000000000000005`. That is 48 MB, and the link carried 57 MB in
the first 1214 s.

The cluster is small (37 MB of databases, 70 MB in the data directory),
so the reseed is cheap: `pg_basebackup` compresses the copy on the
holder. `pg_rewind` sends every WAL file in full, and 3 files are 48 MB.
On a cluster that has several failovers inside one segment, the number of
files grows. A development run with 7 files took 2641 s. A development
run that used `--dry-run` before the run took 2426.6 s, because it read
the files twice.

keel keeps the rewind in every case, as the decision says. The rewind is
cheaper than the reseed only when the data is large: the files that
changed are the only data that `pg_rewind` copies besides the WAL.


## The test

Nodes: CT 9151 (W, BR1), 9152 (B, BR1) on `hw12-br1`, and CT 9153 (C,
BR2) on `nfs1-br2`. W holds the third etcd voter, B and C are the
PostgreSQL pair. The mesh, etcd and the VIP come from `keel` commands only.
Netem is `delay 250ms 25ms loss 1.5%` on the egress of the BR2 CT, set
with `tc` from the host. The base rounds ran with no netem. The overlay
RTT with netem is 253 ms.

Faults: the network cut of a CT is an `nft` table that drops UDP 51820.
Writers ran on both pair nodes, one row each 0.1 s through the local
socket, only while the node carries the VIP. A write is acknowledged only
on a clean `INSERT 0 1`.

Case (c) makes the binary not executable (`chmod a-x
/usr/lib/postgresql/17/bin/pg_rewind`), restores it after, and takes the
node through `keel spec apply --system-only --destroy-local-database` to
streaming. With the file mode removed, `pg_rewind` fails before it prints
`need to copy`. The case where the file is gone is a unit test: keel
stops nothing then.

Four extra real checks ran on a development image (19.0-7, 0.23.43, with
the tree of keel#213 copied in), before the image above existed:

| Check | Result |
| --- | --- |
| The older pair drop-in | `keel spec apply` wrote `wal_keep_size = 256MB` and reloaded. The postmaster start time did not change, and `repl` held the 4 grants |
| `pg_rewind` killed 110 s into its copy | `rewind-failed` was written. The half copy did not start ("waiting for WAL"). `keel database follow` said "the server is not answering". `keel spec apply --system-only --destroy-local-database` replaced the copy with a copy of the holder (127 s, most of it the wait for the server) |
| A holder that is not promoted yet | The old primary waited, with no record and no alert, and rewound at the next run |
| The VIP fence after a rewind | The fence stayed set when the holder was idle. Fixed: the replayed position counts. The next failover was automatic after the fix |

## Open

- **The rewind is slow where the link is poor.** On 250 ms and 1.5 % loss
  the rewind of a small cluster takes 21 minutes, and the reseed 2.4
  minutes. The new primary commits alone during these minutes. The
  decision keeps the rewind in every case, and keel does so. A rule is
  possible: keel rewinds only if `pg_rewind` copies less than the base
  backup would. `pg_rewind --progress` prints both sizes ("need to copy 51
  MB (total source directory size is 70 MB)"). The rule would send small
  clusters back to the reseed that needs `--destroy-local-database`.
- The pair keeps up to 256 MB more WAL on each node (`wal_keep_size`).
- A node that failed halfway needs the operator. The mark and the reseed
  are in place, and the alert for it is the existing divergence alert.
- The image gate run 26 booted the image. It does not test a failover.

Question for the maintainer, as one yes or no: should keel rewind only
when the rewind copies less than the base backup, and reseed after the
confirmation otherwise?

## CTs

CTs 9151, 9152 and 9153 are removed. The templates and the spec files of
the test are removed from both hosts. No netem and no test `nft` table
remain.

