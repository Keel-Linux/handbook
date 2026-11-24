# 0097: keel writes the firewall in every mode, with a drop policy for inbound traffic

Date: 2026-11-23
Status: **accepted 2026-11-23 by the maintainer. Urgent lane.** The
maintainer put the fix in the urgent lane on 2026-11-23. His direction:
`keel` writes the firewall rules in every mode, from one source. The
image holds no fixed list. He answered the 2 questions: B for the
transition, and yes for the advisory now (see "Questions for the
maintainer, answered"). Then he accepted the whole note. The code is in
`keel` pull request 307 (branch `fix/firewall-every-mode`), which is not
merged. Two real-node tests of that pull request are merged on main:
["the first test"](../../evidence/2026-11-23-keel-307-firewall-real-test.md)
(head `86370ed`) and
["the second test"](../../evidence/2026-11-23-keel-307-firewall-real-test-2.md)
(head `2120276`). "The second evidence" stays the name of the
stopgap evidence of handbook PR 203. Where the built design differs from
the first text of this note, the note says what is built and why.

Sources. Each repository path was read on its default branch after
`git fetch` on 2026-11-23: `keel` `35e8aa6` (keel 0.23.97), `common`
`18522b4` (branch `19.x`), `keel-core` `cfa5907`, `keel-web` `f800f9d`,
`inithooks` `db4c03d`, `confconsole` `a1abe09`, `keel-lnmp` `d3db52a`,
`keel-lnpp` `51d00ee`, `keel-mariadb` `efa3596`, `keel-postgresql`
`9d9807f`, `keel-redis` `da0d67b`, `keel-ntfy` `36f8e2e`,
`keel-wordpress` `d1fa447`, `keel-laravel` `3642463` (branch `19.x`),
`keel-odoo` `7900659`, `keel-nextcloud` `33d2a8c`, `keel-nodebb`
`8aa6ac8`. `keel` pull request 307 was read at `de69d2b`: its
`docs/spec.md`, its `docs/apply.md` and the code. "Read in code" means
that nobody tested it on a running node. "Tested" names the evidence
file. A commit after `2120276` is "built, not tested on a real node".

## What was asked

The real-node test of 2026-11-23
([evidence](../../evidence/2026-11-23-webmin-removal-firewall-and-ssh-tunnel.md),
result A1) found that a published image in the `simple` and
`cloud_simple` modes loads no inbound firewall rule at boot. A listener
on TCP 9999, a port that no list names, answered from outside on IPv4
and IPv6. The maintainer asked for a fix in the urgent lane, with
`keel` as the one source of the rules in every mode.

A second real-node test of 2026-11-23 ("the second evidence" below:
[`evidence/2026-11-23-firewall-stopgap-and-cloud-advanced.md`](../../evidence/2026-11-23-firewall-stopgap-and-cloud-advanced.md),
merged on main by handbook PR 203) found
that a published node in `cloud_advanced` is also open, and that the
mesh services answer through the uplink to a neighbour on the same
link. It also tested the Proxmox VE firewall as a stopgap.

## What is true today

### 1. How keel writes the firewall

keel has a complete firewall for one mode. It derives the rules from the
manifests, and it is tested on real containers.

| Part | Where | What it does |
| --- | --- | --- |
| The rule set | `keel/manifest/firewall.py` | One nftables table, `inet keel`, one input chain with `policy drop` (lines 13-22, 135-137). The file replaces the table in one transaction (lines 128-140) |
| Always accepted | `keel/manifest/firewall.py:48-56` | `lo`, `ct state established,related`, all ICMPv6, IPv4 echo, DHCPv6 client replies from `fe80::/10` on UDP 546, DHCPv4 on UDP 68. `ct state invalid` is dropped |
| The allow list | `keel/manifest/firewall.py:83-123` | Each `listen` with `expose: public` of a process whose overlay is enabled, on every interface (line 112). Each `expose: mesh` port only for packets that come in on the WireGuard interface: `iifname "wg0"` (line 115). The WireGuard UDP port (line 104). TCP 51821 with `iifname "wg0"` (line 118). The set `mesh_invites` of 0048 on every interface (line 119) |
| Mesh ports need the overlay | `keel/manifest/firewall.py:102-110` | If the spec declares no `network.overlay.wireguard`, keel opens no mesh port and says so |
| Guest bridges | `keel/manifest/firewall.py:65-69`, `keel/system/fwstate.py:140-159` | DNS and DHCP on a bridge that only carries guests, never on the uplink |
| The plan and its guards | `keel/system/firewall.py:54-146` | `nft -c` before `nft -f`. No change while a network change waits for confirmation (0018). A file that keel did not write is not replaced |
| The SSH guard | `keel/system/firewall.py:123-138`, `keel/system/fwstate.py:90-117` | The ports of `sshd -T` and of an active `ssh.socket`. If a port is not in the public list, or the ports are unknown, keel **refuses the whole rule set** |
| The file | `/etc/keel/firewall/keel-manifest.nft`, mode 0600 | Written by `keel spec apply --system` (`keel/system/firewall.py:99-116`). Under `--root`, keel writes the file and does not load it |
| The unit | `debian/keel.keel-firewall.service` | `nft -f` of the file at boot, `After=nftables.service`, `Before=network-pre.target`. `ConditionPathExists` on the file (line 21): with no file, systemd skips the unit |
| Drift | `keel/diff/appliance.py:186-214` | `keel diff` compares the file and the digest of the loaded table |
| Inspect | `keel/inspect/overlays.py:88-93` | `keel inspect` writes `firewall.enabled: false` when no file of keel's exists |
| The package | `debian/keel.postinst` | It runs `keel network mtu` only. It runs no `keel spec apply`. Thus an upgrade of `keel` changes no firewall rule by itself |

The rule set ran with `policy drop` on real containers in cloud
advanced: LNMP and LNPP across 2 sites
([evidence 2026-10-16](../evidence/2026-10-16-lnmp-lnpp-19.0-3-cross-site.md),
"Firewall"), and the Odoo and WordPress tests of 2026-10-18
([Odoo](../evidence/2026-10-18-odoo-nginx-cross-site.md),
[WordPress](../evidence/2026-10-18-wordpress-nginx-cross-site.md)). The
containers were unprivileged on Proxmox VE. Thus the change of this note
is a change of scope, not a new mechanism.

### 2. Why `simple` and `cloud_simple` have no firewall

The skip is by design. It rests on a premise that was false.

- keel refuses `firewall.enabled: true` in any mode except
  `cloud_advanced` (`keel/spec/validate_firewall.py:1-11, 37-47`). The
  docstring and `keel/docs/spec.md:1003-1011` say: "Optional, and for
  cloud advanced installations only, as the maintainer scoped it on
  2026-09-30: in the simple and cloud simple modes keel installs and
  changes no firewall rule."
- 0048 (lines 107-110, 378-388) and 0049 (lines 323-329) repeat the
  scope: "everywhere else keel touches no firewall it does not own".
- The premise was that TurnKey's `webmin-fw` loads `rules.v4` and
  `rules.v6` in the other modes. `keel/docs/apply.md` says "while a
  TurnKey image still loads its `rules.v4`". The test of 2026-11-23
  showed that nothing loads them: the `webmin-iptables` units do not
  exist, and `iptables-persistent` is not installed.
- Also in `cloud_advanced`, nothing turns the firewall on. The mode
  screen writes `installation.mode` and the overlays only
  (`confconsole/keelmode.py:226-233`). No installer, preseed or
  commissioning contract writes `firewall:`. The test of 2026-10-16 set
  `firewall.enabled: true` by hand.
- **Tested: a published node in `cloud_advanced` is open** (the second
  evidence, T2.2 and T2.4). On a primary, a replica and an etcd witness
  made with the mode screen, the spec has no `firewall:` key,
  `keel-manifest.nft` is absent and systemd skips `keel-firewall`. An
  undeclared TCP and UDP port answers on IPv6 and IPv4. Thus the fix
  covers the 3 modes and the witness.

### 3. What the notes promised

- **0041** (item 6, item 7 and the Core table, line 126): "In a simple
  installation ... the firewall opens 22 and 12321." `docs/manifest-v1.md`
  line 592 says the same. The derived firewall replaces
  `WEBMIN_FW_TCP_INCOMING`.
- **0095** (section 2, item 1): "the node is closed by default", the
  same at both promise levels.
- **0094** (transition, step 1, and work item 3): a replacement loader
  for the simple modes comes before any removal of Webmin. The evidence
  of 2026-11-23 showed that there is nothing to replace.
- **0080** speaks of the network stack only (ifupdown-ng, dhcpcd-base).
  It does not speak of the firewall or of `iptables-legacy`.
- `iptables-legacy` comes from `common/conf/turnkey.d/webmin-fw:79-86`,
  which has "TODO: drop use of iptables-legacy and use nftables
  directly" on line 3.

Thus 0041 and 0095 promise a closed node in every mode. The code keeps
that promise only in `cloud_advanced`, and only after an edit by hand.

### 4. What each image needs open

From the manifests, not from the `Makefile` lists. "On wg0" is what
the rule set must accept: packets that come in on the WireGuard
interface, and only when the spec declares `network.overlay.wireguard`.
`keel mesh create` and `keel mesh join` write that key
(`keel/mesh/node.py:216-222`). It is not where the service listens
(section 4a).

| Image | `simple` | `cloud_simple` and `cloud_advanced` add |
| --- | --- | --- |
| core | TCP 22, TCP 12321 (Webmin, until 0094) | UDP 51820, TCP 51821 on wg0, the invite set. `cloud_advanced`: etcd TCP 2379, 2380 on wg0 |
| web, ntfy | core, and TCP 80, 443 | core, and Syncthing TCP and UDP 22000 on wg0 |
| lnmp, wordpress, laravel, nextcloud | web | web, and MariaDB TCP 3306 on wg0 |
| lnpp, odoo, nodebb | web | web, and PostgreSQL TCP 5432 on wg0 |
| mariadb | core | core, and TCP 3306 on wg0 |
| postgresql | core | core, and TCP 5432 on wg0 |
| redis | core | core, and TCP 6379 on wg0 |

Sources: `keel-core/packages/keel-core/manifest.yaml:13-30`,
`keel-web/packages/keel-web/manifest.yaml:7-14`,
`common/packages/{nginx,syncthing,etcd}/manifest.yaml`, and
`overlay/usr/share/keel/appliances/NAME.yaml` of each application
(lnmp line 18, lnpp line 16, postgresql line 17, redis line 21,
`keel-mariadb/packages/keel-mariadb/manifest.yaml:16`). The VIP is an
address on wg0 (0049), so the mesh rules cover it.

In `simple`, each other listener is on the loopback. In the cloud
modes, the databases are not on the loopback only (section 4a). The
listeners on the loopback in each mode: Postfix 25 (0092), Anubis 8923,
CrowdSec 6060 and 8080, the Syncthing GUI 8384, etcd 2381, ntfy 2586,
Redis in Nextcloud, Odoo (`keel-odoo/overlay/etc/odoo/odoo.conf:13`),
NodeBB (`keel-nodebb/overlay/usr/lib/inithooks/bin/nodebb.py:230`).

Two lists differ from the manifests:

- The `WEBMIN_FW_TCP_INCOMING` of `keel-core` opens 80 and 443. The core
  manifest has no nginx. The derived set is smaller.
- The `keel-laravel` `Makefile` opens 12320 (the web shell). No manifest
  declares it.

One listener is not in a manifest. With no overlay address, keel writes
the Syncthing `listenAddress` as `tcp://:0`
(`keel/system/filesync.py:282-283`). Syncthing then listens on a random
TCP port on all addresses. The first test of 2026-11-23 saw `*:36551`
and `*:44051` on one-node `cloud_simple` nodes with no overlay. In a
real pair, Syncthing listens on TCP 22000 on the wg0 address (the second
evidence, T2.3). A drop policy closes the random port, and no peer uses
it.

UDP 12321 of `miniserv.pl` listens on all IPv4 addresses and answers
from outside on IPv4 (the second evidence, T1.0 and T2.4). The core
manifest declares TCP 12321 only.

### 4a. The mesh services answer through the uplink

In `cloud_simple` and `cloud_advanced`, MariaDB 3306, etcd 2379 and
2380, and Syncthing 22000 listen on the address of wg0. MariaDB also
listens on the VIP. A neighbour on the same link as eth0 (another guest
on the same bridge or VLAN, or the upstream router) can send a route for
that address through the node. Linux accepts a packet for a local
address on any interface. The second evidence (T2.5, T1.4) shows that
these ports then answer through eth0, from a machine that is not a mesh
member. Only the invite port 51821 refuses, because it binds to the
device (`%wg0`). A probe of the public address does not show this path.

The exposure in one sentence: a neighbour on the link can reach the
login of MariaDB, and the TLS ports of etcd and Syncthing, with no
WireGuard key.

How serious each service is, read in code:

- **etcd** requires TLS 1.3 and a client certificate signed by the mesh
  CA, on the client port and on the peer port
  (`keel/mesh/etcdconf.py:102-110`: `ETCD_CLIENT_CERT_AUTH=true`,
  `ETCD_PEER_CLIENT_CERT_AUTH=true`, `ETCD_TLS_MIN_VERSION=TLS1.3`).
  Without such a certificate, a neighbour gets no access. The test did
  not try TLS.
- **Syncthing** accepts only the device IDs that keel writes into its
  configuration (`keel/system/filesync.py:255-280`).
- **MariaDB** sends its greeting and accepts a password login. This is
  the serious part.

The rule set of this note already closes this path, because
`keel/manifest/firewall.py` accepts mesh ports only with `iifname
"wg0"` (line 115), and the input policy is `drop` (line 136). A packet
for the wg0 address or the VIP that comes in on eth0 matches no accept
rule, unless its port is public. Tested on IPv6 in both tests of pull
request 307 (the first test, item 3, and the second test, item 2): each
mesh port gives a timeout through eth0, and the control without
`inet keel` answers. The overlay had no IPv4 address, so IPv4 was not
tested.

### 5. What the node always needs

- **IPv6.** Neighbour discovery, router advertisements and path MTU are
  ICMPv6. The rule set accepts all ICMPv6. DHCPv6 replies come to UDP
  546 from a link-local address, which the rule set accepts.
- **IPv4.** dhcpcd-base (0080) gets DHCPv4 replies on UDP 68, which the
  rule set accepts. An ICMP error for a connection that exists is
  `related` and is accepted.
- **A Proxmox container** gets its network from `pct` through
  `/etc/network/interfaces` (0080). The rule set loads in an
  unprivileged container: tested 2026-10-16, and `nftables.service`
  loaded its table in each container of 2026-11-23. In `enforce`, a
  DHCPv4 and DHCPv6 rebind, a router advertisement and neighbour
  discovery worked in a container (the second test, item 1c). SLAAC and
  a lease that expires by time are not tested.
- **A VM from the ISO** uses the same network stack (0080, item 3). The
  rule set was never loaded in a VM from the ISO. Not tested.

### 6. What else touches the firewall on a node

- **The init fence.** `turnkey-init-fence` redirects TCP 80, 443, 12321
  and 12322 to 60080 and 60443 until the first login
  (`inithooks/default/turnkey-init-fence`, `inithooks/lib/init-fence.sh:86-121`).
  It uses `iptables` and adds an `ACCEPT` for the fence ports
  (lines 136-145). The input hook sees the port after the redirect. Thus
  `inet keel` drops the fence page unless it accepts it. If the nat
  table is not available, the fence rejects the port (lines 59-72).
- **nftables.service** loads `/etc/nftables.conf`, the Debian default:
  `flush ruleset` and an empty `inet filter` table with policy accept.
  A `systemctl restart nftables.service` removes `inet keel` and the
  tables of CrowdSec.
- **CrowdSec** (in the cloud modes) adds `table ip crowdsec` and
  `table ip6 crowdsec6`, with policy accept. They drop only banned
  addresses. keel always sets the bouncer to `mode: nftables`
  (`keel/docs/apply.md`, "The bouncer runs in nftables mode, always").
- **Legacy iptables.** `rules.v4` and `rules.v6` hold `INPUT DROP` and
  the TCP list of the `Makefile`. They have no WireGuard port. If an
  administrator installs `iptables-persistent`, the files load and cut
  WireGuard in a cloud mode. The `-m state` rules need `xt_state`. An
  unprivileged container cannot load that module.
- **Several base chains.** nftables runs each base chain on the input
  hook. A drop in any chain is final. An accept in another table cannot
  open what `inet keel` drops. Thus a table or an iptables rule of the
  administrator can only make the set smaller.

### 7. What can break on a node in the field

| Case | With a drop policy | Guard |
| --- | --- | --- |
| sshd on a second port, set by hand | Today keel refuses the whole rule set, and the node stays open (`keel/system/firewall.py:131-138`) | This note: keel opens each port that sshd is configured for, and each port that the running sshd daemon listens on (section 3) |
| A service of the administrator on a public address | Its new connections are dropped | The report state lists it first |
| A database opened on purpose to another host | 3306 or 5432 is `mesh`. A client on the uplink is dropped | The report lists it. `firewall.allow` with `from` opens it |
| Webmin on 12321 | Stays open: the core manifest declares it public | It closes with the removal act of 0094 |
| The Proxmox firewall on the guest (the stopgap of section 7) | Both filter. Each can only narrow | No conflict. A port opened at Proxmox must also be declared in keel |
| A container that cannot load nftables | `nft` fails. The old state stays, which is open | The failure is visible (section 4 below) |
| A pair during replication | The table changes in one transaction. Connections that exist stay (`established`). New ones need the mesh port on wg0 | The report shows a mesh listener that the rule set does not open. One node at a time (0073, item 6) |
| A pair whose spec has no `network.overlay.wireguard` | No mesh port opens. Replication fails at its next connection | The plan says "not opened" today. The report state shows it before enforcement |
| The init fence at the first boot | The fence page does not answer | A rule for the redirected fence ports (section 6) |

Decision 0073 rules the upgrade: `keel` never goes to Keel
`trixie-security` (item 6). The operator upgrades one node at a time,
with an advisory. A table load restarts no service. Decision 0090
demands an upgrade test on each published application before `keel`
goes to `trixie`.

## Why (brief section 10)

1. **Why it is necessary.** Each published node filters no inbound
   port today, in each of the 3 modes (tested). Any service that listens
   on a public address is open to the network. In the cloud modes, the
   database also answers to a neighbour on the link (section 4a). This
   breaks the promise of 0041 and 0095.
2. **Whether it can be made to work.** The rule set, its guards, its
   unit and its drift check exist and passed on real containers in
   cloud advanced. The change is a change of scope, a stronger SSH
   guard, a transition for the nodes in the field, and the tests.
3. **Why this is better.** One source of the rules: the declared state
   that `keel diff` reads. No second list in the image. An administrator
   opens a port through `keel`, so the port goes to the replica and
   survives an upgrade.

## Decision

### 1. One rule set in every mode (point A)

1. keel writes `inet keel` in `simple`, `cloud_simple` and
   `cloud_advanced`, with the same code and `policy drop` on input.
2. `keel-firewall.service` is the one unit that loads inbound rules at
   boot. On a new image, `nftables.service` is disabled, because its
   file holds only an empty accept table. On a node in the field, keel
   does not change `/etc/nftables.conf` and does not disable
   `nftables.service`. The package adds a drop-in to `nftables.service`
   that loads keel's file again after each start, reload and stop of
   that unit (section 4, item 2). The first text said that keel does not
   change `nftables.service`. The drop-in is necessary, because a
   restart of that unit removes `inet keel` (the first test, item 6).
3. Output and forward stay as they are. This note filters inbound
   traffic only.
4. keel touches no other table: not CrowdSec's, not an iptables rule,
   not a table of the administrator.
5. **`iptables-legacy`.** keel does not change the alternative on a node
   in the field. New images go back to the Debian default
   (`iptables-nft`) when the Webmin conf scripts go (0094, work items 3
   and 14). The init fence then writes its rules into nftables tables.
   That must be tested (section D).
6. **`rules.v4` and `rules.v6`.** New images do not have them. On a node
   in the field, keel does not delete them, but `keel diff` names them
   with a warning: "do not install iptables-persistent".
7. **CrowdSec.** Its tables stay. A ban still drops, because a drop in
   any base chain is final.

8. **Mesh ports by input interface.** A `mesh` port is accepted only
   for a packet that comes in on the WireGuard interface (`iifname`), as
   `keel/manifest/firewall.py:115` and `:118` do today. Thus a packet for
   the wg0 address or the VIP that comes in on eth0 is dropped, unless
   its port is public (section 4a). The rule set does not match on the
   destination address.
9. **No sysctl as a second layer.** `rp_filter` and
   `arp_ignore`/`arp_announce` act on IPv4 only, and IPv6 has no equal
   setting. The rule set closes the path on both families. This note
   adds no sysctl, because none was tested and the rule set is enough.

Danger: a node that a host cannot give nftables (for example a container
of 0043 with no `CAP_NET_ADMIN`) cannot have the firewall. Section 4
makes that visible. It does not close the node.

### 2. The allow list comes from the declared state (point B)

The allow list is the union of these, and nothing else:

1. The `public` and `mesh` ports of the image's manifest and of each
   enabled overlay, as today.
2. Each port that sshd listens on (section 3).
3. A new spec list, `firewall.allow`, for the ports of the
   administrator. Each item has `port`, `protocol` and an optional
   `from`, a list of prefixes. With no `from`, the port opens on every
   interface.
4. While the unit of the init fence is enabled: TCP 60080 and 60443,
   only for redirected packets (`ct status dnat`). A direct connection
   to these ports stays dropped. The fence ports come from
   `/etc/default/turnkey-init-fence`. A socket of the fence's own unit
   on these ports does not keep rule B in `report` (section 5). The
   first test found that a running fence kept the node in `report`
   (item 8). The second test passed this case (item 3).

An administrator opens a port with `keel` only. Later, a confconsole
menu writes `firewall.allow` (0094, design rule 1). A hand edit of the
file is drift in `keel diff`, and the next apply overwrites it. A rule
in another table cannot open the port (section 6 of "What is true
today"). keel copies `firewall.allow` to the replica with the other
settings sections (0094, decision 8).

Danger: `firewall.allow` with no `from` opens a database to the world.
keel accepts it, and `keel diff` names each `allow` item that opens a
database port with no `from`.

### 3. SSH is never closed

1. keel adds 2 sets of TCP ports to the allow list, and names them in
   the plan:
   - the ports that sshd is configured for: `sshd -T`, and
     `ssh.socket` while it is active.
   - the ports that the running sshd daemon listens on now: the
     process runs as root and is the daemon of the sshd unit, or the
     listener of an active `ssh.socket`. A process that only has the
     name `sshd` does not count. A process of a user session inside the
     unit does not count.

   It does not refuse any more when sshd listens on a port that the
   manifests do not declare. This changes `keel/system/firewall.py:131-138`.
   The first text named `sshd -T` only. `sshd -T` reads the files, not
   the running process. The second test found 2 lock-outs with it: a
   port from `SSHD_OPTS` in `/etc/default/ssh`, and a `Port` changed in
   the file before a restart of sshd (item 4). The second set is built
   after the second test (`82a085b`) and is not tested on a real node.
   A review of pull request 307 found that the code matched by name
   only. The pull request corrects this before its merge, and the
   correction is not tested on a real node yet.
2. If `sshd -T` does not answer, keel reads `sshd_config` and
   `sshd_config.d/*.conf` as sshd reads them. The ports are unknown only
   when a file cannot be read, or when an `Include` names a file outside
   `sshd_config.d`. Then keel writes nothing and loads nothing. The old
   state stays, and the plan says why. Section 5 says when this fails
   the apply. Tested: the first test, item 5, and the second test,
   item 7.
3. `nft -c` checks the file before `nft -f`, and the load is one
   transaction. A file that nft refuses leaves the old table (as today).
4. `ct state established,related` keeps the SSH session that runs the
   apply.
5. While a network change waits for `keel network confirm`, the rule
   set does not change (0018, as today).

### 4. A failed load is visible, and a lost table comes back

1. If `keel-firewall.service` fails at boot, the node comes up without
   `inet keel`. On a new node that is open. The unit fails, and the
   node is `degraded`. Tested with a broken file: the unit fails, a
   loaded table stays, and SSH works (the first test, item 5, and the
   second test, item 6). An empty or cut file loads no table, and nft
   does not refuse it. The second test found such a node open after a
   reboot, with the unit in success (item 6). Now a check after the
   load fails the unit when `inet keel` is not loaded with the policy of
   the file. The apply writes an empty or cut file again. This is built
   after the second test (`de69d2b`) and is not tested on a real node.
2. A lost table comes back without Monit, in every mode, whatever the
   spec says:
   - A drop-in for `nftables.service` loads keel's file again after
     each start, reload and stop of that unit. The node is open between
     the 2 nft runs.
   - `keel-firewall-watch.timer` runs `keel firewall check --restore`
     every 30 s. This covers a flush by hand, which no unit can see.
   - `keel firewall check` compares the rules of the loaded table with
     the rules of the file, one by one, and runs `nft -c` on the file.
     It trusts no comment.
   - If the spec enables the monitor, Monit runs the same check.

   The first text gave this task to Monit. The first test found that a
   node with no `monitor:` section has no Monit check, and no published
   spec has one. That node stayed open for 540 s (item 6). In the
   second test, a restart of `nftables.service` left the node open for
   at most about 0.22 s. A flush by hand left it open for 17.7 to
   27.1 s (item 5). The second test also found 2 failures: an upgrade
   of `keel` stopped the timer, and keel did not see a rule replaced by
   a wider rule (cases b and d). The fixes are built after the second
   test (`f1f58f0`, `ad04bdc`) and are not tested on a real node.
3. When 0085 exists, a failed check sends one ntfy message.

Danger: a boot with a broken file leaves the node open until the
administrator acts. The other choice, an SSH-only fallback file, closes
the applications of a working node because of one bad file. This note
chooses the open node with a visible failure, as the guards of 0041 do.

### 5. The transition (point C)

**New images.** The image build runs `keel spec apply --system --root`
on the image, with `firewall.state: enforce` in the spec of the build.
keel writes the `simple` rule set of the image's manifest
and does not load it. At the first boot, `keel-firewall.service` loads
it before the network. Thus the node is closed from its first packet.
The first apply then writes the rule set of the chosen mode. The mode
screen writes `firewall.state: enforce` into `instance.yaml`. Under
`--root`, keel sees no socket, so a spec with no state writes `report`.
Thus the build must declare `enforce` (keel `docs/spec.md`, "firewall").
This rule stays, and it is not built yet. In the second test, a new
node got `enforce` from its first-boot apply. But no file existed
before the first boot, so the table loaded after the network (item 8).

**Nodes in the field.** The upgrade of `keel` loads no rule by itself
(`debian/keel.postinst`). As built, the upgrade also enables
`keel-firewall-watch.timer` with no start, and installs the drop-in
for `nftables.service`. The second test records this against 0073 as
"not met" (item 1x). The change comes at the next system apply.
A person runs it with `keel spec apply --system` or through a
confconsole menu. In a cloud mode, keel also runs it with no person:
`keel-mesh-sync.timer` runs `keel mesh sync` every 15 min, and a change
of the members applies the whole spec (`keel/mesh/sync.py:498`,
`keel/mesh/node.py:63-66`). Thus a rule that goes to `enforce` by
itself must run only in an apply that a person starts, never in an
apply of `keel mesh`. As built, `keel mesh` never begins enforcement,
also when the spec says `enforce`. It keeps `report` until a person
applies. The apply of a person holds the lock of `keel mesh sync`.
Thus a mesh apply cannot write `report` over the `enforce` that the
apply of a person wrote. Tested: the first test, item 4, and the second
test, items 3 and 9. The spec gets a key `firewall.state` with 3
values:

| Value | Meaning |
| --- | --- |
| `enforce` | `inet keel` with `policy drop` |
| `report` | `inet keel` with `policy accept`, and one counter rule for each packet that `enforce` would drop. `keel diff` lists each socket that listens on an address that is not a loopback and that the allow list does not open. The table drops nothing |
| `off` | no table of keel's. `keel diff` warns |

How keel reads each spelling (from keel `docs/spec.md`, "firewall", in
pull request 307):

| The spec says | The state | Who moves it |
| --- | --- | --- |
| no `firewall:` key (each published spec) | `report`, then `enforce` by rule B | the first apply that a person runs and whose sockets all belong to the manifests. Never `keel mesh` |
| `firewall: {enabled: false}` (what `keel inspect` of keel 0.23.97 wrote) | the same as no key | the same |
| `firewall: {allow: [...]}` with no state | the same as no key, with those ports | the same |
| `firewall: {enabled: true}` | `enforce` | an apply that a person runs. `keel mesh` keeps `report` until then |
| `firewall: {state: enforce}` | `enforce` | the same |
| `firewall: {state: report}` | `report`, on purpose. Rule B never moves it | only a change of the spec |
| `firewall: {state: off}` | no table of keel's. The plan and `keel diff` warn | only a change of the spec |

An absent key and `firewall.enabled: false` give `report`, and rule B
then decides. The reason: in `simple`
and `cloud_simple`, validation never accepted `true`, and `keel inspect`
writes `false` when it finds no file. Thus `false` records no choice of
the administrator. `off` exists only when the spec says `off`.
`state: report` is the one way to keep a node in `report` on purpose.
When keel's file is in `enforce`, an apply with no state keeps
`enforce`. keel refuses `enabled` together with `state`. `keel inspect`
writes `state: enforce` from keel's file, and leaves a `report` state
out. Thus a spec that inspect writes again does not keep a node in
`report`. The first test found that rule B did not run on a spec with
no `firewall:` key (item 1). The second test found `enforce` on 9 nodes
with no key (item 1).

**A firewall that keel cannot decide.** If the spec does not say
`enforce`, a guard that refuses does not fail the apply. A rule set
that nft refuses does not fail it either. The plan says `NOT APPLIED,
the node keeps the firewall it has`, with the reason, and the other
steps run. Only an explicit `state: enforce` or `enabled: true` makes
it a failure of the apply. The first text did not say this. The reason:
a node that chose nothing must not lose its other steps because of the
firewall, and `keel mesh` must not put the spec back for it. Tested:
the second test, item 7. The second test also found that a masked
timer failed the apply with no explicit `enforce` (case c). The fix is
built after the second test (`f1f58f0`) and is not tested on a real
node.

How a node in `report` goes to `enforce`: the maintainer chose **B**
on 2026-11-23. The choices were:

- **A. Only the act of the administrator.** A confconsole item, or
  `firewall.state: enforce` in the spec. Danger: a node whose
  administrator never acts stays open for ever.
- **B. Enforce at once when no unknown process listens, else wait for
  the act.** The test looks at the process, not at the port. At an
  apply that a person starts, keel lists each socket on a public
  address. If each one belongs to a unit of the resolved manifest,
  keel goes to `enforce`. Else it stays in `report`, tells the
  administrator, and waits. As built, a socket on a mesh port also
  keeps `report` when its address is not the overlay address or the
  VIP, for example MariaDB on `0.0.0.0`. The reason: `enforce` opens
  that port on wg0 only, and cuts a client outside the mesh. Tested:
  the second test, item 3. A port of a declared process that the
  manifest does not list closes, and `keel diff` names it as
  information. Two such ports exist on each published node: UDP 12321
  of `miniserv.pl` (the manifest declares TCP 12321 only,
  `keel-core/packages/keel-core/manifest.yaml:27`), and the random
  Syncthing port of a node with no overlay address. Nothing uses them.
  Danger: the report sees the sockets of that moment only. A service
  that a timer starts later is not in it, and `enforce` cuts it.
- **C. Enforce at the next apply on every node.** The advisory says:
  declare the ports first. Danger: a service of the administrator stops
  answering from outside, and the administrator learns it from a user.

**Decided: B** (the maintainer, 2026-11-23). It closes most nodes at
their first apply, and it does not cut a service that the report can
see.

"Report first" leaves a node open for longer than "enforce at once".
That is the price of no surprise on a production node. In each choice,
the node is open until a person runs an apply. The advisory (section E)
says how to run it.

### 6. How it is proved (point D)

Each test runs in the test VM of a site, one nested Proxmox VE VM for
each site. The topology is the release topology: 2 nodes on BR1 and 1
on BR2, with the netem profile of 250 ms. Each probe runs on IPv6 and
on IPv4. Each test has an evidence file (0053). No package goes to
`trixie-testing` before items 1 to 12 pass.

Status after the 2 tests of pull request 307. Both tests ran in the
test VM of BR1 only, on one bridge, with no netem. Thus no item passed
in the release topology yet. "Covered" names what the tests showed on
the core, lnmp and lnpp images. "Remains" names what is still to test.

1. **Each mode, closed.** `simple`, a `cloud_simple` pair, a
   `cloud_advanced` pair with its etcd witness: a listener on TCP 9999
   and on UDP 9999 does not answer from outside. UDP 12321 does not
   answer.
   Covered: each mode and the witness, IPv6 and IPv4 (the second test,
   item 1c). Remains: the release topology.
2. **Each application, open.** On each of the 13 images: each port of
   the table of "What is true today", section 4, answers from outside.
   The checks of the application pass (0090, item 2).
   Covered: the declared ports of core, lnmp and lnpp (the second test,
   item 1c). Remains: the other 10 images, and the checks of each
   application in `enforce`.
3. **Mesh only on wg0.** 3306, 5432, 6379, 2379, 2380, 22000 and 51821
   answer through wg0 and on the VIP, and do not answer on the public
   address.
   Covered: replication on 3306, etcd and Syncthing work on wg0 in
   `enforce` (the second test, item 2). Remains: 5432 and 6379, which
   no tested pair had.
4. **No mesh port through the uplink.** A neighbour on the same link,
   not a mesh member, adds a route for the wg0 address and for the VIP
   of each node through eth0, as T2.5 of the second evidence did. Each
   mesh port gives a timeout on IPv6, and on IPv4 where the overlay has
   IPv4. The same probe without `inet keel` answers, as a control.
   Covered: on IPv6, with the control (the first test, item 3, and the
   second test, item 2). The overlay had no IPv4. Remains: the release
   topology.
5. **Replication.** A write on the primary arrives on the standby. A
   file arrives through Syncthing. A failover by `keel vip promote`
   works, and the old primary rejoins.
   Covered: the write, Syncthing, a failover by `pct shutdown`, and the
   return of the old primary (the second test, item 2). Remains: a
   failover by `keel vip promote`, and by a hard stop.
6. **Mesh join.** `keel mesh invite` and `keel mesh join` work, and the
   invite port closes after its expiry.
   Remains: all of it.
7. **Reboot.** The journal shows `keel-firewall.service` before
   `network-pre.target`. The probes of items 1 and 2 give the same
   results.
   Covered (the first test, item 2c, and the second test, item 1c).
8. **SSH.** With `Port 2222` added by hand, an apply keeps 22 and 2222.
   With an sshd file that keel cannot read, the apply refuses and the
   old state stays.
   Covered: `Port 2222` with 22, `Port 2222` alone, `ssh.socket` on a
   second port, and an unreadable configuration (the first test,
   item 5, and the second test, items 4 and 7). Remains: the 2
   lock-outs of the second test (section 3), with `82a085b`.
9. **Failure.** A broken file: the unit fails, the node is `degraded`,
   and SSH still works. `systemctl restart nftables.service`: the
   drop-in loads the table again at once. A flush by hand: the timer
   loads the table again within about 35 s.
   Covered: the broken file, the restart and the flush (the second
   test, items 5 and 6). Remains: an empty or cut file, a wider rule,
   and an upgrade of `keel`, with the fixes after the second test.
10. **First boot.** An interactive first boot: the fence page answers on
   80 and 443. A container whose nat table is not available: the fence
   rejects, as today.
   Covered: the fence page through the legacy redirect, and a direct
   connection to the fence ports dropped (the first test, item 8, and
   the second test, item 3). Remains: the container with no nat table,
   and the fence with `iptables-nft`.
11. **ISO.** An install from the ISO in a VM, under BIOS and UEFI
    (0052): DHCPv4, DHCPv6 and SLAAC still work after the lease time.
    A Proxmox container with `ip=dhcp,ip6=dhcp` (0080): the same.
    Covered: in a container, a DHCPv4 and DHCPv6 rebind and a router
    advertisement (the second test, item 1c). Remains: the ISO, SLAAC,
    and a lease that expires by time.
12. **CrowdSec.** In a cloud mode, a ban by `cscli decisions add` still
    drops the address.
    Covered (the first test, item 8). Also seen: a restart of
    `nftables.service` removes the CrowdSec tables, and keel does not
    load them again (the second test, item 8).
13. **Upgrade of a published node (0090).** One node of each published
    application, from its published image: upgrade `keel` by `apt`,
    run the apply. The node goes to `report` or `enforce` as the answer
    to B says. The checks of the application pass. SSH stays
    open. Then a reboot, and the checks again. One test with a service
    of the administrator on a public port, and one with Webmin still
    installed.
    Covered: `dpkg -i` with Webmin installed, on lnmp in each mode, on
    core in `simple` and as the witness, and on lnpp in `simple`. The
    upgrade loads no rule, and the apply gives `enforce`.
    A listener of the administrator keeps `report` (the second test,
    items 1 and 3). Remains: `apt` from the repository, the other 10
    images, and the checks of each application.
14. **Pair upgrade.** A `cloud_simple` pair and a `cloud_advanced` pair
    under writes: the standby first, the VIP holder last (0073, item 6).
    No acknowledged write is lost.
    Remains: the upgrade under writes. The tests upgraded the pair and
    the trio in this order with no load.

### 7. Advisory and stopgap (point E)

An advisory is necessary. Each of the 11 stable images and the 2 images
in testing are affected, in each mode. It goes to
`docs/advisories/`, with the status `open` until the fixed `keel` is in
`trixie` and the images are built again.

The advisory says:

- Who is affected: each node from a Keel image, in each of the 3
  modes, the etcd witness included (tested). A `cloud_advanced` node
  with `firewall.enabled: true` in its spec, set by hand, is not
  affected.
- What is open on a node that nobody changed: TCP 22, 80, 443 (web
  images), TCP 12321, and UDP 12321 on IPv4. In `cloud_simple` and
  `cloud_advanced`, MariaDB 3306, etcd 2379 and 2380, and Syncthing
  22000 also answer to a neighbour on the same link (section 4a). In
  `simple`, the databases listen on the loopback only.
- What is at risk: each service that an administrator added and that
  listens on a public address, and in the cloud modes the login of
  MariaDB from the link.
- What to do today: the stopgaps below.
- When the fix comes, and that the fix needs one apply on each node.

Stopgaps:

| Stopgap | State |
| --- | --- |
| The Proxmox VE firewall on the guest. The procedure is in the second evidence, section "Procedure". 3 levels must be on: the datacenter, `firewall=1` on the network device, and `enable: 1` in the guest file. The node level is not necessary: `enable: 0` in `host.fw` keeps the host unfiltered. The guest file needs `dhcp: 1` and `ndp: 1`: with `dhcp: 0`, the node loses its address at the next rebind. A node of a pair needs UDP 51820. The stopgap also closes the path of section 4a | **tested** in `simple` and on a `cloud_simple` pair, with a reboot (the second evidence, T1.2 to T1.4). **Not tested**: `cloud_advanced`, the witness, a VM from the ISO, the nftables back end of Proxmox VE |
| An `/etc/nftables.conf` written by hand with the same list, loaded by `nftables.service` | **not tested** |
| In `cloud_advanced`: `firewall.enabled: true` in the spec, then `keel spec apply --system` | tested 2026-10-16 on LNMP 19.0-3 and LNPP 19.0-4, not on the images of release 2026-11-12 |

Caution for the Proxmox stopgap: the datacenter switch sets the
sysctls `bridge-nf-call-iptables` and `bridge-nf-call-ip6tables` to 1
for every bridge of the host. Then each bridged frame also goes through
the `forward` hook. If the host has its own `forward` chain with a drop
policy, the guest loses all its traffic. Add an accept for the bridged
traffic first (the second evidence, T1.2).

Caution: on a `cloud_simple` or `cloud_advanced` pair, a stopgap that
does not accept the WireGuard UDP port and the wg0 ports stops
replication and Syncthing. Do not install `iptables-persistent` as a
stopgap: its files have no WireGuard port, and they need `xt_state`.

The Proxmox stopgap is now tested in `simple` and `cloud_simple`. The
maintainer answered yes: the advisory goes out now, before the fix
(answer 2).

### 8. Relation to 0094 and 0095 (point F)

- **0094.** Webmin's 12321 stays open while the core manifest declares
  the `webmin` process. The removal act of 0094 removes the declaration,
  and the next apply closes 12321. A new image without Webmin never
  opens it. This note replaces 0094's transition step 1 and its work
  item 3: there is no Webmin loader to replace, and the loader is
  `keel-firewall.service`. The restriction of 12321 to wg0 in 0049 is
  not in `render()`. It is not built, because Webmin retires.
- **0095.** The rule is a security rule, so it is the same at both
  promise levels. The images in testing (Nextcloud, NodeBB) get it at
  the same time. The tests of section 6 join the commissioning of 0075
  for both levels.

## What this amends

This note changes these notes. It does not edit them.

- **0041**: the derived firewall is no longer "optional, and for cloud
  advanced installations only". It is on in every mode. The spec key
  `firewall.enabled` becomes `firewall.state`, and `firewall.allow` is
  new.
- **0048**: the invite port opens through `inet keel` in each mode that
  has the overlay, not only where `firewall.enabled: true`.
- **0049**: "In cloud simple, where keel touches no firewall it does not
  own" ends. The other points stay.
- **0094**: transition step 1 and work item 3 (section 8 above).

## Not verified

Tested since the first text of this note:

- A published `cloud_advanced` node is open, and UDP 12321 answers on
  IPv4 (the second evidence).
- `inet keel` drops the path of section 4a, on IPv6 (the first test,
  item 3, and the second test, item 2).
- The rule set on published images: lnmp in each mode, core in
  `simple` and as the witness, and lnpp in `simple` (the second test,
  item 1).
- The init fence with a drop policy, through the legacy redirect (the
  first test, item 8, and the second test, item 3).
- A reinstall of `nftables` (`apt-get install --reinstall`) stops and
  starts `nftables.service`. The drop-in loads `inet keel` again, and
  the node is open for about 0.15 s (the second test, item 5). An
  upgrade to a new version runs the same maintainer scripts. That is an
  inference, not a test.

Still not verified:

- The rule set in a VM from the ISO, under BIOS and UEFI.
- The release topology: 2 sites with the netem profile of 250 ms.
- The other 10 of the 13 images.
- `keel mesh invite` and `keel mesh join` with the invite port, and the
  close of that port after its expiry.
- The image build with `--root` and `state: enforce`, and the mode
  screen that writes `firewall.state: enforce`.
- The init fence with `iptables-nft`, and a container whose nat table is
  not available.
- SLAAC, and a lease that expires by time.
- A power loss between the write and the rename of the rule set (the
  second test, item 6: the kill did not hit that window).
- The commits after `2120276`: the ports of a running sshd, the timer
  after an upgrade and when masked, the rule-by-rule check, and an
  empty or cut file. Pull request 307 still changes.
- The Proxmox stopgap in `cloud_advanced`, on a witness, on a VM from
  the ISO, and with the nftables back end. The stopgap with
  `/etc/nftables.conf`.
- TLS or a login on the mesh ports through the uplink. The second
  evidence proved a TCP connection and the MariaDB greeting only.

## Questions for the maintainer, answered

The maintainer answered on 2026-11-23:

1. How does a node in `report` go to `enforce`? **B**: at an apply that
   a person starts, keel enforces at once when each public socket
   belongs to a unit of the resolved manifest. Else the node stays in
   `report` until the act of the administrator (section 5).
2. May a public advisory with the tested stopgap go out now, before the
   fix? **Yes.** The advisory is
   `docs/advisories/2026-11-23-no-inbound-firewall.md`. It gives the
   Proxmox VE stopgap of the second evidence.

## Work list

In order. Items 3 to 8 are built in `keel` pull request 307, which is
not merged and still changes.

1. Done: the Proxmox VE firewall stopgap, tested in `simple` and on a
   `cloud_simple` pair (the second evidence, merged by handbook
   PR 203).
2. Done: the advisory `docs/advisories/2026-11-23-no-inbound-firewall.md`,
   published before the fix (answer 2, handbook PR 204). Update it when
   the fix is in `trixie`.
   Done: the `Decision:` link of the advisory names this file, not
   handbook PR 202.
3. Built: keel accepts `firewall` in every mode. It has `firewall.state`
   and `firewall.allow`, and reads `enabled` as section 5 says.
   `keel inspect` writes `state: enforce` only, and leaves a `report`
   state out.
4. Built: keel adds the sshd ports instead of the refusal (section 3).
5. Built: the `report` state, its counter rule and the list of
   undeclared listeners in `keel diff`. The rule of answer 1 (B).
6. Built: the rule for the redirected fence ports.
7. Built: the drop-in for `nftables.service`,
   `keel-firewall-watch.timer`, and the Monit check `keel-firewall`
   where the spec enables the monitor (section 4).
8. Built: keel writes Syncthing's `listenAddress` on the loopback when
   there is no overlay address, not `tcp://:0`.
9. confconsole: the mode screen writes `firewall.state: enforce`. Later
   a menu for `firewall.allow` (0094).
10. Images: the build writes the `simple` rule set with `--root` and
    `firewall.state: enforce` (section 5).
    Disable `nftables.service`. Remove `rules.v4`, `rules.v6` and the
    `iptables-legacy` switch with 0094 work item 14. Change the
    `tests/firewall.bats` of `keel-mariadb`, `keel-postgresql` and
    `keel-redis`, and the `WEBMIN_FW_TCP_INCOMING` lists.
11. The tests of section 6, items 1 to 12, in the test VM of each site.
    Evidence file. Started: the 2 tests of pull request 307 in the test
    VM of BR1. Section 6 says what remains.
12. `keel` to `trixie-testing`. The upgrade tests of section 6, items 13
    and 14 (0090). Evidence file.
13. `keel` to `trixie` with the advisory updated (0073, item 6). Build
    the images again and run commissioning (0075) on BR1 and BR2.
14. Documentation: `keel/docs/spec.md` and `apply.md` (written in pull
    request 307), `docs/manifest-v1.md`, the application pages (0077), and the site's
    security page.
15. When 0085 exists: the ntfy message for a failed check and for a node
    in `report`.

## Related notes

It applies 0041, 0053, 0073, 0075, 0090 and 0095. It uses the
confirmation window of 0018, the mesh of 0024 and 0048, the VIP of 0049
and the network stack of 0080.
