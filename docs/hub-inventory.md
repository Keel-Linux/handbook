# Hub dependency inventory

Deliverable for BRIEF.md section 5.6. Read-only survey: no code was changed.

Sources, all cloned on this machine and unmodified with respect to their
upstream remotes:

- `/home/navigator/Projects/TKL/upstream/{tklbam,confconsole,inithooks,common,tklbam-profiles,buildtasks,fab}`
- `tklbam-python-boto` and `turnkey-pylib` are absent from
  `/home/navigator/Projects/TKL/forks/`, so both were cloned read-only into
  a scratch directory from `https://github.com/turnkeylinux/<name>.git`.
  Paths below prefixed `tklbam-python-boto/` refer to that clone.

`upstream/tklbam` is at `31134d3`, identical to `origin/master`, so the S3 and
1.5.4 commits visible in its log are upstream, not local work. Citations are
`repo/path:lines`; anything not confirmed is marked UNVERIFIED.

## 1. Capability table

Read this first. Detail follows in sections 3 to 8.

| Capability | Verdict | Reason (one line) |
| --- | --- | --- |
| Backup upload and download (duplicity to S3) | Keeps working without the Hub | `tklbam-backup --address` and `tklbam-restore --address` drive duplicity directly, and the address can be any duplicity URL (`tklbam/lib/cmd_backup.py:26`, `tklbam/lib/cmd_restore.py:44`). |
| Backup encryption key and passphrase | Keeps working without the Hub | The secret is generated locally and never sent; only the wrapped key packet goes up (`tklbam/lib/cmd_init.py:155-166`). |
| S3 credentials for the backup bucket | Needs a Keel service or a decision | Today they come from `GET credentials/`; the alternative is static credentials in the registry, which no code path writes yet (`tklbam/lib/hub.py:233-235`). |
| Backup profile download | Needs a Keel service | `GET archive/` and `GET archive/timestamp/` are Hub-specific and serve base64 tarballs; `--force-profile=path` is the only offline route (`tklbam/lib/hub.py:237-262`). |
| Backup record catalogue (list, ids, addresses) | Needs a Keel service | `record/*` and `records/` are Hub-specific bookkeeping with no open equivalent (`tklbam/lib/hub.py:264-292`). |
| API key to sub-key exchange | Needs a Keel service | `GET subkey/` is the only way `sub_apikey` is ever obtained (`tklbam/lib/hub.py:228-231`). |
| IAM role credential refresh (STS agent) | Needs a Keel service or a decision | `tklbam-internal stsagent` re-asks the Hub for short-lived credentials; static credentials make it unnecessary (`tklbam/lib/cmd_internals/cmd_stsagent.py:114-122`). |
| HubDNS dynamic DNS | Needs a decision | `hubdns-init` / `hubdns-update` are external binaries from a package not in the forked set; the appliance only shells out to them (`inithooks/bin/hubservices.py:104-114`). |
| Let's Encrypt certificates | Keeps working without the Hub | Plain ACME through dehydrated, CA configurable, no Hub involvement (`confconsole/share/letsencrypt/dehydrated-confconsole.config:18-29`). |
| DNS-01 challenge providers | Keeps working without the Hub | lexicon against the operator's own DNS provider (`confconsole/share/letsencrypt/dehydrated-confconsole.hook-dns-01.sh:30-62`). |
| Security alert subscription | Needs a decision | A one-shot `curl` to a Hub endpoint that has no open equivalent and no local effect if dropped (`inithooks/bin/secalerts.sh:57-70`). |
| initfence usage beacon | Needs a decision | Two `<script>` tags pointing at `ajax.turnkeylinux.org`, cosmetic and removable (`inithooks/firstboot.d/29tagid:22-27`). |
| Mail relay signup | Keeps working without the Hub | The Hub URL is prose in a dialog; the relay itself is plain SMTP to whatever host the operator types (`confconsole/plugins.d/Mail_Relaying/mail_relay.py:12-18`). |
| Package archive | Needs a Keel service | `archive.turnkeylinux.org` is a plain APT repository, so it is easy to repoint but something has to serve it (`common/conf/bootstrap_apt:208-291`). |
| Build image mirror | Needs a Keel service | `mirror.turnkeylinux.org` is plain HTTP file serving (`buildtasks/bt-img:121`, `buildtasks/bt-iso:356`). |

