# 0094: Keel retires Webmin: SSH, confconsole, SFTP and a database client through SSH

Date: 2026-11-23
Status: **accepted 2026-11-23.** The maintainer decided the direction on
2026-11-23: Keel retires Webmin. He chose the database tool: DBeaver on
the administrator's computer through an SSH tunnel, and no web database
tool on the node. On 2026-11-23 he answered the 8 questions of the
proposal. The answers are under "Questions for the maintainer,
answered". Nothing in this note is built.

Sources: a study of Webmin and its alternatives and a package inventory,
both of 2026-11-23. They are not published in this handbook. This note
gives the repository path for each fact that it takes from them. Each
repository path below was read on the default branch of the repository
on 2026-11-23, after `git fetch`. "Read in code" means that
nobody tested it on a running node.

## What was asked

Webmin is in all 11 published images (release 2026-11-12), from the core
layer. The maintainer gave 3 reasons to retire it:

1. **Security.** Webmin is a web server that runs as root. It listens on
   TCP 12321 on every address. Keel ships the TurnKey binaries
   `2.660.turnkey0` and cannot build them again from source.
2. **Drift.** A change in Webmin (a certificate, `php.ini`, a service)
   is outside the declared state. Thus it does not go to the other node
   in `cloud_simple` or `cloud_advanced`, and an upgrade can lose it.
3. **Maintenance.** Webmin is 23 of the 54 binary packages of the Keel
   archive that Keel must follow.

The replacement: the administrator connects by SSH and uses confconsole.
confconsole gets explicit menus for the settings. Files move by SFTP. A
graphical database tool stays available, because customers edit tables,
database users and single fields, not only imports. The maintainer
accepts that users must learn SSH and SFTP. A graphical front end over
the same engine can come much later. It is out of scope.

## Why (brief section 10)

1. **Why a change is necessary.** Webmin is the only root web listener
   on a Keel node, and it is public in every mode today. Decision 0049
   restricts it but is not built. Most Webmin writes go to files that
   `keel diff` does not read: sshd, Postfix, iptables rules, fail2ban,
   packages, the root password. keel reads only its own nftables table
   and the units and users (`keel/keel/inspect/`).
2. **Whether it can be made to work.** An administrator can do nothing
   in Webmin that a root SSH session cannot do. Each Webmin module is a
   front end to files and commands of the system.
   confconsole already has screens that write the spec through `keel`
   (certificate, WireGuard, database mode). DBeaver Community has an SSH
   tunnel and supports MariaDB and PostgreSQL.
3. **Why this is better.** It removes a root listener and 23 packages
   that Keel cannot build. Each setting that a menu changes goes through
   one engine into `instance.yaml`, where `keel diff` sees it.

## Decision

1. Keel retires Webmin from all images. No web administration panel
   replaces it.
2. The administrator connects by SSH. confconsole is the menu for the
   settings. Files move by SFTP.
3. The database tool is a desktop client on the administrator's
   computer, through an SSH tunnel. The documented client is DBeaver
   Community. Keel installs no web database tool on the node.
4. Port 12321 closes. Keel opens no new public port.
5. Removal from a node in the field is always an act of its
   administrator, never a side effect of an upgrade.
6. An administrator account opens confconsole directly when it logs in
   by SSH (design rule 3).
7. Redis has no graphical tool. The administrator uses `redis-cli` in
   the SSH session.
8. keel copies the settings sections of `instance.yaml` from the primary
   to the replica, as 0092 decided for `mail`.
9. A read-only confconsole screen shows the resource use: CPU, memory,
   disk, I/O and PSI.
10. Webmin is deprecated with the first stable image that has all the
    menus.

## What replaces each Webmin task

Columns: "spec key" means that `keel` has a key in `instance.yaml` for
it today (`keel/docs/spec.md`). "Screen" means that confconsole has a
screen for it today (`confconsole/plugins.d/`). "Pair" means that the
result reaches the other node of a pair today.

No mechanism copies `instance.yaml` from one node of a pair to the
other today. Only `appliance.vip` travels, in the invite
(`keel/docs/spec.md`, `appliance.vip`). Decision 0092 decided that the
replica gets the `mail` section, but that is not built. Thus "Pair" is
"no" for each setting today. Decision 8 makes keel copy the settings
sections to the replica (work item 4). Until then, reason 2 of the
maintainer is not solved.

