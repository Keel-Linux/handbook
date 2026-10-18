# Evidence: the keel tests job on pytest-xdist

Date: 2026-10-18. The time zone is UTC. The maintainer approved the task:
shorten the `tests` job of Keel-Linux/keel, one pytest process of about 18
minutes that sets the wall time of every pull request. The runner binary,
the runners and the fork rule are unchanged. No test and no timing bound
changed. No secret is in this file. Output is trimmed.

## Result

The `tests` job runs on 4 pytest-xdist workers. The job takes 10.4 to 11.5
minutes instead of 17.9 to 18.2 minutes. The coverage is the same, 98.23
percent, and the gate stays 95 percent.

The wall time of a whole pull request does not fall. The 8 jobs with a
container wait for 5 `keel-lxc` instances, and the last of them ends
about 19 to 20 minutes after the push. The `tests` job is no longer the
longest job. The queue of the container jobs is the limit now.

| Measure | Before (2026-10-17, runs 232, 234, 236) | After (3 runs, same tree) |
| --- | --- | --- |
| `tests` job (min) | 18.2, 18.2, 17.9 | 10.6, 11.5, 10.4 |
| Pull request, push to last job (min) | 18.3, 18.2, 18.0 | 19.2, 20.0, 19.1 |
| Jobs that failed | 0, 0, 0 | 0, 0, 0 |

The control runs of the same day, with the `tests` job on one process (the
tree of main with an empty commit), took 21.5 and 22.2 minutes. The VM was
slower that day (see "Other flakes").

## Method

1. A suite review and runs on the runner VM (PVE VM 8500), as the user
   `nobody`, with `CI=true` as in the job, in a virtual environment with
   `pytest-xdist`, `pytest-cov` and `pytest-randomly`.
