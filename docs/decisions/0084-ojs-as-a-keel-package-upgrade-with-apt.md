# 0084: OJS 3.5 LTS as a Keel package, and an upgrade with apt

Date: 2026-11-10
Status: **accepted by the maintainer, 2026-11-10** ("sim aceito", after
the results of the first test), as the direction for OJS. The
maintainer asked for the application and for the upgrade with apt on
the same day. A first prototype of the packages exists in
`Keel-Linux/ojs`. Nothing is released. The tests at the end must pass on
a real machine before a package or an image is released (0075). A test
that fails changes this note before the build continues.

A first test by hand ran on 2026-11-10, on a real container on BR1
(`evidence/2026-11-10-ojs-3.5-php-8.4-first-test.md`). It corrected
some facts and it added some conditions. Each such place has the mark
"(first test)".

A third test by hand ran on the same day, on a second container on BR1
(`evidence/2026-11-10-ojs-3.3-to-3.5-upgrade-and-restore.md`). It
upgraded a 3.3.0-24 dataset to 3.5.0-6, it stopped the upgrade at three
points, and it compared two restore methods. It changed the restore,
the failed mark, the `app_key` steps and the plugin check. Each such
place has the mark "(third test)".

A second test by hand ran on the same day, on a third container on BR1
(`evidence/2026-11-10-ojs-3.5.0-6-new-install-plugins-maintenance.md`).
It made a new install of 3.5.0-6 and ran the PKP checklist in a
browser. It tested the gallery setting, a plugin as files, a local
plugin directory, the maintenance mark, the worker and the scheduler,
and the site with no network. It was complete after the third test. It
corrected the first-boot facts and it added conditions for nginx, the
plugins and the worker. Each such place has the mark "(second test)".