Call sites found, counting code paths that perform a network request or invoke
a command that does:

| Repository | Hub API call sites | Other `*.turnkeylinux.org` |
| --- | --- | --- |
| tklbam | 14 (10 distinct operations) | 2 (`archive.turnkeylinux.org` in a contrib script) |
| inithooks | 2 (secalerts curl, initfence beacon) plus 6 shell-outs to `tklbam-init` / `hubdns-*` | 4 documentation URLs |
| confconsole | 0 | 3 (all display or documentation text) |
| common | 0 | 7 (`archive.turnkeylinux.org` APT lines) |
| buildtasks | 0 | 3 (`mirror.turnkeylinux.org`, key fetch) |
| fab, tklbam-profiles | 0 | 0 |
| tklbam-python-boto | 0 | 0 |

## 2. The one hardcoded Hub base URL

`tklbam/lib/hub.py:212`

    API_URL = os.getenv('TKLBAM_APIURL', 'https://hub.turnkeylinux.org/api/backup/')

Every tklbam Hub request is `API_URL + uri` (`tklbam/lib/hub.py:224-226`,
`tklbam/lib/hub.py:230`). So the whole Hub API surface is already repointable
with one environment variable. Nothing in the packaged code sets it: there is
no `/etc/tklbam/conf` option for it (`tklbam/lib/conf.py:180-186` lists the
accepted options and `apiurl` is not among them), and no init script exports
it. That is the cheapest existing lever and the reason the S3 work in section 8
is a separate, smaller problem.

A second, complete bypass already exists: `tklbam/lib/hub.py:317-319` swaps the
entire `Backups` class for `dummyhub.Backups` when `TKLBAM_DUMMYHUB` is set or
`/etc/tklbam/dummyhub` exists. `tklbam/lib/dummyhub.py:245-360` implements the
same interface locally, handing out `file://` addresses
(`tklbam/lib/dummyhub.py:318-326`). It is a test harness, not a product, but it
proves the interface is the only coupling point.

## 3. tklbam: the Hub API surface

The contract is documented in the module docstring, `tklbam/lib/hub.py:12-79`,
including the exception names the client keys on. Sub-key authentication is a
`subkey` request header on every call except `subkey/`
(`tklbam/lib/hub.py:18`, `tklbam/lib/hub.py:224-226`).

| Operation | Method and path | Defined at | Purpose |
| --- | --- | --- | --- |
| API key exchange | `GET subkey/` | `hub.py:228-231` | Turns the account API key into the stored sub-key |
| Credentials | `GET credentials/` | `hub.py:233-235` | S3 access key, secret, session or user/product token |
| Profile timestamp | `GET archive/timestamp/` | `hub.py:249-250` | Is there a newer profile |
| Profile download | `GET archive/` | `hub.py:255-262` | base64 tarball, written to a temp file and extracted |
| Record create | `POST record/create/` | `hub.py:264-270` | Allocates a backup id and the S3 address |
| Record read | `GET record/<id>/` | `hub.py:272-274` | Re-reads the address before a backup |
| In-progress flag | `PUT record/<id>/inprogress/` | `hub.py:276-280` | Locking or status display |
| Key update | `PUT record/<id>/` | `hub.py:282-284` | Uploads the re-wrapped key packet |
| Record touched | `PUT record/update/` | `hub.py:286-288` | Marks the backup as freshly written |
| Record list | `GET records/` | `hub.py:290-292` | Backup catalogue for list and restore |

### 3.1 Call sites, first-boot status, failure behaviour

