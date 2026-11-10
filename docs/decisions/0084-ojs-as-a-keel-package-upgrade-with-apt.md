# 0084: OJS 3.5 LTS as a Keel package, and an upgrade with apt

Date: 2026-11-10
Status: **proposed.** The maintainer asked for the application and for
the upgrade with apt on 2026-11-10. The maintainer did not decide the
design below. Nothing in it is built. The tests at the end must pass on
a real machine before the decision is accepted.

A first test by hand ran on 2026-11-10, on a real container on BR1
(`evidence/2026-11-10-ojs-3.5-php-8.4-first-test.md`). It corrected
some facts and it added some conditions. Each such place has the mark
"(first test)".

## What was asked

The maintainer wants a Keel appliance for PKP Open Journal Systems (OJS).
OJS has no Debian package. The maintainer wants `apt update` and
`apt upgrade` to move an installation to the next OJS release, so that
each version change is a simple transition. The maintainer said that
OJS is one of the most difficult applications to upgrade, and that the
method to do this with apt is not known.

## Facts checked

The facts were checked on 2026-11-10. docs.pkp.sfu.ca refused the fetch
tools (an Anubis challenge). The text of that site was read from its
source repository, `pkp/pkp-docs` (marked "docs repo" below).

| Item | Fact | Source |
| --- | --- | --- |
| Lines | 3.5 LTS, released 2026-07-01, end of life Q2 2029. 3.4 STS, end of life Q2 2027. 3.3 LTS, end of life Q2 2027 (the download page says "at least January 1, 2027"). 3.2 is end of life | pkp.sfu.ca/software/releases/; download page |
| Latest builds | 3.5.0-6 LTS, 3.4.0-12, 3.3.0-24. The release notes give 2026-10-31 for 3.5.0-6, the download page gives 2026-11-01 | download page; `docs/release-notes/README-3.5.0` at tag `3_5_0-6` |
| LTS rule | An LTS line has 3 to 5 years. An upgrade can go from one LTS to the next LTS directly, "from 3.3 to 3.5" | releases page; 3.5 release notebook (docs repo) |
| PHP, 3.5 | "PHP 8.2 or later". `PHP_REQUIRED_VERSION = '8.2.0'`. Composer `platform` is 8.2.0. No upper limit is written | `README.md` at `3_5_0-6`; pkp-lib `classes/core/PKPApplication.php` |
| PHP, 3.5 CI | The CI of `stable-3_5_0` and `main` runs PHP 8.2 and 8.3 only. It does not run PHP 8.4 | `.github/workflows/stable-3_5_0.yml`, `main.yml` |
| PHP 8.4 fixes | 3.5.0-6 fixes "TypeError on PHP 8.4" (#13139). pkp-lib#13140 "Fix Intl locale initialization on PHP 8.4" is closed | README-3.5.0; GitHub issues of pkp/pkp-lib |
| PHP, 3.4 | Composer `platform` is 8.0.2. The CI runs PHP 8.1, 8.2 and 8.3 | pkp-lib at the 3_4_0-12 submodule; `stable-3_4_0.yml` |
| PHP, 3.3 | "PHP 7.3.x, 7.4.x, 8.0.x, 8.1.x, or 8.2.x" | `docs/README.md` at `3_3_0-24` |
| Databases, 3.5 | "MySQL 5.7.22+, MariaDB 4.1+ or PostgreSQL 9.5+". The CI runs MariaDB, MySQL and PostgreSQL. The CI tests an upgrade to 3.5 from 3.3 and 3.4 on MySQL and PostgreSQL, but from 3.4 only on MariaDB | `README.md`; `stable-3_5_0.yml` |
| Debian 13 | php8.4 8.4.24-1~deb13u1, mariadb 1:11.8.6-0+deb13u1, postgresql-17 17.11-0+deb13u1. (first test) On 2026-11-10 a trixie node installs php8.4 8.4.27-1~deb13u1 | sources.debian.org API; first test |
| Upgrade steps | Stop the scheduled tasks and the job worker. Block access ("OJS does not support a maintenance mode yet"). Back up the database, `files_dir`, `public`, `config.inc.php`, `plugins` and local changes. Unpack the new package. Copy back the config and `public`. Run `php tools/upgrade.php check`, then `php -d memory_limit=2048M tools/upgrade.php upgrade` | upgrade guide (docs repo) |
| Duration | "may take from a few minutes up to several hours". If the upgrade runs out of memory "it will fail and you will need to restore from backup" | upgrade guide |
| Version table | The guide says that a build (`3.3.3-3`) has "No breaking changes or database migrations" | upgrade guide |
| Builds migrate | The code does not agree with the guide. `upgrade.xml` at `3_5_0-6` has a block `3.5.0.0` to `3.5.0.99` with 11 migrations. A build upgrade inside 3.5 runs them. (first test) The upgrade of 3.5.0-5 to 3.5.0-6 ran the 11 migrations and 3 code steps. They changed data. They did not change the schema of the test database | `dbscripts/xml/upgrade.xml`; first test |
| Refused jumps | `upgrade.xml` runs `abort` for a database from `2.0.0.0` to `3.2.9.9`. So 3.5 accepts only 3.3 and 3.4. The guide says "3.2.1-x can be upgraded to any version 3.3 or later". The code refuses 3.2 to 3.5 | `upgrade.xml`; upgrade guide |
| Failure | If a migration fails, the installer calls `down()` on the migrations that it ran, in reverse order. It stops at the first `DowngradeNotSupportedException`. No transaction holds the full upgrade. MariaDB commits each DDL statement | pkp-lib `classes/install/Installer.php` (`executeAction`) |
| `upgrade.php check` | It gets the latest version from pkp.sfu.ca. (first test) With no network it stops with an exception that it does not catch (`ConnectException`, "Could not resolve host"), and the exit code is 255 | pkp-lib `classes/cliTool/UpgradeTool.php`; first test |
| Maintenance | `isUnderMaintenance()` is true only when `installed` is Off or an upgrade runs in that process. No web code compares the code version with the database version (a search of pkp-lib found none) | `PKPApplication.php`, `PKPPageRouter.php` |
| Fixed paths | The base directory is the directory of `index.php`. `config.inc.php`, `cache/` and the default `public/` are under it. Pages load JavaScript from `<base>/lib/pkp/lib/vendor/` | pkp-lib `classes/core/Core.php`, `classes/config/Config.php`, `PKPTemplateManager.php` |
| `app_key` | The 3.5 migration writes `app_key` into `config.inc.php`. If a key exists, it does nothing. 3.5.0-6 encrypts stored credentials with it (#12074) | pkp-lib `I9895_AddAppKeyToConfigFile.php`; README-3.5.0 |
| Plugins | The gallery reads `plugins.xml` from pkp.sfu.ca (`plugin_gallery_urls`). It downloads the package, checks its MD5, copies it to `<base>/plugins/<category>/<name>`, and writes its schema and its `versions` row. `lib/pkp/tools/installPluginVersion.php` does the database step from the command line. The guide says: after an upgrade, "Use the Plugin Gallery to restore any custom plugins" | pkp-lib `PluginGalleryGridHandler.php`, `PluginHelper.php`, `PluginGalleryDAO.php`; upgrade guide |
| Plugin breaks | 3.5 does not load plugins with `.inc.php` files or with no namespace | 3.5 release notebook |
| Scheduled tasks, 3.5 | `php lib/pkp/tools/scheduler.php run` from cron every minute, with `task_runner = Off`. The Acron plugin is removed | admin guide, deploy-scheduled-tasks (docs repo) |
| Jobs, 3.4 and 3.5 | One method only: a worker (`php lib/pkp/tools/jobs.php work`), cron (`jobs.php run`) or the built-in runner. `jobs.php restart` stops the worker after the current job | admin guide, deploy-jobs |
| Signatures, Debian | The tarball has no published checksum and no signature (`.md5`, `.sha256`, `.asc`, `.sig` give 404). The tag `3_5_0-6` is a lightweight tag on an unsigned commit. Debian had `ojs` 2.2.4 (squeeze), removed from unstable in 2012 (bug 662828) | download URLs; GitHub API; tracker.debian.org/pkg/ojs |
| Other packagings | YunoHost `ojs_ynh` 3.5.0-4 keeps `config.inc.php`, `public` and each plugin that is not on its core list, replaces the rest of the tree, then runs `upgrade.php upgrade` on php8.2. `pkp/docker-ojs` is archived. The `pkp-upgrade` script of `pkp/containers` sets `installed = Off`, runs `upgrade.php upgrade`, and sets `installed = On`. It takes no backup | `ojs_ynh` `scripts/upgrade`; `pkp/containers` `pkp-upgrade` |

**The answer for trixie.** Only OJS 3.5 LTS is a candidate on PHP 8.4.
3.3 lists PHP up to 8.2 only. 3.4 is STS and ends in Q2 2027. 3.5 states
no upper limit and fixes PHP 8.4 bugs, but no PKP line lists PHP 8.4 as
tested. Keel's commissioning (0075) must prove 3.5 on PHP 8.4 and
MariaDB 11.8.

(first test) 3.5.0-6 was installed by an upgrade from 3.5.0-5 on PHP
8.4.27 and MariaDB 11.8.6. In one flow (a journal, a registration, a
submission with a file, the public pages and the administration pages)
it wrote no PHP error and no warning, and 59 deprecation messages.
3.5.0-5 does not show its public theme on this PHP: the theme plugin
stops with the `TypeError` that 3.5.0-6 corrects. Thus the first Keel
package is 3.5.0.6, and Keel packages no build before it. The PKP
checklist was not run, and the commissioning is not done.

If the commissioning fails, the options are:
1. Wait for a PKP fix and send the defect to pkp-lib.
2. Carry a Keel patch on the package.
3. Use PHP 8.2 from a third-party archive. This option is not
   recommended, because it adds a second PHP and a second security source.

## Why (brief section 10)

1. **Why the current approach is not enough.** The PKP procedure is a
   hand procedure of 15 steps. Each tool that automates it (YunoHost, the
   PKP containers) replaces a writable code tree. No tool takes a backup
   and stops in a known state when a migration fails.
2. **Whether it can be made to work.** It can. The Keel archive carries
   packages that Debian does not have (0074, 0083). LNMP gives nginx,
   MariaDB and PHP-FPM 8.4. The pair, the file replication and the
   writable gate exist (0049, 0050, 0068).
3. **Why this is better.** A package makes the code read-only and
   versioned. The maintainer scripts do the PKP steps in the same order
   each time. They refuse a jump before a file changes, and they leave a
   dump and a file copy that match the old package.

## Proposed

### 1. Stack and line

`keel-ojs` is an application layer on LNMP (0059), with MariaDB. LNPP
has no PHP. The first line is 3.5 LTS. 3.3 and 3.4 are not packaged.

(first test) LNMP does not have all the PHP modules that OJS needs. The
package depends on these Debian packages: `php8.4-bcmath`, `php8.4-curl`,
`php8.4-gd`, `php8.4-intl`, `php8.4-mbstring`, `php8.4-xml` and
`php8.4-zip`.

### 2. The source and the build

A source repository `Keel-Linux/ojs-deb`, in the pattern of
`vaultwarden-deb` (0074). The build downloads
`ojs-3.5.0-6.tar.gz` from pkp.sfu.ca. The source pins its sha256 (0012).
PKP signs nothing, so the build also compares the tarball with the git
tag `3_5_0-6` and its submodule commits. The tarball adds `vendor/` and
the built JavaScript, and the build lists that difference in the build log.

### 3. Package names and versions

| Package | Content |
| --- | --- |
| `ojs-3.5` | The code of one line. Version `3.5.0.6-1` (the PKP `-6` becomes `.6`, because `-` starts the Debian revision) |
| `ojs-3.5-plugin-NAME` | One gallery plugin, from its `plugins.xml` release, checked by sha256 that the source pins |
| `ojs-common` | The paths, the system user setup, the systemd units, the nginx routes and the `ojs-upgrade` script |

`ojs-3.5` and a future `ojs-3.7` both provide `ojs-code` and conflict
with each other. `apt upgrade` moves only inside a line, because it never
installs a new package name. No meta package moves the line. A line
change is a deliberate act after an advisory (0073 item 6). The plugin
packages depend on their line, so the operator replaces all of them in
one command: `apt install ojs-3.7 ojs-3.7-plugin-NAME ...`.

### 4. Layout

| Path | Owner | Content |
| --- | --- | --- |
| `/usr/share/ojs/` | root, read-only | The code and the bundled plugins |
| `/usr/share/ojs/config.inc.php` | link | to `/etc/ojs/config.inc.php` |
| `/usr/share/ojs/cache` | link | to `/var/cache/ojs` (www-data) |
| `/usr/share/ojs/public` | link | to `/var/lib/ojs/public` (www-data) |
| `/var/lib/ojs/files` | www-data, 0750 | `files_dir`, never under the web root |
| `/var/backups/ojs/` | root, 0700 | the dump and the file copy of each upgrade |
| `/var/log/ojs/` | root | the log of each `upgrade.php` run |

nginx has the web root `/usr/share/ojs`. It sends PHP to PHP-FPM and
serves static files, `public/` and `lib/` included, because pages load
JavaScript from `lib/pkp/lib/vendor/`. It runs no PHP file except
`index.php`. It refuses `config.inc.php`, `cache/`, `dbscripts/` and
`tools/`.

`/etc/ojs/config.inc.php` is not a conffile. A conffile prompt stops an
unattended run, and OJS writes `app_key` into the file. The first boot
writes the file from `config.TEMPLATE.inc.php` and the manifest values.
It is root:www-data 0640. `app_key`, `salt` and `api_key_secret` are
manifest secrets with `shared: true`, so both nodes of a pair decrypt
the same rows. The first boot writes `app_key`, so the migration does
nothing to the file.

(first test) The first boot runs `tools/install.php` as www-data, with
the file already in place and read-only for www-data. This is
necessary, not only safe:
- The installer makes a new `app_key` each time. With a file that it
  can write, it replaces the key of the manifest. It also writes an
  empty `allowed_hosts` and an empty `time_zone`.
- With a read-only file, the installer changes nothing in it and the
  key stays. But `installed` stays `Off`. The first boot, as root, sets
  `installed = On` after the installer ends with code 0.
- The installer needs `files_dir`, `public` and `cache` writable, and
  no other path.
- `base_url` must have a host name. With an IPv6 address in brackets,
  the session cookie gets a domain that curl refuses, and the login
  fails. The behaviour of a browser was not tested.
- The install took 85 seconds. The test report says that most of this
  time is the download of two data sets (ROR and the IP database of the
  usage statistics), so the first boot needs the network. This was not
  measured separately.

### 5. Plugins

The code tree is read-only, so the gallery cannot install a plugin.
Keel sets `plugin_gallery_urls` to an empty list. A gallery plugin comes
as an `ojs-3.5-plugin-NAME` package under
`/usr/share/ojs/plugins/<category>/<name>`. Thus a plugin has the same
version on both nodes, and a package upgrade never deletes it. The
gallery also writes the plugin's schema and `versions` row. So the
plugin package's `postinst` runs `installPluginVersion.php` on the
writable node only, in the same way as the core migration. An operator
who needs a plugin that is not packaged asks for a package. A local
plugin directory is an open test (see below).

### 6. `preinst`

`preinst` changes nothing. It runs on `upgrade`. It also runs on
`install` when a database or `/etc/ojs/config.inc.php` exists, because a
line change installs a new package name. If one check fails, it exits 1.
On an upgrade, dpkg then runs the old `postinst abort-upgrade`, and the
old version stays installed and configured.
0. **Failed mark.** Refuse while `/var/lib/ojs/upgrade-failed` exists.
   dpkg records the version of a failed migration as installed (section
   7), so without this check the next build runs `upgrade.php` on a
   half-migrated schema.
1. **Database version.** Read `versions` (`product_type =
   'core'`, `current = 1`) with the stack's account. Do not use
   `upgrade.php check`, because it needs the network.
2. **Jump.** Allow the same line at the same or a later build. For
   `ojs-3.5`, allow a database at 3.3 or 3.4 (an import from outside
   Keel). Refuse a database at 3.2.9.9 or lower (as `upgrade.xml` does).
   Refuse a database that is newer than the new code.
3. **PHP.** `PHP_VERSION` is at least the line's required version.
4. **Disk.** The free space on `/var/backups` is at least the size of the
   database plus `files_dir` plus `public`, plus 20 %.
5. **Pair state.** Read the role of the node (0049, 0054 pattern). A
   writable node needs a writable database. A standby needs a reachable
   primary.
6. **Plugins.** Each active plugin in `versions` has a package for the
   new line. If not, refuse, and name the plugin.

### 7. `postinst configure`

On a standby, or before the first boot, `postinst` clears
`/var/cache/ojs` and exits 0. If the database version equals the code
version, it does the same. Otherwise, on the writable node, it calls
`ojs-upgrade`:
1. Stop `ojs-scheduler.timer`. Run `jobs.php restart`, then stop
   `ojs-jobs.service`.
2. Write the maintenance mark. nginx answers every OJS path with 503 and
   a notice.
3. Dump the database (`mariadb-dump --single-transaction`). Copy
   `files_dir` and `public` to `/var/backups/ojs/<old version>-<date>/`.
   Copy `/etc/ojs/config.inc.php` too.
4. Run `php -d memory_limit=2048M tools/upgrade.php upgrade` as www-data.
   Write the log to `/var/log/ojs/`.
5. On success, clear the cache, reload PHP-FPM, start the jobs service
   and the timer, remove the mark, and exit 0. (first test) The reload
   is new. OPcache holds the old code for `revalidate_freq` seconds (30
   in the image). The test did not measure old code after the change,
   but the setting permits it.

**If the migration fails**, `ojs-upgrade` keeps the maintenance mark and
writes `/var/lib/ojs/upgrade-failed`. It keeps the jobs and the timer stopped.
It sends an alert (0063) and exits 0. It does not exit non-zero, for
these reasons:
- A non-zero `postinst` leaves the package half-configured.
- Then each later apt run calls `postinst` again. That runs
  `upgrade.php` again on a half-migrated schema.
- It also blocks the daily security run of cron-apt (0073) on that node.

The operator then runs one of two commands:
- `ojs-upgrade --retry`. It continues after a fix, for example more memory.
- `ojs-upgrade --restore`. It restores the dump first, then the files
  and the config. Then it installs the old `.deb` from the pool (0016)
  with `--allow-downgrades`. The dump comes first, or the old `preinst`
  refuses a database that is newer than its code.

A monit check fails while the failed mark exists.

**What apt can roll back.** apt can install the old code again, if the
old `.deb` is in the pool. apt cannot roll back the database or
`files_dir`. Old code does not run on a newer schema. So a rollback is
always all three parts together: the dump, the file copy and the old
package.

### 8. Unattended upgrades

Each OJS build upgrade runs the migrations of its line (see "Facts
checked"). In the first test they changed data only, but a different
build can change the schema. So no OJS upgrade is code-only, and none
goes to Keel trixie-security. cron-apt
does not take OJS. In `simple` mode, the operator runs `apt upgrade`. In
a pair, the operator upgrades one node at a time (0073 item 6). A line
change (3.5 to 3.7) is always a deliberate act. 3.5 removed old plugin
formats, and the next line can do the same.

The operator does not look for a new build. The node sends a message
through ntfy when an OJS upgrade waits
([0085](0085-a-node-tells-the-administrator-when-an-upgrade-waits.md)).
The OJS packages carry the field `Keel-Upgrade-Note` of that note, which
tells the operator that the upgrade migrates the database and that the
site is in maintenance during the migration. A new line is a new package
name, so apt does not show it as an upgrade, and the node sends no
message for it. The application page (0077) announces a new line.

A later note can allow a build upgrade inside a line on a timer in
`simple` mode, after 2 build upgrades pass the tests below.

### 9. The pair

Both nodes run the same package version. One database is replicated.
`files_dir` and `public` replicate by Syncthing (0050, 0068
`state.replicate`). `cache/` does not replicate.
1. Upgrade the standby first. It gets the new code and does not migrate.
   It shows the replica notice (the 0082 pattern).
2. Upgrade the VIP holder last. It is the writable node, so `postinst`
   runs the migration there. The migration replicates to the standby.
3. The scheduler timer and the jobs worker run only on the writable node.
   The writable gate starts them after a promote.
4. Between steps 1 and 2, a promote must not serve new code on an old
   schema. OJS has no such check, so the gate compares the code version
   and the database version. If they differ, the gate keeps the
   maintenance mark and alerts.

## Rejected alternatives

- **A writable code tree that the package replaces (YunoHost pattern):**
  the web user writes PHP code, dpkg does not own the files, and a
  plugin is on one node only.
- **One package name for all lines:** `apt upgrade` would cross a line
  with no deliberate act.
- **`config.inc.php` as a conffile:** the dpkg prompt stops an unattended
  run, and OJS writes the file.
- **`postinst` that exits non-zero on a failed migration:** the
  half-configured loop described in section 7.
- **The migration in a background unit after `postinst`:** an operator
  who runs apt does not see the result and the log in that apt run.
- **OJS 3.3 or 3.4 on trixie:** 3.3 lists PHP up to 8.2 only. Both end
  in 2027, and 3.4 is STS.
- **A PHP 8.2 from a third-party archive:** a second PHP and a second
  security source on the base.
- **The PKP container image:** no container runtime in Keel.

## Not decided / tests before acceptance

Each test makes an evidence file (0053). Use 2 LXC on BR1 and 1 on BR2,
with netem (0075).
1. Install 3.5.0-6 on PHP 8.4 and MariaDB 11.8. Run the PKP checklist
   (upgrade guide step 11) and check the PHP-FPM log for deprecations.
   (first test) Partly done: 3.5.0-6 came from an upgrade, not from a
   new install, and the checklist was not run. The log is in the
   evidence.
2. Upgrade 3.5.0-5 to 3.5.0-6 with the package. Measure the duration.
   Check the 11 build migrations.
   (first test) Done by hand, with no package: code 0 in 1.2 seconds on
   a database with one journal and one submission. The 11 migrations
   ran. The duration on a large journal is not known.
3. Upgrade a 3.3.0-24 dataset to 3.5 on MariaDB 11.8. PKP CI does not
   test this path.
4. Stop the migration (kill the process, or set a low `memory_limit`).
   Then run `ojs-upgrade --restore`. Compare the database and the files
   with the state before the upgrade.
5. Paths and plugins:
   - Run `upgrade.php` as www-data with a read-only `config.inc.php`
     that has `app_key`. No step writes the file.
     (first test) Passed for 3.5.0-5 to 3.5.0-6: the file has the same
     sha256, the process opened it one time and read-only, and no file
     of the code tree changed. The migration that writes `app_key` is
     in the block of 3.1 to 3.4, so only test 3 can show its behaviour.
   - The links for `config.inc.php`, `cache` and `public` work with
     PHP-FPM, OPcache and Smarty.
     (first test) Passed.
   - `plugin_gallery_urls = '[]'` empties the gallery. The upload of a
     plugin fails cleanly on a read-only tree.
     (first test) The install function of the upload form refuses
     cleanly ("Failed to copy plugin to destination folder"), with no
     directory and no `versions` row. It was called from the command
     line, not through the form. The gallery setting was not tested.
   - A plugin package with `installPluginVersion.php` gives the same
     schema and `versions` row as a gallery install.
   - A local plugin directory (a link to `/var/lib/ojs`) loads, or not.
6. Pair: upgrade the standby, promote it, and check that the gate keeps
   the maintenance mark. Then complete the upgrade and run the 0075
   passes. Check that the timer and the worker move with a promote.
7. Measure the dump and the file copy for a journal of about 10 GB.
   Check the disk rule of `preinst`.
   (first test) A new installation with one submission already gives a
   dump of 31 MB and a file copy of 122 MB.
8. Run a line change with a test package `ojs-3.6` (from `main`) and
   check that `preinst` runs on `install`.

Not verified in this note:
- The Debian WNPP search (refused) and the reason of bug 662828 (a
  challenge page).
- An Ubuntu PPA and Bitnami: not checked.
- The database versions in PKP CI: `pkp/pkp-github-actions` not read.
- The web code on a code and schema mismatch: a search found no check.
  Test 6 covers it.
- The package names are proposals.

## Sources

- <https://pkp.sfu.ca/software/releases/>
- <https://pkp.sfu.ca/software/ojs/download/>
- <https://pkp.sfu.ca/ojs/xml/ojs-version.xml>
- <https://pkp.sfu.ca/ojs/download/ojs-3.5.0-6.tar.gz> (and the `.md5`, `.sha256`, `.asc`, `.sig` names, all 404)
- docs.pkp.sfu.ca pages, read from the source files in
  <https://github.com/pkp/pkp-docs> (main): `dev/upgrade-guide/en/index.md`
  (<https://docs.pkp.sfu.ca/dev/upgrade-guide/en/>),
  `dev/release-notebooks/en/3.5-release-notebook.md`,
  `admin-guide/en/getting-started.md`, `deploy-scheduled-tasks.md`,
  `deploy-jobs.md` (<https://docs.pkp.sfu.ca/admin-guide/en/>)
- <https://github.com/pkp/ojs/tree/3_5_0-6>: `README.md`,
  `docs/release-notes/README-3.5.0`, `dbscripts/xml/upgrade.xml`,
  `config.TEMPLATE.inc.php`, `.github/workflows/stable-3_5_0.yml`
- <https://github.com/pkp/ojs/blob/main/.github/workflows/main.yml>
- <https://github.com/pkp/ojs/blob/3_4_0-12/.github/workflows/stable-3_4_0.yml>
- <https://github.com/pkp/ojs/blob/3_3_0-24/docs/README.md>
- <https://github.com/pkp/pkp-lib/tree/c4c0aa8c5293254ad253544aea230b1b607d5249> (the 3_5_0-6 submodule): `composer.json`, `classes/install/Installer.php`, `classes/cliTool/UpgradeTool.php`, `classes/core/Core.php`, `classes/core/PKPApplication.php`, `classes/config/Config.php`, `classes/plugins/PluginHelper.php`, `classes/plugins/PluginGalleryDAO.php`, `controllers/grid/plugins/PluginGalleryGridHandler.php`, `classes/migration/upgrade/v3_5_0/I9895_AddAppKeyToConfigFile.php`
- <https://github.com/pkp/pkp-lib/issues/13139>, <https://github.com/pkp/pkp-lib/issues/13140>
- <https://github.com/pkp/docker-ojs> (archived), <https://github.com/pkp/containers>
- <https://github.com/YunoHost-Apps/ojs_ynh>
- <https://tracker.debian.org/pkg/ojs>, <https://sources.debian.org/api/src/ojs/>
- <https://sources.debian.org/api/src/php8.4/>, <https://sources.debian.org/api/src/mariadb/>, <https://sources.debian.org/api/src/postgresql-17/>
