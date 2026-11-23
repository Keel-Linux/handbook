# 0097: keel writes the firewall in every mode, with a drop policy for inbound traffic

Date: 2026-11-23
Status: **proposed 2026-11-23. Urgent lane.** The maintainer put the
fix in the urgent lane on 2026-11-23. His direction: `keel` writes the
firewall rules in every mode, from one source. The image holds no fixed
list. This note proposes the design and the transition.
Two points wait for the maintainer (see "Open points"). Nothing in this
note is built.

Sources. Each repository path was read on its default branch after
`git fetch` on 2026-11-23: `keel` `35e8aa6` (keel 0.23.97), `common`
`18522b4` (branch `19.x`), `keel-core` `cfa5907`, `keel-web` `f800f9d`,
`inithooks` `db4c03d`, `confconsole` `a1abe09`, `keel-lnmp` `d3db52a`,
`keel-lnpp` `51d00ee`, `keel-mariadb` `efa3596`, `keel-postgresql`
`9d9807f`, `keel-redis` `da0d67b`, `keel-ntfy` `36f8e2e`,
`keel-wordpress` `d1fa447`, `keel-laravel` `3642463` (branch `19.x`),
`keel-odoo` `7900659`, `keel-nextcloud` `33d2a8c`, `keel-nodebb`
`8aa6ac8`. "Read in code" means that nobody tested it on a running
node. "Tested" names the evidence file.

## What was asked

The real-node test of 2026-11-23
([evidence](../../evidence/2026-11-23-webmin-removal-firewall-and-ssh-tunnel.md),
result A1) found that a published image in the `simple` and
`cloud_simple` modes loads no inbound firewall rule at boot. A listener
on TCP 9999, a port that no list names, answered from outside on IPv4
and IPv6. The maintainer asked for a fix in the urgent lane, with
`keel` as the one source of the rules in every mode.

## What is true today

### 1. How keel writes the firewall

keel has a complete firewall for one mode. It derives the rules from the
manifests, and it is tested on real containers.

| Part | Where | What it does |
| --- | --- | --- |
| The rule set | `keel/manifest/firewall.py` | One nftables table, `inet keel`, one input chain with `policy drop` (lines 13-22, 135-137). The file replaces the table in one transaction (lines 128-140) |
| Always accepted | `keel/manifest/firewall.py:48-56` | `lo`, `ct state established,related`, all ICMPv6, IPv4 echo, DHCPv6 client replies from `fe80::/10` on UDP 546, DHCPv4 on UDP 68. `ct state invalid` is dropped |
| The allow list | `keel/manifest/firewall.py:83-123` | Each `listen` with `expose: public` of a process whose overlay is enabled, on every interface. Each `expose: mesh` port on the WireGuard interface only. The WireGuard UDP port. TCP 51821 on `wg0`, and the set `mesh_invites` of 0048 |
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
  `firewall.enabled: true` by hand. Thus a published node in
  `cloud_advanced` is also open. Read in code, not tested.

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

From the manifests, not from the `Makefile` lists. "wg0" means the
WireGuard interface only, and only when the spec declares
`network.overlay.wireguard`.

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

Each other listener is on the loopback: Postfix 25 (0092), Anubis 8923,
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
TCP port on all addresses. The test of 2026-11-23 saw `*:36551` and
`*:44051`. A drop policy closes it, and no peer uses it.

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
  loaded its table in each container of 2026-11-23.
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
| sshd on a second port, set by hand | Today keel refuses the whole rule set, and the node stays open (`keel/system/firewall.py:131-138`) | This note: keel adds each port of `sshd -T` |
| A service of the administrator on a public address | Its new connections are dropped | The report state lists it first |
| A database opened on purpose to another host | 3306 or 5432 is `mesh`. A client on the uplink is dropped | The report lists it. `firewall.allow` with `from` opens it |
| Webmin on 12321 | Stays open: the core manifest declares it public | It closes with the removal act of 0094 |
| The Proxmox firewall on the guest | Both filter. Each can only narrow | No conflict. A port opened at Proxmox must also be declared in keel |
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

