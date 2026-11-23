# Evidence: the firewall loader and the SSH tunnel before the removal of Webmin (decision 0094)

Date: 2026-11-23. Site: BR1, the Keel test VM (nested Proxmox VE, VM 143).
Status: draft. For decision 0094, work items 1 and 2.

## Question

Decision 0094 retires Webmin. Two of its facts were read in code only.
This test checks them on published stable images:

- **A. Firewall.** In `simple` and `cloud_simple`, what loads the
  firewall rules at boot? What is the rule set after the removal of the
  Webmin packages and a reboot?
- **B. SSH tunnel.** Is the TurnKey sshd drop-in with
  `AllowTcpForwarding no` in a built image? Does `ssh -L` to the database
  on the loopback fail today? What is the smallest sshd change that lets
  an administrator account open a tunnel? Can a database account that is
  not root log in with a password over TCP on the loopback?

The test also records these facts:

- which images have `webmin-mysql` or `webmin-postgresql`
- the listening sockets before and after the removal
- whether `iptables-legacy` stays selected after the removal
- the errors that confconsole, the login banner, Monit, fail2ban,
  systemd and `keel` show after the removal

Each result says if it was **tested** on a node, **read** from an image
file system without a boot, or **read in code**.

## Machines and images

The test VM is `keel-pve-br1` (Proxmox VE 9.2.31, kernel
7.0.14-30-pve). All CTs are unprivileged, `nesting=1`, 2 cores, 2 GiB,
rootfs on `local`. Each CT is on the VM's internal bridge `vmbr1` with
a static address: `2804:710:d0:59::11:1NN/120` and `10.189.0.NN/24`.

| CT | Image | Mode | Address (IPv6, IPv4) |
|---|---|---|---|
| 9401 | lnmp 19.0-7 | simple | `::11:141`, `10.189.0.41` |
| 9402 | lnpp 19.0-10 | simple | `::11:142`, `10.189.0.42` |
| 9403 | lnmp 19.0-7 | cloud_simple, mariadb primary, one node | `::11:143`, `10.189.0.43` |
| 9404 | lnpp 19.0-10 | cloud_simple, postgresql primary, one node | `::11:144`, `10.189.0.44` |

The templates come from `https://mirror.keellinux.org/images/`. For
each template, `sqv --keyring keel-images-keyring.asc` on the `.sha512.asc`
exited 0 and printed the images key
`E71DB9C3CA6AC18075395CC3ED3A709C4F3E2F3C`, and `sha512sum -c` passed:

| Template | sha256 |
|---|---|
| `debian-13-keel-lnmp_19.0-7_amd64.tar.zst` | `66aa6fb14aa69a80a73211035daadc6480d20e1e72933a9372051f30405b5319` |
| `debian-13-keel-lnpp_19.0-10_amd64.tar.zst` | `0fe16d74e14b56f921d086f12dc53b661df7ab4de9cbc717ba2e51868ecbdff0` |

Versions on the images: `keel` 0.23.96, `keel-core` 0.1.4, `confconsole`
2.2.3+keel24, OpenSSH 10.0p2 Debian-7+deb13u4, MariaDB 11.8.6,
PostgreSQL 17.11, Webmin 2.660.turnkey0.

