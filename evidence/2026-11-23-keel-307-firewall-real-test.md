# Evidence: real-node test of keel pull request 307, the firewall in every mode (decision 0097)

Date: 2026-11-23. Site: BR1, the Keel test VM (nested Proxmox VE, VM 143).
Status: draft. For decision 0097, section D, and for `keel` pull request 307.

## Question

`keel` pull request 307 (branch `fix/firewall-every-mode`, head
`86370ed`, version 0.23.99) makes keel write and load the table
`inet keel` in every installation mode. Does it work on published nodes?

1. The upgrade path in `simple`, in a `cloud_simple` pair and in a
   `cloud_advanced` trio. Which state does the apply of a person give,
   and which sockets keep rule B in `report` on each image?
2. Is `enforce` real on IPv6 and IPv4, TCP and UDP, after a reboot too?
3. Does the rule set close the mesh ports to a neighbour on the link?
4. The edge cases of rule B.
5. The SSH guard, a broken rule file, a failed load.
6. The loss of the table.
7. A new node.
8. `nft -c` and the load in an unprivileged container, CrowdSec, the
   init fence.

A failure is a result. No code was changed.

## Summary

| Item | Result | The observed fact |
| --- | --- | --- |
| 1. Upgrade path | **FAIL** | The install changes no rule. But the apply of a person gives `report` on all 8 nodes (3 images, 3 modes). The sockets are never listed, because the published spec has no `firewall:` key (`keel/system/appstate.py:120`). With the key, rule B gives `enforce` on each image and mode |
| 2. Enforce is real | PASS | With `enforce` (from an added `firewall: {enabled: false}` key): TCP and UDP 9999 time out, declared ports answer, DHCP, RA, ND, apt and port 80 work, the table loads before the network at boot |
| 3. Neighbour path | PASS (IPv6) | 3306, 2379, 2380, 22000 and 51821 time out through eth0. The control without the table answers. Replication, etcd, Syncthing and a failover work on wg0. The overlay has no IPv4 |
| 4. Rule B edge cases | PASS, with the key | A hand listener keeps `report` and is named. Without it, `enforce`. A mesh apply never begins `enforce`, also with `state: enforce`. A node in `enforce` stays there |
| 5. SSH guard, broken file | PASS | Port 2222 is opened and named, also as the only port. An sshd configuration that keel cannot read refuses the apply. A broken file fails the unit and keeps the old table. `keel firewall check` does not see a broken file |
| 6. Table loss | **FAIL** on the published spec | No `monitor:` section, so Monit does not load keel's check. After `systemctl restart nftables.service`, the table did not come back in 501 s and TCP 9999 answered for 540 s. With `monitor.enabled: true`: 225 s (restart) and 73 s (flush) |
| 7. A new node | **FAIL** | 0.23.99 installed before the first boot: the first-boot apply gives `report`, for the cause of item 1 |
| 8. Unprivileged, CrowdSec, fence | PASS | `nft -c` and the load work in each unprivileged container. A CrowdSec ban drops. The fence page answers through the legacy REDIRECT. A running fence keeps rule B in `report` |

The answer to "which sockets keep rule B in `report` on each image": no
socket of any of the 3 images. On a published node the missing
`firewall:` key keeps every node in `report`. With the key, the sockets
of each image and mode belong to units of the manifests. The only socket
that `enforce` closes is UDP 12321 of `webmin.service`, as information.

## Machines, images and the package

The test VM is `keel-pve-br1`. Each CT is unprivileged, `nesting=1`, 2
cores, 2 GiB, rootfs on `local`, on the bridge `vmbr1` of the VM, with
DHCPv4 and DHCPv6 from the dnsmasq of the VM (`ip=dhcp,ip6=dhcp`).

| CT | Image | Mode | How it was made |
| --- | --- | --- | --- |
| 9400 | core 19.0-13 | simple | instance description before the first boot. The probe node: not a mesh member, keel 0.23.96 kept |
| 9401 | lnmp 19.0-7 | simple | the same |
| 9402 | lnpp 19.0-10 | simple | the same |
| 9403 | core 19.0-13 | simple | the same |
| 9404 | lnmp 19.0-7 | simple | the same, and `inithooks.service` masked before the first start (item 7) |
| 9420, 9421, 9422 | lnmp 19.0-7, lnmp 19.0-7, core 19.0-13 | cloud_advanced: primary, replica, witness | `keel-commission --pass cloud_advanced`, the mode screen answered on the console |
| 9430, 9431 | lnmp 19.0-7 | cloud_simple: primary, replica | `keel-commission --pass cloud_simple` |

