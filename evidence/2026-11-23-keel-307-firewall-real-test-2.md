# Evidence: second real-node test of keel pull request 307, the firewall in every mode (decision 0097)

Date: 2026-11-23. Site: BR1, the BR1 test VM (nested Proxmox VE).
Status: draft. For decision 0097, section D, and for `keel` pull request 307.

## Question

The first test (`evidence/2026-11-23-keel-307-firewall-real-test.md`,
head `86370ed`) failed items 1, 6 and 7. The commits `2ce1e16`,
`156b1a1` and `2120276` say that they correct these failures. Does head
`2120276` work on published nodes, with the published specs unchanged?

The test uses the method and the scripts of the first test. It also
tests the 4 cases that the coordinator added during the run (a to d).
A failure is a result. No code was changed.

## Tested head and package

- Branch `fix/firewall-every-mode`, tested head
  `2120276e317c67955db70e4c0125a02a20e49528`, version 0.23.99.
- During the run the head of the pull request moved to `fd16a68`. That
  head is not tested here.
- `keel_0.23.99_all.deb`, sha256
  `f2f0fa441585f743ea93159a2ed05df2c72602d30ebc41c9dc1844a231ac0ab6`.
- Built on the workstation from `git archive 2120276` with
  `dpkg-buildpackage -us -uc -b` (the command of `build-deb.yml` of
  `Keel-Linux/.github`), `SOURCE_DATE_EPOCH=1795462536` (the commit
  time), dpkg-dev 1.22.22, debhelper 13.24.2. The `package` job of the
  `keel` CI checks the changelog only and builds no package.
- The package went to the CTs by `pct push` only, and was installed with
  `dpkg -i`. It went to no apt repository and no mirror.

## Machines and images

Each CT is unprivileged (`uid_map 0 100000 65536`), `nesting=1`, 2
cores, 2 GiB, on the bridge `vmbr1` of the VM, with DHCPv4 and DHCPv6
from the dnsmasq of the VM.

| CT | Image | Mode | Use |
| --- | --- | --- | --- |
| 9400 | core 19.0-13 | simple | the probe node, keel 0.23.96 kept, not a mesh member |
| 9401 | lnmp 19.0-7 | simple | upgrade, enforce probes, table loss, timer cost, cases b and d |
| 9402 | lnpp 19.0-10 | simple | upgrade, rule B, states, init fence, case c, item 7 in report |
| 9403 | core 19.0-13 | simple | upgrade, SSH cases, item 7 in enforce |
| 9405 | lnmp 19.0-7 | simple | upgrade, network functions, reboot, MariaDB on 0.0.0.0, broken file, power loss |
| 9404 | lnmp 19.0-7 | simple | a new node (item 8) |
| 9420, 9421, 9422 | lnmp, lnmp, core witness | cloud_advanced | `keel-commission --pass cloud_advanced`: PASS, 117 checks |
| 9430, 9431 | lnmp, lnmp | cloud_simple | `keel-commission --pass cloud_simple`: PASS |

The `simple` CTs got the instance description of the first test before
the first boot. `keel-commission` is `bin/keel-commission` of
`Keel-Linux/.github` at `f75cfec`, as in the first test.

Templates from `https://mirror.keellinux.org/images/`, keyring sha256
`437ac43a7b8d25241c390835dcf38eeef3ed2713430404c780a25185da1ed35c`.
For each template `sqv` exited 0 and `sha512sum -c` passed. The sha256
values are the same as in the first test:

| Template | sha256 |
| --- | --- |
| `debian-13-keel-lnmp_19.0-7_amd64.tar.zst` | `66aa6fb14aa69a80a73211035daadc6480d20e1e72933a9372051f30405b5319` |
| `debian-13-keel-lnpp_19.0-10_amd64.tar.zst` | `0fe16d74e14b56f921d086f12dc53b661df7ab4de9cbc717ba2e51868ecbdff0` |
| `debian-13-keel-core_19.0-13_amd64.tar.zst` | `e32029debdf15a852084a08f24d8187dd526bd3ceebc3cc1e6512a1bf7fb4401` |

Each image has `keel` 0.23.96, `nftables` 1.1.3-1, `iproute2` 6.15.0-1,
`monit` 1:5.34.3-1.

Probes: `probe.py`, `listen.sh` (throwaway listeners on TCP and UDP
9999), `ra.py`, as in the first test. New: `fastprobe.py` tries TCP 9999
and TCP 22 every 50 ms with a timeout of 100 ms and prints each change.
Its resolution is about 0.15 s. `meshapply.py` takes the sync lock of
keel mesh and calls `keel.mesh.node.live_apply`, the function that
`keel mesh sync`, `members` and `join` call (`attended=False`).

## Summary

