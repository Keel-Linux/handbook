# 0003: Test coverage standard

Date: 2026-09-24
Status: decided by the maintainer

## Decision

- Any repository, appliance or code that runs inside a repository of the
  organization must have at least **90 percent** test coverage.
- Code authored by the project (the `keel` library and CLI, `keel-transition`,
  `keel-archive-keyring`, build tooling such as `bt-layer`, and any new module
  added to a fork) must have at least **95 percent**, in every respect: line
  and branch coverage, every subcommand, every exit code, every error path.

## How it is measured and enforced

- Python: `coverage run --branch` over the package, `coverage report
  --fail-under=<threshold>`, with the threshold committed in the repository
  (`pyproject.toml` `[tool.coverage.report] fail_under`), so the number is
  part of the code review, not of a dashboard.
- Shell (`bt-*`, inithooks): tests are shell test files that exercise the
  script against scratch paths on the build host; coverage is measured with
  `bash -x` trace line counting through `kcov` where available, otherwise by
  an explicit checklist of code paths in the test file. Which tool becomes the
  standard is an open item below.
- Gate: a merge into the default branch of a project repository requires the
  threshold to pass on an LXC runner with native systemd (brief section 10:
  no container runtime of any other kind). Until the runner exists, the check
  runs on the build host and its output is quoted in the PR description.
- Exceptions: none by default. If a file cannot be tested without root or a
  real network (for example a first-boot hook that touches the live system),
  it is split so the logic is a pure function under test and the side effect
  is a thin wrapper, which is the same rule the brief applies to confconsole
  (section 6: no logic in the dialogs).

## What this means for the forks

The inherited upstream code (fab, common, inithooks, confconsole, buildtasks,
tkldev, the appliance recipes) ships today with little or no test suite: the
Python 3.13 survey found no pytest or unittest suite in fab, common, tklbam or
turnkey-pylib, and turnkey-chroot has 10 unit tests. Those repositories start
below the 90 percent floor through no fault of ours.

Rule for them, so the standard is real and not aspirational:

1. Every change of ours to a fork adds tests for the code it touches, and the
   touched file must reach the 95 percent bar for project-authored code.
2. Each fork carries a `COVERAGE.md` stating the measured number at fork time
   and the plan to reach 90 percent, per file, so the gap is visible and
   honest, in the same spirit as the catalog tiers in brief section 8.
3. No fork is labeled tier-1 maintained until it meets the floor.

## Measured at decision time

`keel` (7 commits, 51 tests): 83 percent branch coverage on 2026-09-24,
below the 95 percent bar for project-authored code. Files under the bar:
validate.py (75), runtime.py (56), fields.py (81), validate_network.py (81),
apply.py (84), secretstore.py (87), render.py (90), `__main__.py` (0). The
number is being raised to 95 before any further feature lands, and the
threshold is being committed to the repository.

## Open items for the maintainer

- The shell coverage tool: decided in 0004 (bats plus kcov).
- Whether appliance recipes (a `Makefile`, a `plan`, `conf.d` scripts and an
  overlay) count as code under the 90 percent floor, and what "test" means
  for them: the honest answer is a build plus a boot test on LXC per recipe,
  which the M0 gate procedure already describes for core.