The instance description of the `simple` nodes is the `instance:` block
of the simple pass of the `keel-lnmp` contract at tag `19.0-7`, with the
appliance name changed for lnpp and core. `keel-commission` is
`bin/keel-commission` of `Keel-Linux/.github` at `f75cfec`, as in the
earlier evidence. Both runs passed: `cloud_advanced` 117 checks, and
`cloud_simple` 87 checks, `keel-commission exit 0` (logs 20, 40).

The templates come from `https://mirror.keellinux.org/images/`. The
keyring is `keys/keel-images-keyring.asc` of the `apt` repository at
`a22cde2`, sha256
`437ac43a7b8d25241c390835dcf38eeef3ed2713430404c780a25185da1ed35c`. For
each template, `sqv` exited 0 and `sha512sum -c` passed (log 01).

| Template | sha256 |
| --- | --- |
| `debian-13-keel-lnmp_19.0-7_amd64.tar.zst` | `66aa6fb14aa69a80a73211035daadc6480d20e1e72933a9372051f30405b5319` |
| `debian-13-keel-lnpp_19.0-10_amd64.tar.zst` | `0fe16d74e14b56f921d086f12dc53b661df7ab4de9cbc717ba2e51868ecbdff0` |
| `debian-13-keel-core_19.0-13_amd64.tar.zst` | `e32029debdf15a852084a08f24d8187dd526bd3ceebc3cc1e6512a1bf7fb4401` |

Each image has `keel` 0.23.96, `nftables` 1.1.3-1, `iproute2` 6.15.0-1
and `monit` 1:5.34.3-1 (log 03).

**The package under test.** `keel_0.23.99_all.deb`, sha256
`9d36b480faee33966d22a9e46d759bd5f9d770a2197753d279fb90e043ed6504`.
It was built on the workstation from `git archive 86370ed` with
`dpkg-buildpackage -us -uc -b`, which is the command of the reusable
workflow `build-deb.yml` of `Keel-Linux/.github`.
`SOURCE_DATE_EPOCH` was the commit time. The `package` job of the `keel`
CI checks the changelog only, so it builds no package. The package went
to the CTs by `pct push` only. It went to no apt repository and no
mirror. It was installed with `dpkg -i`, not `apt`, so that no
`needrestart` run can restart a service.

### The probes

- `probe.py` (from the earlier evidence) opens a TCP connection or sends
  one UDP datagram. It prints `open`, `refused` or `timeout` for TCP,
  and `reply`, `refused` or `timeout` for UDP.
- `listen.sh` starts 2 throwaway listeners on the target: TCP 9999
  (`ev-tcp.service`) and a UDP echo on 9999 (`ev-udp.service`).
- Port 9998 has no listener. Without a filter it is `refused`. Behind a
  drop it is `timeout`.
- Each probe ran on the IPv6 and IPv4 address of the target, from CT
  9400 and from the VM.
- `snap.sh` records the state that an upgrade must not change: the
  `nft` rule set digest and tables, the main PID and start time of each
  running service, `keel-firewall.service`, WireGuard handshake ages,
  the VIP, the MariaDB role and replica status, etcd, the `keel diff`
  exit code, failed units.
- `ra.py` waits on a raw ICMPv6 socket for a router advertisement. A
  raw socket gets a packet after the netfilter input hook. Thus a
  received RA went through the input chain.
- `watchport.py` connects to a TCP port once a second and prints each
  change of result with the time.

## Item 1: the upgrade path (FAIL)

### 1a. The install of 0.23.99 over 0.23.96 (logs 10, 41-cs, 21-adv)

Order in the pair and the trio: the replica first, then the witness,
then the VIP holder.

| Check | simple (9401, 9402, 9403) | cloud_simple (9431, then 9430) | cloud_advanced (9421, 9422, then 9420) |
| --- | --- | --- | --- |
| `dpkg -i`, then `diff` of `snap.sh` before and after | only `keel 0.23.96` to `keel 0.23.99` | the version, and new PIDs of `keel-mesh-members.service` and `keel-mesh-members-listen.service`. `keel diff` exit 0 to 14 | the same, and on the primary and the replica also new PIDs of `keel-vip.service`, `keel-vip-control.service` and `keel-database-position.service` |
| Rule loaded | none: `table inet filter` only, no `/etc/keel/firewall` | none: `inet filter`, `ip crowdsec`, `ip6 crowdsec6` | the same |
| `keel-firewall.service` | `inactive enabled`, `ConditionResult=no` | the same | the same |
| Node still open | TCP and UDP 9998 `refused` from CT 9400, both families | | |
| MariaDB, etcd, Syncthing, `wg-quick@wg0` | not restarted | not restarted. Replica `Slave_IO_Running: Yes`, 0 s behind | not restarted. etcd 3 healthy voters. The VIP stays on 9420 |

