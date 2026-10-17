# Evidence: more runners for the CI of Keel-Linux/keel

Date: 2026-10-17. The time zone is UTC. The maintainer approved the task:
make the CI faster with more jobs in parallel on the VM Keel-Linux-Runner
(PVE VM 8500, 16 cores, 23 GB RAM). The runner binary is unchanged
(`v13.2.0+keel1`, the trust gate), and the rule that a host runner refuses
a fork job is unchanged.

No secret is in this file. Output is trimmed.

## Result

More runner instances do not make the CI of one pull request faster. The
`tests` job, one pytest process of 18 minutes on one core, sets the wall
time. The 10 other jobs end earlier. In the first measurement, the last job
that had to wait for a runner ended 24 s after `tests`. More instances make the 8 jobs with a container run
at the same time, and the CPU of the VM then is the limit: the timing tests
at 250 ms fail more often.

What the change does: it puts the jobs in two classes of instances, so a
`keel-host` job never holds a `keel-lxc` slot. The two classes are 5
instances for `keel-lxc` and 4 for `keel-host`. Before, 6 instances took
all labels.

| Measure | Before (6 instances, all labels) | After (5 `lxc` + 4 `host`) |
| --- | --- | --- |
| One pull request, push to last job | 18.6 min (1 run) | 18.3, 18.2, 18.0 min (3 runs) |
| One pull request, in the history of the repository | 18.8 to 26.5 min, median 23.4 min (17 runs) | not applicable |
| Two pull requests at once, first | 21.1 min | 20.1, 20.2 min |
| Two pull requests at once, second | 33.5 min | 30.8, 32.3 min |
| Runs with a failed job | 1 of 3 (history: 7 of 23 full runs) | 1 of 7 |
| Timing margin, `writable_after_carried_s` of mariadb-simple (bound 3.0 s) | 1.94, 2.29, 2.35 s | 1.10 to 1.74 s (7 runs) |

The history is the run list of Keel-Linux/keel from 2026-10-14. The runs of
the history overlapped with other runs (a push run after a merge, a second
pull request), which explains the longer times. The time of the first
measurement is the time of a run alone on the VM.

The gain is small: about 0.5 minute for one pull request and 1.5 to 2.5
minutes for the second of two. The size of the sample (3 and 4 runs) does not
allow a stronger claim. The CI of two pull requests at once still takes about
31 minutes, because the 8 jobs with a container of the second pull request
wait for the 5 slots.

## Method

- A no-op pull request (an empty commit) on Keel-Linux/keel, pushed again
  for each run. Closed without merge after the runs, branches deleted. The
  keel workflows have no `workflow_dispatch`, so a pull request is the way.
- Wall time: the epoch of the push to the end of the last job of the run
  (`updated_at` of the tasks in the Forgejo API). For two pull requests,
  both branches were pushed within 1 second.
- A sampler on the VM (every 2 s): for each `user-UID.slice`, `memory.current`,
  anonymous memory, `cpu.stat`, `cpu.pressure`; for the VM, load average,
  CPU use, `MemAvailable`, disk use. A job was matched to its runner by the
  end time of the `forgejo-runner@I` service cycle in the journal.
- The timing values come from the `RESULT` lines of the job logs.

## Baseline: resources of the jobs

One keel pull request, 6 instances, run 206 (the job table of a run: 11 jobs
including `security`). Slices of 2.5 GB. "Peak anon" is the anonymous memory
of the slice. "Peak memory" includes the page cache, which the kernel takes
back at the limit.

| Job | Time (min) | CPU (s) | Average cores | Peak anon (MB) | Peak memory (MB) |
| --- | --- | --- | --- | --- | --- |
| tests | 18.2 | 1105 | 1.01 | 129 | 298 |
| mesh | 11.4 | 105 | 0.15 | 547 | 1158 |
| postgres | 10.9 | 1205 | 1.83 | 633 | 2225 |
| mariadb | 8.5 | 539 | 1.06 | 854 | 2103 |
| vip-upgrade | 7.9 | 661 | 1.39 | 600 | 1530 |
| vip | 7.5 | 577 | 1.28 | 599 | 1483 |
| etcd | 7.0 | 183 | 0.44 | 518 | 1281 |
| etcd-auth | 5.1 | 382 | 1.26 | 608 | 1555 |
| mariadb-simple | 4.7 | 295 | 1.04 | 853 | 2166 |
| security | 1.4 | 259 | 3.04 | 327 | 907 |
| package | 0.1 | 7 | 1.16 | 46 | 112 |

- One pull request needs 5300 CPU seconds, 4.8 cores on average over 18.6
  minutes. Short bursts use 3 to 10 cores in one slice.
- Memory: at most 0.9 GB of anonymous memory in one slice. The slices
  reached their 2.5 GB limit with page cache (`memory.events` `max` counts in
  the thousands), with no OOM kill (`oom_kill 0`).
- Disk: 6.6 GB written for 6 jobs and 11.6 GB for 11 jobs, 1 GB for each job,
  removed by the job reset. The disk has 87 GB free.
- 6 jobs at once: the load average peaked at 10.6 and the CPU use at 99 % in
  one tick, 32 % on average.

## Limits that force jobs to run one after another

- Runner instances: 6, each takes one job (`one-job`). Two pull requests need
  22 jobs. This was the only fixed limit.
