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

## Amendment 2026-10-16: contributions on GitHub and on git.pop.coop

Status: **decided 2026-10-16 by the maintainer** ("não quero perder os
contribuidores que ajudaram por lá"). The design was approved in chat.
The coordinator decided the details under the maintainer's delegation of
design calls. The place of the bridge container was the maintainer's own
choice.

### The problem

Point 2 of this note turned off issues and pull requests on GitHub. The
people who contributed on GitHub lost their way in. The maintainer wants
contributions on GitHub and on git.pop.coop, with issues and pull
requests bridged. git.pop.coop stays the source.

### The decision

1. **Pull requests and issues are on again on GitHub**, on the public
   repositories that are not archived (51 on 2026-10-16, and
   `keel-bridge`). The private repositories (`apt`, `demo-repository`) and
   the archived ones stay closed. The description of each GitHub copy is
   now "Mirror of git.pop.coop/Keel-Linux/<repo>. Issues and PRs welcome
   here or there."
2. **A light CI on GitHub-hosted runners, like OCA.** Each repository has
   `.github/workflows` that run on `pull_request` only: unit tests, lint,
   the package build in a `debian:trixie` container and the security
   scan. They call the `github-*.yml` reusable workflows of
   `Keel-Linux/.github`, which use `ubuntu-latest` only, hold no secret
   and have `permissions: contents: read`. No workflow has a `push`,
   `schedule`, `pull_request_target` or `workflow_run` trigger, so a push
   of the mirror starts no run. The full CI stays in `.forgejo/workflows`
   on git.pop.coop.
3. **The bridge, `Keel-Linux/keel-bridge`.** It polls both APIs every 2
   minutes, so it needs no inbound webhook.
   - A GitHub issue gets a copy on git.pop.coop, and a git.pop.coop issue
     gets a copy on GitHub. Each copy starts with "Mirrored from ...",
     the link to the original and the name and link of its author. The
     original gets a comment with the link to the copy.
   - Comments, labels (the names that exist on both sides) and the open
     or closed state sync both ways. Edits of the title and the body go
     from the original to the copy.
   - A GitHub pull request gets a copy on git.pop.coop. The bot pushes the
     exact head commit of the original to the branch `gh-pr/<n>` of its
     own fork `keel-bridge/<repo>`, and opens the pull request from that
     fork. Reviews sync both ways as comments that name the state.
   - The merge is on git.pop.coop only, with a merge commit. The push
     mirror then puts the original head commit on the GitHub `main`, and
     GitHub shows the original pull request as merged. If GitHub does not
     do this within 15 minutes, the bridge closes the original with a link
     to the merge commit.
   - Pull requests that start on git.pop.coop stay there.
4. **The issue numbers of the two sides are different.** The bridge keeps
   an ID map in SQLite, and each copy has the link to its original in its
   body. A copy turns `#N` into a link to the origin side. It gives other
   references (`owner/repo#N`, `#N` in code or in a heading) a word
   joiner, so a closing keyword does not act on the wrong server. It also
   neutralizes `@mentions`, so a copy does not notify an unrelated user
   of the same name. The items of the import of 2026-10 have the same
   number on both sides; `keel-bridge seed` links them.
5. **The 4 open issues of the inithooks archive** (GitHub inithooks#21,
   #26, #31 and #40) are unlocked and in the sync, with copies on
   git.pop.coop. GitHub inithooks#31 is what inithooks PR #48 fixes.

### Why a new tool

No maintained tool does this. The closest, `eleboucher/forgesync`, copies
issues and comments from a GitHub push mirror back to Forgejo. It has no
path from Forgejo to GitHub and no bridge for pull requests. Thus
`keel-bridge` is a small Python program (standard library, plus
python3-jwt for the GitHub App) with tests on in-memory servers, and a
coverage gate of 95 percent.

### The loop rules

1. The bridge skips every item and comment that the bridge bot of that
   side wrote.
2. The bridge skips every item and comment that has a bridge marker
   (`<!-- keel-bridge:v1 o=<side> r=<repo> id=<id> -->`). Only the last
   marker of a text counts, and a copy escapes each `<!--` of the user
   text, so a user cannot make a marker.
3. Before the bridge creates a copy, it writes a "pending" row. If the
   row is still there at the next pass, the bridge looks for the marker on
   the other side before it creates the copy again. Thus each operation is
   idempotent.
4. The open or closed state and the labels are compared with the last
   synced value. The side that changed wins. If both sides changed,
   git.pop.coop wins.
5. An item that fails 3 times is left until it changes again, so one bad
   item does not block a repository.

### The trust boundaries

| Part | What it can do | What it cannot do |
| --- | --- | --- |
| GitHub light CI | run the pull request code on a GitHub-hosted runner, with a read-only token | read a secret; use a self-hosted runner (the organization setting for self-hosted runners is "none"); start on a mirror push |
| GitHub App `keel-linux-bridge` | issues write, pull requests write, metadata read; it asks for no more in each installation token | write code, workflows or settings; it has no webhook |
| Forgejo user `keel-bridge` | issues and pull requests write on the bridged repositories (team `bridge`), code read, its own forks | write code or Actions on a Keel-Linux repository, merge, change a setting; it is not an administrator |
| Heavy CI on git.pop.coop | run after a maintainer approves the run, on `keel-container` only | start by itself (the pull request comes from a fork of a user that has no Actions write, so Forgejo holds every run); run on a host runner (the trust gate refuses a fork job) |
| Bridge container | hold the two tokens; open outbound HTTPS | accept a connection from anything |

The bot does not push to a branch of a Keel-Linux repository, and it has
no push right there. A pull request from a branch of the same repository
is trusted: Forgejo does not hold its run (`services/actions/trust.go`),
and the trust gate of the runner lets it run on the VM. Bridged code from
GitHub is not trusted. Thus the bot pushes it to its own fork only. Then
three controls apply to each bridged pull request:

1. Forgejo holds each run until a maintainer approves it once.
2. The host runners (`keel-host`, `keel-lxc`) refuse its jobs (the trust
   gate of the amendment above). It can run only on `keel-container`, in
   a new rootless container.
3. The forks of the bot have Actions, issues and the wiki off.

Branch protection for `gh-pr/*` is thus not necessary. A repository
whose jobs do not run on `keel-container` shows red checks on a bridged
pull request. This is expected and safe. The maintainer reads the
change, and then pushes the branch into the repository (or merges it
after a trusted run). Tested on 2026-10-16: keel-keys#5 from
`keel-bridge:gh-pr/test` waited for approval, and after the approval the
host runners refused all 4 jobs before any step
(docs/evidence/2026-10-16-github-bridge.md). Do not select "always
trust" for `keel-bridge`.

### Where the bridge runs: the accepted risk

The maintainer chose to put the bridge container on the CI runner VM
`Keel-Linux-Runner`, the VM where pull request code runs. It is not on
the build host, where the signing keys are. The risk is that a job that
escapes to root on the VM can read the two tokens. The controls:

- The container is an unprivileged LXC container (idmap 2000000), with no
  nesting and no shared mount with a runner user.
- It is on its own bridge `kbr0`, not on `lxcbr0`. The nft table
  `inet keel_bridge` refuses every connection to it: from the job
  containers, from the runner users (`meta skuid 1100-1199`), from root
  and from the LAN. It can open outbound HTTPS and DNS only.
- The tokens are files in the container, root only (0600). The service
  reads them as root, then changes to the user `keel-bridge` before it
  opens a connection. The fetch from GitHub runs with no token, and the
  git credential helper is scoped to git.pop.coop.
- The tokens have the scopes in the table above. A stolen token can post
  and edit issues and pull requests, and close them. It cannot change
  code, a workflow or a setting, and it cannot merge.

docs/infra/keel-lxc-2.md has the rebuild record.

### Known gaps

- The commits of a bridged pull request are the exact commits of the
  original, so their messages are not changed. A `Fixes #N` in a commit
  message can close item N of git.pop.coop on merge. Read the commit
  messages before the merge.
- After a bridged pull request is closed or merged, a reopen is not
  synced.
- A deleted comment stays on the other side. Comment edits go from the
  original to the copy only.
- A review syncs as a comment, not as a review of the other server.
- A change of the base branch of a GitHub pull request is not synced.

### State on 2026-10-16

- Pull requests and issues are on for the 51 repositories and
  `keel-bridge`. GitHub Actions is on, with GitHub-owned actions only,
  read-only tokens and approval for every outside contributor, except in
  5 repositories: `keel`, `keel-nodejs-nginx`, `keel-nodebb`,
  `keel-wordpress` and `keel-postgresql`. Their light CI pull requests
  are red on Forgejo for reasons outside this change (keel#184,
  keel-nodejs-nginx#6, keel-nodebb#21, keel-wordpress#20,
  keel-postgresql#20). Turn Actions on there after each one merges.
- The bridge container, the Forgejo bot, its team and the code are in
  place. The GitHub App needs an owner of the GitHub organization in a
  browser (keel-bridge `deploy/github-app-manifest.html`). The bridge
  timer starts after that, then `keel-bridge seed` and
  `keel-bridge backfill`, then the end-to-end test.