The restart of the `keel-vip` units comes from the trigger of the
package `keel-overlay-vip` (`interest-noawait
/usr/lib/python3/dist-packages/keel`), which exists before this pull
request. The journal of 9420 says: `vip fd4f:478b:3701::ffff:1: kept
while the unit restarts`. The VIP address stayed on wg0. The restart of
the mesh-members units comes from the package scripts of `keel`.

A run of `keel-mesh-sync.service` (the unit of the timer) with stable
members said `no member this node does not know` and applied nothing
(log 42-cs). No file was written.

**Result 1a: the install loads no rule and leaves the node open. It
restarts keel's own mesh-members units, and in `cloud_advanced` the
`keel-vip` units. It does not restart the database, etcd, Syncthing or
WireGuard.**

### 1b. The apply of a person with the published spec (logs 12 to 15, 23)

Command: `keel spec apply --system`. No published spec has a
`firewall:` key (`grep -c "^firewall:" /etc/keel/instance.yaml` gives 0
on each node).

| Node | State | Plan text |
| --- | --- | --- |
| 9401 lnmp, simple | **report** | `derived.firewall: report: the sockets cannot be listed (not the live system: no socket is seen), so enforce waits; firewall.state: enforce enforces anyway` and `write /etc/keel/firewall/keel-manifest.nft (report): public tcp 22, 80, 443, 12321` |
| 9402 lnpp, simple | **report** | the same text, `public tcp 22, 80, 443, 12321` |
| 9403 core, simple | **report** | the same text, `public tcp 22, 12321` |
| 9430, 9431 lnmp, cloud_simple | **report** | the same text, `public tcp 22, 80, 443, 12321 and udp 51820, mesh tcp 3306, 22000 and udp 22000 on wg0` |
| 9420, 9421 lnmp, cloud_advanced | **report** | the same text, and `mesh tcp 2379, 2380, 3306, 22000 and udp 22000 on wg0` |
| 9422 core witness, cloud_advanced | **report** | the same text, `public tcp 22, 12321 and udp 51820, mesh tcp 2379, 2380 on wg0` |

The table loads with `policy accept` and the counter rule `keel-report:
enforce would drop these`. A second apply gives the same text.

The cause, read in code at `86370ed`: `keel/system/appstate.py:119-121`
calls `observe_firewall(tree, tree.root == ROOT_DEFAULT and
doc.get("firewall") is not None)`. The comment says "nft is asked only
when the spec speaks of the firewall". With no `firewall:` key, `live`
is false. `observe_listeners` then returns "not the live system", and
`choose()` in `keel/system/firewall.py` keeps `report`. With `live`
false, the SSH ports also come from the files only, not from `sshd -T`
or `ssh.socket`, and the loaded digest is not read, so each apply loads
the table again.

The dry run (`keel spec apply --system --dry-run`) shows the same
`report` text. `keel diff` lists the sockets: it does not use this
condition. On each of the 8 nodes it said only:
`derived.firewall.listeners: not compared (report: enforce would close
udp 0.0.0.0:12321 of webmin.service (miniserv.pl))`.

### 1c. The same apply with a `firewall:` key (logs 13, 14, 15, 24)

Note 0097 says that a node in the field can have `firewall.enabled:
false` (the value that `keel inspect` writes). The test added these 2
lines to each spec, then ran `keel spec apply --system`:

```yaml
firewall:
  enabled: false
```

| Node | State | Plan text |
| --- | --- | --- |
| each of the 8 nodes | **enforce** | `derived.firewall: enforce: each socket on an address that is not a loopback belongs to a unit of the manifests (decision 0097, B)` and `closes udp 0.0.0.0:12321 of webmin.service (miniserv.pl): the manifests declare its process, not this port` |

After each step in the pair and the trio, the replica showed
`Slave_IO_Running: Yes`, and etcd showed 3 voters.

### 1d. The sockets on a public address, per image and mode (logs 12, 27)

From `ss -Hlnptu`. Loopback sockets are left out.