| # | Call site | Operation | First boot | Blocks appliance | On failure today |
| --- | --- | --- | --- | --- | --- |
| 1 | `tklbam/lib/cmd_init.py:188` | `subkey/` | Yes, via `80hub-services` | No | `fatal(e)`, `tklbam-init` exits 1 (`cmd_init.py:187-190`) |
| 2 | `tklbam/lib/cmd_init.py:196` | `credentials/` | Yes | No | `NotSubscribed` is caught and printed; the link still stands (`cmd_init.py:200-202`) |
| 3 | `tklbam/lib/registry.py:302` | `archive/timestamp/` + `archive/` | Yes, `cmd_init.py:207-209` | No | Cached profile is reused with a warning, else `sys.exit(1)` (`registry.py:307-318`, `registry.py:417-437`) |
| 4 | `tklbam/lib/cmd_backup.py:345` | `credentials/` | No | No | Cached credentials reused with a warning, except for `iamrole` or `NotSubscribed`, which are fatal (`cmd_backup.py:346-357`) |
| 5 | `tklbam/lib/cmd_backup.py:361` | `record/<id>/` | No | No | Cached address reused with a warning (`cmd_backup.py:362-374`) |
| 6 | `tklbam/lib/cmd_backup.py:376` | `record/create/` | No | No | Uncaught, so the backup aborts when no record is cached |
| 7 | `tklbam/lib/cmd_backup.py:421` | `record/<id>/inprogress/` | No | No | Caught and warned (`cmd_backup.py:418-424`) |
| 8 | `tklbam/lib/cmd_backup.py:508` | `record/update/` | No | No | Bare `except: pass` (`cmd_backup.py:506-510`) |
| 9 | `tklbam/lib/cmd_restore.py:224` | `record/<id>/` | No | No | `InvalidBackupError` is reported, other errors are fatal (`cmd_restore.py:218-230`) |
| 10 | `tklbam/lib/cmd_restore.py:229` | `records/` | No | No | Used to resolve a non-numeric backup argument |
| 11 | `tklbam/lib/cmd_restore.py:427` | `credentials/` | No | No | Wrapped in `fatal(e)` (`cmd_restore.py:427-429`) |
| 12 | `tklbam/lib/cmd_list.py:110` | `records/` | No | No | Uncaught; `tklbam-list` is unusable offline |
| 13 | `tklbam/lib/cmd_passphrase.py:67` | `PUT record/<id>/` | No | No | Re-raised; the local key is deliberately not saved unless the upload succeeds (`cmd_passphrase.py:63-76`) |
| 14 | `tklbam/lib/cmd_internals/cmd_stsagent.py:120` | `credentials/` | No | No | `fatal()`; duplicity then loses its `credential_process` and the transfer dies |

Nothing in tklbam is on the blocking part of first boot: `80hub-services`
exits immediately when `HUB_APIKEY` is `SKIP`
(`inithooks/firstboot.d/80hub-services:7`), and with no API key the interactive
dialog is skippable (`inithooks/bin/hubservices.py:128`).

`tklbam-status`, which confconsole renders, reads the local registry only and
makes no request; it just prints Hub URLs as guidance
(`tklbam/lib/cmd_status.py:75-95`).

### 3.2 The server id

`record/create/` optionally carries `server_id`, read from
`/var/lib/hubclient/server.conf`, key `serverid`
(`tklbam/lib/cmd_backup.py:185-193`). That file is written by a `hubclient`
package that is not among the forked repositories, so its provenance and
permissions are UNVERIFIED. When absent, `get_server_id()` returns `None` and
the field is simply omitted (`tklbam/lib/hub.py:264-268`).

## 4. Credentials and identifiers on disk

All tklbam state lives in one directory, default `/var/lib/tklbam`, overridable
with `TKLBAM_REGISTRY` (`tklbam/lib/registry.py:66-67`). The directory is
created `0700` (`tklbam/lib/registry.py:81-83`), and every file the registry
writes is opened `O_CREAT|O_TRUNC` with mode `0600` under `umask(0)`
(`tklbam/lib/registry.py:100-106`).

| File | Content | Written by | Notes |
| --- | --- | --- | --- |
| `sub_apikey` | Hub sub-key, the only credential the API accepts | `tklbam/lib/cmd_init.py:192` | Cleared by `--solo` (`cmd_init.py:168-172`) |
| `secret` | Locally generated 160-bit backup secret, base64 | `tklbam/lib/cmd_init.py:155-157` | Never sent to the Hub |
| `key` | Key packet: the secret wrapped with the passphrase | `tklbam/lib/cmd_init.py:157`, `tklbam/lib/cmd_passphrase.py:60-68` | This is what `record/create/` and `PUT record/<id>/` upload |
| `credentials` | `key=value` lines: access key, secret key, and session, user or product token | `tklbam/lib/cmd_init.py:197`, `tklbam/lib/cmd_backup.py:345` | Parsed back through `hub.Credentials.from_dict` (`registry.py:138-142`, `hub.py:187-209`) |
| `hbr` | Cached backup record: `address`, `backup_id`, `updated` | `tklbam/lib/registry.py:144-159` | The cached S3 address that lets a backup survive a Hub outage |
| `profile/` | Extracted profile plus `stamp` and `profile_id` | `tklbam/lib/registry.py:166-215` | `stamp` mtime carries the Hub archive timestamp |
| `iam_role` | Role ARN, read only | `tklbam/lib/py2_duplicity.py:112-114` | Read, never written here; origin UNVERIFIED |