| Item | Result | The observed fact |
| --- | --- | --- |
| 1. Upgrade, then the apply of a person | PASS | No rule loaded after the upgrade, node open. The apply of a person gives `enforce` on all 9 nodes (3 images, 3 modes) with no `firewall:` key. Every enforce check passes |
| 1x. Decision 0073: the upgrade starts nothing | **not met** | The upgrade enables `keel-firewall-watch.timer` (new link), reloads systemd 8 times, restarts keel's path, timer, mesh-members and vip units. These restarts exist before this pull request |
| 2. Neighbour path, mesh over wg0 | PASS | Mesh ports time out through eth0, the control answers. Replication, etcd, Syncthing, failover and return work in enforce |
| 3. Rule B | PASS | Hand listener and MariaDB on 0.0.0.0 hold report and are named. `allow` with `from` releases. The fence does not hold report. The mesh apply never begins enforce |
| 4. SSH | **FAIL** | Two lock-outs: `SSHD_OPTS="-p 2200"`; and a `Port` changed in the file while sshd runs on the old port |
| 5. Table loss, timer | **FAIL** (cases b, d) | Service cases: open at most one probe round (about 0.15 to 0.22 s). Hand cases: 17.7 to 27.1 s. A replaced, wider rule is never seen. A reinstall of keel stops the timer |
| 6. Broken or cut file, power loss | **FAIL** in part | A broken file: PASS. An empty or cut file: the apply refuses to write it again. An empty file loads at boot with success, and the node is open. Power loss: the kill never hit the write |
| 7. Undecidable firewall | PASS | NOT APPLIED with the reason, the other steps run, exit 0, also in the mesh apply. A node in enforce stays in enforce |
| 8. New node, unprivileged, CrowdSec | PASS | First-boot apply gives `enforce`. Load in unprivileged CTs works. A restart of nftables.service removes the CrowdSec tables (recorded) |
| 9. Concurrency | PASS | The lock works in each order, with the real `keel-mesh-sync.service` too. Final state `enforce` in 11 of 11 tries |
| Case a | **FAIL** (see item 4) | |
| Case b | **FAIL** | After `dpkg -i` of the same package the timer is inactive. A deleted table did not come back in 2 min |
| Case c | finding | A masked timer makes the apply exit 16 on a node with no explicit enforce |
| Case d | **FAIL** | A rule replaced by `tcp dport 1-65535 accept`: `keel firewall check` exit 0, `keel diff` same, the apply unchanged, the timer silent. Port 9999 open for more than 70 s, until a restart by hand |

## Item 1: upgrade and the apply of a person

### 1a. The upgrade (logs 10, 21-adv-upgrade, 41-cs-upgrade)

`upgrade.sh` takes `snap.sh` before and after `dpkg -i`, the links in
`/etc/systemd/system`, and the systemd journal since the install. Order
in the pair and the trio: replica, witness, VIP holder.

| Check | simple (9401, 9402, 9403, 9405) | cloud_simple (9431, 9430) | cloud_advanced (9421, 9422, 9420) |
| --- | --- | --- | --- |
| Tables after | `table inet filter` only | `inet filter`, `ip crowdsec`, `ip6 crowdsec6` | the same |
| `/etc/keel/firewall` | absent | absent | absent |
| TCP and UDP 9998 from CT 9400, both families | `refused` (open) | | `refused` on 9420, 9421, 9422 |
| New link | `timers.target.wants/keel-firewall-watch.timer` | the same | the same |
| `keel-firewall-watch.timer` | `inactive enabled` | the same | the same |
| `nftables.service` DropInPaths | `/usr/lib/systemd/system/nftables.service.d/keel-firewall.conf` | the same | the same |
| Service PIDs that changed | none | `keel-mesh-members`, `keel-mesh-members-listen` | the same, and on 9420 and 9421 `keel-database-position`, `keel-vip`, `keel-vip-control` |
| Units restarted (journal) | `keel-mesh-members.path`, `keel-mesh-sync.timer`, `keel-mesh-etcd.timer`, `keel-database-follow.path`, `keel-database-watch.timer`, `keel-database-dump.timer`, `keel-database-position.timer` | the same and the services above | the same, and `keel-vip-check.timer`; runs of `keel-database-follow.service`, `keel-vip-check.service`, `keel-database-watch.service` |
| MariaDB, etcd, Syncthing, wg-quick | not restarted | not restarted | not restarted, VIP stays on 9420 |
| `keel diff` exit | | 0 to 14 | 0 to 14 |

The new package's maintainer scripts (read with `dpkg-deb -e`): the
postinst runs `deb-systemd-helper enable 'keel-firewall-watch.timer'`
and runs no start for it (`--no-start`). The postinst runs
`systemctl daemon-reload` for each unit with a restart. The restarts of
the keel path and timer units come from `dh_installsystemd` without
`--no-restart-after-upgrade`; they exist before this pull request.