| Image, mode | Sockets on an address that is not a loopback | Unit | In the `enforce` rule set |
| --- | --- | --- | --- |
| lnmp, lnpp, simple | TCP 22 (`sshd`, `systemd`), TCP 80 and 443 (`nginx`), TCP 12321 and UDP 12321 on IPv4 (`miniserv.pl`), UDP 68 and 546 (`dhcpcd`) | `ssh`, `nginx`, `webmin`, the DHCP client | yes, except UDP 12321 |
| core, simple | TCP 22, TCP and UDP 12321, UDP 68 and 546 | the same without nginx | yes, except UDP 12321 |
| lnmp, cloud_simple | the simple set, UDP 51820 (no process: the kernel), MariaDB 3306 on the wg0 address and on the VIP, Syncthing 22000 on the wg0 address, invite TCP 51821 on `%wg0` | the same, and `mariadb`, `syncthing`, the WireGuard port, `keel-mesh-invite` | yes |
| lnmp, cloud_advanced | the cloud_simple set, and etcd 2379, 2380 on the wg0 address | the same, and `etcd` | yes |
| core witness, cloud_advanced | TCP 22, TCP and UDP 12321, UDP 51820, etcd 2379, 2380, invite 51821 | `ssh`, `webmin`, `etcd` | yes, except UDP 12321 |

No client UDP socket and no random Syncthing port was seen on these
nodes.

**Result for item 1: FAIL.** The install part works as the pull request
says. The apply of a person never gives `enforce` on a published node,
because rule B does not look at the sockets when the spec has no
`firewall:` key. No published spec has one.

## Item 2: enforce is real (PASS)

`enforce` here came from the added `firewall: {enabled: false}` key of
item 1c, not from the published spec.

### 2a. Probes (logs 20-simple, 25)

From CT 9400 and from the VM, each address on IPv6 and IPv4, with the
throwaway listeners on TCP and UDP 9999 running:

| Port | lnmp (3 modes), lnpp (simple) | core (simple), witness |
| --- | --- | --- |
| TCP 9999, UDP 9999 (listener) | **timeout** | **timeout** |
| TCP 9998, UDP 9998 (no listener) | timeout | timeout |
| TCP 22, 12321 | open | open |
| TCP 80, 443 | open | timeout (no web server, not declared) |
| UDP 12321 | **timeout**, both families | timeout |

The first probe of 9430 in log 25 ran while the test had flushed the rule
set of 9430 for item 6. Its rows show an open node and do not count. The
probe of 9430 again, after the table was back, gave the results above.

### 2b. Network functions on 9401 in enforce (log 21-simple)

| Function | Command | Observed |
| --- | --- | --- |
| DHCPv4 and DHCPv6 rebind | `dhcpcd -n eth0` | `rebinding lease of 10.189.0.218`, `leased 10.189.0.218 for 7200 seconds`, `REPLY6 received from fe80::948a:2fff:fe30:ba4f` |
| Router advertisement | `ra.py 40` and `dhcpcd -n eth0` | `RA received from fe80::948a:2fff:fe30:ba4f M=1 O=1 router-lifetime=600s` |
| Neighbour discovery | `ip -6 neigh show dev eth0` | the router `REACHABLE`. IPv6 probes from CT 9400 answer |
| `apt-get update` | | `apt exit 0` |
| ACME-style request | `curl http://ADDR/.well-known/acme-challenge/ev307` from CT 9400 | `HTTP 404` on IPv6 and IPv4: nginx got the request |

### 2c. Reboot (logs 22-simple, 26, 33)

`keel-firewall.service` has `DefaultDependencies=no`,
`After=local-fs.target nftables.service`, `Wants=network-pre.target`
and `Before=network-pre.target`. `network-pre.target` is pulled in by
this unit itself (`Wants=`). `nftables.service` is enabled and active on
the images, and keel's unit runs after it.

`journalctl -b -o short-monotonic` after `pct reboot 9401`:

```
[372633.826377] Starting keel-firewall.service
[372633.867388] Finished keel-firewall.service
[372633.911441] Reached target network-pre.target
[372633.919315] Starting networking.service
[372635.832674] dhcpcd[179]: eth0: leased 10.189.0.218 for 7200 seconds
[372635.991308] Starting ssh.service
```

The table loaded 2 s before the first lease and before sshd. On 9431
(`cloud_simple` replica) the table also loaded before
`network-pre.target` and before `wg-quick@wg0.service`. After the
reboot the probes of 2a gave the same results on 9401. On 9431,
replication ran, 0 s behind, and new Syncthing sessions came in on wg0.

As far as the journal shows, no window is open: the table is in place
before the interfaces get an address. The test did not capture packets
during the boot.

## Item 3: the neighbour path (PASS, IPv6)

CT 9400 is on the same bridge and is not a mesh member. It added a
`/128` route for each wg0 address and each VIP through the link-local
address of the node on `vmbr1`, then probed (log 30-neighbour). The overlay has
IPv6 addresses only, so there is no IPv4 probe of this path.