Three credential shapes exist: `DevPay`, `IAMUser` and `IAMRole`
(`tklbam/lib/hub.py:159-185`). A registry file with no `type=` is treated as
`DevPay` for backwards compatibility (`tklbam/lib/hub.py:202-204`).

Credentials leave the registry in two ways. For `devpay` and `iamuser` they are
exported to duplicity as `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and
`X_AMZ_SECURITY_TOKEN` (`tklbam/lib/py2_duplicity.py:96-103`). For `iamrole`
the static variables are deliberately unset and boto3 is pointed at a temporary
`AWS_CONFIG_FILE` holding a `credential_process` line
(`tklbam/lib/py2_duplicity.py:105-129`), written `0600` and removed after the
child exits (`tklbam/lib/py2_duplicity.py:48-62`, `py2_duplicity.py:156-159`).
The passphrase reaches duplicity through the environment
(`tklbam/lib/py2_duplicity.py:131`).

The Hub API key itself is passed on the `tklbam-init` command line by
`80hub-services` (`inithooks/bin/hubservices.py:97-102`), which the tool's own
help calls out as less secure than prompting (`tklbam/lib/cmd_init.py:53-60`).
It also lands in the inithooks answers file as `HUB_APIKEY`
(`inithooks/firstboot.d/80hub-services:6-9`); the permissions of that file are
UNVERIFIED here.

## 5. inithooks

| Call site | Operation | First boot | Blocks | On failure today |
| --- | --- | --- | --- | --- |
| `inithooks/firstboot.d/80hub-services:9` -> `inithooks/bin/hubservices.py:97-114` | Non-interactive: `tklbam-init`, then `hubdns-init` and `hubdns-update` | Yes | Yes in the non-interactive path | All three run with `check=True`, so a failure raises `CalledProcessError` and the hook, running under `bash -e`, fails |
| `inithooks/bin/hubservices.py:133-139` | `host -W 2 hub.turnkeylinux.org` reachability probe | Yes, interactive path | No | Dialog shows `CONNECTIVITY_ERROR` and breaks out of the loop (`hubservices.py:56-65`) |
| `inithooks/bin/hubservices.py:141-152` | `tklbam-init` | Yes, interactive path | No | stderr shown in a msgbox, loop continues |
| `inithooks/bin/hubservices.py:169-186` | `hubdns-init` and `hubdns-update` | Yes, interactive path, only after tklbam linked (`hubservices.py:154`) | No | Failures shown in a msgbox, loop continues |
| `inithooks/firstboot.d/85secalerts:10-12` -> `inithooks/bin/secalerts.sh:57-70` | `POST https://hub.turnkeylinux.org/api/server/secalerts/` with `email` and `turnkey_version` | Yes | No | The generated `/etc/cron.hourly/enable_secalerts` runs `curl --silent --fail ... \|\| exit 0` and only deletes itself on success, so it retries hourly forever |
| `inithooks/firstboot.d/29tagid:22-27` | Appends two `<script src="https://ajax.turnkeylinux.org/initfence/$BUILD/$VERSION/$APP_NAME.js\|.direct">` tags to the initfence page | Yes | No | Nothing: the tags are written unconditionally and the fetch happens in the visitor's browser, not on the appliance |

`29tagid` is guarded by `[ -n "$_TURNKEY_INIT" ] && exit 0`
(`inithooks/firstboot.d/29tagid:3`), so it does not re-run under
`turnkey-init`. The beacon is a build and version identifier, so it is also a
fingerprint of the appliance: `BUILD`, `VERSION` and `APP_NAME` are derived
from `/etc/turnkey_version` and `/etc/apt/apt.conf.d/01turnkey`
(`inithooks/firstboot.d/29tagid:5-7`).