No `keel-mesh-sync.service` run started between the upgrade and the
apply on the trio (journal count 0 from 20:28 to 20:32). On the pair the
next sync ran after the apply.

**Result 1a: no rule loaded, the node stays open: PASS. Against
decision 0073 ("none"): not met. The upgrade enables the new timer and
restarts keel's own units (as before this pull request).**

### 1b. The apply of a person with the published spec (logs 12, 23-adv-apply, 42-cs-apply)

`grep -c "^firewall:" /etc/keel/instance.yaml` gave 0 on each node.
Command: `keel spec apply --system`. Each apply exited 0.

| Node | State | Plan text |
| --- | --- | --- |
| 9401, 9405 lnmp simple | **enforce** | `derived.firewall: enforce: each socket on an address that is not a loopback belongs to a unit of the manifests (decision 0097, B)`, `closes udp 0.0.0.0:12321 of webmin.service (miniserv.pl): the manifests declare its process, not this port`, `write ... (enforce): public tcp 22, 80, 443, 12321`, `start keel-firewall-watch.timer ...: done` |
| 9402 lnpp simple | **enforce** | the same text, `public tcp 22, 80, 443, 12321` |
| 9403 core simple | **enforce** | the same text, `public tcp 22, 12321` |
| 9430, 9431 cloud_simple | **enforce** | `public tcp 22, 80, 443, 12321 and udp 51820, mesh tcp 3306, 22000 and udp 22000 on wg0` |
| 9420, 9421 cloud_advanced | **enforce** | `public tcp 22, 80, 443, 12321 and udp 51820, mesh tcp 2379, 2380, 3306, 22000 and udp 22000 on wg0` |
| 9422 witness | **enforce** | `public tcp 22, 12321 and udp 51820, mesh tcp 2379, 2380 on wg0` |

The dry run gave the same text with `would`. After each step of the
pair and the trio: `Slave_IO_Running: Yes`, 0 s behind, etcd 3 healthy
voters. `keel firewall check`: `table inet keel is the one
/etc/keel/firewall/keel-manifest.nft says`. `keel diff` exits 14 on the
simple nodes for `network.interfaces.eth0.ipv6.method: drift (declared
auto, observed dhcp)` only; `derived.firewall: same`.

### 1c. Enforce checks (logs 20-simple-enforce-probe, 25-adv-enforce-probe, 43-cs-enforce-probe, 21-simple-netfunc, 22-simple-reboot)

Each node was probed from CT 9400 and from the VM, IPv6 and IPv4, with
the listeners on TCP and UDP 9999 running (4 rows per node, read from
the raw log lines):

| Port | lnmp, lnpp (9401, 9402, 9405, 9420, 9421, 9430, 9431) | core (9403), witness (9422) |
| --- | --- | --- |
| TCP 9999, UDP 9999 (listener) | timeout | timeout |
| TCP 9998, UDP 9998 | timeout | timeout |
| TCP 22, 12321 | open | open |
| TCP 80, 443 | open | timeout (not declared) |
| UDP 12321 | timeout | timeout |

The 9421 rows were taken from 20:32:44 to 20:33:55. The failover of
item 2 moved the VIP at 20:33:40, so the last rows of 9421 overlap it.
The results are the same as on the other nodes.

| Function on 9405 in enforce | Observed |
| --- | --- |
| DHCPv4 and DHCPv6 rebind (`dhcpcd -n eth0`) | `rebinding lease of ...`, `leased ... for 7200 seconds`, `REPLY6 received from fe80::...` |
| Router advertisement (`ra.py 40`) | `RA received from fe80::... M=1 O=1 router-lifetime=600s` |
| Neighbour discovery | after `ip -6 neigh flush`, a ping to a public IPv6 address: 2 of 2 received, the router `REACHABLE` |
| `apt-get update` | `apt exit 0` |
| Port 80 from CT 9400 | `curl http://ADDR/.well-known/acme-challenge/ev307r2`: `404` on IPv6 and IPv4 |
| `pct reboot 9405`, journal | `Finished nftables.service` 379543.439, `Finished keel-firewall.service` 379543.525, `Reached target network-pre.target` 379543.591, `Started keel-firewall-watch.timer` 379544.232, `eth0: leased` 379544.375, `Starting ssh.service` 379544.530 |
| Probes after the reboot | the same as in the table above, 4 of 4 rows |

**Result for item 1: PASS.** The failure of the first test is corrected:
rule B decides with no `firewall:` key.

## Item 2: neighbour path and the mesh over wg0 (PASS)

CT 9400 added a `/128` route for each wg0 address and the VIP through
the link-local address of the node on `vmbr1` (logs 30, 31, 44).