| Target | 3306 | 2379 | 2380 | 22000 TCP | 22000 UDP | 51821 | 22 (reference) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cloud_advanced primary 9420 wg0 | timeout | timeout | timeout | timeout | timeout | timeout | open |
| cloud_advanced VIP (on 9420) | timeout | | | | | | open |
| cloud_advanced replica 9421 wg0 | timeout | timeout | timeout | timeout | timeout | timeout | open |
| cloud_advanced witness 9422 wg0 | | timeout | timeout | | | timeout | open |
| cloud_simple primary 9430 wg0 | timeout | | | timeout | timeout | timeout | open |
| cloud_simple VIP (on 9430) | timeout | | | | | | open |
| cloud_simple replica 9431 wg0 | timeout | | | timeout | timeout | timeout | open |

**Control (log 31).** On 9421, `nft delete table inet keel`, then the
same probe: 3306 `open`, 2379 `open`, 2380 `open`, 22000 `open`, 51821
`refused`. `systemctl restart keel-firewall.service` loaded the table
again, and `keel firewall check` said `table inet keel is the one
/etc/keel/firewall/keel-manifest.nft says`.

**The mesh on wg0 in enforce (logs 32, 33).**

| Check | Observed |
| --- | --- |
| Replication | a row written on 9420 arrived on 9421. `Master_Host: fd4f:478b:3701::1`, `Slave_IO_Running: Yes`, 0 s behind. The `cloud_simple` replica the same |
| etcd | `etcd: 3 voter(s)`, each `healthy` |
| Syncthing | established sessions on 22000 between the wg0 addresses, in both pairs |
| Failover | `pct shutdown 9420`. The VIP was on 9421 after 32 s. `@@read_only` 0 on 9421. A row written on 9421 |
| The old primary returns | `pct start 9420`. The table loaded at boot (`policy drop`). The journal: `rejoined: no errant GTID, replicating from [fd4f:478b:3701::4e11]:3306 over TLS`. Both rows on 9420. etcd 3 healthy voters |

The return made new connections on wg0 (etcd, MariaDB over TLS) while
both nodes were in `enforce`. The VIP stayed on 9421 after the return.

## Item 4: the edge cases of rule B (PASS, with the key)

Each case below had the `firewall:` key of item 1c in the spec. Without
the key, rule B never runs (item 1).

| Case | Node | Observed |
| --- | --- | --- |
| A listener started by hand before the apply | 9402 | `report: enforce waits, because these sockets belong to no unit of the manifests: udp *:9999 of ev-udp.service (python3); tcp *:9999 of ev-tcp.service (python3)` |
| The listener stopped, apply again | 9402 | `enforce: each socket on an address that is not a loopback belongs to a unit of the manifests (decision 0097, B)`, `policy drop` |
| The unattended mesh apply on a node in report | 9421 | `derived.firewall: report: only an apply a person runs (keel spec apply --system) moves this node to enforce`, file `# state: report` (log 22-adv) |
| The unattended mesh apply with `state: enforce` in the spec | 9421 | `report until an apply a person runs: the spec says enforce, and keel mesh never begins enforcement (decision 0097)`. Then `keel spec apply --system` gave `enforce` (log 28) |
| The unattended mesh apply on a node in enforce | 9422 | `enforce, as keel's file already says`, `policy drop` (log 34) |
| The apply of a person with the key removed again | 9401 | `enforce, as keel's file already says; firewall.state: report goes back` (log 35) |

How the unattended apply was made. With stable members, `keel mesh sync`
applies nothing. The repair path of keel#96 applies when the spec names
a peer that wg0 lacks. The test removed one peer from wg0 with `wg set
wg0 peer KEY remove` (the key in a shell variable, never printed). Then
it ran `systemctl start keel-mesh-sync.service`. On a pair this does not
work: with its only peer gone, no member answers, and sync changes
nothing (log 42-cs).

**Observed, not caused by this pull request as far as the test shows:**
in each repair run, the mesh apply ran, but `network.overlay: unchanged
(/etc/wireguard/wg0.conf says what the spec declares)` did not put the
peer back. Sync then said `this node's overlay did not come up (apply
exited 0); the spec is put back as it was` and exited 16. The test put
the peer back by hand with `wg syncconf wg0 <(wg-quick strip wg0)` and
`wg set wg0 private-key /etc/wireguard/wg0.key`. A first try with
`wg syncconf` alone removed the private key of the interface (the
configuration sets it in `PostUp`). The replica lost replication for
about 1 min until the key was set again.

## Item 5: the SSH guard and a broken file (PASS)

On 9403 (core, `enforce`), with a console path through `pct exec` (log 37):

