# 0053: No merge on a red check, and evidence for every test on the real platform

Date: 2026-10-08
Status: **decided by the maintainer, 2026-10-08**: two rules of practice,
both in force from this date. Neither needs code; each changes what a
pull request must carry before it merges. The other items the maintainer
heard the same day are listed under "What comes next" and are not
decided.

## What was asked

The maintainer asked what would make the project enterprise-grade and
trustworthy. Two things happened in the days before that made the
answer concrete. keel-mariadb's `appliance / boot-published-layer` check
has been red since 2026-09-30 and pull requests kept merging past it, the
required context removed so the merge button would work, the red treated
as known noise. And on 2026-10-08 the mesh nodes web-1, web-2 and web-3
were reported at keel 0.22.0, from `dpkg -l keel` and the etcd member
checks, while `keel --version` on the same nodes printed 0.19.0
(Keel-Linux/keel#98, a hardcoded `__version__`). Both reports were true,
each from its own command, and the maintainer had no way to tell from
the reports which one described the nodes.

## Why (brief section 10)

1. **Why the current approach is not enough.** A check that is red and
   merged past is a check nobody reads: once one red is "known", the
   next red hides behind it, and the branch protection the gate exists
   for is undone by hand each time. A test report that says "verified on
   the mesh" with no commands and no output cannot be checked, cannot be
   compared with the next report, and cannot show a discrepancy like
   0.22.0 against 0.19.0, because the discrepancy is between two outputs
   and the report carries neither.
2. **Whether it can be made to work.** It can, with no tooling. A red
   check is fixed in the repository that owns it, or the check is fixed
   first if it is the check that is wrong; either is one pull request.
   An evidence file is the terminal session the test already produced,
   trimmed and committed next to the change; the handbook has one such
   set already (0050's `docs/evidence/2026-10-03-storage/`), and 0048's
   amendment made admission evidence a record a mesh keeps.
3. **Why this is better.** Green means green: a required check is
   required again, and a red one is a bug with an owner and a pull
   request, never a state of the repository. A result is a file someone
   else can read, re-run and dispute, so a wrong report is caught by the
   file, as keel#98 would have been at once with both commands' output
   side by side.

## Decision

Decided by the maintainer on 2026-10-08:

1. **No pull request merges with a red check.** A failing CI check,
   required or not, is a bug to fix before the merge, never "known
   noise". Removing a required context to let a merge through ends with
   this note. If the check itself is wrong, the fix to the check is the
   first pull request, and the change waits behind it.
2. **Every test on the real platform leaves an evidence file.** A test
   run on real nodes (Proxmox CTs, the mesh web-1, web-2 and web-3, a
   replicated pair) produces `evidence/<date>-<topic>.md` in the pull
   request or the tracker issue it supports: the commands run, their
   output trimmed and never paraphrased, the package versions from
   `dpkg`, the hashes of the artifacts used, and the timings. **A report
   without its evidence file is not a result.**

## 1. The red check

**The rule.** A check that fails on a pull request, or on the default
branch, is fixed before anything merges over it: in the code when the
code is wrong, in the check when the check is wrong, and in that order
of pull requests when both are. Marking a context not required, closing
a check's job, or merging with an admin override are not fixes.
`docs/ci-cd.md`'s "the red check on `master` is the honest state of the
fork" stands as a description, not as a licence: the honest state is
fixed, not merged past.

**The concrete case.** keel-mariadb's `appliance / boot-published-layer`
has failed since 2026-09-30 and has been bypassed since. The defect is in
`tests/lib/boot-test-lib.sh`: the primary is not given time to converge
before the test runs the replica's refusal step, so the step reads a
primary that is not ready and the check fails on a timing it created
itself. The fix is a reorder of that library, in keel-mariadb, so the
primary converges first and the refusal step runs against a converged
primary. That fix is the first pull request on keel-mariadb; the check
is made required on its default branch again when it is green, and
nothing else merges there before.

**What a check that is wrong looks like.** A check is wrong when it
fails on something the repository does not promise (a timing it does not
control, a fixture that drifted, an upstream outage). The fix is to the
check, first, in its own pull request, with its own evidence of why the
failure was the check's. A check is not wrong because it is
inconvenient.

## 2. The evidence file

**Where.** `evidence/<date>-<topic>.md`, with the date as `YYYY-MM-DD`,
committed in the pull request that claims the result, or attached to the
tracker issue the test answers when there is no pull request. Evidence
that supports a decision note moves to the handbook under
`docs/evidence/<date>-<topic>/`, as 0050's did, and the note links it.

**What it holds**, in this order, in fenced blocks:

| Section | Holds |
| --- | --- |
| Where and when | the hosts (CT id or node name), the date and time, who ran it |
| Versions | `dpkg -l keel keel-* 2>/dev/null \| grep ^ii` on every node, and the `--version` of every binary the test exercises, side by side |
| Artifacts | the file names and SHA-512 of every template, layer or package the test used |
| Commands and output | each command as typed, then its output, trimmed to what the claim rests on, never rewritten or summarised in the block |
| Timings | wall clock per step where the claim is about time, from `time` or timestamps in the output |
| What it shows | one paragraph: what the output proves and what it does not |

Trimming cuts lines; it does not change them. A cut is marked `[...]`.
Output that contradicts the claim stays in the file, with the
contradiction named in "What it shows".

**The concrete case.** On 2026-10-08 the three mesh nodes were reported
at keel 0.22.0 on the strength of `dpkg -l keel` and the etcd member
checks, and `keel --version` printed 0.19.0 on each: keel#98, the
version string hardcoded as `__version__` and not read from the package.
An evidence file with the "Versions" row above carries both outputs on
adjacent lines, and the mismatch is the first thing a reader sees. The
reports, as given, carried neither line.

**What is and is not a test on the real platform.** Anything run on a
Proxmox CT, a mesh node, a pair, the build host or a released image is;
CI on the runner, unit tests, and netns harnesses on a developer's
machine are not, and their results are their logs. A claim made from a
real-platform run without the file is treated as untested: the pull
request is not merged on it, and the issue is not closed on it.

## What comes next

Heard on 2026-10-08 and not decided; each would be its own note:

- Support lines with dates: a stable line per Debian release, supported
  for two years.
- The upgrade of a live pair as a release criterion (keel#91).
- A security process: `SECURITY.md`, an SBOM per release, reproducible
  builds, a key ceremony.
- The restore of a pair from backup as a CI test.
- Standard metrics and logs across appliances.
- Runbooks for the operations the screens do not cover.
- Governance and a contribution policy.
- Fewer appliances first: core, web, mariadb, postgresql, redis,
  wordpress.

## Consequences

- keel-mariadb merges nothing until `boot-published-layer` is green, and
  the check is required there again.
- Every pull request that claims a run on real nodes grows by one file,
  and reviewers read the file before the description.
- A tracker issue closed on a real-platform result links its evidence
  file; one closed without it is reopened.
- `docs/ci-cd.md` is corrected where it records a check kept advisory
  "until the layer is rebuilt": the layer is rebuilt first.

## What this amends

- **0006**, review policy: a merge requires every check green, not only
  the required ones.
- **0003**: unchanged; coverage is one of the checks this note keeps
  green.
- **0048, amendment (admission evidence)**: unchanged; admission evidence
  is a record the mesh keeps, this note's evidence is a record the
  pull request keeps.
- **0050**: its `docs/evidence/` directory is the form every later
  decision's evidence takes.
- **docs/ci-cd.md**: the keel-nodebb row and the "until the layer is
  rebuilt" paragraph, as above.
