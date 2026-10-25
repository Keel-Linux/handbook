# Evidence: keel picks the cheaper rejoin of an old PostgreSQL primary (keel 0.23.47)

Date: 2026-10-19 (the test began at 01:30, the time zone is UTC).
Decision: 0054, second amendment of 2026-10-18. The maintainer answered
"manda bala" to the question of
`evidence/2026-10-18-postgresql-pg-rewind.md`. Rule of the maintainer: a
release test uses 3 CTs, 2 on BR1 and 1 on BR2, with the database pair
across the 2 sites.

No secret is in this file. Output is trimmed. Test passwords are random.

## Result

| Image | sha512 (first 16) | keel | Result |
| --- | --- | --- | --- |
| `debian-13-keel-postgresql_19.0-7_amd64.tar.zst` | `8fd53addb77aa214` | 0.23.47 | PASS, every case |

The image is the one that the image gate built and passed: build
20261019T011705Z, `image-gate` run 29. keel 0.23.47 is in `trixie-testing`
only (apt#58). `trixie` stays at 0.23.21. As in the last test, no
watched repository changed, so the build began by a wrong saved head of
`keel-postgresql` in `/srv/keel-ci/state/heads` on the build host. The
public archive got 0.23.47 with `keel-publish-mirror --archive-only` first.

| Case | Link | What keel picked | Result |
| --- | --- | --- | --- |
| (a) The holder is cut for 90 s with no writer | base | `pg_rewind` | Streaming 16.9 s after the heal, the rewind 10.5 s. No copy of the holder, no divergence record |
| (b) A holder cut under writes, second failover in a row | base | `pg_rewind` | Streaming 12.9 s after the heal, the rewind 6.7 s. 1 unacknowledged write discarded, 0 of 1065 acknowledged writes lost |
| (b) with netem, the source on BR1 | 250 ms ±25 ms, 1.5 % loss | the reseed | Streaming 42.3 s after the heal. 0 of 237 acknowledged writes lost |
| (b) with netem, the source on BR2 | 250 ms ±25 ms, 1.5 % loss | the reseed | Streaming 128.7 s after the heal, against 1257 s for the rewind in the last test. 0 of 854 acknowledged writes lost |
| The kept copy | | | Each reseed kept the old data directory. The path is in the log and in the alert text. See "The kept copy" |
| Pruning | | | 3 old copies were deleted, the 2 newest stayed |
| End | | | `keel diff` shows no drift on W, B and C |

In each round the old primary and the new primary held the same ids
afterwards, and the data of the old primary that the new one lacked was
1 unacknowledged write in the dump that keel kept first.

## What changed

| PR | What |
| --- | --- |
| handbook#117 | Decision 0054, second amendment |
| keel#217 | keel 0.23.47: the estimate (`keel/system/dbpgcost.py`), the kept copy and its pruning (`dbpgkeep.py`), the alert for an unusable copy (keel#214) |
| apt#58 | keel 0.23.47 in `trixie-testing` only |

Every pull request merged with every check green, merge commits only.
The tests were written first. `dbpgcost.py`, `dbpgkeep.py` and
`dbpgrewind.py` have 100 percent of lines and branches covered.

## What keel decided, from the log

```
no-write cut, base:     rewound against [..]:5432 in 10.5 s
netem, source on BR1:   the reseed is cheaper than the rewind: pg_rewind would copy about 64 MB,
                        which is 557 s at 118 kB/s, and the reseed about 6 MB
netem, source on BR2:   the reseed is cheaper than the rewind: pg_rewind would copy about 32 MB,
                        which is 288 s at 114 kB/s, and the reseed about 6 MB
                        reseeding with no flag: the holder holds the newest claim, this node is
                        fenced, and its old data is kept
```

## The kept copy

After the test, B held two copies and C held one:

| Node | Kept copy | Size |
| --- | --- | --- |
| B | `main.keel-kept-20261019T013359Z` (the first seed of the node, with the flag) | 47 MB |
| B | `main.keel-kept-20261019T015546Z` (the automatic reseed of the last round) | 150 MB |
| C | `main.keel-kept-20261019T014703Z` (the automatic reseed of the netem round) | 23 MB |

The log of the follow says `the old data directory is kept at <path>`. The
alert is sent with the title "the old data of this node is kept" and the
path in its text. The test nodes have no alert channel, so the journal
shows `database-kept-copy: ...; no alert sent (secret file not found)`,
which proves the attempt and not the delivery.

Pruning ran on B. Three fake copies were added: two 40 days old and one 10
days old. One `keel database follow` deleted all three and kept the two
real copies, which are younger than 7 days. The deletion by low free space
and the refusal for lack of room (the flag is then required) are unit
tests: the disks of the test hosts have room.

## Findings

- **The estimate is cautious for the fast direction.** In the netem round
  with the source on BR1, the probe read 256 KB at 118 kB/s, and keel
  estimated 557 s for the rewind. The rewind of the last test took 32 s in
  this direction, because a short read does not open the TCP window. keel
  picked the reseed, which took 42.3 s. The cost of the error was a copy
  of 6 MB instead of a rewind. A longer probe would be more exact and
  would cost more time on a slow link.
- **The no-write cut at base still rewinds** (10.5 s), as the rule says.
- **The alert for an unusable copy (keel#214)** has unit tests. The real
  test did not kill `pg_rewind` again: the last test did, and the code of
  the kill path did not change.
- **The first seed of a node keeps its old cluster** when that cluster
  holds data. B kept 47 MB of its first cluster at the bootstrap. The
  rule keeps a copy at each reseed that replaces data.

## CTs

CTs 9151, 9152 and 9153 are removed, with the templates and the spec files
on both hosts. No netem and no test `nft` table remain. No CT outside
9151 to 9159 was read or changed.