The `hubdns` package is installed as part of the base plan
(`common/plans/turnkey/base:40`). Its source is not in the forked set, so what
`hubdns-init` and `hubdns-update` actually speak, and where they store the API
key, is UNVERIFIED from this inventory.

## 6. confconsole

No confconsole code contacts the Hub. Three occurrences are text:

- `confconsole/confconsole.py:566-570` prints `https://hub.turnkeylinux.org`
  under "TurnKey Backups and Cloud Deployment" on the services screen.
- `confconsole/plugins.d/Mail_Relaying/mail_relay.py:12-18` points the operator
  at `https://hub.turnkeylinux.org/email` to sign up for a relay account. The
  plugin itself opens an SMTP session against whatever host is entered
  (`mail_relay.py:29-40`) and stores the password in
  `/etc/postfix/sasl_passwd`, root-readable only, as the dialog states
  (`mail_relay.py:20-26`).
- `confconsole/docs/Mail_relay.rst:33` repeats the URL.

Backup status in the TUI is obtained by running the local `tklbam-status
--short`, guarded by a `which` check (`confconsole/confconsole.py:516-532`), so
confconsole degrades to a message when tklbam is absent and never makes a
network call of its own.

Let's Encrypt is entirely ACME. The CA is a dehydrated config variable, with
the staging directory URL present as a comment
(`confconsole/share/letsencrypt/dehydrated-confconsole.config:18-29`), driven
by `confconsole/plugins.d/Lets_Encrypt/dehydrated-wrapper:20-26`. DNS-01 uses
lexicon against the operator's own provider
(`confconsole/share/letsencrypt/dehydrated-confconsole.hook-dns-01.sh:30-62`,
provider templates in `confconsole/share/letsencrypt/lexicon-confconsole-provider_*.yml`).
Nothing here needs replacing.

## 7. Package archive and build mirrors

These are not Hub API calls, but they are project-hosted infrastructure the
appliance and the builds depend on.

- `common/conf/bootstrap_apt:208`, `:225`, `:251` write
  `URIs: http://archive.turnkeylinux.org/debian` into deb822 sources, and
  `:261`, `:268`, `:279` write the one-line equivalents for `main`,
  `-security` and `-testing`. `:291` can comment them all out again.
- `buildtasks/bt-img:121` sets `IMAGES="http://mirror.turnkeylinux.org/turnkeylinux/images"`
  and `buildtasks/bt-iso:356` sets the bootstrap base URL under the same host.
- `buildtasks/bin/signature-verify:97` fetches the signing key from
  `https://www.turnkeylinux.org/$BT_GPGKEY.asc`.
- Publication targets are already environment variables:
  `BT_PUBLISH_IMGS`, `BT_PUBLISH_META`, `BT_PUBLISH_PROFILES`,
  `BT_PUBLISH_SCREENS` (`buildtasks/bt-iso:275-279`,
  `buildtasks/bt-container:53-54`).
- `tklbam/contrib/ez-apt-install.sh:26` and `:34` default `APT_URL` to
  `http://archive.turnkeylinux.org/debian`, already overridable.

All of this is plain APT and plain HTTP: easy to repoint, but Keel has to host
the replacement.

## 8. The S3 path, and the smallest change

### 8.1 tklbam-python-boto is no longer on the S3 path

The brief names `tklbam-python-boto` as the first piece to study. On tklbam
1.5.x it is dead code with respect to backups. `tklbam/debian/control:20-33`
lists `tklbam-python-boto` under `Conflicts` and `Replaces`, not `Depends`, and
`tklbam/debian/control:34-44` depends on Debian's `duplicity` plus
`turnkey-python3-boto3 | python3-boto3`. The bundled dependency list
(`tklbam/dep-commit-ids:1-4`) contains `python-pycurl`, `pycurl-wrapper`,
`python-dateutil` and `python-six`, fetched by
`tklbam/duct-tape-deps.sh:24-50`; boto is not among them. The fork itself still
hardcodes `DefaultHost = 's3.amazonaws.com'`
(`tklbam-python-boto/boto/s3/connection.py:137`, constructor default at `:143`),
but nothing in tklbam imports it. Patching it would change nothing.

The real chain is: tklbam builds a `Target`, then execs `/usr/bin/duplicity`,
which uses boto3.

### 8.2 What already exists