1. **Why it is necessary.** Each node in `simple` and `cloud_simple`
   filters no inbound port today, and each node in `cloud_advanced`
   also, unless an administrator edited its spec. Any service that
   listens on a public address is open to the network. This breaks the
   promise of 0041 and 0095.
2. **Whether it can be made to work.** The rule set, its guards, its
   unit and its drift check exist and passed on real containers in
   cloud advanced. The change is a change of scope, a stronger SSH
   guard, a transition for the nodes in the field, and the tests.
3. **Why this is better.** One source of the rules: the declared state
   that `keel diff` reads. No second list in the image. An administrator
   opens a port through `keel`, so the port goes to the replica and
   survives an upgrade.

## Decision (proposed)

### 1. One rule set in every mode (point A)

1. keel writes `inet keel` in `simple`, `cloud_simple` and
   `cloud_advanced`, with the same code and `policy drop` on input.
2. `keel-firewall.service` is the one unit that loads inbound rules at
   boot. On a new image, `nftables.service` is disabled, because its
   file holds only an empty accept table. On a node in the field, keel
   does not change `nftables.service` or `/etc/nftables.conf`.
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
4. While the init fence runs: TCP 60080 and 60443, only for redirected
   packets (`ct status dnat`). A direct connection to these ports stays
   dropped. The fence ports come from `/etc/default/turnkey-init-fence`.

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

1. keel adds each port of `sshd -T`, and of `ssh.socket` while it is
   active, to the allow list. It names them in the plan. It does not
   refuse any more when sshd listens on a port that the manifests do not
   declare. This changes `keel/system/firewall.py:131-138`.
2. If keel cannot find the ports of sshd, keel writes nothing and loads
   nothing. The old state stays, and the failure is visible.
3. `nft -c` checks the file before `nft -f`, and the load is one
   transaction. A file that nft refuses leaves the old table (as today).
4. `ct state established,related` keeps the SSH session that runs the
   apply.
5. While a network change waits for `keel network confirm`, the rule
   set does not change (0018, as today).

### 4. A failed load is visible, and a lost table comes back

1. If `keel-firewall.service` fails at boot, the node comes up without
   `inet keel`. On a new node that is open. The unit fails, and the
   node is `degraded`.
2. Monit gets a check `keel-firewall`: the loaded table has the digest
   of the file (the comparison of `keel diff`, `keel/diff/appliance.py:205-214`).
   If the table is absent or differs, Monit restarts
   `keel-firewall.service`. Thus a `systemctl restart nftables.service`
   by hand leaves the node open for at most one Monit cycle and 2 cycles
   of grace.
3. When 0085 exists, a failed check sends one ntfy message.

Danger: a boot with a broken file leaves the node open until the
administrator acts. The other choice, an SSH-only fallback file, closes
the applications of a working node because of one bad file. This note
chooses the open node with a visible failure, as the guards of 0041 do.

### 5. The transition (point C)

**New images.** The image build runs `keel spec apply --system --root`
on the image. keel writes the `simple` rule set of the image's manifest
and does not load it. At the first boot, `keel-firewall.service` loads
it before the network. Thus the node is closed from its first packet.
The first apply then writes the rule set of the chosen mode. The mode
screen writes `firewall.state: enforce` into `instance.yaml`.

**Nodes in the field.** The upgrade of `keel` changes nothing by itself
(`debian/keel.postinst`). The change comes at the next
`keel spec apply --system`, which the administrator runs, or which a
confconsole menu runs. The spec gets a key `firewall.state` with 3
values:

| Value | Meaning |
| --- | --- |
| `enforce` | `inet keel` with `policy drop` |
| `report` | `inet keel` with `policy accept`, and one counter rule for each packet that `enforce` would drop. `keel diff` lists each socket that listens on an address that is not a loopback and that the allow list does not open. The table drops nothing |
| `off` | no table of keel's. `keel diff` warns |

`firewall.enabled: true` reads as `enforce`. An absent key, or
`firewall.enabled: false`, reads as `report`. The reason: in `simple`
and `cloud_simple`, validation never accepted `true`, and `keel inspect`
writes `false` when it finds no file. Thus `false` records no choice of
the administrator. `off` exists only when the spec says `off`.

How a node in `report` goes to `enforce` is the first open point. The
choices:

- **A. Only the act of the administrator.** A confconsole item, or
  `firewall.state: enforce` in the spec. Danger: a node whose
  administrator never acts stays open for ever.
- **B. Enforce at once when the report is empty, else wait for the
  act.** At an apply, if no undeclared socket listens on a public
  address, keel goes to `enforce`. Else it stays in `report`, tells the
  administrator, and waits. Danger: the report sees the sockets of that
  moment only. A service that a timer starts later is not in it, and
  `enforce` cuts it.
- **C. Enforce at the next apply on every node.** The advisory says:
  declare the ports first. Danger: a service of the administrator stops
  answering from outside, and the administrator learns it from a user.

The proposal is **B**. It closes most nodes at their first apply, and
it does not cut a service that the report can see.

"Report first" leaves a node open for longer than "enforce at once".
That is the price of no surprise on a production node. In each choice,
the node is open until somebody runs an apply. The advisory (section E)
says how to run it.

### 6. How it is proved (point D)

Each test runs in the test VM of a site, one nested Proxmox VE VM for
each site. The topology is the release topology: 2 nodes on BR1 and 1
on BR2, with the netem profile of 250 ms. Each probe runs on IPv6 and on IPv4. Each
test has an evidence file (0053). No package goes to `trixie-testing`
before items 1 to 10 pass.

1. **Each mode, closed.** `simple`, a `cloud_simple` pair, a
   `cloud_advanced` pair with its etcd witness: a listener on TCP 9999
   and on UDP 9999 does not answer from outside.
2. **Each application, open.** On each of the 13 images: each port of
   the table of "What is true today", section 4, answers from outside.
   The checks of the application pass (0090, item 2).
3. **Mesh only on wg0.** 3306, 5432, 6379, 2379, 2380, 22000 and 51821
   answer through wg0 and on the VIP, and do not answer on the uplink.
4. **Replication.** A write on the primary arrives on the standby. A
   file arrives through Syncthing. A failover by `keel vip promote`
   works, and the old primary rejoins.
5. **Mesh join.** `keel mesh invite` and `keel mesh join` work, and the
   invite port closes after its expiry.
6. **Reboot.** The journal shows `keel-firewall.service` before
   `network-pre.target`. The probes of items 1 and 2 give the same
   results.
7. **SSH.** With `Port 2222` added by hand, an apply keeps 22 and 2222.
   With an sshd file that keel cannot read, the apply refuses and the
   old state stays.
8. **Failure.** A broken file: the unit fails, Monit reports it, and
   SSH still works. `systemctl restart nftables.service`: Monit loads
   the table again within its cycles.
9. **First boot.** An interactive first boot: the fence page answers on
   80 and 443. A container whose nat table is not available: the fence
   rejects, as today.
10. **ISO.** An install from the ISO in a VM, under BIOS and UEFI
    (0052): DHCPv4, DHCPv6 and SLAAC still work after the lease time.
    A Proxmox container with `ip=dhcp,ip6=dhcp` (0080): the same.
11. **CrowdSec.** In a cloud mode, a ban by `cscli decisions add` still
    drops the address.
12. **Upgrade of a published node (0090).** One node of each published
    application, from its published image: upgrade `keel` by `apt`,
    run the apply. The node goes to `report` or `enforce` as the answer
    to open point 1 says. The checks of the application pass. SSH stays
    open. Then a reboot, and the checks again. One test with a service
    of the administrator on a public port, and one with Webmin still
    installed.
13. **Pair upgrade.** A `cloud_simple` pair and a `cloud_advanced` pair
    under writes: the standby first, the VIP holder last (0073, item 6).
    No acknowledged write is lost.

### 7. Advisory and stopgap (point E)

An advisory is necessary. Each of the 11 stable images and the 2 images
in testing are affected, in each mode. It goes to
`docs/advisories/`, with the status `open` until the fixed `keel` is in
`trixie` and the images are built again.

The advisory says:

- Who is affected: each node from a Keel image, in each mode. In
  `cloud_advanced`, a node with `firewall.enabled: true` in its spec is
  not affected.
- What is open on a node that nobody changed: TCP 22, 80, 443 (web
  images), TCP and UDP 12321, and in `cloud_simple` a random Syncthing
  port. The databases listen on the loopback only.