Each CT got an instance description in `/etc/keel/instance.yaml` and new
secret files before its first boot. This is the method of the
2026-11-13 upgrade test (`make_preseed.py` from the `instance` section of
the application's `tests/commission.yaml`). The `network` block declares
the static addresses above. For `cloud_simple`, the description turns
on the cloud overlays that the contract names and keeps etcd and vip
off. Thus 9403 and 9404 are one-node `cloud_simple` nodes, not a pair.
Each first boot ended with `0 failed` (log 02).

Kernel modules on the VM: `ip_tables`, `ip6_tables`, `iptable_filter`
and `ip6table_filter` are loaded. `xt_state` is not loaded. An
unprivileged CT cannot load a module. This had no effect on the result,
because no unit on the image tries to load an iptables rule set.

Secret handling: the VM made the secrets inside the file system of each
stopped CT, and no command printed them. The test accounts `evtunnel` (SSH, key only) and `evtest`
(database) are throwaway accounts. Their key and passwords stayed on the
VM and in the CTs, and the CTs are destroyed. A scan of all logs with
each secret value and each test password found 0 matches (log 90). The
first pass on 9402 took a wrong field of the `.pgpass` file (`*`) and
counted false matches. The log has that pass and the correct pass.

## Results

### A1. What loads the firewall at boot (tested, logs 10, 11, 12, 13)

The same result on the 4 nodes, in `simple` and in `cloud_simple`, after
the first boot and after a reboot:

**Nothing loads `/etc/iptables/rules.v4` or `rules.v6`.** The node has
no host firewall that filters input.

- The files exist. `common/conf/turnkey.d/webmin-fw` wrote them at build
  time: `INPUT DROP`, then accept `lo`, ICMP, `ESTABLISHED,RELATED` and
  TCP 22, 80, 443, 12321.
- `webmin-iptables.service` and `webmin-ip6tables.service` do not exist
  (`systemctl is-enabled`: `not-found`). Only the drop-in directories
  that `webmin-fw` makes are in `/etc/systemd/system/`.
- The `webmin-firewall` package does not make the units at install. Its
  `postinst` has no `systemctl` or `iptables` line. The module makes them
  in `create_firewall_init` (`firewall/firewall-lib.pl`, called from the
  module's own pages) when an administrator turns on the firewall at
  boot. Read in code.
- `netfilter-persistent` and `iptables-persistent` are not installed.
- `nftables.service` is enabled and loads `/etc/nftables.conf`. That file
  is the Debian default: `flush ruleset`, then `table inet filter` with 3
  empty chains, policy `accept`.
- `keel-firewall.service` is enabled, but systemd skips it:
  `ConditionPathExists=/etc/keel/firewall/keel-manifest.nft` is not met.
  keel writes that file only in `cloud_advanced` (read in code: the unit
  comment and `keel/docs/spec.md`, `firewall`).
- In `cloud_simple`, the CrowdSec bouncer adds `table ip crowdsec` and
  `table ip6 crowdsec6`. Their input chains have policy `accept` and drop
  only the addresses that CrowdSec bans.

Live rule sets on each node:

```
# iptables-legacy -S INPUT          # ip6tables-legacy -S INPUT
-P INPUT ACCEPT                     -P INPUT ACCEPT
# nft list tables  (simple)         # nft list tables  (cloud_simple)
table inet filter                   table inet filter
                                    table ip crowdsec
                                    table ip6 crowdsec6
```

Proof by effect. A throwaway HTTP listener on TCP 9999, a port that no
list names, answered from the VM on IPv6 and IPv4 (logs 11, 54):

```
[2804:710:d0:59::11:141]:9999 curl_exit=0 http=404     (9401, simple)
10.189.0.41:9999 curl_exit=0 http=404
[2804:710:d0:59::11:143]:9999 curl_exit=0 http=404     (9403, cloud_simple)
10.189.0.43:9999 curl_exit=0 http=404
```

Thus each TCP socket that listens on a public address is open to the
network today. On these nodes that is 22, 80, 443 and 12321, and in
`cloud_simple` the Syncthing listener on a random TCP port on all
addresses (`*:36551` on 9403, `*:44051` on 9404). UDP 12321 also listens
on all IPv4 addresses, and no rule filters it. UDP was not probed from
the VM.

Not tested: an ISO install in a VM, and `cloud_advanced`. The unit files
are absent from the image file system, so a VM made from the same layers
has the same units. An ISO first boot can differ. That is not checked.

**Result for A1: the premise of 0094 is false.** Webmin's firewall module
loads nothing on a published image. The firewall in `simple` and
`cloud_simple` is open, with or without Webmin.

### A2. The rule set after the removal and a reboot (tested, logs 20, 50 to 54)

`apt-get -s remove '^webmin'` removes the 22 Webmin packages and nothing
else. No Keel package depends on Webmin. `apt-get remove` ran on the 4
nodes (exit 0). Then `pct reboot`.

- The rule set is the same as before: legacy `INPUT ACCEPT`, the empty
  `inet filter` table, and in `cloud_simple` the CrowdSec tables. TCP
  9999 still answers on both families (log 54).
- `update-alternatives`: `iptables` and `ip6tables` stay in manual mode
  on `iptables-legacy` and `ip6tables-legacy`. A build script set them,
  not a package.

**Result for A2: PASS.** The removal changes no firewall rule, because
no rule was loaded.

### A3. Listening sockets before and after the removal (tested, logs 12, 52)

| Socket | Before | After |
|---|---|---|
| TCP `0.0.0.0:12321`, `[::]:12321` (`miniserv.pl`) | yes | no. curl from the VM: exit 7, connection refused |
| UDP `0.0.0.0:12321` (`miniserv.pl`) | yes | no |
| TCP 22, 80, 443 on all addresses | yes | yes |
| TCP `127.0.0.1:25` | yes | yes |
| MariaDB `127.0.0.1:3306`, `[::1]:3306` (lnmp) | yes | yes |
| PostgreSQL `127.0.0.1:5432`, `[::1]:5432` (lnpp) | yes | yes |
| `cloud_simple` only: CrowdSec `127.0.0.1:6060`, `127.0.0.1:8080`, bouncer `127.0.0.1:60601`, Syncthing `127.0.0.1:8384` and `*:<random>`, Anubis `[::1]:8923` | yes | yes |

Before the removal, the first IPv4 request to 12321 from the VM timed out
after 4 s (curl exit 28). A later request answered in 0.47 s. The cause
was not examined.

### A4. Errors after the removal (tested, logs 53, 55)

The same on the 4 nodes:

1. **systemd: the node is `degraded`.** `webmin-after-firstboot.path` and
   `webmin-after-firstboot.service` fail at each boot with
   `Failed to start webmin.service: Unit webmin.service not found.`
   `common/conf/turnkey.d/webmin-enable` writes these 2 units into
   `/etc/systemd/system/`. No package owns them.
2. **keel stops working.** `keel manifest validate`, `keel diff`,
   `keel spec validate` and `keel spec apply --system-only --dry-run`
   exit 3:

   ```
   Error: /usr/share/keel/appliances/core.yaml: processes[1].unit: webmin.service has no unit file under /
   Error: /etc/keel/instance.yaml: appliance.name: the chain of lnmp does not resolve: in web: base: core cannot be used: /usr/share/keel/appliances/core.yaml fails validation (1 errors)
   ```

   Before the removal, `keel manifest validate` exited 0 and `keel diff`
   exited 14 (drift found) on the 4 nodes (log 21). `keel spec validate`
   and `keel spec apply --system-only --dry-run` ran only after the
   removal, on 9401 and 9403 (log 55).
3. **confconsole** still shows `Webmin: https://[...]:12321` and
   `Webmin: https://...:12321` on its usage screen. The lines come from
   `/etc/confconsole/services.txt`. No exception.
4. **fail2ban** is active and still runs the `webmin-auth` jail. No error.
5. **Monit**: no error. `monit -t` passes. The Webmin check is in
   `/etc/keel/monit/keel-manifest.conf`, and `monitrc` does not include
   that file on these nodes (only `conf.d/*` and `conf-enabled/*`).
6. **Login banner**: `run-parts /etc/update-motd.d` exits 0. No file in
   `/etc/update-motd.d`, `/etc/issue*` or `/etc/motd` names Webmin.
7. Remains on disk: `/usr/share/webmin`, the 3 drop-in directories
   `/etc/systemd/system/webmin*.service.d`, and 22 packages in dpkg state
   `rc`. `apt-get remove` deleted `/etc/webmin`.

### A5. Which images have a Webmin database module (read, log 60)

Each stable image of release 2026-11-12 was downloaded and verified
(`sqv` exit 0, `sha512sum -c` pass). `tar` read only
`./var/lib/dpkg/status` and `./etc/ssh/sshd_config.d/`. No image was
booted for this table.

| Image | sha256 of the `.tar.zst` | Webmin packages | Database module |
|---|---|---|---|
| core 19.0-13 | `e32029debdf15a852084a08f24d8187dd526bd3ceebc3cc1e6512a1bf7fb4401` | 21 | none |
| laravel 19.0-8 | `30ed7ba94184b38d5e98f4a4203b9fab65be3b0d7355e8df67a1160b449ed335` | 22 | `webmin-mysql` |
| lnmp 19.0-7 | `66aa6fb14aa69a80a73211035daadc6480d20e1e72933a9372051f30405b5319` | 22 | `webmin-mysql` |
| lnpp 19.0-10 | `0fe16d74e14b56f921d086f12dc53b661df7ab4de9cbc717ba2e51868ecbdff0` | 22 | `webmin-postgresql` |
| mariadb 19.0-12 | `b63dffe12176e98c5f4598e0a9c7785b0b91c9024ca424964cb71a5dea69f611` | 22 | `webmin-mysql` |
| ntfy 19.0-7 | `7a8faaa362626b24059277b58868666ebf95579d41dea1ba06b8cecfd3a5b757` | 21 | none |
| odoo 19.0-19 | `3f1d24487e5b6d790608d60deb5fc6035a97da708022033d19d31e424807c721` | 22 | `webmin-postgresql` |
| postgresql 19.0-9 | `dbf57eddd592cb3bf14a5e067d85147f38e0b7d3f09e11e05f0e1cc1245fb4b1` | 22 | `webmin-postgresql` |
| redis 19.0-13 | `924779592724088e320f98c3163f730c896572ec2baf3601f330a4795040e1e3` | 21 | none |
| web 19.0-14 | `2af5203c10466910cf2a384a3af58bab30abb3a9d1a7b0aa105ba7c5a3718bf2` | 21 | none |
| wordpress 19.0-22 | `a562756a04dc319163fc34a8a49f549dd95c30ff8b60beb7f0cb3c6fb0e45922` | 22 | `webmin-mysql` |

The 21 core packages are the list of 0094 minus `webmin-mysql` and
`webmin-postgresql`. No image has both database modules, so each image
has 21 or 22 of the 23 packages in the archive.

### B1. The TurnKey sshd drop-in in a built image (read and tested, logs 30, 31, 60)

Each of the 11 images has exactly one sshd drop-in,
`/etc/ssh/sshd_config.d/turnkey.conf`, with `AllowTcpForwarding no`
(log 60). `/etc/ssh/sshd_config` has `Include /etc/ssh/sshd_config.d/*.conf`
on line 12, so the drop-in comes before the Debian lines.

`sshd -T -C user=U,host=vm,addr=2804:710:d0:59::11:101,laddr=::,lport=22`
on 9401, for `root`, `evtunnel` and `nobody`:

```
allowtcpforwarding no; permitopen any; maxsessions 2; maxauthtries 3;
allowstreamlocalforwarding yes; permitrootlogin yes; x11forwarding no
banner /root/.ssh/banner (root only), none (others)
```

**Result for B1: the drop-in is in every image.**

### B2. `ssh -L` today (tested, logs 32, 33)

The test VM opened `ssh -N -L 127.0.0.1:LPORT:TARGET USER@NODE` with a
throwaway ed25519 key (`IdentitiesOnly=yes`, `BatchMode=yes`) and then
connected to `LPORT`:

| User | Target | Result |
|---|---|---|
| evtunnel | `127.0.0.1:3306` on 9401 | refused |
| root | `127.0.0.1:3306` on 9401 | refused |
| evtunnel | `127.0.0.1:5432` on 9402 | refused |
| root | `127.0.0.1:5432` on 9402 | refused |
| evtunnel | `/run/mysqld/mysqld.sock` (a Unix socket) | refused |

Client message: `channel 1: open failed: administratively prohibited:
open failed`. sshd log: `refused local port forward: originator
127.0.0.1 port N, target 127.0.0.1 port 3306`. For the Unix socket,
sshd logs `Received request to connect to path /run/mysqld/mysqld.sock,
but the request was denied.` Thus `allowstreamlocalforwarding yes` does
not open a way around `AllowTcpForwarding no`.

**Result for B2: the tunnel fails today, for root and for another
account.**

### B3. The smallest sshd change (tested, logs 40 to 46)

The tested block, for the throwaway account `evtunnel`:

```
Match User evtunnel
    AllowTcpForwarding local
    PermitOpen 127.0.0.1:3306 127.0.0.1:5432
```

| Variant | File | `sshd -T` for evtunnel | `sshd -T` for root and nobody | Tunnel to 3306 and 5432 |
|---|---|---|---|---|
| V1 | `00-keel-tunnel.conf` (before `turnkey.conf`) | `local`, `permitopen 127.0.0.1:3306 127.0.0.1:5432` | unchanged: `no`, `any`, `maxauthtries 3`, root banner kept | PASS |
| V2 | `zz-keel-tunnel.conf` (after `turnkey.conf`) | the same | unchanged | PASS |
| V3a | a global line `AllowTcpForwarding local`, no `Match`, in `00-` | `local` | `local` for **every** user | not run |
| V3b | the same global line in `zz-` | `no` | `no` | not run |

Facts from the variants:

- A `Match` block works in each position. A value in a matching `Match`
  block replaces the global value. OpenSSH 10.0 ends a `Match` block at
  the end of its included file: in V1, root still gets the TurnKey
  values (`maxauthtries 3`, `banner /root/.ssh/banner`).
- A global line only has an effect before `turnkey.conf`, because sshd
  keeps the first value. It then opens forwarding for all users. Do not
  use that form.
- `sshd -t` exits 0 for each variant.

Tunnel results with V1 and with V2 (logs 41, 43):

| User | Target | Result |
|---|---|---|
| evtunnel | `127.0.0.1:3306` | PASS: `11.8.6-MariaDB-0+deb13u1` greeting |
| evtunnel | `127.0.0.1:5432` | PASS: `S` answer to an SSLRequest |
| evtunnel | `localhost:3306`, `localhost:5432` | refused |
| evtunnel | `[::1]:3306` | refused |
| evtunnel | `127.0.0.1:25` | refused |
| evtunnel | `/run/mysqld/mysqld.sock` | refused |
| root | `127.0.0.1:3306`, `127.0.0.1:5432` | refused (no change for root) |

`PermitOpen` compares the host text that the client sends. Thus a
client that asks for `localhost` or `::1` is refused by this list.

V4 (log 47): with `PermitOpen 127.0.0.1:3306 localhost:3306
127.0.0.1:5432 localhost:5432` in `zz-keel-tunnel.conf`, the tunnel to
`localhost:3306` also gets the MariaDB greeting. `127.0.0.1:3306` still
works, and `[::1]:3306` is still refused.

`MaxSessions 2` (log 45): 1 SSH connection with `-L` and no session
channel (`ssh -N`) carried 4 TCP connections at the same time. All 4 got
the MariaDB greeting. Thus `MaxSessions 2` does not limit the forwarded
connections of a tunnel. After the tunnel closed, a shell command as
`evtunnel` worked. Not tested: 1 SSH connection that carries a session
and forwards at the same time.

SFTP (log 45): the first SFTP run in `multi.sh` read its batch from
standard input and stopped at the 60 s timeout (`exit=124`). A separate
run with a batch file passed: `sftp -b` with `pwd` and `ls -a` works for
`evtunnel` and for `root` with a key (exit 0).

End to end with real clients through the tunnel (log 46). On each node,
the node itself was the SSH client to its own public address, so the
path is the same as from a remote computer:

```
9401: evtest@127.0.0.1  evtest@localhost  11.8.6-MariaDB-0+deb13u1 from Debian   client_exit=0
9402: evtest|127.0.0.1|PostgreSQL 17.11 (Debian 17.11-0+deb13u1) on x86_64-pc-linux-gn   client_exit=0
```

**Result for B3: PASS.** The smallest change is the 3-line `Match`
block in its own drop-in. The position does not matter.

### B4. Password login over TCP on the loopback (tested, logs 34, 35)

MariaDB (9401):

- `bind_address` `::1,127.0.0.1`, port 3306, `skip_networking` 0.
- Accounts: `admin` at `127.0.0.1`, `::1` and `localhost`
  (`mysql_native_password`), and the system accounts.
- A test account `evtest` at `127.0.0.1` and `::1` logs in with its
  password on `-h 127.0.0.1` and on `-h ::1` (exit 0). A wrong password
  gets `ERROR 1045 (28000): Access denied` (exit 1).

PostgreSQL (9402):

- `listen_addresses` `::1,127.0.0.1`, `password_encryption`
  `scram-sha-256`.
- `/etc/postgresql/17/main/pg_hba.conf`, the lines that are not
  comments:

  ```
  local   all             postgres                                peer
  local   all             all                                     peer
  host    all             all             127.0.0.1/32            scram-sha-256
  host    all             all             ::1/128                 scram-sha-256
  local   replication     all                                     peer
  host    replication     all             127.0.0.1/32            scram-sha-256
  host    replication     all             ::1/128                 scram-sha-256
  ```

- Roles that can log in: `postgres` (superuser, has a SCRAM password),
  `root` (superuser, no password), `keel-check` (no password).
- A test role `evtest` logs in with its password on `-h 127.0.0.1` and
  on `-h ::1` (exit 0). A wrong password gets `FATAL: password
  authentication failed` (exit 2).

**Result for B4: PASS on both engines.** `pg_hba.conf` needs no change.

## Summary

| Question | Result |
|---|---|
| A1. What loads the firewall at boot in `simple` and `cloud_simple` | **nothing**: no iptables loader exists, nftables loads an empty accept table, `keel-firewall` is skipped. An unlisted port answers on both families |
| A2. The rule set after the removal and a reboot | PASS: the same open rule set. `iptables-legacy` stays selected |
| A3. Listeners after the removal | PASS: TCP and UDP 12321 are closed. The others do not change |
| A4. Errors after the removal | **FAIL**: the node is `degraded` and every `keel` command that resolves the manifest exits 3. confconsole and fail2ban still name Webmin |
| B1. TurnKey drop-in in the image | yes, in all 11 images |
| B2. `ssh -L` today | fails for every user: `administratively prohibited` |
| B3. Smallest sshd change | PASS: a `Match User` block with `AllowTcpForwarding local` and `PermitOpen 127.0.0.1:3306 127.0.0.1:5432`, in any position |
| B4. Password login over TCP on the loopback | PASS on MariaDB and PostgreSQL |

## What this means for 0094

These are proposals only. Nothing was changed in a repository.

1. **Transition step 1 rests on a false premise.** Webmin does not load
   a firewall today, so its removal cannot drop one. The firewall loader
   is not a blocker for the removal. It is a separate gap with a larger
   effect: a node in `simple` or `cloud_simple` filters no input port
   today. Report it to the maintainer as a security finding, apart from
   0094.
   Smallest change proposed: replace the iptables part of
   `common/conf/turnkey.d/webmin-fw` with an `/etc/nftables.conf` that
   holds the same allow list (`inet` table, input policy drop, `lo`,
   ICMPv6, ICMP echo, `ct state established,related`, the TCP and UDP
   lists). `nftables.service` is already enabled on each image and loads
   that file before the network. This adds no package and no unit, and it
   ends the `iptables-legacy` switch. The fence of inithooks and the
   CrowdSec tables must then be tested with it. The other option is that
   keel writes `keel-manifest.nft` in every mode, because
   `keel-firewall.service` is already enabled. That follows design rule 1
   ("one engine"), but it is a larger keel change. The maintainer
   decides.
2. **The removal act must change the manifest at the same time.** If a
   node has no `webmin.service` and the core manifest still declares the
   process, keel refuses the whole chain. Thus the act must drop the
   `webmin` process from the resolved manifest in the same step. This is
   the reverse case of transition step 5 of 0094.
3. **The removal act must also remove** the 2 units of `webmin-enable`
   (`webmin-after-firstboot.path`, `.service`), the 3 drop-in
   directories of `webmin-fw` and `webmin-enable`, the `[webmin-auth]`
   jail, and the 2 Webmin lines of confconsole's `services.txt`.
4. **sshd (work item 5).** Add one drop-in, for example
   `/etc/ssh/sshd_config.d/keel-db-tunnel.conf`:

   ```
   Match User <administrator account>
       AllowTcpForwarding local
       PermitOpen 127.0.0.1:3306 127.0.0.1:5432
   ```

   Its position does not matter. Do not add a global
   `AllowTcpForwarding` line. `MaxSessions 2` does not limit the
   tunnel. The account name waits for the design of work item 6.
5. **The DBeaver guide (work item 12)** sets the database host to
   `127.0.0.1`. If the drop-in should also accept a client that keeps
   `localhost`, add `localhost:3306 localhost:5432` to `PermitOpen`
   (tested, V4). `::1` stays refused unless the list names `[::1]:3306`.
6. **Work item 7.** `pg_hba.conf` already accepts a SCRAM password on
   `127.0.0.1` and `::1`. MariaDB `admin` already has `127.0.0.1` and
   `::1` hosts. The database side needs no change for the tunnel.

## What was not tested

- `cloud_advanced`, a real pair with a mesh, and an ISO install.
- DBeaver itself. The tunnel was tested with `ssh -L` and the
  `mariadb` and `psql` clients.
- Redis, and the images other than lnmp and lnpp on a running node.
  The other 9 images were read from their file system only (A5, B1).
- A `Match Group` form, and the restricted login of work item 6.
- 1 SSH connection that carries a session and forwards at the same time,
  as a client such as DBeaver can open.

## Logs

The logs and scripts are kept on the maintainer's workstation in
`repos/evidence-0094-2026-11-23/`. Numbers: 01 create, 02 first boot,
10 to 13 firewall before the removal, 20 removal simulation, 21 checks
before the removal, 30 to 47 sshd and database, 50 to 55 removal and
checks after it, 60 image package scan, 90 secret scan, 99 cleanup.

## Cleanup

CTs 9401, 9402, 9403 and 9404 were destroyed (log 99). The test VM keeps
no file of this test.