| Target | 3306 | 2379 | 2380 | 22000 TCP | 22000 UDP | 51821 | 22 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cloud_advanced primary 9420 wg0 | timeout | timeout | timeout | timeout | timeout | timeout | open |
| cloud_advanced VIP | timeout | | | | | | open |
| cloud_advanced replica 9421 wg0 | timeout | timeout | timeout | timeout | timeout | timeout | open |
| witness 9422 wg0 | | timeout | timeout | | | timeout | open |
| cloud_simple primary 9430 wg0 | timeout | | | timeout | timeout | timeout | open |
| cloud_simple VIP | timeout | | | | | | open |
| cloud_simple replica 9431 wg0 | timeout | | | timeout | timeout | timeout | open |

Control on 9421: timer stopped, `nft delete table inet keel`, the same
probe: 3306 `open`, 2379 `open`, 2380 `open`, 22000 `open`, 51821
`refused`. Then the timer and its unit started again: `table inet keel
is the one ... says`.

| Check in enforce | Observed |
| --- | --- |
| Replication | a row written on 9420 arrived on 9421: `Master_Host` the wg0 address of 9420, `Slave_IO_Running: Yes`, `Master_SSL_Allowed: Yes`, 0 s behind. The same on the pair (9430 to 9431) |
| etcd | `etcd: 3 voter(s), 0 learner(s)`, each `healthy` |
| Syncthing | established sessions on 22000 between the wg0 addresses, both pairs |
| Failover | `pct shutdown 9420` at 20:33:06 (done 20:33:14). VIP on 9421 at 20:33:40. `@@read_only` 0, a row written on 9421 |
| Return | `pct start 9420`. `keel-firewall.service` before `network-pre.target` before `wg-quick@wg0`, `policy drop`. At 20:35:37 `keel-database-follow`: replicating from the wg0 address of 9421, `Slave_IO_Running: Yes`, both rows present. About 2.5 min from the start to replication. etcd 3 healthy voters |

The overlay has IPv6 addresses only, so there is no IPv4 probe of the
neighbour path.

## Item 3: rule B (PASS)

| Case | Node | Observed |
| --- | --- | --- |
| Hand listener on a node already in enforce | 9402 | apply: `enforce, as keel's file already says`, no word of the listener. Only `keel diff` names it: `enforce closes ... udp *:9999 of ev-udp.service (python3); tcp *:9999 of ev-tcp.service (python3)` |
| Hand listener, node in report, no key | 9402 | `report: enforce waits, because these sockets belong to no unit of the manifests: udp *:9999 of ev-udp.service (python3); tcp *:9999 of ev-tcp.service (python3). Declare each in firewall.allow, or stop it, or set firewall.state: enforce`, `policy accept`, `keel-report` counter |
| Listener stopped, apply | 9402 | `enforce: each socket ... (decision 0097, B)`, `policy drop` |
| MariaDB with `bind-address = 0.0.0.0` (a cnf file of its own), node in report, no key | 9405 | `ss`: `0.0.0.0:3306 mariadbd`, also after the apply. `report: enforce waits, because these sockets belong to no unit of the manifests: tcp 0.0.0.0:3306 of mariadb.service (mariadbd): enforce opens this port on wg0 only, and a client outside the mesh would be cut` |
| `allow: [{port: 3306, protocol: tcp, from: [CT 9400 /128, CT 9400 /32]}]` | 9405 | `enforce`, rules `ip saddr ... tcp dport 3306 accept` and `ip6 saddr ... tcp dport 3306 accept`. From CT 9400: IPv4 `open`, IPv6 `refused` (MariaDB listens on IPv4 only; the packet passed the filter). From the VM: `timeout` on both families |
| Running init fence (60080, 60443), node in report, no key | 9402 | `enforce: each socket ... (decision 0097, B)`, rule `ct status dnat tcp dport { 60080, 60443 } accept`. From CT 9400: `http://ADDR/` and `https://ADDR/` give `200`, 2943 bytes, both families. Direct TCP 60080 and 60443: `timeout`. Fence stopped and disabled: the `dnat` rule goes |
| `state: report` with no listener | 9402 | `report`, `policy accept`, a second apply `unchanged` |
| `state: off` | 9402 | `remove /etc/keel/firewall/keel-manifest.nft ...: done`, `remove keel's table ... (nft delete table inet keel): done`. Tables: `inet filter` only. `keel diff`: `warning: off in the spec` |
| Mesh apply on a node in enforce | 9422 | `enforce, as keel's file already says`, exit 0, `policy drop` |
| Mesh apply on a node in report, no key | 9422 | `report: only an apply a person runs (keel spec apply --system) moves this node to enforce`, exit 0, `policy accept` |
| Mesh apply with `state: enforce` | 9422 | `report until an apply a person runs: the spec says enforce, and keel mesh never begins enforcement (decision 0097)` |

The mesh apply here is `meshapply.py` (see "Machines and images"), with
no member change.

## Item 4: SSH (FAIL)

