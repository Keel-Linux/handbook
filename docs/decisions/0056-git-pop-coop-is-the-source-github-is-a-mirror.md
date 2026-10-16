# 0056: git.pop.coop is the source, GitHub is a mirror

Date: 2026-10-14
Status: **decided 2026-10-14 by the maintainer** ("Abre uma nova ORG no
git.pop.coop e faz o GITHUB ser 100% um mirror de lá todos os repos da org
keel-linux"). The coordinator designed the details under the maintainer's
delegation of design calls.

## The problem

The CI of the project runs on GitHub Actions. Since 2026-10-10 the runs of
`common` stay in the state `queued` and do not start (the CodeQL runs of
common#51 and common#52, and of the branch `19.x`). A pull request with no
check result cannot merge (0053). The project cannot repair a queue that
GitHub operates.

The maintainer operates git.pop.coop, a Forgejo server (Forgejo 14.0.2).
It has Forgejo Actions and runners that the project can operate itself.

## The decision

1. **The organization `Keel-Linux` on git.pop.coop is the source of
   truth.** Every repository of the GitHub organization `Keel-Linux` is
   imported to <https://git.pop.coop/Keel-Linux> with its issues, pull
   requests, labels, milestones, releases and wiki. The import keeps the
   issue and pull request numbers, so `keel#147` points to the same item
   on both servers.

2. **GitHub `Keel-Linux` is a read-only push mirror.** Each repository on
   git.pop.coop has a push mirror to its GitHub copy. Forgejo pushes on
   every commit and every 8 hours. The push mirror deletes on GitHub every
   branch and tag that is not on git.pop.coop. Thus:
   - Do not push to a GitHub copy. Do not merge on GitHub.
   - The description of each GitHub copy says that it is a mirror of
     `git.pop.coop/Keel-Linux/<repo>`.
   - Issues and pull requests on GitHub are disabled after the import of
     the open ones.
   - Branch protection on GitHub is removed, because the mirror pushes
     merge commits that have no GitHub checks. Branch protection is on
     git.pop.coop.

3. **The credential of the mirror is one deploy key for each repository.**
   Forgejo makes an SSH key pair for each push mirror. Its public key is a
   deploy key with write access on that GitHub repository only. A key that
   leaks gives write access to one mirror, and git.pop.coop can push the
   correct content again. No personal token of the maintainer is kept on
   git.pop.coop. For this, the GitHub organization setting "allow deploy
   keys" is on since 2026-10-14.

4. **Pull requests, issues and CI move to Forgejo.** The CI is Forgejo
   Actions. The runners of the project are on the VM `Keel-Linux-Runner`
   (docs/infra/keel-lxc-2.md), registered to the organization
   `Keel-Linux` only, not to the server. Jobs of other organizations on
   git.pop.coop do not run there. The shared runner of git.pop.coop does
   not run Keel jobs.

5. **What changes in the workflows.** Forgejo reads `.forgejo/workflows`
   when it is there, and ignores `.github/workflows` then. Thus the port
   adds `.forgejo/workflows` and does not change the GitHub files. The
   changes:
   - Forgejo runs a called workflow inline, on the runner of the calling
     job. Thus each call of a reusable workflow in `.forgejo/workflows`
     has a `runs-on` line (`keel-lxc` for `lxc-trixie.yml` and
     `test-appliance.yml`, `keel-host` for the others). A call without
     `runs-on` waits and never starts.
   - The reusable workflows of `Keel-Linux/.github` on git.pop.coop use
     the label `keel-host` in place of `ubuntu-latest`. No job has sudo:
     the runner host has the packages, and `keel-need-packages` fails a
     job when one is missing.
   - The artifact actions are `forgejo/upload-artifact@v4` and
     `forgejo/download-artifact@v4` of code.forgejo.org. Forgejo does not
     support `actions/upload-artifact@v4` and later.
   - The security scan does not upload SARIF to GitHub code scanning
     (`github/codeql-action` is GitHub only). It keeps its reports as
     artifacts and fails on a finding, as before.

   The names of the required checks on git.pop.coop come from the commit
   statuses of the first green run on Forgejo, not from the GitHub names.

6. **The order of the cutover.** First the repositories that no other
   work changes. `keel`, `handbook`, `.github` and `apt` are last, because
   a push mirror replaces all of the GitHub content and would remove work
   that is not yet on git.pop.coop. `keel` and `handbook` get a new import
   at that time. `.github` and `apt` are already on git.pop.coop without a
   push mirror: their GitHub `main` is merged into the git.pop.coop `main`
   first, and the push mirror starts after the GitHub CI of `keel` and
   `handbook` is off (the Forgejo `.github` uses the label `keel-host`,
   which GitHub does not have).

7. **Archived repositories stay archived.** GitHub refuses a push to an
   archived repository. The archived repositories are imported and
   archived on git.pop.coop, and get no push mirror.

## What this does not change

- The GitHub Pages site `keel-linux.github.io` stays on GitHub. The push
  mirror updates its branch, and GitHub Pages builds it as before.
- The signing keys and the build host (0055). The CI runners hold no
  signing key.
- The rule of 0053: no merge on a red check, on Forgejo as on GitHub.

## Known gaps

- GitHub limited the self-hosted runner group to two workflows at
  `refs/heads/main`. Forgejo has no such limit: a workflow of any
  repository of the organization can use the Keel runners.
- A pull request from a fork is held until a maintainer approves it.
  Tested on 2026-10-15 with a user that is not a member of `Keel-Linux`:
  a fork pull request to `keel-keys` that changed `.forgejo/workflows`
  made 4 runs, each `need_approval`, and no job started. Forgejo 14
  (`services/actions/trust.go`) trusts only users with write access to
  the repository. Every other poster needs an approval for each run,
  unless a maintainer selects "always trust" for that user. Thus approve
  once, after reading the workflow change, and do not select "always
  trust". This is the default of Forgejo 14; no setting was changed.
  Registration on git.pop.coop is closed, so only existing accounts can
  open such a pull request.
- **Amended 2026-10-16 by the maintainer:** an approved fork job ran its
  steps on the VM itself, as a runner user (inithooks#48, label
  `keel-host`). Now a job of a pull request from a fork never runs on the
  VM. It runs only on the label `keel-container`, in a new rootless
  container. The runner enforces the rule, not the workflow, because a
  fork can change its workflow: forgejo-runner carries a trust gate patch
  and the host instances refuse a fork job. The approval of each run
  stays. Details: docs/infra/keel-lxc-2.md, "Fork pull requests run in a
  container".
- The Forgejo runners run one job for each start (`forgejo-runner
  one-job`), so the resets of the GitHub job hooks run before and after
  every job (docs/infra/keel-lxc-2.md). The GitHub runners
  `keel-lxc-2-1` to `keel-lxc-2-8` were stopped, disabled and removed
  from the GitHub organization on 2026-10-15.
