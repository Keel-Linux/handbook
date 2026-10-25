# Evidence: the GitHub bridge, part 2 (2026-10-16)

Decision: 0056, amendment of 2026-10-16. Part 1:
docs/evidence/2026-10-16-github-bridge.md.

| Item | Result | Detail |
| --- | --- | --- |
| 1. GitHub App | PASS | `keel-linux-bridge`, App ID 5345455, made by hand by the maintainer, installation 172084338 (all repositories). The key is in the container, root, 0600; the source was shredded. In the container: bot login `keel-linux-bridge[bot]`, an installation token, 57 repositories, none of the 52 bridged ones missing, rate limit 6850 for each hour. |
| 2. seed | PASS | 702 items of the import linked by number and title: 199 issues and 503 pull requests (keel 156, handbook 73, tracker 59, inithooks 35, ...). The state database after the test: 702 import links, 12 from git.pop.coop, 6 from GitHub. |
| 3. backfill | PASS | inithooks GitHub #21, #26, #40, #31 to git.pop.coop #52, #53, #54, #55; common #56 and keel #198, #195, #193, #192, #188, #186, #167, #163, #162, #161 to GitHub (common #53, keel #160 to #169). |
| 4. inithooks #31 and PR #48 | Done | a comment on inithooks#55 (the copy of GitHub #31) links PR #48, and it synced to GitHub #31; a comment on PR #48 links #55 and GitHub #31. |
| 5. Timer | On | `keel-bridge.timer`, every 2 minutes. |
| 6. Issue round trip | PASS | section 1 |
| 7. Comments, labels, state | PASS | section 1 |
| 8. Pull request bridged | PASS | the exact head commit, from the bot fork (section 2) |
| 9. Light CI on GitHub | PASS | 7 checks green on GitHub keel-keys#4 |
| 10. Heavy CI | PASS as designed | held until an approval; then the host runners refused the 4 jobs of the bridged pull request; the same commit in a branch of keel-keys got a trusted green run |
| 11. Merge on git.pop.coop, GitHub shows merged | PASS | keel-keys#9 merge commit 7bb074ddde0c; GitHub keel-keys#4 `MERGED` at 14:54:35 UTC, 4 s after the merge |
| 12. Mirror pushes start no run | PASS after a fix | section 3 |
| 13. Cleanup | Done | section 4 |

The time stamps are UTC. The contributor is the maintainer's GitHub
account `marcos-mendez`. The git.pop.coop side is the maintainer's
account `navigator`.

## 1. Issues

    13:15:14 GitHub keel-keys#2 opened, label documentation; the text names #1 and @octocat
    13:17:59 git.pop.coop keel-keys#6 by keel-bridge: label documentation, "#1" a link to GitHub,
             the mention neutralized, marker o=gh r=keel-keys id=2; GitHub #2 got the link note
    13:18:12 a comment on GitHub #2; a comment and the label bug on git.pop.coop #6
    13:21:53 both comment copies there, each credits the author by name and link; GitHub labels: bug, documentation
    13:22:16 git.pop.coop #6 closed  -> 13:25:41 GitHub #2 closed
    13:25:44 GitHub #2 reopened      -> 13:28:46 git.pop.coop #6 open
    13:29:07 git.pop.coop keel-keys#7 (a native issue) -> 13:33:02 GitHub keel-keys#3 "Mirrored from git.pop.coop"

## 2. The pull request

    13:33:24 GitHub keel-keys#4 from marcos-mendez:docs/where-to-contribute, head 4395424926f9
    13:36:52 git.pop.coop keel-keys#8 by keel-bridge from keel-bridge/keel-keys:gh-pr/4, head 4395424926f9 (the same commit)
             statuses: package/build, security, tests/tests, tests/package = "Blocked by required conditions"
    GitHub light CI on #4: build/trixie, package/changelog, security bandit, gitleaks, semgrep,
             shellcheck, tests/coverage: all pass (GitHub-hosted runners)
    13:37:18 a comment on GitHub #4; a comment and a review on git.pop.coop #8
    13:40:40 the comments and the review synced both ways ("reviewed this pull request on git.pop.coop")
    13:41:12 approved once by a throwaway write user, deleted after; "always trust" not selected
    13:41:22 the maintainer pushed 4395424926f9 to the keel-keys branch bridge/gh-pr-4 and opened keel-keys#9
    14:49:59-14:50:27 runs 20, 21, 22 (keel-keys#8): every job "refused by the Keel trust gate: event
             pull_request: the pull request is from keel-bridge/keel-keys, not from Keel-Linux/keel-keys"
    14:52:12-14:53:35 runs 23, 24, 25 (keel-keys#9): 4 jobs "Job succeeded"; combined status success
             (the wait between 13:41 and 14:49 was the queue of the host runners)
    14:54:31 keel-keys#9 merged with a merge commit, 7bb074ddde0c
    14:54:35 GitHub keel-keys#4 state MERGED, mergeCommit 7bb074ddde0c (the push mirror)
    then the bridge closed git.pop.coop #8 and deleted gh-pr/4 from its fork

The merge path is the documented one for a repository whose jobs do not
run on `keel-container`: the maintainer reads the bridged change and
pushes the exact commit into the repository for a trusted run. The
bridged copy keeps the approval and the trust gate. The text of the note
on #8 said "closed on GitHub", which is not correct for a merge.
keel-bridge#4 changes it to a merged note.

## 3. Mirror pushes and GitHub runs

The runs of all bridged repositories since Actions went on (11:00 UTC):
3 `pull_request` runs on keel-keys (the test), and 2 `dynamic` CodeQL
runs on common. CodeQL "default setup" of GitHub code scanning was still
on in 26 repositories, and it runs on each push to the default branch.
It is now `not-configured` in all 26 (anubis, buildtasks, common,
confconsole, coreruleset, fab, inithooks, keel-ejabberd,
keel-linux.github.io, keel-mariadb, keel-moodle, keel-odoo,
tkl-installer, tklbam, tklbam-profiles, tklbam-python-boto,
turnkey-chroot, turnkey-conffile, turnkey-netinfo, turnkey-pylib,
turnkey-sysinfo, turnkey-version, unit-mariadb, unit-postgresql,
unit-redis, webmin). The security scan of the light CI and of Forgejo
covers the same code. The 2 CodeQL runs and 7 older ones on common stay
`queued` on GitHub (the queue of common has not moved since 2026-10-10);
GitHub refuses to cancel or delete them (HTTP 409 and 403).

## 4. Cleanup

- GitHub keel-keys#2 and #3 deleted (GraphQL `deleteIssue`); git.pop.coop
  keel-keys#6 and #7 deleted.
- GitHub keel-keys#4 (merged), git.pop.coop keel-keys#8 (closed) and #9
  (merged) stay, because a merged pull request cannot be deleted. The
  README of keel-keys keeps the two lines "Contributing" of the test.
- The branch of the fork `marcos-mendez/keel-keys` is deleted. The fork
  itself stays: the `gh` token has no `delete_repo` scope. The maintainer
  can delete it.
- The throwaway approver user is deleted.