| Case | Observed |
| --- | --- |
| `Port 22` and `Port 2222` in `sshd_config.d`, sshd restarted, apply | `SSH stays open: tcp 22, 2222, the ports sshd listens on (sshd -T)`, rule `tcp dport { 22, 2222, 12321 } accept`. From CT 9400: 22 `open`, 2222 `open`, 9998 `timeout`, both families |
| `Port 2222` only | `SSH stays open: tcp 2222`. From CT 9400: 2222 `open`, 22 `refused` (no listener, the port stays declared) |
| A bad directive in `sshd_config.d` (`sshd -T` exit 255), sshd not restarted, apply | no refusal: keel read the files and found 2222: `SSH stays open: tcp 2222, the ports sshd listens on (/etc/ssh/sshd_config)`. The table did not change |
| The same, and `Include /etc/ssh/ev307-extra.conf` in `sshd_config` | `refused: the ports sshd listens on cannot be determined (sshd -T did not answer, and /etc/ssh/sshd_config says Include /etc/ssh/ev307-extra.conf, which keel does not follow): no firewall is applied ... nothing is written or loaded`, apply exit 16. Table digest the same before and after. 2222 still `open` |

The fallback to the files is the design of `ports_from_files()` in
`keel/system/fwstate.py`. keel refuses only when `sshd -T` fails and the
files cannot be read, or name an `Include` outside
`sshd_config.d`.

**A broken rule file (log 39).** A line that nft cannot read was added
after the header of `keel-manifest.nft` on 9403:

| Step | Observed |
| --- | --- |
| `nft -c -f` | `syntax error, unexpected !` |
| `systemctl restart keel-firewall.service` | exit 1, `ActiveState=failed`. The table digest is the same before and after: the old table stays, `policy drop`. `systemctl is-system-running`: `degraded`. TCP 22 `open` from CT 9400 |
| `keel firewall check` | exit 0: `table inet keel is the one /etc/keel/firewall/keel-manifest.nft says`. It compares the digest comment only, so Monit would not report a broken file while the old table is loaded |
| `keel diff` | `derived.firewall: drift (... observed a file that differs from it)` |
| `pct reboot` with the broken file | unit `failed`, no `inet keel`, node `degraded`. Open: TCP 9998 `refused`, UDP 12321 `reply` on IPv4. TCP 22 `open` |
| `keel spec apply --system` | the file written again and loaded, `policy drop`, 9998 `timeout` |

The node is open after a reboot with a broken file. That is the choice
of note 0097, section 4. A failed load of `keel spec apply` itself was
not made: the test found no way to make keel render a file that nft
refuses.

**Result for item 5: PASS.** Gap: note 0097, section D, item 9 says
"Monit reports" a broken file. `keel firewall check` does not see it
while the old table is loaded.

## Item 6: the loss of the table (FAIL on the published spec)

Monit runs `set daemon 120`. keel writes the check `keel-firewall` into
`/etc/keel/monit/keel-manifest.conf` on each node.

**With the published spec (logs 36, 36-probe).** No published spec has a
`monitor:` section. `keel diff` says `derived.monit.included: not
compared (no monitor section: the include is left as an earlier apply
set it)`. `/etc/monit/conf.d` and `/etc/monit/conf-enabled` hold no
keel file. Thus Monit does not run the check.

| Step on 9401 | Observed |
| --- | --- |
| `systemctl restart nftables.service` at 18:39:13 | tables: `inet filter` only |
| 501 s later | still no `inet keel`. `keel firewall check`: `table inet keel is not loaded ...`, exit 14. `monit.log` has no `keel-firewall` line |
| TCP 9999 from CT 9400 | `18:39:14 open`, and open to the end of the probe at 540 s |

On 9430 (`cloud_simple`, published spec), `nft flush ruleset` removed
`inet keel`, `ip crowdsec` and `ip6 crowdsec6`. 180 s later no table was
back. `systemctl restart keel-firewall.service
crowdsec-firewall-bouncer.service` brought all 3 back (log 38).

**With `monitor.enabled: true` and `notify: {email: true}` added to the
spec of 9401 (logs 36b, 36c).** The apply wrote `include
/etc/keel/monit/keel-manifest.conf from /etc/monit/conf.d`.

| Loss | Table back after | TCP 9999 open from CT 9400 | Monit log |
| --- | --- | --- | --- |
| `systemctl restart nftables.service` at 18:49:06 | **225 s** (18:52:51) | 18:49:07 to 18:52:51 | `18:50:49 warning 'keel-firewall' status failed (14)`, `18:52:50 ... trying to restart`, `restart: '/usr/bin/systemctl restart keel-firewall.service'` |
| `nft flush ruleset` at 18:53:39 | **73 s** (18:54:52) | 18:53:40 to 18:54:53 | `18:54:52 'keel-firewall' trying to restart` |