On 9403 (core, enforce). The console path was `pct exec`. Probes from
CT 9400, both families (log 40).

| Case | Plan text | Observed |
| --- | --- | --- |
| 4.1 `Port 22` and `Port 2222` in `sshd_config.d`, sshd restarted | `SSH stays open: tcp 22, 2222, the ports sshd listens on (sshd -T)` | 22 `open`, 2222 `open`, 9998 `timeout` |
| 4.2 `Port 2222` only | `SSH stays open: tcp 2222 (sshd -T)` | 2222 `open`, 22 `refused` (declared by the manifest, no listener) |
| 4.3 socket activation, `ListenStream=` and `ListenStream=2022` in `ssh.socket.d`, no `Port` | `SSH stays open: tcp 22, 2022, ... (/etc/ssh/sshd_config sets no Port: sshd's default 22, ssh.socket)`, rule `tcp dport { 22, 2022, 12321 }` | 2022 `open` (port not in the table before), 22 `refused` |
| a1 `SSHD_OPTS="-p 2200"` in `/etc/default/ssh`, no `Port` in the files, `ssh.socket` stopped | `closes tcp 0.0.0.0:2200 of ssh.service (sshd): the manifests declare its process, not this port`, `public tcp 22, 12321` | **lock-out**: 2200 `timeout`, 22 `refused`, both families. `ps`: `sshd -D -p 2200` |
| a2 `Port 2222` written, no restart, image default (socket mode, 22) | `SSH stays open: tcp 22, 2222 (sshd -T, ssh.socket)` | 22 `open`, 2222 `refused` |
| a2b the same with `ssh.service` alone on 22 | `SSH stays open: tcp 2222, the ports sshd listens on (sshd -T)` | 22 `open`, but only because the manifest declares 22. 2222 `refused` |
| a2c sshd restarted on `Port 2222`, then the file changed to `Port 2333`, no restart | `closes tcp 0.0.0.0:2222 of ssh.service (sshd)` and `SSH stays open: tcp 2333 (sshd -T)` | **lock-out**: 2222 `timeout`, 2333 `refused`, 22 `refused` |

In a1 and a2c the plan itself names the socket of sshd that enforce
closes. keel takes the ports from `sshd -T`, which reads the files and
not the command line or the running process. After each case SSH was
put back as found (`ssh.socket` and `ssh.service` active, 22 `open`).

## Item 5: table loss and the timer (FAIL, cases b and d)

On 9401 (lnmp, enforce), listener on TCP 9999. `fastprobe.py` from CT
9400 on IPv6 and IPv4 in parallel (logs 50, 51, 52). Times are UTC.

| Loss | Open window (TCP 9999) | Journal |
| --- | --- | --- |
| `systemctl restart nftables.service` (3 tries) | IPv6: 12.226 to 12.443, 42.245 to 42.396, 01.900 to 02.050. IPv4: none, 42.369 to 42.520, 01.899 to 02.050. At most one probe round, about 0.15 to 0.22 s | `Stopping nftables.service` 42.181, `Finished` 42.423: the whole unit run 0.24 s |
| `systemctl reload nftables.service` | none seen | `Reloading` 22.219, `Reloaded` 22.322 |
| `systemctl stop nftables.service` | none seen | after: `table inet keel` only, `inet filter` gone, nftables inactive |
| `apt-get install --reinstall nftables` | first try void: `cannot be downloaded`. After `apt-get update`: IPv6 18.575 to 18.726, IPv4 none | `Stopping nftables.service` 18.462, `Finished` 18.735 |
| `nft flush ruleset` | **27.1 s** both families (29.89 to 56.95) | `table inet keel is not loaded; ... loaded again`. `inet filter` does not come back |
| `nft delete table inet keel` | **24.9 s** (38.13 to 03.04) | the same line |
| `nft flush chain inet keel input` | 9999 stays closed; **TCP 22 closed for 17.7 s** (50.74 to 08.48), both families: the node is closed, not open | `holds 0 rule(s), and the file has 8 (a chain flushed or edited by hand): loaded again` |
| input policy changed to accept | **18.8 s** (58.15 to 16.95) | `has policy accept, and the file says drop: loaded again` |
| Case d: the rule `tcp dport { 22, 80, 443, 12321 } accept` replaced by `tcp dport 1-65535 accept` (same rule count) | **open from 21:00:20.8 to the end of the 75 s probe**, and until `systemctl restart keel-firewall.service` by hand | no line. `keel firewall check`: `table inet keel is the one ... says (a08b6b17d635a90b)`, exit 0. `keel diff`: `derived.firewall.loaded: same`. `keel spec apply --system`: `unchanged (..., loaded as table inet keel)` |
| Case b: `dpkg -i` of the same package on a node in enforce, then `nft delete table inet keel` | open from 21:02:21.7 to the end of the 60 s probe; 2 min later still no table (`nft list tables` empty) | after `dpkg -i`: `keel-firewall-watch.timer: Deactivated successfully`, `inactive enabled`. The next apply of a person: `start keel-firewall-watch.timer ...: done` |