- `DUPLICITY` selects the binary (`tklbam/lib/py2_duplicity.py:27-28`).
- `TKLBAM_APIURL` selects the Hub base URL (`tklbam/lib/hub.py:212`).
- `TKLBAM_REGISTRY` and `TKLBAM_CONF` relocate state and config
  (`tklbam/lib/registry.py:66-67`, `tklbam/lib/conf.py:91`).
- `--address` on both `tklbam-backup` and `tklbam-restore` overrides the target
  entirely and bypasses every Hub call except the profile
  (`tklbam/lib/cmd_backup.py:26`, `tklbam/lib/cmd_backup.py:337`,
  `tklbam/lib/cmd_restore.py:44`, `tklbam/lib/cmd_restore.py:441-448`).
- `/etc/tklbam/conf` accepts `full-backup`, `volsize`, `s3-parallel-uploads`,
  `restore-cache-size`, `restore-cache-dir`, the three `backup-skip-*` flags
  and `force-profile` (`tklbam/lib/conf.py:180-186`). There is no `address`
  and no endpoint option: `Conf.address` exists as an attribute
  (`tklbam/lib/conf.py:150`) but is only ever set from the command line
  (`tklbam/lib/cmd_backup.py:267-268`).

### 8.3 What blocks a non-AWS endpoint

`Target.__init__` (`tklbam/lib/py2_duplicity.py:217-247`) parses the address,
and it only understands AWS hostnames. `S3_ENDPOINT_RE`
(`tklbam/lib/py2_duplicity.py:214-215`) matches
`^s3[.-](?:dualstack\.)?([a-z0-9-]+)\.amazonaws\.com$`, with
`s3.amazonaws.com` special-cased to `us-east-1`
(`tklbam/lib/py2_duplicity.py:231-232`). When a region is found, the host
element is deleted from the address and the region is passed on as
`--s3-region-name` by `_region_opts` (`tklbam/lib/py2_duplicity.py:181-198`,
used at `py2_duplicity.py:270` and `py2_duplicity.py:364`). The host has to be
removed because duplicity parses the whole `s3://` URL as a path and would
otherwise read the endpoint as the bucket name
(`tklbam/lib/py2_duplicity.py:184-190`).

So for `s3://storage.example.net/bucket/prefix`, the regex does not match, the
host is left in the address, and duplicity treats `storage.example.net` as the
bucket. The code prints `ERROR: could not determine AWS region - this may cause
failure` (`tklbam/lib/py2_duplicity.py:242-243`) and carries on to fail. Note
also that both transfers pass `--s3-unencrypted-connection`
(`tklbam/lib/py2_duplicity.py:295`, `py2_duplicity.py:388`), which is a
separate decision worth a note of its own.

### 8.4 Recommendation: the smallest change

Duplicity already has the right knob, `--s3-endpoint-url`, which takes a full
endpoint URL and makes the host-in-path problem go away. The minimal change is
therefore confined to one file and two functions:

1. `tklbam/lib/conf.py`, `Conf.__init__` and `Conf.__setitem__`
   (`tklbam/lib/conf.py:100-140` and `tklbam/lib/conf.py:141-192`): add one
   option, `s3-endpoint-url`, to the tuple at `tklbam/lib/conf.py:180-186`,
   default `None`, with an environment override in the same style as
   `TKLBAM_APIURL`, for example `TKLBAM_S3_ENDPOINT_URL`.
2. `tklbam/lib/py2_duplicity.py`, `Target.__init__`
   (`tklbam/lib/py2_duplicity.py:217-247`): accept an optional
   `endpoint_url` argument, store it on the `Target`, and when it is set skip
   the region extraction and the warning at
   `tklbam/lib/py2_duplicity.py:236-243`, leaving the address untouched.
3. `tklbam/lib/py2_duplicity.py`, `_region_opts`
   (`tklbam/lib/py2_duplicity.py:181-198`): when `target.endpoint_url` is set,
   emit `[("s3-endpoint-url", target.endpoint_url)]` in addition to, or instead
   of, the region option. Both callers already route their options through this
   one function (`py2_duplicity.py:270`, `py2_duplicity.py:364`), so
   `Downloader` and `Uploader` need no change at all.

The two `Target(...)` construction sites then pass the new value through:
`tklbam/lib/cmd_backup.py:402` and `tklbam/lib/cmd_restore.py:462`.