A package test ran on 2026-11-11, on two containers on BR1
(`evidence/2026-11-11-ojs-package-real-node.md`). It tested the first
prototype of the packages `ojs-3.5` and `ojs-common`. It corrected the
source, the version, the preinst, the failure path and the restore.
Each such place has the mark "(package test)".

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
| Databases, 3.5 | "MySQL 5.7.22+, MariaDB 4.1+ or PostgreSQL 9.5+". The CI runs MariaDB, MySQL and PostgreSQL. The CI tests an upgrade to 3.5 from 3.3 and 3.4 on MySQL and PostgreSQL, but from 3.4 only on MariaDB. (third test) The upgrade of the PKP 3.3.0-24 dataset to 3.5.0-6 passed on MariaDB 11.8.6: 123 migrations, code 0 | `README.md`; `stable-3_5_0.yml`; third test |
| Debian 13 | php8.4 8.4.24-1~deb13u1, mariadb 1:11.8.6-0+deb13u1, postgresql-17 17.11-0+deb13u1. (first test) On 2026-11-10 a trixie node installs php8.4 8.4.27-1~deb13u1 | sources.debian.org API; first test |
| Upgrade steps | Stop the scheduled tasks and the job worker. Block access ("OJS does not support a maintenance mode yet"). Back up the database, `files_dir`, `public`, `config.inc.php`, `plugins` and local changes. Unpack the new package. Copy back the config and `public`. Run `php tools/upgrade.php check`, then `php -d memory_limit=2048M tools/upgrade.php upgrade` | upgrade guide (docs repo) |
| Duration | "may take from a few minutes up to several hours". If the upgrade runs out of memory "it will fail and you will need to restore from backup" | upgrade guide |
| Version table | The guide says that a build (`3.3.3-3`) has "No breaking changes or database migrations" | upgrade guide |
| Builds migrate | The code does not agree with the guide. `upgrade.xml` at `3_5_0-6` has a block `3.5.0.0` to `3.5.0.99` with 11 migrations. A build upgrade inside 3.5 runs them. (first test) The upgrade of 3.5.0-5 to 3.5.0-6 ran the 11 migrations and 3 code steps. They changed data. They did not change the schema of the test database | `dbscripts/xml/upgrade.xml`; first test |
| Refused jumps | `upgrade.xml` runs `abort` for a database from `2.0.0.0` to `3.2.9.9`. So 3.5 accepts only 3.3 and 3.4. The guide says "3.2.1-x can be upgraded to any version 3.3 or later". The code refuses 3.2 to 3.5. (third test) The 3.3 path has a pre-flight check. When it refuses, the schema is not changed, but `versions` gets a row `3.3.9.9` with `current = 1`. One such check: `base_url` must agree with the URLs in the usage statistics log | `upgrade.xml`; upgrade guide; third test |
| Failure | If a migration fails, the installer calls `down()` on the migrations that it ran, in reverse order. It stops at the first `DowngradeNotSupportedException`. No transaction holds the full upgrade. MariaDB commits each DDL statement. (third test) After a `kill -9` or a memory failure, the schema is half-migrated and `versions` shows the old version as current. A second upgrade run on the 3.3 half state failed in 3 of 3 cases | pkp-lib `classes/install/Installer.php` (`executeAction`); third test |
| `upgrade.php check` | It gets the latest version from pkp.sfu.ca. (first test) With no network it stops with an exception that it does not catch (`ConnectException`, "Could not resolve host"), and the exit code is 255 | pkp-lib `classes/cliTool/UpgradeTool.php`; first test |
| Maintenance | `isUnderMaintenance()` is true only when `installed` is Off or an upgrade runs in that process. No web code compares the code version with the database version (a search of pkp-lib found none). (third test) 3.5.0-6 code on a 3.3 database gives HTTP 500 on each page. A half-migrated database can give HTTP 200 on the public pages and the login. (second test) An nginx rule that looks for one file gives 503 on each OJS path with no reload | `PKPApplication.php`, `PKPPageRouter.php`; third test; second test |
| Fixed paths | The base directory is the directory of `index.php`. `config.inc.php`, `cache/` and the default `public/` are under it. Pages load JavaScript from `<base>/lib/pkp/lib/vendor/` | pkp-lib `classes/core/Core.php`, `classes/config/Config.php`, `PKPTemplateManager.php` |
| `app_key` | The 3.5 migration writes `app_key` into `config.inc.php`. If a key exists, it does nothing. 3.5.0-6 encrypts stored credentials with it (#12074). (third test) When the migration cannot write the file and no key exists, the upgrade continues and ends with code 0. It writes one line to the PHP log. Then each request gives HTTP 500 (`MissingAppKeyException`) | pkp-lib `I9895_AddAppKeyToConfigFile.php`; README-3.5.0; third test |
| Plugins | The gallery reads `plugins.xml` from pkp.sfu.ca (`plugin_gallery_urls`). It downloads the package, checks its MD5, copies it to `<base>/plugins/<category>/<name>`, and writes its schema and its `versions` row. `lib/pkp/tools/installPluginVersion.php` does the database step from the command line. The guide says: after an upgrade, "Use the Plugin Gallery to restore any custom plugins". (second test) For the PLN plugin, the tool gave the same `versions` row and the same tables as the gallery. The tool writes the `versions` row before the plugin migration, catches a failure of that migration, and does not give its result as the exit code | pkp-lib `PluginGalleryGridHandler.php`, `PluginHelper.php`, `PluginGalleryDAO.php`, `tools/installPluginVersion.php`, `classes/plugins/Plugin.php`; upgrade guide; second test |
| Plugin breaks | 3.5 does not load plugins with `.inc.php` files or with no namespace | 3.5 release notebook |
| Plugins that 3.5 removed | (third test) 10 plugins that 3.3 bundles have no directory in 3.5.0-6 (`ldap`, `resolver`, `usageStats`, `orcidProfile`, `acron`, `crossref`, `datacite`, `doi`, `counterReport`, `views`). The upgrade passes with their rows. 5 of the rows stay with `current = 1` after it | third test |
| Network during an upgrade | (third test) The 3.3 to 3.5 upgrade passes with no network (code 0, 12 seconds). With the network it took 52 to 128 seconds, because one migration downloads the ROR registry. Scheduled tasks get the ROR data and the IP database later | third test |
| Collations | (third test) MariaDB 11.8 gives a table with `CHARSET=utf8mb3` and no collation `utf8mb3_uca1400_ai_ci`. The OJS connection default is `utf8_general_ci`. After the upgrade of the imported dataset, 105 tables have the first and 31 have the second. No error was seen. (second test) A new install has no mix: the database default is `utf8mb4_unicode_ci`, and all 132 tables have `utf8mb3_general_ci` | third test; second test; pkp-lib `classes/core/PKPContainer.php` |
| New install | (second test) `tools/install.php` passes on PHP 8.4.27 and MariaDB 11.8.6: code 0, 132 tables, 76 to 106 seconds with the network. About 45 of the 76 seconds are local work (the schema, and the import of the ROR data). With no network it passes in 12 seconds, and the ROR data and the IP database stay empty. Two monthly scheduled tasks get them | second test |
| Network at run time | (second test) A running site makes one outgoing call: the version check to pkp.sfu.ca, on 3 administration pages. With no network, each page gives 200. With a DNS server that does not answer, PHP-FPM waits for a reverse DNS query, and some pages take 6 to 13 seconds. The cause in the OJS code was not found. pkp.sfu.ca and `download.db-ip.com` have no AAAA record | second test |
| Scheduled tasks, 3.5 | `php lib/pkp/tools/scheduler.php run` from cron every minute, with `task_runner = Off`. The Acron plugin is removed. (second test) A systemd timer did this. The scheduler does not process the job queue when `process_jobs_at_task_scheduler` is `Off` | admin guide, deploy-scheduled-tasks (docs repo); second test |
| Jobs, 3.4 and 3.5 | One method only: a worker (`php lib/pkp/tools/jobs.php work`), cron (`jobs.php run`) or the built-in runner. `jobs.php restart` stops the worker after the current job. (second test) Under systemd with `Restart=on-failure`, the worker completed its job, ended with code 0, and systemd did not start it again. `jobs.php restart` writes its signal as a file in the cache directory | admin guide, deploy-jobs; second test |
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

(second test) A new install of 3.5.0-6 passed, and the PKP checklist
passed in a browser: the reader pages, a registration, the roles, a
submission with a PDF up to a published issue, and the unpublish. The
flow wrote 1 PHP fatal error and 10 warnings. The fatal error is an
OJS defect: with `require_validation = On` and a journal that has no
support contact, a registration sends no message and the account stays
disabled. The template default is `Off`, and Keel keeps it. The
application page (0077) tells the operator to set the support contact
before the validation is set to `On`. The commissioning is not done.

(third test) 3.5.0-5 also cannot upgrade a 3.3 database on this PHP:
the upgrade stops with the same `TypeError`.

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

## Decision

### 1. Stack and line

`keel-ojs` is an application layer on LNMP (0059), with MariaDB. LNPP
has no PHP. The first line is 3.5 LTS. 3.3 and 3.4 are not packaged.

(first test) LNMP does not have all the PHP modules that OJS needs. The
package depends on these Debian packages: `php8.4-bcmath`, `php8.4-curl`,
`php8.4-gd`, `php8.4-intl`, `php8.4-mbstring`, `php8.4-xml` and
`php8.4-zip`.

### 2. The source and the build

The source repository is `Keel-Linux/ojs`. (package test) It has the
name of the package, as the repository `anubis` has. Its layout is the
one of keel-web: a directory `packages/NAME/debian/` for each package,
and bats tests with kcov coverage. The image repository is `keel-ojs`,
a later repository. The build downloads `ojs-3.5.0-6.tar.gz` from
pkp.sfu.ca. The source pins its sha256 (0012).

PKP signs nothing, so the build also compares the tarball with the git
tag `3_5_0-6` and its submodule commits. The tarball adds `vendor/` and
the built JavaScript, and the build lists that difference in the build log.
(package test) The prototype does not do this comparison yet. It checks
the pinned sha256 only.

### 3. Package names and versions

| Package | Content |
| --- | --- |
| `ojs-3.5` | The code of one line. Version `3.5.0.6+keel1` (the PKP `-6` becomes `.6`, because `-` starts the Debian revision) |
| `ojs-3.5-plugin-NAME` | One gallery plugin, from its `plugins.xml` release, checked by sha256 that the source pins. Not in the prototype |
| `ojs-common` | The paths, the systemd units, the nginx routes and the notice page, the scripts that the maintainer scripts of `ojs-3.5` call (`ojs-preinst`, `ojs-postinst`), the first boot (`ojs-firstboot`) and the `ojs-upgrade` script |

(package test) The prototype has two binary packages, `ojs-3.5` and
`ojs-common` (version 0.1.0), from two native sources in
`Keel-Linux/ojs`. The version is `3.5.0.6+keel1`, not `3.5.0.6-1`: the
build tool of the Keel archive refuses a rebuild of an upstream with no
`+keelN` suffix. The maintainer scripts of `ojs-3.5` are thin calls to
the scripts of `ojs-common`, which is a `Pre-Depends`.

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

(second test) nginx must send `.mjs` files as `text/javascript`. The
`mime.types` of nginx 1.26 has no `mjs`, so the PDF viewer of OJS
(`pdf.mjs`) stays empty. The OJS routes carry this rule:
`location ~ \.mjs$ { types { text/javascript mjs; } }`. The test also
refused, with 403, the directories `classes`, `registry`, `locale`,
`jobs` and `docs`, the `.tpl`, `.po`, `.xml` and `.inc.php` files and
the dot files, and the full flow passed with these rules.

`/etc/ojs/config.inc.php` is not a conffile. A conffile prompt stops an
unattended run, and OJS writes `app_key` into the file. The first boot
writes the file from `config.TEMPLATE.inc.php` and the manifest values.
It is root:www-data 0640. `app_key`, `salt` and `api_key_secret` are
manifest secrets with `shared: true`, so both nodes of a pair decrypt
the same rows. The first boot writes `app_key`, so the migration does
nothing to the file.

(third test) This order is a condition, not an option. A config with no
key does not stop the upgrade, and the exit code does not show the
defect (see "Facts checked"). So `ojs-upgrade` checks the key two
times (section 7).

(package test) The image runs etckeeper. It commits
`/etc/ojs/config.inc.php` and `/etc/ojs/app_key` into `/etc/.git`
before and after each apt run. `/etc/.git` is root 0700, but its
history keeps each old secret after a change. This is open. The
appliance layer `keel-ojs` decides it.

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
- (second test) The first boot does not need the network. The first
  test said that most of the install time is download, and that the
  first boot needs the network. Both were wrong. With the network, the
  install took 76 to 106 seconds: about 28 seconds for the download of
  the ROR data, about 29 seconds for its import, and about 13 seconds
  for the schema. With no network it took 12 seconds and ended with
  code 0. Then the ROR data and the IP database of the usage
  statistics are empty until the monthly tasks of the scheduler get
  them. With a DNS server that does not answer, the install took 45
  seconds.
- (second test) The installer also does not write `allowed_hosts`,
  `time_zone` and `enable_beacon` into a read-only file. The first
  boot writes them: `allowed_hosts` with the host name of `base_url`,
  `time_zone` from the node, and `enable_beacon = Off`. With an empty
  host in `allowed_hosts`, each request gives HTTP 400. The template
  has `repository_id = ojs.pkp.sfu.ca`, and the first boot writes the
  host name there. The beacon is `Off` because it gives data of the
  journal to PKP, and the operator did not choose that. The operator
  can set it to `On`.
- (second test) A new database gets all tables with
  `utf8mb3_general_ci` (`connection_charset = utf8`), as upstream
  does. Keel does not change this.

### 5. Plugins

The code tree is read-only, so the gallery cannot install a plugin.
Keel sets `plugin_gallery_urls` to an empty list. A gallery plugin comes
as an `ojs-3.5-plugin-NAME` package under
`/usr/share/ojs/plugins/<category>/<name>`. Thus a plugin has the same
version on both nodes, and a package upgrade never deletes it. The
gallery also writes the plugin's schema and `versions` row. So the
plugin package's `postinst` runs `installPluginVersion.php` on the
writable node only, in the same way as the core migration. An operator
who needs a plugin that is not packaged asks for a package.

(second test) The results for this section:
- `plugin_gallery_urls = '[]'` empties the gallery, and the site sends
  no packet to pkp.sfu.ca for it.
- The upload form stays in the page. On the read-only tree it installs
  nothing: no directory and no `versions` row. But the page shows no
  message, and the PHP log gets some hundreds of warnings. The
  application page (0077) tells the operator that the form does not
  work.
- For the PLN plugin, files that root copies and
  `installPluginVersion.php` as www-data give the same `versions` row
  and the same tables as a gallery install on a writable tree.
- The exit code of `installPluginVersion.php` is not sufficient. From
  its code, it writes the `versions` row first, and a plugin migration
  that fails does not change the exit code. So the plugin `postinst`
  also checks the tables that the plugin package declares. A run with
  a migration that fails comes before the first plugin package.
- The plugin tarballs have file modes that a package cannot keep: one
  unpacks with directories 0700, one with 0777. With 0700 and owner
  root, OJS does not list the plugin, and it shows no error. The
  package sets root, 0755 for directories and 0644 for files.
- A local plugin directory loads: a link in the code tree to a
  directory under `/var/lib/ojs`, with files that www-data can read.
  The first package does not have such a directory. A plugin there is
  on one node only, and no package owns it. A later note can add it.

### 6. `preinst`

`preinst` runs on `upgrade`. It also runs on `install` when
`/etc/ojs/config.inc.php` exists, because a line change installs a new
package name. (package test) Without the config, the database name is
not known, so a database alone does not start the checks. If one check
fails, it exits 1. On an upgrade of a configured package, dpkg then
calls the old `postinst abort-upgrade`, and the old version stays
installed and configured.

(package test) The preinst has these effects:
- Before the checks, it removes a token `/run/ojs/unpack` of an earlier
  run. A maintenance mark `state=unpack` of an earlier run becomes
  `state=unpack-interrupted`. It does this also when a check refuses
  (section 7, "The unpack").
- When the checks pass on an installed node, it closes the site before
  dpkg unpacks the new code. On the writable node it stops the timer
  and the worker first. In the test, a power loss during the unpack
  with no such close left a mixed code tree that answered HTTP 200,
  with the worker active.
- After a power loss during the unpack, the old package is half
  installed, and dpkg calls no `postinst` of it. If a check then
  refuses and the mark says `state=unpack-interrupted`, the preinst
  sends the alert itself.

(package test) In the prototype, check 5 is "the database answers"
only. The pair state belongs to the appliance layer `keel-ojs`. The
list of check 6 for an import is in `postinst`, before the migration,
because the new code is not unpacked at preinst time. Check 4 runs only
on the writable node with a database that is older than the code,
because only then a backup follows.
0. **Incomplete mark.** Refuse while `/var/lib/ojs/upgrade-incomplete`
   exists. dpkg records the version of a failed migration as installed
   (section 7), so without this check the next build runs `upgrade.php`
   on a half-migrated schema. (third test) The `versions` table cannot
   do this work: after each interruption it showed the old version.
1. **Database version.** Read `versions` (`product_type =
   'core'`, `current = 1`) with the stack's account. Do not use
   `upgrade.php check`, because it needs the network.
2. **Jump.** Allow the same line at the same or a later build. For
   `ojs-3.5`, allow a database at 3.3 or 3.4 (an import from outside
   Keel). Refuse a database at 3.2.9.9 or lower (as `upgrade.xml` does).
   Refuse a database that is newer than the new code. (third test) Read
   `3.3.9.9` as 3.3: a pre-flight check that refused leaves this
   version.
3. **PHP.** `PHP_VERSION` is at least the line's required version.
4. **Disk.** The free space on `/var/backups` is at least the size of the
   database plus `files_dir` plus `public`, plus 20 %.
5. **Pair state.** Read the role of the node (0049, 0054 pattern). A
   writable node needs a writable database. A standby needs a reachable
   primary.
6. **Plugins.** Each installed `ojs-X-plugin-NAME` package has a
   package for the new line. If not, refuse, and name the plugin.
   (third test) The check reads dpkg, not `versions`. A 3.3 database
   has active rows for 10 plugins that 3.5 removed, and a check on
   `versions` refuses each import. For an import from outside Keel,
   `preinst` lists each active row that has no directory in the new
   code. It does not refuse.

### 7. `postinst configure`

On a standby, or before the first boot, `postinst` clears
`/var/cache/ojs` and exits 0. If the database version equals the code
version, it does the same. (second test) On the writable node it stops
the worker first (step 1) and starts it after, because the signal of
`jobs.php restart` is a file in that cache. Otherwise, on the writable
node, it calls `ojs-upgrade`:
1. Stop `ojs-scheduler.timer`. Run `jobs.php restart`, then stop
   `ojs-jobs.service`. (second test) After `jobs.php restart`, the
   worker completes its job and ends with code 0, and
   `Restart=on-failure` does not start it again. `ojs-upgrade` waits
   for the unit to become inactive, with a time limit, and then stops
   the unit. The jobs that wait stay in the queue.
2. Write the maintenance mark `/var/lib/ojs/maintenance` and
   `/var/lib/ojs/upgrade-incomplete`.
   nginx answers every OJS path with 503 and a notice. (third test) The
   503 is necessary: a half-migrated database can answer HTTP 200.
   (second test) nginx looks for the mark file on each request, so no
   reload is necessary: the pages, the API, a POST and the static files
   gave 503 with `Retry-After` in about 1 ms, and 200 again when the
   file was removed. The path `/keel-health` stays out of the rule. The
   mark does not stop the worker or the timer, which are separate
   processes. So step 1 is necessary.
3. Dump the database (`mariadb-dump --single-transaction`). Copy
   `files_dir` and `public` to `/var/backups/ojs/<old version>-<date>/`.
   Copy `/etc/ojs/config.inc.php` too. Record the default character set
   and collation of the database there.
4. (third test) Check that `app_key` has a value. If not (an import
   from outside Keel), write the manifest key as root.
5. Run `php -d memory_limit=2048M tools/upgrade.php upgrade` as www-data.
   Write the log to `/var/log/ojs/`. (third test) With
   `memory_limit=32M` the upgrade of the small dataset fails. With
   2048M the process used 107 MB.
6. The upgrade passed only if the exit code is 0, the core row of
   `versions` equals the code version, and `app_key` has a value.
7. On success, clear the cache, reload PHP-FPM, start the jobs service
   and the timer, remove the two marks, and exit 0. (first test) The reload
   is new. OPcache holds the old code for `revalidate_freq` seconds (30
   in the image). The test did not measure old code after the change,
   but the setting permits it. (second test) The worker starts after
   the cache clear, not before it.

(package test) On an upgrade, the preinst already closed the site, and
on the writable node it stopped the timer and the worker (section 6).
Step 2 then writes an empty maintenance mark, which is the mark of a
migration. Step 3 also copies the kept file of the old package into the
backup, if the node has it. On a standby, before the first boot, and
with a database at the code version, `postinst` opens a site that the
preinst closed. In the test, the migration of 3.5.0.5 to 3.5.0.6
took less than 1 second. The site gave 503 for about 21 seconds, from
the preinst to the end of the configure.

**If the migration fails**, `ojs-upgrade` keeps the two marks. It
keeps the jobs and the timer stopped. It sends an alert and exits 0.
(third test) `ojs-upgrade` writes the incomplete mark before the dump
and removes it only after a success. Thus a `kill -9` or a power loss,
where `ojs-upgrade` cannot write anything, leaves the same state as a
failure that it sees. It does not exit non-zero, for these reasons:
- A non-zero `postinst` leaves the package half-configured.
- Then each later apt run calls `postinst` again. That runs
  `upgrade.php` again on a half-migrated schema.
- It also blocks the daily security run of cron-apt (0073) on that node.

(package test) Until the Keel alert (0063) is on the nodes, the alert
is three things: a message on stderr, a `logger -p daemon.crit -t
ojs-upgrade` line, and a call of each executable in `/etc/ojs/alert.d`
with the text. The text names the two versions, the cause, the log, the
backup and the two commands. The cause is the exit code of
`upgrade.php`, a core row that is not the code version, or an empty
`app_key`. In the test, `upgrade.php` gave code 2 for an SQL lock
timeout and code 137 after `kill -9`.

(package test) After a power loss during the migration, dpkg shows the
package as half configured (`iF`). The worker and the scheduler do not
start at the boot, because their units have
`ConditionPathExists=!/var/lib/ojs/maintenance`. Each apt command
returns 100 until `dpkg --configure -a` runs. That configure finds the
incomplete mark. It runs no migration, sends the alert and exits 0.
Then the operator runs `--retry` or `--restore`.

The operator then runs one of two commands:
- `ojs-upgrade --retry`. It does the restore below, then it runs the
  upgrade again. Use it after a fix, for example more memory or a
  corrected `base_url`. (third test) It does not continue on the half
  state: a second run on a 3.3 half state failed in 3 of 3 cases.
  (package test) A correction in the database after the failure is
  lost. If the backup has no `complete` stamp, the migration did not
  start: then `--retry` makes a new backup and does not restore.
- `ojs-upgrade --restore`. It does the restore below. Then it installs
  the old package with `apt-get --allow-downgrades`. The database comes
  first, or the old `preinst` refuses a database that is newer than its
  code. (package test) The old `preinst` also refuses while the
  incomplete mark exists. So `--restore` removes the mark before
  `apt-get`. If `apt-get` fails, it writes the mark again and sends the
  alert.

(package test) The Keel repository index holds one version of each
package. After the repository moves, apt cannot get the old version
from it. Thus each configure copies the file of its package from the
apt archive to `/var/lib/ojs/packages`, and only the file of the
running package stays there. Each backup gets a copy of the kept file
of the old package, which is 77 MB. `--restore` installs the file from the
backup, else the kept file, else `PACKAGE=VERSION` from the repository.
In the test, the repository had only the new version, and `--restore`
installed the old package from the backup in 22 seconds. An install
with `dpkg -i` leaves no file in the apt archive, so then no copy is
kept.

**The unpack** (package test). dpkg unpacks the new code between the
preinst and the configure. The prototype uses two marks for this time:
- The maintenance mark `/var/lib/ojs/maintenance`. nginx answers 503
  while it exists, and the worker and the scheduler do not start. An
  empty mark is the mark of a migration, a retry or a restore. The
  preinst writes `state=unpack`, and `workers=stopped` when it stopped
  the worker and the timer.
- The token `/run/ojs/unpack`. The preinst writes it after the mark. It
  says that the mark is of the preinst of this dpkg run. The next
  preinst and each configure remove it. A boot removes it too, because
  `/run` is a tmpfs.

A configure that passes removes a mark of the preinst. Then it starts
the worker and the timer, if the preinst stopped them and they are
enabled. An empty mark stays until a migration, `--retry` or `--restore`
passes.

If the new preinst refuses or the unpack fails, dpkg puts the old files
back. Then it calls the old `postinst abort-upgrade`, or `abort-remove`
after a line change that it takes back. With `state=unpack` and the
token, the old `postinst` empties the cache, reloads PHP-FPM and opens
the site. In the test, a cut package file gave 503 for 4 seconds, and
the old version stayed configured. With no token, or with
`state=unpack-interrupted`, the code tree is not known to be whole. Then
the site stays closed, and an alert names `apt-get install --reinstall`.

After a power loss during the unpack, the site stays closed after the
boot, and dpkg shows the package as half installed (`iHR`). To end the
upgrade:
1. Run `dpkg --configure -a`. It configures the other packages, and the
   OJS code package stays half installed.
2. Run `apt-get install --reinstall ojs-3.5`. The new code is unpacked
   again, and its configure runs the migration.

When the unpack of the OJS code package fails, other packages of the
same apt run can stay unpacked and not configured. In the test, these
were keel-web and an nginx module. `apt-get upgrade` also configures
such packages, nginx included, while the site is in maintenance.

**The restore** (third test):
1. Drop the database. Create it again with the recorded character set
   and collation. Load the dump.
2. Synchronize `files_dir` and `public` from the copy, and delete each
   file that is not in the copy.
3. Copy the config back.
4. Empty `/var/cache/ojs` and make its directories again.
   (package test) The web user removes the files (`runuser` and `find
   -delete`, from `/`) and makes the directories. Root sets only the
   owner and the mode of `/var/cache/ojs`. The web user can put a link
   in its own directory, and a `chown` as root follows a link. OJS
   makes `/var/cache/ojs/opcache` again by itself.

A dump that is loaded into the half-migrated database is not a restore.
In the test, 27 new tables and 5 new files stayed, and the next upgrade
failed ("Table 'failed_jobs' already exists"). The restore above gave a
state identical to the state before the upgrade in each case, and the
next upgrade passed.

**An import from outside Keel** (a 3.3 or 3.4 database) has no old
Keel package. After `--restore`, the node has the old data and the 3.5
code, and it stays in maintenance. The operator corrects the cause and
runs `--retry`, or keeps the old machine. A retry after a pre-flight
check that refused, with no restore, was not tested. (package test) In
this case `--restore` exits 0, and the incomplete mark stays with
`phase=restored`. This is from the code. It was not tested.

**Exit codes** (package test), from the code:

| Script | 0 | 1 | 2 |
| --- | --- | --- | --- |
| `ojs-preinst` | The checks pass | Refused. dpkg does not unpack the new code | Usage |
| `ojs-postinst configure` | Done. Also after a failed migration, and with an incomplete mark | Nothing ran: the database does not answer, the database is newer than the code, or another `ojs-upgrade` holds the lock. dpkg runs the configure again on the next apt run. If the site is closed, an alert says so, except for the lock | Usage |
| `ojs-postinst abort-upgrade`, `abort-remove` | Always | Not used | Usage |
| `ojs-upgrade --retry`, `--restore` | Done. Also `--restore` of an import from outside Keel, with the mark and the maintenance kept | Failed or refused. The marks stay | Usage |

A monit check fails while the incomplete mark exists and no
`ojs-upgrade` runs. (package test) This check belongs to the appliance
layer `keel-ojs`, and it is not built. Until then, a boot that finds a
mark sends no alert, and `/keel-health` stays 204.

**What apt can roll back.** apt can install the old code again, if the
file of the old package is on the node (in the backup or in
`/var/lib/ojs/packages`) or in the repository. apt cannot roll back the
database or `files_dir`. Old code does not run on a newer schema. So a
rollback is always all three parts together: the database, the files
and the old package.

### 8. Unattended upgrades

Each OJS build upgrade runs the migrations of its line (see "Facts
checked"). In the first test they changed data only, but a different
build can change the schema. So no OJS upgrade is code-only, and none
goes to Keel trixie-security. cron-apt does not take OJS. (third test)
An upgrade does not need the network. In `simple` mode, the operator
runs `apt upgrade`. In a pair, the operator upgrades one node at a time
(0073 item 6). A line
change (3.5 to 3.7) is always a deliberate act. 3.5 removed old plugin
formats, and the next line can do the same.

(package test) `apt upgrade` upgrades each package that waits, in one
run. In the test, nginx and keel-web were configured in the same run,
while the OJS site was in maintenance. The site is closed from the
preinst of the OJS code package to the end of its configure, not for
the full apt run.

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
   maintenance mark and alerts. (third test) This check also covers a
   writable node that stops in the middle of a migration: the database
   then shows the old version, and the standby has the new code.
5. A restore runs on the writable node. The drop of the database and
   the deletion of files replicate. Test 6 checks this.

### 10. The network

(second test) OJS on a Keel node works with no network to the
internet. The first boot and an upgrade pass without it.

A running site makes one outgoing call: the version check, to
pkp.sfu.ca on tcp 443, when an administrator opens the administration
index, the system information or the site settings. With
`enable_beacon = On`, the call carries the id of the site and its OAI
address. When the call fails fast, the page comes at the usual speed
and the PHP log gets one line.

Two limits are known and not solved:
- pkp.sfu.ca and `download.db-ip.com` have no AAAA record. On an
  IPv6-only node, the version check and the IP database download
  cannot pass. No such node was tested.
- With a DNS server that does not answer, PHP-FPM waits two times 3
  seconds for a reverse DNS query of the client address. Public pages
  with journal content took 6 seconds, and the 3 administration pages
  took 13 seconds. The test did not find the OJS code that asks. A
  node needs a resolver that answers.

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

## Tests before the release

Each test makes an evidence file (0053). Use 2 LXC on BR1 and 1 on BR2,
with netem (0075).
1. Install 3.5.0-6 on PHP 8.4 and MariaDB 11.8. Run the PKP checklist
   (upgrade guide step 11) and check the PHP-FPM log for deprecations.
   (first test) Partly done: 3.5.0-6 came from an upgrade, not from a
   new install, and the checklist was not run. The log is in the
   evidence.
   (second test) Done by hand, with no package: a new install (code 0),
   and the checklist in a browser. Two defects: the `.mjs` type
   (section 4) and the registration with email validation ("The answer
   for trixie"). The install command wrote 48 deprecation messages.
2. Upgrade 3.5.0-5 to 3.5.0-6 with the package. Measure the duration.
   Check the 11 build migrations.
   (first test) Done by hand, with no package: code 0 in 1.2 seconds on
   a database with one journal and one submission. The 11 migrations
   ran. The duration on a large journal is not known.
   (package test) Done with the package, from `3.5.0.5+keel1` (test
   material, never published) to `3.5.0.6+keel1`. `apt-get upgrade`
   gave code 0 in 32 seconds, with 9 other packages in the same run.
   The 11 migrations ran in less than 1 second. The site gave 503 for
   about 21 seconds. The duration on a large journal is not known.
3. Upgrade a 3.3.0-24 dataset to 3.5 on MariaDB 11.8. PKP CI does not
   test this path.
   (third test) Done by hand, with no package: code 0 in 52 to 128
   seconds with the network and 12 seconds with no network, on the PKP
   dataset (19 submissions). The counts are the same, the pages give
   HTTP 200, and the PHP log has 0 errors. Not done: a 3.4 database, a
   3.3 build before 3.3.0-24, and a large journal.
4. Stop the migration (kill the process, or set a low `memory_limit`).
   Then run `ojs-upgrade --restore`. Compare the database and the files
   with the state before the upgrade.
   (third test) Done by hand with scripts, at three points (two
   `kill -9` and `memory_limit=32M`). The restore of section 7 gives the
   identical state. The restore that this note had before the test does
   not. The package must repeat this test with `ojs-upgrade`.
   (package test) Done with `ojs-upgrade` on 3.5.0.5 to 3.5.0.6: a
   failed migration (a lock timeout) with `--retry` and with
   `--restore`, a `kill -9` of `upgrade.php` with `--retry`, and a power
   loss during the migration with `--retry`. Each one passed. The test
   compared the core version, the count of tables, the code release,
   the marks, the units and the HTTP answers, not the full content.
   Also passed: a power loss during the unpack, a failed unpack, and a
   refused preinst after a power loss. Not done with the package: a low
   `memory_limit`, and a 3.3 import.
5. Paths and plugins:
   - Run `upgrade.php` as www-data with a read-only `config.inc.php`
     that has `app_key`. No step writes the file.
     (first test) Passed for 3.5.0-5 to 3.5.0-6: the file has the same
     sha256, the process opened it one time and read-only, and no file
     of the code tree changed. The migration that writes `app_key` is
     in the block of 3.1 to 3.4, so only test 3 can show its behaviour.
     (third test) Passed for 3.3.0-24 to 3.5.0-6 with a key in the
     file: the same checks, the same results. With no key, the upgrade
     gives code 0 and a site that does not work (section 7, steps 4
     and 6).
   - The links for `config.inc.php`, `cache` and `public` work with
     PHP-FPM, OPcache and Smarty.
     (first test) Passed.
   - `plugin_gallery_urls = '[]'` empties the gallery. The upload of a
     plugin fails cleanly on a read-only tree.
     (first test) The install function of the upload form refuses
     cleanly ("Failed to copy plugin to destination folder"), with no
     directory and no `versions` row. It was called from the command
     line, not through the form. The gallery setting was not tested.
     (second test) The setting empties the gallery. Through the form,
     the upload installs nothing, but the page shows no message
     (section 5).
   - A plugin package with `installPluginVersion.php` gives the same
     schema and `versions` row as a gallery install.
     (second test) Passed by hand for PLN 4.0.1.0, with no package.
     Not done: a plugin migration that fails (section 5).
   - A local plugin directory (a link to `/var/lib/ojs`) loads, or not.
     (second test) It loads, if www-data can read the files.
6. Pair: upgrade the standby, promote it, and check that the gate keeps
   the maintenance mark. Then complete the upgrade and run the 0075
   passes. Check that the timer and the worker move with a promote.
7. Measure the dump and the file copy for a journal of about 10 GB.
   Check the disk rule of `preinst`.
   (first test) A new installation with one submission already gives a
   dump of 31 MB and a file copy of 122 MB.
8. Run a line change with a test package `ojs-3.6` (from `main`) and
   check that `preinst` runs on `install`.
   (package test) Also check `abort-remove`: the new line refuses or
   fails, and the old package opens the site again.

Not verified in this note:
- The Debian WNPP search (refused) and the reason of bug 662828 (a
  challenge page).
- An Ubuntu PPA and Bitnami: not checked.
- The database versions in PKP CI: `pkp/pkp-github-actions` not read.
- The web code on a code and schema mismatch: a search found no check.
  Test 6 covers it.
- The package names are proposals.
- A retry after a pre-flight check that refused, with no restore.
- A join of text columns across the two collations of an imported
  database.
- The restore on a pair (test 6).
- An IPv6-only node (section 10).
- The OJS code that makes the reverse DNS query (section 10).
- A plugin migration that fails with `installPluginVersion.php`
  (section 5). The result is from the code.
- `enable_beacon = Off`: its effect on the version check call.
- `systemctl stop` of a worker in the middle of a job, and a cache
  clear while a worker runs.
- The two scheduled tasks that get the ROR data and the IP database
  after a first boot with no network.
- The full-text index of a PDF. The template has the `pdftotext` line
  as a comment, and the worker skips each PDF.
- An account activation with `require_validation = On`.
- (package test) The package with a 3.3 import, the Anubis front, plugin
  packages, a standby node, the PKP checklist on a node that the package
  installed, and a refusal of the disk check.
- (package test) The exclusion of the OJS secrets from etckeeper
  (section 4).

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
- From the tarball `ojs-3.5.0-6.tar.gz` (second test): `lib/pkp/tools/installPluginVersion.php`, `lib/pkp/classes/plugins/Plugin.php`, `config.TEMPLATE.inc.php`
- <https://github.com/pkp/pkp-docs> at commit `58079b5` (second test): the checklist of step 11 of the upgrade guide
- <https://github.com/pkp/pkp-lib/issues/13139>, <https://github.com/pkp/pkp-lib/issues/13140>
- <https://github.com/pkp/docker-ojs> (archived), <https://github.com/pkp/containers>
- <https://github.com/YunoHost-Apps/ojs_ynh>
- <https://tracker.debian.org/pkg/ojs>, <https://sources.debian.org/api/src/ojs/>
- <https://sources.debian.org/api/src/php8.4/>, <https://sources.debian.org/api/src/mariadb/>, <https://sources.debian.org/api/src/postgresql-17/>