2. A pull request on Keel-Linux/keel (#207) with the workflow change, pushed
   again for each run (amend and force push, as the Forgejo API has no
   rerun). The wall time is the epoch of the push to the end of the last
   job (`updated_at` of the tasks in the Forgejo API).
3. A read-only sampler on the VM (every 5 s: load, CPU use, steal, CPU
   pressure) for the control runs and the last runs.

## Review of the suite

The suite has 163 test files and 3915 tests in the `tests` job. I looked for
what two processes can share:

- Files: every test makes its directory with `tempfile.mkdtemp`. The
  tests write nothing in the checkout.
- Environment, current directory, umask, `sys.path`: these belong to one
  process. They cannot reach another worker.
- Ports: the listeners bind port 0. A few tests find a free port with a
  probe that binds port 0 and closes. They keep the usual small risk of
  that method.
- Real services and fixed names: none. The netns tests are skipped in this
  job (`CI` set, no `KEEL_*_NETNS`).
- Order: no test depends on another test in another file.

So no test needed a change and no test needed a serial group.

## Runs on the VM

All runs: 3915 passed, 112 skipped, 651 subtests passed, `CI=true`, the
coverage as in the job (tests and report only, without `pip` and `apt`).

| Run | Time | Result |
| --- | --- | --- |
| One process, coverage.py | 14.2 min | 98.23 percent |
| `-n 4`, pytest-cov | 7.7 min | 98.23 percent |
| `-n 6`, pytest-cov | 5.9 min | 98.23 percent |
| `-n 4`, random order, seed 11111 | 3.0 min | 3915 passed |
| `-n 4`, random order, seed 22222 | 2.8 min | 3915 passed |
| `-n 4`, random order, seed 33333 | 4.2 min | 3915 passed |
| `-n 4`, random order, seed 44444 | 4.1 min | 3915 passed |
| `-n 4`, random order, seed 55555 | 4.8 min | 3915 passed |

The report of the coverage is the same line in the 3 coverage runs: 387
missed lines and 158 partial branches. The runs with random order had no
coverage and no failure.

Without `CI`, the suite also runs the netns tests that skip in CI. A first
`-n 4` run without `CI` shared the classes of these tests between workers,
and each worker paid their set-up of 200 s again. The job sets `CI`, so this
does not occur there.

The job needs 4 workers and not 6: with 4 the `tests` job (about 11
minutes) already ends before `mesh` (11.8 minutes), and a burst of 4 cores
leaves the other jobs more CPU.

## Runs in the CI of the pull request

The `tests` job passed in all runs except run 2. The other jobs failed in
runs that are not related to the `tests` job.

| Run | Tree | `tests` (min) | Pull request (min) | Failed jobs |
| --- | --- | --- | --- | --- |
| 1 | workflow | 11.5 | 23.7 | postgres |
| 2 | workflow | 11.0 (failed) | 29.8 | tests |
| 3 to 7 | workflow and `tests/ports.py` | 12.1, 11.9, 11.8, 10.5, 11.8 | 20.1, 20.3, 19.9, 19.7, 21.0 | mariadb-simple; none; none; etcd; mesh and mariadb-simple |
| 8 | workflow | 11.3 | 22.1 | mariadb-simple, postgres |
| 9, 10, 11 | workflow | 10.6, 11.5, 10.4 | 19.2, 20.0, 19.1 | none |

- Run 2 failed in `tests/test_mesh_channel.py::TestPost::test_a_client_
  without_tls_does_not_stop_the_listener` (the TLS handshake of the second
  client read an end of file). I thought a free-port race between two
  workers was the cause and added `tests/ports.py` in runs 3 to 7. Run 7
  showed the same test failing in the `mesh` job, in one process in a
  container. So the cause is not the workers. I removed `tests/ports.py` and
  it is not part of the pull request. The test is a flake of its own (open,
  below).
- The runs 9 to 11 are the evidence for the final tree. The 3 runs passed
  all 11 jobs.

## Other flakes (not caused by this change)

The VM ran on a busy host that day. The sampler shows a steal time of 6
percent (median), 14 percent (90th percentile) and 28 percent (maximum) in
the control runs and the last runs. The `tests` job of the control runs took
21.5 and 22.2 minutes instead of 18.2.

| Job | Test | Seen |
| --- | --- | --- |
| postgres | `test_c_the_unplanned_failover_loses_no_acknowledged_row`: `pg_ask` reads `pg_replication_slots` once, right after the promote, and gets an empty answer | runs 1, 8 |
| mariadb-simple | `test_the_writes_come_back_within_15_s_of_the_promote`: 4.31, 3.53 and 11.14 s against the bound of 3.0 s | runs 3, 7, 8 |
| mesh and tests | `test_a_client_without_tls_does_not_stop_the_listener` | run 7 (mesh), run 2 (tests) |
| etcd | `test_a_partitioned_follower_leaves_the_quorum_and_rejoins` | run 6 |
| vip-upgrade, mariadb | not looked at | one control run |

The control runs without xdist had 2 failed jobs in the first run and none
in the second. The sample does not allow a claim that the 4 workers change
the rate of these flakes. The values of `writable_after_carried_s` that
passed in the runs with xdist are 1.38 to 2.93 s (1.10 to 1.74 s in the
evidence of 2026-10-17). The margin to the bound of 3.0 s is small in both
cases.

## What changed

- Keel-Linux/.github#29 (merged): the reusable workflow `test-python.yml`
  has a new input `workers`. If it is empty (the default), nothing changes.
  If it has a number, the job installs `pytest-xdist` and `pytest-cov` with
  `pip` (the job already installs `pytest` and `coverage` with `pip`) and runs
  `pytest -n N --cov=PACKAGE --cov-branch --cov-report=`. The report step
  and the threshold are the same.
- Keel-Linux/keel#207: `.forgejo/workflows/tests.yml` sets `workers: "4"`.
  `tests/README.md` shows how to run the suite with `-n 4`.

## Left for the maintainer

- To make the pull request faster, run the `keel-lxc` jobs in the order of
  their length. The jobs start in the order of the file: `mesh`, `etcd`,
  `vip`, `vip-upgrade`, `etcd-auth`, `mariadb`, `mariadb-simple`,
  `postgres`. The longest, `postgres` (10.7 min), starts last, after about 8
  minutes. With `postgres`, `mesh`, `vip-upgrade`, `mariadb` and `vip` first,
  the last job would end near minute 14. This was not tried.
- The postgres test reads the replication slot once. Waiting for the slot
  with a bound, as the test does for `synchronous_standby_names`, would
  remove that flake without a loosened bound.
- The flake of `test_mesh_channel.py` (end of file at the TLS handshake of
  the second client) needs its own issue.