This touches no Hub code, no registry format and no credential handling. It
makes `tklbam-backup --address=s3://bucket/prefix` work against any
S3-compatible endpoint when the endpoint is configured in `/etc/tklbam/conf`,
which is exactly the sovereign-backup case, while leaving the Hub path
bit-identical when the option is unset.

Two follow-ons, deliberately out of scope of that change because they are
larger and need decisions:

- Static credentials in the registry. `hub.Credentials.from_dict`
  (`tklbam/lib/hub.py:187-209`) will already build an `IAMUser` from a file
  containing `type=iamuser` plus the three fields, and
  `tklbam/lib/py2_duplicity.py:96-103` will export them. No command writes such
  a file today, so a `tklbam-init --credentials-file` or equivalent is the
  missing piece for backups with no Hub at all.
- Profiles. With the endpoint configurable and credentials static, the only
  remaining hard Hub dependency on the backup path is the profile
  (`tklbam/lib/registry.py:294-318`). `--force-profile=path` already accepts a
  local directory (`tklbam/lib/registry.py:239-275`) and `tklbam-profiles`
  holds the profile sources, so serving profiles over plain HTTP from the Keel
  archive is a smaller job than replacing the Hub API.

## 9. Documented protocol versus Hub-specific API

Easy to repoint, because the protocol is public:

- S3, spoken by duplicity and boto3 (`tklbam/lib/py2_duplicity.py:295`,
  `py2_duplicity.py:388-404`). Also `file://`, `rsync://`, `ssh://` and
  `ftp://` targets, which `Target` explicitly tolerates
  (`tklbam/lib/py2_duplicity.py:222-226`).
- AWS STS, reached through the Hub rather than directly, but the credential
  shapes and the boto3 `credential_process` JSON are public
  (`tklbam/lib/cmd_internals/cmd_stsagent.py:79-100`).
- ACME through dehydrated, with a configurable CA
  (`confconsole/share/letsencrypt/dehydrated-confconsole.config:18-29`).
- DNS, through lexicon providers
  (`confconsole/share/letsencrypt/dehydrated-confconsole.hook-dns-01.sh:30-62`).
- SMTP, for the mail relay (`confconsole/plugins.d/Mail_Relaying/mail_relay.py:29-60`).
- APT over HTTP (`common/conf/bootstrap_apt:208-291`).
- Plain HTTP file serving for build inputs (`buildtasks/bt-img:121`,
  `buildtasks/bt-iso:356`).

Hub-specific, with no open equivalent, so each needs a Keel service or a
decision to drop it:

- `GET subkey/` (`tklbam/lib/hub.py:228-231`). An account-key to sub-key
  exchange with a Hub-defined key format (`tklbam/lib/cmd_init.py:92-99`).
- `GET credentials/` (`tklbam/lib/hub.py:233-235`). A credential broker with
  three Hub-defined credential shapes (`tklbam/lib/hub.py:159-185`).
- `GET archive/` and `GET archive/timestamp/`
  (`tklbam/lib/hub.py:237-262`). Profile distribution as a base64 tarball
  inside a JSON field, keyed by `turnkey_version`.
- `POST record/create/`, `GET record/<id>/`, `PUT record/<id>/`,
  `PUT record/<id>/inprogress/`, `PUT record/update/`, `GET records/`
  (`tklbam/lib/hub.py:264-292`). The backup catalogue, including address
  allocation and escrowed key storage.
- `POST /api/server/secalerts/` (`inithooks/bin/secalerts.sh:61-64`).
- `https://ajax.turnkeylinux.org/initfence/...`
  (`inithooks/firstboot.d/29tagid:24-25`).
- HubDNS, whatever `hubdns-init` and `hubdns-update` speak
  (`inithooks/bin/hubservices.py:104-114`). Protocol UNVERIFIED: the package is
  not in the forked set. The capability itself, dynamic DNS, has open
  equivalents, so this is a decision rather than a reimplementation.

The Hub's own error vocabulary is part of the contract too, and a replacement
service has to reproduce at least the names tklbam branches on:
`BackupRecord.NotFound`, `BackupAccount.NotSubscribed`,
`BackupAccount.NotFound` (`tklbam/lib/hub.py:114-126`) and
`BackupArchive.NotFound` (`tklbam/lib/registry.py:310-313`). The full list is
at `tklbam/lib/hub.py:65-78`.