| Task | Replacement | Spec key | Screen | Pair |
| --- | --- | --- | --- | --- |
| a. Send and manage files | SFTP with the SSH account. OpenSSH has it, no new package | n/a | n/a | the replicated paths of 0050 go to the pair. Other paths do not |
| b1. SSH settings | a confconsole screen that calls `keel` | `users.<name>.authorized_keys` only. No key for sshd options | no | no |
| b2. nginx settings | a confconsole screen that calls `keel` | no (0042 sites are not in `spec.md`) | no | no |
| b3. PHP settings (`php.ini`) | a confconsole screen that calls `keel` | no | no | no |
| b4. Python, Go, Rust, Ruby back ends | the same model as b3, one key set per runtime (0091 names `keel-app.service`) | no | no | no |
| c. Import a dump (`.sql`, `.sql.gz`, `.zip`) | the dump goes up by SFTP, then a confconsole screen calls a `keel` command that imports it. DBeaver can also import it | n/a (data) | no | yes, by database replication, when the import runs on the primary |
| d. Browse and edit tables, database users, single fields | DBeaver through an SSH tunnel to the primary | n/a (data) | n/a | yes, by database replication |
| d2. The same for Redis | `redis-cli` in the SSH session (decision 7) | n/a | n/a | depends on the image: 0087 keeps one Redis on each node, not replicated |
| e. Resource use: CPU, memory, disk, I/O, PSI | today: the `monitor` section sends alerts for CPU, load, memory, swap, disk, inodes and network (`keel/docs/spec.md`, `monitor`, and decision 0021). A live view of I/O and PSI does not exist. A read-only confconsole screen shows it (decision 9) | `monitor.checks.*` for thresholds | no | no |
| f. Add system users | a confconsole screen that calls `keel` | yes: `users.<name>` with `authorized_keys`, `shell`, `groups` (`apply --system` creates, never deletes) | no | no |
| g. TLS certificates | the confconsole Let's Encrypt screen. It writes `tls.acme.*` through `keelcli` (`confconsole/plugins.d/Lets_Encrypt/get_certificate.py`) | yes: `tls.acme.*` | yes | no |
| h. A root terminal | SSH | n/a | n/a | n/a |

Summary: certificates (g), files (a) and the root terminal (h) exist
today. Users (f) have a key and need a screen. Everything else must be
built. The tunnel for d does not work today (see "The database client").

## Design rules

### 1. One engine

A confconsole menu does not edit a configuration file. It calls `keel`,
which writes `instance.yaml` and converges the node. The certificate
screen and the WireGuard screen (`confconsole/wgscreen.py`) already
follow this rule. A setting that has no spec key gets a key in keel
first, then a screen. `keel diff` then reports a change that a person
made by hand.

### 2. Files go by SFTP

File transfer is SFTP, the subsystem of OpenSSH that each image already
has. Keel does not offer plain FTP, because FTP sends the password and
the files in clear text and needs extra ports.

### 3. A restricted administrator login

An administrator account opens confconsole directly when it logs in by
SSH. The design is work item 6. It must answer these questions:

- Which user: root with a forced command, or a new account. sudo is not
  in the base plan (`common/plans/turnkey/base`) or in the Keel stable
  pool (`apt/conf/pools/stable-4/files`).
- Keys only, or keys and a password.
- SFTP for the same account, or a separate account in a chroot.

### 4. The database client

The node offers SSH only. The administrator runs DBeaver Community on
his computer. DBeaver opens an SSH tunnel to the node and connects to
the database on the loopback of the node.

Facts about DBeaver, read 2026-11-23:

- DBeaver Community is Apache-2.0
  (<https://raw.githubusercontent.com/dbeaver/dbeaver/devel/LICENSE.md>).
- The Community wiki describes the SSH tunnel with a password, a key or
  an agent, and jump hosts. The page names no edition limit
  (<https://github.com/dbeaver/dbeaver/wiki/SSH-Configuration>).
- dbeaver.io lists MySQL, MariaDB, PostgreSQL and SQLite for Community
  (<https://dbeaver.io/>).
- Redis is not in Community. The vendor page says: "This driver is
  available in Lite, Enterprise, and Ultimate editions only."
  (<https://dbeaver.com/docs/dbeaver/Redis/>).

What the node must allow, checked against the images:

| Need | State today | Work |
| --- | --- | --- |
| sshd lets the account forward a TCP port | **no**: `common/overlays/turnkey.d/sshd/etc/ssh/sshd_config.d/turnkey.conf` sets `AllowTcpForwarding no` and `MaxSessions 2` (read in code) | a `Match User` block for the administrator account with `AllowTcpForwarding local` and `PermitOpen` set to the loopback database ports only (3306, 5432). Redis needs no forward, because `redis-cli` runs on the node. sshd keeps the first value it reads for a keyword, and the TurnKey file ends in `Match user *`. Thus the place and order of a Keel drop-in must be tested |
| The database listens on the loopback | yes: MariaDB `bind-address = ::1,127.0.0.1` (`keel-lnmp/conf.d/main`, `99-keel-bind.cnf`). PostgreSQL `listen_addresses = '::1,127.0.0.1'` (`keel-postgresql/conf.d/main`) | none |
| A database account with a password | MariaDB: `admin` on `localhost`, `::1`, `127.0.0.1`, with the password of `secrets.db_password` at first boot (`keel-mariadb/conf.d/main`). PostgreSQL: `postgres` gets the same password at first boot (`keel-postgresql/README.rst`). Redis: an ACL user that the first boot declares (`keel-redis/conf.d/main`) | a confconsole screen that shows the account name and that changes its password through `keel`. Whether `pg_hba.conf` accepts a password on TCP loopback is not checked |
| No write on a replica | MariaDB: keel takes `READ_ONLY ADMIN` from every account except the socket accounts, `admin` included (`keel/keel/system/dbreadonly.py`). PostgreSQL: a hot standby refuses writes | the guide tells the administrator to tunnel to the primary. The Webmin warning of 0049 goes away with Webmin |

Rejected alternatives, with the reason: a web tool from Debian trixie
main on the node. `adminer` 5.2.1+dfsg-1 (MariaDB, PostgreSQL and others)
has 17 CVEs open in trixie on the security tracker. `phpmyadmin`
4:5.2.2-really+dfsg-1+deb13u1 (MariaDB only) has 4 open in every suite.
`phppgadmin` 7.14.7+dfsg-1 (PostgreSQL only) has 4 not yet triaged.
`pgadmin4` is not in Debian. It comes from the pgAdmin APT repository.
No Redis web or desktop tool is in Debian. Each web tool adds a web
surface on the node, needs PHP or a web server, and is software that
Keel must follow. Sources:
<https://security-tracker.debian.org/tracker/source-package/adminer>,
the same page for `phpmyadmin` and `phppgadmin`,
<https://qa.debian.org/madison.php?package=pgadmin4&text=on>,
<https://www.pgadmin.org/download/pgadmin-4-apt/>.

The import of a dump stays a confconsole item (task c). The file goes up
by SFTP.

### 5. No new public port

12321 closes. Keel opens no other port for administration. The work
items below list each place that names 12320, 12321 or 12322. This note
changes none of them.

Files that name one of the 3 ports, by repository (default branch, with
tests, without changelogs):

| Repository | Files |
| --- | --- |
| `keel-core` | `Makefile`, `README.rst`, `docs/locking-down-services.rst`, `overlay/etc/confconsole/services.txt`, `packages/keel-core/manifest.yaml` (process `webmin`, 12321 `expose: public`, a Monit check, the `root_password` text "for SSH and Webmin"), `tests/banner.bats`, `tests/commission.yaml`, `tests/package.bats` |
| `keel-web`, `keel-lnmp`, `keel-wordpress`, `keel-nodebb`, `keel-nextcloud` | `Makefile` (`WEBMIN_FW_TCP_INCOMING`), `services.txt` (not nextcloud), `tests/commission.yaml`, `tests/commission-core.yaml`, the recipe or image tests; `keel-wordpress/README.rst` |
| `keel-lnpp`, `keel-odoo`, `keel-laravel` (branch `19.x`), `keel-loops` | `Makefile`, `services.txt`, `tests/boot-test.sh`, `tests/boot-test.bats`, `tests/lib/boot-test-lib.sh`, `tests/commission*.yaml`; `keel/instance.example.yaml` of lnpp and odoo; `README.rst` of laravel. laravel and loops also open 12320 |
| `keel-mariadb`, `keel-postgresql`, `keel-redis` | `Makefile`, `README.rst`, `COVERAGE.md`, `keel/instance.example.yaml`, `services.txt`, `tests/README.md`, `tests/boot-test.*`, `tests/firewall.bats`, `tests/commission*.yaml`; `keel-mariadb/evidence/2026-10-08-boot-gate.md` |
| `keel-ntfy` | `Makefile`, `tests/commission.yaml`, `tests/layer.bats` |
| `keel-lnmn`, `keel-lnpn`, `keel-pixelfed` | `Makefile`, `services.txt` (pixelfed: no remote branch, read in the local checkout) |
| `keel-lamp`, `keel-lapp`, `keel-apache-php` | retired by 0059; `Makefile`, `README.rst`, `conf.d/main`, the boot tests |
| `common` | `conf/turnkey.d/webmin-fw`, `webmin-conf-logging`, `overlays/turnkey.d/fail2ban/etc/fail2ban/jail.local`, `tests/webmin-brand.bats`, `tests/webmin-net.bash`; 12322 in `conf/adminer*`, `mk/turnkey/*.mk`, `overlays/adminer`, and other TurnKey overlays that no Keel image uses |
| `confconsole` | `README.rst`, `conf/services.txt` (also the web shell on 12320), `confconsole.py`, `docs/Networking.rst`, `tests/test_confconsole_usage.py` |
| `inithooks` | `default/turnkey-init-fence` (`HTTPS_PORTS=(443 12321 12322)`), its tests and fixtures |
| `keel` | `keel/manifest/firewall.py` derives 12321 from the manifest in cloud advanced; `docs/apply.md`, `docs/manifest.md` (12320 and 12321 as Core ports), the docstring of `keel/system/dbreadonly.py`, test fixtures |
| `dot-github` | the commissioning fixtures and `tests/keel-commission-vm.bats`; `lib/commission/screens.py`, `web.sh`, `webshot.py` take the Webmin screenshots |
| `site` | `security.html` |
| `apt` | the `Packages` files of `trixie` and `trixie-testing`, which list the Webmin packages |

## The WireGuard access peer: a later step

The database client needs no WireGuard. A WireGuard access peer for the
administrator's computer is a later step, which makes the internal
network reachable with no SSH tunnel. It is not a dependency of this
note.

What exists today:

- A WireGuard mesh between Keel nodes on `wg0`, UDP port 51820 by
  default (`network.overlay.wireguard.listen_port`,
  `keel/docs/spec.md`). Nodes join by `keel mesh invite` and
  `keel mesh join` (0048).
- `keel mesh create --adopt` and `keel mesh sync --adopt` make each peer
  that the spec lists an **operator root** (`keel/docs/mesh.md`,
  "trust roots"). An operator root can remove a node from the mesh, have
  a certificate revoked and sign a VIP pair record.
- The derived firewall opens each `expose: mesh` port on `wg0` to each
  peer, for example etcd 2379 and 2380 and Syncthing 22000
  (`common/packages/*/manifest.yaml`).

What does not exist: an access peer for the computer of a person. The
idea is keel#74 (`keel mesh invite --workstation`), open, with no
decision. The manifest of the overlay names a confconsole screen that
does not exist: `screen: /usr/lib/confconsole/plugins.d/Networking/wireguard.py`
(`common/packages/wireguard/manifest.yaml`). confconsole has the screen
at `plugins.d/Instance/Overlay_network.py`.

Proposed rule: **the computer of an administrator is a restricted access
peer, not a mesh member.** It reaches only named services (SSH, and a
database port if the maintainer wants it) and gets no operator root
rights. The reason is the list above: a peer that the spec lists can
become an operator root, and it reaches each mesh port.

The direction of the maintainer for the basic version: the
administrator pastes one command in a terminal on his computer, as the
install command of `cloudflared` does, with a token in the command.
Rules proposed for that work, to confirm when it is designed:

- The value in the command is an enrolment token that is valid once and
  for a short time. It is not the WireGuard private key.
- The script makes the key pair on the computer of the administrator and
  sends only the public key. The node never has the private key.
- The node itself serves the script, or a signed Keel source does.

The platforms (Linux, macOS, Windows) are a question for that design.

Dependency: keel#303. CrowdSec bans a mesh address, because its
whitelist does not have the mesh prefix.

Out of scope: the transport. WireGuard uses UDP only. Thus "443" can
only be UDP 443 or another transport, not TCP 443.

keel#74 holds the wider workstation idea. This note un-parks only the
basic access peer. The wider options of 2026-11-19 stay parked.

## Transition

The 11 published stable images and the nodes in the field move in this
order:

1. **The firewall loader comes first.** `common/conf/turnkey.d/webmin-fw`
   writes `/etc/iptables/rules.v4` and `rules.v6`, switches the iptables
   alternative to `iptables-legacy`, and overrides
   `webmin-iptables.service` and `webmin-ip6tables.service`. Webmin's
   firewall module makes these units (`create_webmin_init` in
   `firewall-lib.pl` of `webmin-firewall` 2.660). keel writes a firewall
   only in cloud advanced (`keel/docs/spec.md`, `firewall`). Thus, if the
   removal of `webmin-firewall` stops the loader, a node in the simple
   or cloud simple mode loses its firewall. Read in code. A replacement
   loader (Debian `netfilter-persistent`, or keel's nftables in every
   mode) is built and tested before any removal.
2. **The menus exist.** The screens of the table above, the sshd change
   for the tunnel and the guides are in a stable image.
3. **Webmin is deprecated** with the first stable image that has all
   the menus (decision 10). The release notes, the site and the boot
   banner say so.
4. **New images ship without Webmin.** No `webmin*` package, no 12321,
   no Webmin process in the manifest.
5. **A node in the field keeps Webmin until its administrator removes
   it.** An upgrade of `keel-core` must not drop the `webmin` process
   from the resolved manifest of a node that still has Webmin, because
   Monit and the cloud advanced nftables follow that manifest. The
   declaration of the process stays with the Webmin package or ends with
   the removal act. The removal is one confconsole item that calls
   `keel`.
6. **The upgrade test of 0090** shows on one node of each published
   image:
   - After the upgrade: 12321 still answers, the firewall rules are
     loaded, Monit is green, `keel diff` is clean.
   - After the removal act: 12321 is closed on IPv6 and IPv4, the
     firewall rules are loaded after a reboot, Monit is green with no
     Webmin check, `keel diff` is clean, fail2ban runs with no
     `[webmin-auth]` jail, SFTP works, and DBeaver connects through the
     tunnel.

## What this amends

This note changes these notes. It does not edit them.

- **0019** (Webmin does not change the network): ends with Webmin.
- **0041** (the manifest, version 1): the Core table loses Webmin and
  12321.
- **0042** (Keel Web sites): the certificate steps no longer restart
  Webmin.
- **0049**: only its Webmin sections end ("Webmin, per mode and role",
  "How miniserv is configured per role", "The replica's warning and
  module"). The VIP, the rejoin and the MariaDB guard on a replica stay.
- **0052**: the boot layer loses `webmin-fdisk`, `webmin-lvm`,
  `webmin-mount` and `webmin-raid`.
- **0059**: `conf/php` no longer points Webmin's PHP module at a
  `php.ini`.
- **0075**: commissioning takes no Webmin screenshot. It takes a
  screenshot of the confconsole screens and a proof of SFTP and of the
  tunnel instead.
- **0077**: the application pages show no Webmin.
- **0091**: `keel-lnmn` does not copy the `webmin-mysql` lines.

The index row of each amended note says "amended by 0094".

## Consequences

Gained:

- No root web listener. The pre-auth surface of administration is sshd
  only.
- The `iptables-legacy` switch can go. CrowdSec no longer needs its
  bouncer forced to nftables (`keel/docs/apply.md`).
- 23 packages fewer, all TurnKey binaries: `webmin`,
  `webmin-authentic-theme`, `-custom`, `-fail2ban`, `-fdisk`,
  `-filemin`, `-firewall`, `-firewall6`, `-logviewer`, `-lvm`, `-mount`,
  `-mysql`, `-net`, `-passwd`, `-postfix`, `-postgresql`, `-raid`,
  `-software`, `-sshd`, `-systemd`, `-updown`, `-useradmin`, `-xterm`
  (`apt/pool/main/w/webmin/`).
- Each setting that a menu changes is in `instance.yaml`.

Lost:

- A browser file manager, a browser terminal and a browser database
  tool.
- Settings that have no menu yet: until the menu exists, the
  administrator edits the file in SSH, as Webmin did.

What users must learn: an SSH client, an SFTP client, `redis-cli`, and DBeaver with
its SSH tunnel.

Documentation needed: a short guide for each platform (Windows, macOS,
Linux) for people from cPanel: make an SSH key, connect, send files by
SFTP, connect DBeaver through the tunnel.

## Questions for the maintainer, answered

The maintainer answered on 2026-11-23.

1. Does an administrator account open confconsole directly at its SSH
   login? Yes.
2. Which Redis tool? (a) `redis-cli` in the SSH session only.
3. When is Webmin deprecated? (a) With the first stable image that has
   all the menus.
4. Is the resource view a confconsole screen? Yes.
5. Does keel copy the settings sections of `instance.yaml` from the
   primary to the replica? Yes.
6. Is a private key made on the node acceptable for the access peer? Not
   necessary: the direction is one command with an enrolment token, and
   the key pair is made on the computer of the administrator.
7. Does this note un-park only the basic access peer of keel#74? Yes.
8. Does the index mark each amended note? Yes.

## What stays open

- The design of the restricted login: which user, keys or a password,
  and SFTP for the same account or a separate one (work item 6).
- The design of the access peer: the platforms, the transport, and the
  confirmation of its 3 rules (work item 18).
- The facts that the work list tests first: the firewall loader, the
  order of the sshd drop-ins, and `pg_hba.conf` on TCP loopback.

## Work list

In order. Nothing is started.

1. **Firewall loader.** Read in code, not tested on a node: test first.
   Test on one node in the simple and the cloud simple mode what loads
   the iptables rules, and what stops after the removal of
   `webmin-firewall`. Evidence file.
2. **sshd forwarding.** Read in code, not tested on a node: test first.
   `AllowTcpForwarding no` in the TurnKey drop-in stops the tunnel. Test
   a `Match User` drop-in with `AllowTcpForwarding local` and
   `PermitOpen` to 3306 and 5432 on the loopback: its order with the
   TurnKey drop-in, SFTP, and `MaxSessions 2` with DBeaver. Evidence
   file.
3. Build the replacement firewall loader for the simple and cloud
   simple modes, and drop the `iptables-legacy` switch from `webmin-fw`.
4. keel: copy the settings sections of `instance.yaml` to the replica.
5. sshd: the drop-in of item 2 in the image.
6. The restricted login: design, then build, with confconsole as the
   session.
7. keel and confconsole: a screen for the database account and its
   password. Check `pg_hba.conf` on TCP loopback.
8. keel and confconsole: the dump import command and screen.
9. confconsole: the users screen on `users.<name>`.
10. keel and confconsole: keys and screens for sshd, nginx and PHP, then
    the other runtimes.
11. confconsole: the resource view.
12. The guides: SSH, SFTP, DBeaver and `redis-cli` for each platform.
13. The deprecation notice with the first stable image that has all the
    menus: release notes, site, boot banner.
14. The image changes: remove Webmin from `common/plans/turnkey/base`,
    the `webmin-*` conf scripts, the image plans, the manifest, the
    firewall lists, `services.txt`, the banner, Monit, `keel` (TLS
    restart, unit list), the boot tests, the fail2ban jail.
15. The removal act for nodes in the field, and its 0090 test.
16. commissioning (0075) and the application pages (0077) without Webmin.
17. The site: `site/security.html`.
18. Later: the WireGuard access peer (keel#74, keel#303, the missing
    screen of `common/packages/wireguard/manifest.yaml`).