Plainly: while the table is lost, the node is fully open, both families,
every port. With the monitor on, the table comes back within about 2
Monit cycles (up to 225 s seen). On a published node, where the spec has
no `monitor:` section, nothing brings it back until a reboot or an apply.
keel does not restore the CrowdSec tables after a flush.

**Result for item 6: FAIL** on the published spec. PASS for the
mechanism when the monitor is enabled.

## Item 7: a new node (FAIL)

No image was built. CT 9404 was made from the lnmp 19.0-7 template with
the instance description. Before its first start, a link
`/etc/systemd/system/inithooks.service -> /dev/null` (owner 100000) was
put in its root file system (log 30-new-node). The CT started with no first boot
(`no-inithooks-log`, `masked`). Then `dpkg -i keel_0.23.99_all.deb`, the
link removed, `systemctl daemon-reload`, `pct reboot 9404`.

| Check | Observed |
| --- | --- |
| First boot | `completed: 1`, no error, `running`, keel 0.23.99 |
| The first-boot apply (`/var/log/inithooks.log`) | `[10keel-system] derived.firewall: report: the sockets cannot be listed (not the live system: no socket is seen), so enforce waits` |
| The file, the table | `# state: report`, `policy accept`, `keel-report` counter |
| `keel diff` | `enforce would close udp 0.0.0.0:12321 of webmin.service (miniserv.pl)` only |

At this first boot, no file existed before the network came up, so the
table loaded after the network. That part is expected until the images
write the rule set with `--root` (a follow-up of the pull request).

**Result for item 7: FAIL**, for the cause of item 1.

## Item 8: unprivileged containers, CrowdSec, the init fence (PASS)

| Check | Observed |
| --- | --- |
| `nft -c` and `nft -f` in an unprivileged container | each apply on the 10 CTs: `checked by nft -c as a copy first ...: done`, `load it in one transaction ...: done` |
| CrowdSec tables next to `inet keel` | `inet filter`, `ip crowdsec`, `ip6 crowdsec6`, `inet keel` on each cloud node |
| CrowdSec ban on 9430 in enforce | `cscli decisions add --ip` for both addresses of CT 9400. From CT 9400: IPv6 TCP 22 and 80 `error:OSError:113` (no route to host), IPv4 `timeout`. After `cscli decisions delete`: `open` (log 38) |
| `iptables` alternative | `/usr/sbin/iptables-legacy` on the images |
| Init fence, simple 9402 and cloud_advanced 9420 | `systemctl enable turnkey-init-fence`, apply: rule `ct status dnat tcp dport { 60080, 60443 } accept`. Fence started: 4 `REDIRECT` rules in the legacy nat table. From CT 9400: `GET http://ADDR/` and `https://ADDR/` (9402) or `https://ADDR:12321/` (9420) give `200`, 2943 bytes, the size of the fence `index.html`. Direct TCP 60080 and 60443: `timeout`. Both families (logs 40-fence, 41-fence) |
| Fence stopped and disabled, apply | the `dnat` rule removed. Replication of 9420 still `Yes` |

**Finding: a running fence keeps rule B in report.** On 9402, with the
fence running and the node in `report`, the apply said: `report:
enforce waits, because these sockets belong to no unit of the manifests:
tcp *:60080 of turnkey-init-fence.service (simplehttpd.py); tcp *:60443
of turnkey-init-fence.service (simplehttpd.py)`. In report, the plan
also said `enforce would close tcp *:60080`, but the `enforce` rule set
accepts redirected packets to that port. With the fence stopped and
disabled, the next apply gave `enforce`. Thus on an interactive first
boot, where the fence runs until the first login, rule B keeps the node
in `report` (when item 1 is fixed).

## Other observations

- The first apply on a `simple` lnmp node restarted `mariadb.service`
  (`database.server: restart the server, which is the only way these
  take effect`), because it wrote
  `/etc/mysql/mariadb.conf.d/99-keel-database.cnf` for the first time.
  This step is not part of the firewall.
- `keel diff` warns on each node: `/etc/iptables/rules.v4 and
  /etc/iptables/rules.v6 are there: do not install iptables-persistent`.
- After the upgrade and before the first apply, `keel diff` exits 14
  (`derived.firewall` drift), as the pull request says.

## What was not tested

- The ISO in a VM, under BIOS and UEFI (section D, item 11).
- The release topology: 2 sites with the netem profile of 250 ms. All
  nodes were on one bridge of one VM.
