# 0006: Organization guidelines

Date: 2026-09-26
Status: decided by the maintainer

1. **One organization for everything**, github.com/keel-linux: infrastructure,
   library and every appliance. No second organization for apps.
2. **Naming.** Infrastructure keeps its upstream name, no prefix: common, fab,
   buildtasks, inithooks, confconsole, tkldev, webmin, tklbam, tklbam-profiles,
   tklbam-python-boto, turnkey-pylib, turnkey-chroot, cdroots, keel. Appliances
   carry the `keel-` prefix: keel-core, keel-lamp, keel-lapp,
   keel-nginx-php-fastcgi, keel-wordpress, keel-moodle, keel-odoo, keel-redis,
   keel-ejabberd, and every future appliance (keel-ojs, keel-mastodon, ...).
   Renamed on 2026-09-26; GitHub redirects the old names.
3. **No global tracker.** Issues are enabled in every repository and live
   where the code lives. Cross-repository work is tracked by issues linking to
   each other, not by a central board.
4. **Tests and coverage are enforced in GitHub.** Every repository runs its
   tests on every pull request through GitHub Actions; the coverage gate is
   at least 90 percent for any repository and 95 percent for code the project
   writes (0003), measured by the tools decided in 0003 and 0004; the check is
   a required status and the default branch is protected, so a pull request
   that fails tests or the threshold cannot be merged. Runners: hosted Ubuntu
   runners for unit tests (they are plain virtual machines), a self-hosted
   runner on an LXC container of the build cluster for anything that builds
   an image or needs root, per brief section 10.
5. **The other standing rules stay:** IPv6 in every example and default,
   English everywhere, history never rewritten, upstream kept as a remote,
   system containers only, no attribution to any tool in commits or docs.

## Consequences

- `tkldev-setup` clones appliances as `<remote>/<app>`; with the prefix it
  must map `wordpress` to `keel-wordpress` when the remote is the
  organization. Small change on the tkldev fork, tracked in the org plan.
- Forks start below the 90 percent floor (docs/coverage-baseline.md); the gate
  is enabled per repository the moment its baseline job exists, with the
  threshold set to the measured number and raised as the plan in each
  COVERAGE.md is executed, never lowered. The 90 percent floor is the target
  every repository must reach before it is labeled maintained.
- Pushing workflow files and creating organization rulesets need token scopes
  the agent's GitHub login does not have today (`workflow`, `admin:org`); the
  maintainer grants them once.