For case b, read from the package: the preinst of 0.23.99 runs
`deb-systemd-invoke stop 'keel-firewall-watch.service'
'keel-firewall-watch.timer'` when `$1` is `upgrade`, and the postinst
does not start it. So each later upgrade of keel would stop the watch
on every node until an apply or a reboot. The drop-in for
`nftables.service` still works then.

The author's claim: milliseconds for the service cases, at most about
35 s for the hand cases. Observed: the service cases at most one probe
round (0.15 to 0.22 s), the hand cases 17.7 to 27.1 s. The claim holds
for these cases. It does not hold for case d (never) and case b (no
timer).

**The timer in report and with `state: off` (log 32).**

| State | Observed |
| --- | --- |
| report, 9402: `nft delete table inet keel` at 20:19:07 | back at 20:19:41 (34 s), `policy accept` with the `keel-report` counter: the timer loads the report table again |
| off, 9402 | 45 s later: `inet filter` only. `keel-firewall-watch.service` `ConditionResult=no`. `systemctl restart nftables.service`: still `inet filter` only. The timer stays `active enabled`, its unit is skipped |

**Case c: the timer masked (log 33).** On 9402, `systemctl mask
keel-firewall-watch.timer`, then `keel spec apply --system`:

- with `state: report`: `apply exit 16`, `start keel-firewall-watch.timer ...: failed: systemctl exited 1: Failed to start keel-firewall-watch.timer: Unit keel-firewall-watch.timer is masked.`, `apply --system: 0 change(s), 1 failed`;
- with no key: the same failure and exit 16, but the file was written and loaded in `enforce` (`2 change(s), 1 failed`).

`docs/apply.md` says that only an explicit `state: enforce` makes a
firewall problem a failure of the apply. A masked timer fails the apply
with no explicit enforce.

**Timer cost on 9401, 10 min (log 53).** Unit accounting of
`keel-firewall-watch.service`, read after each run:

| Measure | Value |
| --- | --- |
| Runs in 600 s | 19 |
| CPU per run | 473 to 938 ms, mean 549 ms |
| CPU in 600 s | 10.4 s, 1.74 % of one core |
| Memory peak per run | 21 MiB |
| Run time | 490 to 987 ms |
| Journal lines of the timer and its unit | 0 in 10 min (0 per hour, extrapolated) |
| All journal lines of the node in the window | 52 |

## Item 6: broken or cut file and power loss (FAIL in part)

On 9405 (log 38, 39).

| Case | Observed |
| --- | --- |
| A broken line after the header | `nft -c`: `syntax error, unexpected !`. `systemctl restart keel-firewall.service`: exit 1, `failed`, table digest the same before and after, `policy drop`. `keel firewall check`: `Error: nft -c refuses ...; keel spec apply --system writes it again`, exit 14. 40 s later: `keel-firewall-watch.service: Failed with result 'exit-code'`, `degraded`. TCP 22 `open`, 9998 `timeout` |
| The file cut to half its bytes | `keel firewall check`: `Error: ... is not a ruleset keel wrote, or it is cut short (an empty file loads no table): keel spec apply --system writes it again`, exit 14. `systemctl restart keel-firewall.service`: exit 1, `failed`, old table kept, `degraded` |
| An empty file | the same check line, exit 14 |
| `keel spec apply --system` with the empty file | **not repaired**: `derived.firewall: NOT APPLIED, the node keeps the firewall it has: /etc/keel/firewall/keel-manifest.nft is there and keel did not write it: it is not replaced; move it away and apply again`, exit 0, file 0 bytes |
| `pct reboot` with the empty file | **node open**: no `inet keel`, `keel-firewall.service` `active`, result `success` (an empty file loads nothing and does not fail). TCP 9998 `refused`, UDP 12321 `reply` on IPv4. `degraded` only by the watch unit |
| Repair | the empty file moved away by hand, then the apply: `enforce`, written and loaded, `running` |

The check says "keel spec apply --system writes it again". The apply
says "keel did not write it: it is not replaced". Both lines are about
the same file.

**Power loss.** 28 tries. Each try changed an `allow` port (8081 or
8082), so the apply had to write the file again, started the apply, and
stopped the CT hard after a delay:

| Tries | How | Delays | Where the kill landed (last line of the apply log) | File after |
| --- | --- | --- | --- | --- |
| 1 to 6 | `pct exec` (it waited for the apply), `pct stop` | 0.4 to 2.4 s | after the apply | 685 bytes, sound |
| 11 to 16 | `systemd-run --no-block`, `pct stop` | 0.3 to 1.8 s | after the apply (`pct stop` itself takes time) | 685 bytes, sound |
| 21 to 28 | `systemd-run --no-block`, `lxc-stop -k` | 0.05 to 1.0 s | before the firewall step | 685 bytes, the old file, sound |
| 31 to 38 | the same | 1.1 to 1.9 s | before the firewall step (try 38: no change to write) | 685 bytes, the old file, sound |

The file was never empty and never cut. But no kill landed between the
write and the rename, so the window was **not hit**. `lxc-stop -k` and
`pct stop` do not drop the page cache of the host, so this test cannot
prove or disprove the `fsync`.

## Item 7: an undecidable firewall (PASS)

`undecided.sh` adds a bad directive in `sshd_config.d` (`sshd -T` exit
255) and `Include /etc/ssh/ev307r2-extra.conf` in `sshd_config`. sshd is
not restarted (log 41).

| Node | Observed |
| --- | --- |
| 9402 in report, no key, a monit file moved away first | `apply exit 0`, `derived.monit: write /etc/keel/monit/keel-manifest.conf ...: done` (the other steps run), `derived.firewall: NOT APPLIED, the node keeps the firewall it has: the ports sshd listens on cannot be determined (sshd -T did not answer, and /etc/ssh/sshd_config says Include /etc/ssh/ev307r2-extra.conf, which keel does not follow) ...`, table digest the same, `policy accept` |
| 9403 in enforce, no key | `apply exit 0`, the same NOT APPLIED line, `0 change(s), 0 failed`, table digest the same, `policy drop` |
| 9403 with `state: enforce` | `apply exit 16`, `derived.firewall: refused: ...`, `0 change(s), 1 failed`, `policy drop` |
| 9421 in enforce, mesh apply | NOT APPLIED line, `keel mesh: 3 change(s), 0 failed`, `mesh apply exit 0`, table and spec digests the same, `policy drop`. The 3 other changes were not examined |
| 9422 in report, mesh apply | NOT APPLIED line, `0 change(s), 0 failed`, exit 0, table and spec the same |

The mesh apply is `meshapply.py` (`live_apply` under the sync lock, no
member change). The path that puts the spec back (after an apply that
exits non-zero) did not run; exit 0 is the evidence that it would not.

## Item 8: new node, unprivileged CT, CrowdSec (PASS)

**New node (log 60).** CT 9404 from the lnmp template with
`inithooks.service` masked before its first start. The CT started once
with no first-boot hooks (`no-inithooks-log`). Then `dpkg -i` of the
package (0.23.99), the mask removed, `pct reboot`. So "before first
boot" here means before the first-boot hooks, not before the first
start.

| Check | Observed |
| --- | --- |
| First boot | `completed: 1`, no error, `running` |
| First-boot apply | `[10keel-system] derived.firewall: enforce: each socket ... (decision 0097, B)`, `write ... (enforce): public tcp 22, 80, 443, 12321: done`, `load ...: done` |
| Table | `policy drop`, file `# state: enforce`, watch timer `active` |
| Boot order | `keel-firewall.service ... skipped, unmet condition check ConditionPathExists`, then `network-pre.target`, then the lease. The table came after the network, from the first-boot apply. Expected until the images write the file with `--root` |

**Unprivileged CTs.** `nft -c` and `nft -f` worked in each of the 10
CTs that got the package (`uid_map 0 100000 65536`).

**CrowdSec on 9431 (record only, log 45).** Before: `inet filter`, `ip
crowdsec`, `ip6 crowdsec6`, `inet keel`. After `systemctl restart
nftables.service`: `inet filter`, `inet keel`, and no CrowdSec table,
also 60 s later, with `crowdsec-firewall-bouncer.service` `active`. A
restart of the bouncer by hand brought both CrowdSec tables back.
Replication still `Yes`.

## Item 9: concurrency (PASS)

On 9422 (log 36). Before each try the node was in report with no key.

| Order | Observed |
| --- | --- |
| A: the mesh apply holds the lock 20 s, a person applies 2 s later | `Warning: keel spec apply waits at most 600 s for the sync lock, which ev307r2 mesh apply (pid ..., since 20:38:01 UTC) holds`. The person's apply ran at the release, exit 0 after 20 s: `enforce`, `policy drop` |
| C: 5 tries, the person's apply and the mesh apply started at the same instant | one waited for the other in each try (person 4 times, mesh 1 time). Final state `enforce`, `policy drop` in 5 of 5. Where the mesh ran first it said `report`, and the person's apply then gave `enforce` |
| D: 5 tries, a person's apply, then 0.2 s later `systemctl start keel-mesh-sync.service` (the unit of the timer) | 4 tries: sync said `another keel mesh sync is adding members: keel spec apply (pid ..., since ...) holds the sync lock; this one leaves it to finish`. 1 try: sync ran after the apply. No deadlock, final state `enforce` in 5 of 5 |