- Image builds: the rule set written with `--root`, `nftables.service`
  disabled, the mode screen that writes `firewall.state: enforce`.
- The other 10 images (section D, items 2 and 13).
- `keel mesh invite` and `keel mesh join` with the invite port, and its
  close after the expiry (section D, item 6).
- SLAAC: the router advertisement of the test network has no prefix
  with `A=1`. A DHCP lease that expires by time: the test forced a
  rebind.
- The init fence with `iptables-nft`, and a container whose nat table is
  not available.
- A pair under writes during the upgrade (section D, item 14). The
  upgrade ran with no load. No acknowledged write was checked under load.
- A failed load during `keel spec apply` (item 5).
- Packet capture during the boot (item 2c).
- A failover by a hard stop. The test used `pct shutdown`.

## What this means for 0097 and pull request 307

These are proposals only. No note and no code is changed by this file.

1. Rule B cannot run on a published node. `keel/system/appstate.py:120`
   observes the sockets, `sshd -T`, `ssh.socket` and the loaded digest
   only when the spec has a `firewall:` key. Note 0097 says that an
   absent key reads as `report` and that rule B then decides. Thus the
   condition must not depend on the key.
2. The Monit check of section 4 runs only where the spec has an enabled
   `monitor:` section. No published spec has one. Section 4 promises
   the restore on every node.
3. `keel firewall check` compares the digest comment only. A broken file
   with an intact comment passes. Section D, item 9 expects Monit to
   report it.
4. A running init fence keeps rule B in `report`. Section 1 of rule B
   lists the fence ports as known only in the rule set, not in
   `keel.system.listeners`.
5. The keel#96 repair did not put a removed peer back in this test.
   This is separate from 0097.

## Logs

The logs and scripts are kept on the maintainer's workstation in
`repos/evidence-0097-2026-11-23/pr307/`. The runner records
(`runner-adv/`, `runner-cs/`) hold console transcripts and are not
copied here.

| Log | Content |
| --- | --- |
| `00-vm-baseline`, `99-vm-after`, `99-vm-diff`, `99-cleanup` | the VM before and after, cleanup |
| `01-images`, `02-create-simple`, `03-firstboot-simple`, `04-push` | templates, simple CTs, first boot, push |
| `10-simple-upgrade` to `15-rule-b-9403` | simple: upgrade, dry run, apply, rule B |
| `20-simple-enforce-probe`, `21-simple-netfunc`, `22-simple-reboot` | simple: enforce probes, network functions, reboot |
| `20-adv-runner`, `21-adv-upgrade`, `22-adv-mesh-unattended` | cloud_advanced: commissioning, upgrade, mesh apply |
| `23-cloud-attended-nokey`, `24-cloud-attended-key`, `25-cloud-enforce-probe`, `26-cloud-reboot`, `27-cloud-sockets`, `28-adv-mesh-declared-enforce` | cloud nodes: applies, probes, reboot, sockets |
| `30-neighbour-enforce`, `31-neighbour-control`, `32-adv-wg0-enforce`, `33-adv-failover`, `34-adv-mesh-on-enforce`, `35-simple-kept` | items 3 and 4 |
| `30-new-node` | item 7 |
| `36-table-loss*`, `36b-*`, `36c-*`, `37-ssh-guard`, `38-crowdsec`, `39-broken-file`, `40-fence`, `41-fence-adv` | items 5, 6, 8 |
| `40-cs-runner`, `41-cs-upgrade`, `42-cs-mesh-unattended` | cloud_simple: commissioning, upgrade, mesh apply |
| `90-secret-scan` | secret scan |

Secret handling: the VM made the secrets of the `simple` nodes inside
the root file system of each stopped CT, and no command printed them.
WireGuard keys were kept in shell variables and never printed. Each log
was scrubbed of base64 keys. The scan of log 90 found no key, no
invitation, no private key, no password and no token in the logs and
scripts.

## Cleanup

CTs 9400 to 9404, 9420 to 9422, 9430 and 9431 were destroyed with
`pct destroy --purge`. The templates `ev307-*` and `/root/ev307` were
removed. The core and Nextcloud templates that were on the VM before the
test were not touched. The Proxmox firewall was not changed:
`pve-firewall status` is `disabled/running`, and `/etc/pve/firewall` is
empty, as before. A diff of the VM state before and after
(`pve-firewall status`, the files of `/etc/pve/firewall` and of the
node, `iptables-save`, `ip6tables-save`, `ebtables-save`, `nft list
ruleset`, the `bridge-nf-call` sysctls, `pct list`, the links), without
packet counters and time stamps, is empty: `diff_exit=0 lines=0`
(log 99).