- Shared names and ranges: none. Each job has its own lxcpath under
  `/var/tmp/keel-ci/keel-trixie-RUN_ID-ATTEMPT-RANDOM`, runs in its own
  container, and every netns test (`wg0`, the namespaces, the fixed
  addresses, ports 51820, 2379, 2380, 3306) lives inside that container.
  The `tests` job on the host binds port 0 only. `lxcbr0` has 253 addresses
  with leases of 10 minutes, and 9 jobs of at most 5 containers use 45.
  Subordinate ids, `lxc-usernet` quota and users are per instance. So the
  test harness needed no change.
- The shared resource is the CPU (and the disk). See below.

## Measurements of the configurations

All runs are no-op runs on the head of main (aacb5a2). A "run" is the
`tests` workflow of one pull request; `security` passed in every run.

| Config | Instances | Runs | Wall (min) | Failed jobs |
| --- | --- | --- | --- | --- |
| Before | 6 with all labels | 206 alone; 208 and 210 together | 18.6; 21.1 and 33.5 | 0; 0 and 1 (etcd-auth) |
| A | 12 with all labels | 212 alone | 18.1 | 2 (etcd-auth, mariadb-simple) |
| B | 6 `lxc` + 4 `host` | 214, 216, 218 alone; 220 and 222, 224 and 226 together | 18.8, 26.0, 18.4; 21.3 and 30.8, 21.4 and 28.0 | 1, 2, 0; 3 and 2, 0 and 0 |
| C | B with 2 own cores for each `lxc` instance | 228, 230 alone | 19.9, 19.1 | 2, 3 |
| E (kept) | 5 `lxc` + 4 `host` | 232, 234, 236 alone; 238 and 240, 242 and 244 together | 18.3, 18.2, 18.0; 20.1 and 30.8, 20.2 and 32.3 | 0, 0, 0; 0 and 1, 0 and 0 |

- A (12 instances): the 11 jobs ran at once. The load average reached 40
  and the CPU use was above 80 % from minute 4 to 7 (85 %, 86 %, 79 %). The
  etcd-auth job lost a read to `context deadline exceeded`, and the mariadb-simple
  promote took 50.6 s with 9.4 s of writes after the carried transactions
  (bound 3.0 s). This is the rule of the task: reduce the parallelism.
- B (6 `lxc`): CPU use peaked at 64 % in a single pull request and at 76 %
  with two. The failures were of the kinds that the history shows (mesh4
  `adopt` without a result, postgres commit and failover, etcd leader
  flap, VIP revoke). 4 of 7 runs had a failed job.
- C (2 own cores for each `lxc` instance, `AllowedCPUs` in the slice): the
  cores of one job were never shared, but the jobs need more than 2 cores in
  a burst. The `cpu.pressure` of each `lxc` slice showed stalls of 136 to
  367 s in one run, and both runs failed. Not kept.
- E (5 `lxc`): the load matches the "before" case for one pull request (5
  jobs with a container and `tests`). 1 of 7 runs had a failed job: the etcd
  `a_partitioned_follower_leaves_the_quorum_and_rejoins` test took 37.2 s
  against its bound of 30 s, and the etcd job failed in 3 runs of the history
  (144, 148, 190).

Failures seen in the history on unchanged code, before this work: mesh (runs
154, 180, 204), etcd (144, 148, 190), postgres (180, 196), etcd-auth (142).
Run 154 shows the same `mesh4_netns.py` "no result" failure as run 214, at a
time when 6 instances took all labels. The failures in B and C did not come
from one cause: for run 214 the VM used 28 % of its CPU when the mesh job
failed.

## What was changed

On the VM (all by `docs/infra/keel-fj-provision.pending` and the registration
below):

- `runner9` to `runner13`: label `keel-lxc` (and `self-hosted`), name
  `keel-fj-lxc-I`, memory limit 1792 MB.
- `runner17` to `runner20`: label `keel-host` (and `self-hosted`), name
  `keel-fj-host-I`, memory limit 1024 MB. New users, uid 1117 to 1120.
- `runner14`, `runner21`, `runner22` were made and removed again (user,
  subordinate ids, `lxc-usernet` line, slice and unit drop-ins).
- The sum of the memory limits is 17.75 GB with the 2 container instances.
  The VM has 23 GB. In the runs of the kept configuration, `MemAvailable`
  did not go below 18.7 GB.
- The sampler ran as `/root/ci-sampler*.sh` (not a service) and was stopped.

Repository: `docs/infra/keel-fj-provision.pending` has the two lists
(`FJ_LXC_IDS`, `FJ_HOST_IDS`), the limits for each class, and an optional
registration with `FJ_REG_TOKEN`; `docs/infra/keel-lxc-2.md` has the new
text. Test changes: none. No timing bound was changed.

## Left for the maintainer

- Forgejo 14 has no API to list or delete a runner. The old registrations
  stay as offline runners in Organization, Settings, Actions, Runners and can
  be deleted there: `keel-fj-9` to `keel-fj-14`, `keel-fj-17` to
  `keel-fj-22`, `keel-fj-lxc-14`. They do not poll for jobs.
- To make the CI of one pull request faster, shorten the `tests` job.
  `pytest` runs 3900 tests in 1252 s in one process. The job uses 1 of 16
  cores. A run with `pytest-xdist` on 4 workers would end near 6 minutes,
  and then `mesh` (11.4 min) would set the time. This changes the coverage
  run of Keel-Linux/.github `test-python.yml`; it was not part of this task
  and was not tried.
- More CPU for the VM (the cores are Xeon E5-2630 v2, 2.6 GHz) is the only
  way to run more `keel-lxc` jobs at once. Measure again after that.
- The baseline flakes (about 3 in 10 full runs) are in the netem tests, whose
  bounds are close to the measured values (for example 1.94 to 2.35 s against
  3.0 s). They need their own work.
