# 0075: A commissioning test for every appliance, and a release gate on it

Date: 2026-11-05
Status: **decided by the maintainer, 2026-11-05** (a structural test in every
appliance that checks the commissioning of the LXC and of the VM: boot,
passwords, all of it). The design below is decided by the coordinator under
the maintainer's delegation.

## What was found

On 2026-11-05 a fresh CT was made from each image in the Proxmox index on
BR2 (core 19.0-11, lnmp 19.0-5, lnpp 19.0-6, mariadb 19.0-10, odoo 19.0-13,
ntfy 19.0-3, wordpress 19.0-11). Every image had the same defects:

- On an LXC the first boot has no console, so every first boot question
  (root password, name, database password, role, cloud, alert email) is
  not asked and is left to keel-init.
- Nothing at login tells the operator to run keel-init.
- The database accounts stay without a password until keel-init runs.
- postfix keeps `myhostname = keel-core`.
- keel-wordpress does not finish its installation, also with keel-init in
  a 40x120 terminal: no `wordpress` database, no `wp-config.php`, HTTP 503.
  The cron sends a mail to root every 5 minutes. The lnmp check database
  `keel_check` is in the WordPress image.

All these images passed CI. The CI job `test-appliance` boots the published
layer with its own preseed. It never does what an operator does: make a
CT from the template in Proxmox, log in, and answer the questions. No
test did that, so no test found the defects. On 2026-11-05 every image and
the Proxmox index were withdrawn from the mirror.

## Decision

1. **One shared runner.** The commissioning test is one program,
   `keel-commission`, in `keel-linux/.github` (`bin/`, with its libraries
   in `lib/commission/`). It is shell, tested with bats under kcov at
   95% or more (decision 0003). It uses no container runtime.

2. **A contract in every appliance.** Each appliance repository has
   `tests/commission.yaml`. It declares:
   - every first boot question, with the hook that asks it;
   - for each secret, what it unlocks and how to prove it: root by `su`
     and SSH, a database account by a TCP login with that password, an
     application admin by its own login (for example `wp user check-password`
     or the HTTP login);
   - the URLs that must answer, and with which status;
   - the services that must be active;
   - what must not be in the image (for example `keel_check` in a layer on
     top of lnmp or lnpp).

   The test-shell job of every appliance fails when the contract is
   missing or does not match the schema. So no appliance can skip it.

3. **What the runner checks.** It runs four passes on a fresh machine each
   time:
   - **LXC, interactive.** `pct create` from the template as an operator
     does, no preseed, first boot. The first boot defers the questions and
     does not fail. A login shell on a terminal with a size shows that
     keel-init must run (or starts it). keel-init is driven with known
     answers that are not the defaults. Then each secret is proved by a
     login with it.
   - **LXC, preseeded.** The secrets are in the instance description. No
     question is asked, and the same proofs pass.
   - **VM from the ISO, interactive.** `qm create`, install from the ISO,
     the same questions and proofs. Screenshots come from
     `qm monitor screendump`.
   - **Hygiene, after every pass:** no `fatal` in the inithooks log, postfix
     `myhostname` equal to the machine name, no mail to root after the
     cron has run 10 minutes, every declared service active, every declared
     URL with its status, and nothing that the contract forbids.

   Each pass writes a record: the template or ISO sha256, the site, the
   answers it used (never the secret values), each check with pass or fail,
   and the screenshots.

4. **A release gate.** keel-release writes an index record for a template
   only when there is a passing commissioning record for that exact sha256
   on BR1 and on BR2. The ISO is published only with a passing VM pass for
   that exact ISO on both sites. A failed or missing pass stops the
   release, and the error names the pass and the check.

5. **The evidence file** of each release is made from these records, with
   the screenshots of the installation, of the application and of Webmin.
   This is the evidence the publish gate requires.

6. The runner is first tested against the defective images that were
   withdrawn on 2026-11-05. It must fail on every defect listed above.
   Only then are the hooks fixed.

## Not chosen

- More checks in `test-appliance`: that job boots the published layer, not
  the template made from the branch, and runs on a runner without Proxmox.
  It cannot do what an operator does. It stays as it is.
- A copy of the test in each repository: copies drift. Only the contract
  belongs to the appliance.
- Answers by pressing Enter on the defaults: a generated password cannot be
  checked after, so that test proves nothing about the passwords.

## Consequences

- A release needs BR1 and BR2 reachable, and some minutes per image and per
  site. This is the price of the publish gate, which already applied.
- Each new first boot question or secret is a change of the contract in the
  same pull request.
