# Advisory 2026-10-30: a MariaDB pair can lose an acknowledged write

Date: 2026-10-30
Status: open
Issue: [Keel-Linux/keel#242](https://git.pop.coop/Keel-Linux/keel/issues/242)

## What the defect is

In a MariaDB pair, the primary can crash after it acknowledged a write
that the replica did not receive. The replica becomes the new primary
without that write, so a client that got "OK" loses its row. The old
primary then refuses to follow, because it holds a transaction the new
primary does not have. It stays read only.

The defect is intermittent. The CI test `tests / mariadb` found it in 2
runs (runs 452 and 482), with 125 ms delay per leg and 2 % loss. The
real-node test of the mariadb layer (`evidence/2026-10-30-mariadb-layer.md`)
lost no row in 2 crashes, but that does not show that the defect is not
there.

## Who is affected

- A MariaDB pair that `keel` sets up from `keel-mariadb` 0.1.1. That
  package was in `trixie` from 2026-10-30 (apt#74) until its withdrawal
  on the same day (apt#78).
- The mariadb layer 19.0-10 on the mirror. It is not in the Proxmox
  index; it is there for the appliance test of the `keel-mariadb`
  repository.
- A single MariaDB server, with no pair, is not affected.
- No effect on a PostgreSQL pair or on Redis is known. keel#242 tells if
  that changes.

## What we did

- `keel-mariadb` 0.1.1 is withdrawn from `trixie`: `bin/withdraw` (new
  in apt#77) removed it, the published tree commit is in apt#78, and the
  public archive has it. It stays in `trixie-testing`. A clean Core
  19.0-11 container on the stable track has no candidate for it
  (`apt-cache show keel-mariadb` exits 100); with `trixie-testing`
  enabled, the candidate is 0.1.1 from `trixie-testing`.
- keel 0.23.62 stays in `trixie`. The defect was there before 0.23.62,
  and 0.23.62 has the fix of keel#235.
- No application moves to a MariaDB pair until the fix is released.

## What to do now

- Do not set up a MariaDB pair for production.
- A test pair: no action is necessary.
- A host that installed `keel-mariadb` 0.1.1 keeps it. apt does not
  remove a package that a suite stops listing. Do not use it for a
  production pair.

## When it returns

`keel-mariadb` goes back into `trixie` after all of these:

1. The fix of keel#242 is merged, and `tests / mariadb` passes 10 runs
   in sequence.
2. The fix is released to `trixie-testing`.
3. A real-node test with 2 nodes on BR1 and 1 on BR2, with netem, does
   at least 10 crashes of the primary and loses 0 acknowledged writes.
   Its evidence file is in `evidence/`.
4. The maintainer promotes it.

This advisory then gets the status "closed" and the version of the fix.