- What is at risk: each service that an administrator added and that
  listens on a public address.
- What to do today: the stopgaps below.
- When the fix comes, and that the fix needs one apply on each node.

Stopgaps:

| Stopgap | State |
| --- | --- |
| The Proxmox VE firewall on the guest: enable it at the datacenter and on the guest, set `firewall=1` on the network device, and accept only the ports of the table above | **not tested** |
| An `/etc/nftables.conf` written by hand with the same list, loaded by `nftables.service` | **not tested** |
| In `cloud_advanced`: `firewall.enabled: true` in the spec, then `keel spec apply --system` | tested 2026-10-16 on LNMP 19.0-3 and LNPP 19.0-4, not on the images of release 2026-11-12 |

Caution: on a `cloud_simple` or `cloud_advanced` pair, a stopgap that
does not accept the WireGuard UDP port and the wg0 ports stops
replication and Syncthing. Do not install `iptables-persistent` as a
stopgap: its files have no WireGuard port, and they need `xt_state`.

The proposal is to test the Proxmox stopgap before the advisory goes
out (work item 1). Whether the advisory can go out before that test is
the second open point.

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

- Whether a package upgrade of `nftables` restarts `nftables.service`.
  Section 1, item 2 disables the unit on new images, and section 4 covers
  a restart.
- The rule set in a VM from the ISO, and in `cloud_advanced` on the
  images of release 2026-11-12.
- Whether a published `cloud_advanced` node is open. Read in code
  only: no installer writes `firewall:`.
- UDP 12321 from outside. The test of 2026-11-23 saw the listener and did
  not probe it.
- The init fence with a drop policy, and with `iptables-nft`.
- The stopgaps of section 7, except the third one.

## Open points

1. Nodes in the field: how does a node in `report` go to `enforce`? A,
   B or C (section 5). The proposal is B.
2. May the advisory go out before the Proxmox stopgap is tested? Yes or
   no. The proposal is no: the test is work item 1, and it is small.

## Work list

In order. Nothing is started.

1. Test the Proxmox VE firewall stopgap on one `simple` node and one
   `cloud_simple` pair in the test VM of BR1. Evidence file.
2. Write the advisory in `docs/advisories/`, as open point 2 decides.
3. keel: accept `firewall` in every mode. Add `firewall.state` and
   `firewall.allow`. Read `enabled` as section 5 says. `keel inspect`
   writes `state`.
4. keel: add the sshd ports instead of the refusal (section 3).
5. keel: the `report` state, its counter rule and the list of undeclared
   listeners in `keel diff`. Then the rule of open point 1.
6. keel: the rule for the redirected fence ports.
7. keel: the Monit check `keel-firewall` and its restart.
8. keel: write Syncthing's `listenAddress` on the loopback when there is
   no overlay address, not `tcp://:0`.
9. confconsole: the mode screen writes `firewall.state: enforce`. Later
   a menu for `firewall.allow` (0094).
10. Images: the build writes the `simple` rule set with `--root`.
    Disable `nftables.service`. Remove `rules.v4`, `rules.v6` and the
    `iptables-legacy` switch with 0094 work item 14. Change the
    `tests/firewall.bats` of `keel-mariadb`, `keel-postgresql` and
    `keel-redis`, and the `WEBMIN_FW_TCP_INCOMING` lists.
11. The tests of section 6, items 1 to 11, in the test VM of each site.
    Evidence file.
12. `keel` to `trixie-testing`. The upgrade tests of section 6, items 12
    and 13 (0090). Evidence file.
13. `keel` to `trixie` with the advisory updated (0073, item 6). Build
    the images again and run commissioning (0075) on BR1 and BR2.
14. Documentation: `keel/docs/spec.md` and `apply.md`,
    `docs/manifest-v1.md`, the application pages (0077), and the site's
    security page.
15. When 0085 exists: the ntfy message for a failed check and for a node
    in `report`.

## Related notes

It applies 0041, 0053, 0073, 0075, 0090 and 0095. It uses the
confirmation window of 0018, the mesh of 0024 and 0048, the VIP of 0049
and the network stack of 0080.