A first order B try did not overlap (the person's apply ended before
the sync started) and is not counted.

## Against the first test

| First test (head `86370ed`) | This test (head `2120276`) |
| --- | --- |
| Item 1 FAIL: the apply of a person gave `report` on all 8 nodes with no `firewall:` key | PASS: `enforce` on all 9 nodes with no key |
| Item 6 FAIL: after `systemctl restart nftables.service` the node was open 540 s and more on the published spec | The drop-in: open at most about 0.15 to 0.22 s. A flush by hand: 17.7 to 27.1 s by the timer. New failures: a replaced rule is never seen (case d); a reinstall of keel stops the timer (case b) |
| Item 7 FAIL: a new node got `report` | PASS: `enforce` at the first-boot apply |
| `keel firewall check` did not see a broken file | it sees a broken, cut or empty file, and the timer's unit fails. But the apply does not write a cut or empty file again |
| A running fence kept rule B in report | it does not |
| SSH guard: 2222 and only 2222 passed | they pass. New cases fail: a port from `SSHD_OPTS`, and a port changed with no restart |

## What was not tested

- The ISO in a VM, BIOS and UEFI (section D, item 11).
- The release topology: 2 sites with netem. All nodes were on one bridge
  of one VM.
- Image builds: the rule set written with `--root`, the mode screen.
- The other 10 images.
- `keel mesh invite` and `join` with the invite port.
- A real member change that runs the mesh apply through `keel mesh
  sync`; the mesh apply was `live_apply` called directly.
- A masked timer in the mesh path (it could make each mesh apply exit
  non-zero).
- Power loss between the write and the rename of the ruleset (not hit),
  and the `fsync` itself.
- SLAAC, a lease that expires by time, packet capture during boot, a
  pair under writes during the upgrade, a failover by a hard stop.
- The head `fd16a68`, which came after the run started.

## Logs

Kept on the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr307-run2/`. The runner records
(`runner-adv/`, `runner-cs/`) hold console transcripts and are not
copied here.

| Log | Content |
| --- | --- |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after, cleanup |
| `01-images`, `02-create-simple`, `03-firstboot-simple`, `04-push` | templates, CTs, first boot, push |
| `10-simple-upgrade`, `11-simple-open-after-upgrade`, `12-simple-apply`, `20-simple-enforce-probe`, `21-simple-netfunc`, `22-simple-reboot` | item 1, simple |
| `20-adv-runner`, `21-adv-pre`, `21-adv-upgrade`, `22-adv-mesh-window`, `23-adv-apply`, `25-adv-enforce-probe` | item 1, cloud_advanced |
| `40-cs-runner`, `41-cs-upgrade`, `42-cs-apply`, `43-cs-enforce-probe`, `46-cs-journal` | item 1, cloud_simple |
| `30-neighbour-enforce`, `31-neighbour-control`, `32-adv-wg0-enforce`, `33-adv-failover`, `44-cs-neighbour` | item 2 |
| `30-rule-b-listener`, `31-rule-b-states`, `34-fence`, `35-mesh-unattended`, `37-mariadb-any` | item 3 |
| `40-ssh` | item 4, case a |
| `32-timer-off-report`, `33-mask-timer`, `50-table-loss`, `51-wider-rule`, `52-reinstall-keel`, `53-timer-cost` | item 5, cases b, c, d |
| `38-broken-file`, `39-power-loss` | item 6 |
| `41-undecided` | item 7 |
| `60-new-node`, `45-crowdsec` | item 8 |
| `36-concurrency` | item 9 |
| `90-secret-scan` | secret scan |

Secret handling: the secrets of the `simple` nodes were made on the VM
inside the root file system of each stopped CT, and no command printed
them. No WireGuard key was read or changed. Each log and each runner
transcript was scrubbed of base64 keys and invitations. The scan of log
90 over 168 files found no key, no invitation, no private key, no
password and no token.

## Cleanup

CTs 9400 to 9405, 9420 to 9422, 9430 and 9431 were destroyed with
`pct destroy --purge`. The templates `ev307r2-*` and `/root/ev307r2`
were removed from the VM. The core and Nextcloud templates that were on
the VM before the test were not touched. The Proxmox firewall was not
changed: `pve-firewall status` is `disabled/running`, and
`/etc/pve/firewall` is empty, as before. The diff of the VM state before
and after (the commands of log 00: `pve-firewall status`, the files of
`/etc/pve/firewall` and of the node, `iptables-save`, `ip6tables-save`,
`ebtables-save`, `nft list ruleset`, the `bridge-nf-call` sysctls,
`pct list`, the links, the template cache, `/root`), without packet
counters, time stamps and veth peer indexes, is empty: `diff_exit=0
lines=0` (log 99).
