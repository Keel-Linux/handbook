# 0007: License of new code, and review policy while the team is one person

Date: 2026-09-26
Status: decided by the maintainer

## License

New code written by the project (the `keel` library and CLI, the transition
and keyring packages, new build tooling, new modules added to forks) is
licensed **GPL-3.0-or-later**. Reasons, from the survey of the upstream
repositories on 2026-09-26: fab, confconsole, tklbam, deck and turnkey-chroot
are GPL-3-or-later; inithooks is GPL-2-or-later; buildtasks is AGPL-3-or-later
in its script headers; the appliance recipes (common, tkldev, core, wordpress,
odoo, tklbam-profiles) declare no license at all. GPL-3-or-later lets code move
between the library and the GPL forks in both directions, and GPL-2-or-later
code accepts it. AGPL was considered and kept as an option for a future network
service repository, decided there, because AGPL code could not move into the
GPL-3 forks.

Forks keep their upstream license unchanged. Forks whose upstream declares
none get a LICENSE file stating GPL-3-or-later for the project's own
contributions, with the upstream origin named in the README, and that fact is
recorded in each fork's first pull request so it is reviewable.

## Review policy

Branch protection required one approving review. GitHub does not let the
author of a pull request approve it, and the organization has one member, so
no pull request could be merged, admins included. Decided: **zero required
approvals** for now, with everything else unchanged (required check
`tests / coverage`, strict up-to-date branches, dismiss stale reviews, linear
history, no force pushes, no deletions, enforced for admins). The test gate
remains the merge gate. The approval requirement returns to one the day a
second maintainer with write access exists, and this note is updated then.

## Justification (three parts, brief section 10)

1. Why the previous state does not work: one required approval with one
   member is a deadlock, proven on pull request keel-linux/keel#1.
2. Whether it could be made to work otherwise: a second account of the same
   person would satisfy the rule in form only; a bot approver would make the
   review meaningless while looking like one.
3. Why this is better: the rule that actually protects the code, tests and
   coverage on every pull request, stays enforced, and the honest state (one
   maintainer) is written down instead of simulated.

## Amendment, same day: merge commits, not linear history

The bootstrap protection required linear history, which forces rebase or
squash merges. Both rewrite the commits of a pull request, and the brief
(section 10) forbids squashing and rewriting history. The requirement was
removed on every protected branch; pull requests are merged with merge
commits, which keep every original commit and record the integration point.
The remaining rules are unchanged.
