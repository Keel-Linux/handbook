# Evidence: the Proxmox guest firewall as a stopgap, and the firewall of a published cloud advanced node (decision 0097)

Date: 2026-11-23. Site: BR1, the Keel test VM (nested Proxmox VE, VM 143).
Status: draft. For decision 0097, work item 1 and the open point
"Whether a published `cloud_advanced` node is open".

## Question

Decision 0097 (proposed) left 2 points that were read in code only:

- **Test 1.** Does the Proxmox VE firewall on the guest close a published
  node in `simple` mode? Which levels must be on? What does it do to
  DHCP, router advertisements and neighbour discovery? Does it survive a
  reboot? The same on a `cloud_simple` pair.
- **Test 2.** Is a published node in `cloud_advanced` open? Do the
  mesh-only ports answer on the public address of the node?

Each result says if it was **tested** on a node or **read in code**.

## Machines and images

The test VM is `keel-pve-br1`: Proxmox VE 9.2.31, kernel 7.0.14-30-pve,
`pve-firewall` 6.0.8. `proxmox-firewall` 1.2.5 (the nftables back end)
is installed, but the test used the default iptables back end. Nothing
set `nftables: 1`.

All CTs are unprivileged, `nesting=1`, 2 cores, 2 GiB, rootfs on
`local`, on the internal bridge `vmbr1` of the VM. Each CT got its
addresses from the dnsmasq of the VM on `vmbr1`: DHCPv4, and DHCPv6
with a `/128` address (`pct` `ip=dhcp,ip6=dhcp`).

| CT | Image | Mode | How it was made |
|---|---|---|---|
| 9410 | lnmp 19.0-7 | simple | instance description before the first boot (method of the 0094 test) |
| 9411 | core 19.0-13 | simple | the same. The probe node: not a mesh member, on the same bridge |
| 9420, 9421, 9422 | lnmp 19.0-7, lnmp 19.0-7, core 19.0-13 | cloud_advanced: primary, replica, witness | `keel-commission --pass cloud_advanced`, the mode screen answered on the console |
| 9430, 9431 | lnmp 19.0-7 | cloud_simple: primary, replica | `keel-commission --pass cloud_simple` |

`keel-commission` is `bin/keel-commission` of `Keel-Linux/.github` at
`f75cfec`. The contract is `tests/commission.yaml` of `keel-lnmp` at tag
`19.0-7` (`d3db52a`), with its `commission-core.yaml` for the witness.
The runner answers the screens of the first boot as an operator does. No
instance description was put in these nodes. Thus their spec is the spec
that the mode screen writes.

The templates come from `https://mirror.keellinux.org/images/`. The
mirror has no `keel-images-keyring.asc` (HTTP 404). The keyring came
from `keys/keel-images-keyring.asc` of the `apt` repository at
`a22cde2`, sha256 `437ac43a7b8d25241c390835dcf38eeef3ed2713430404c780a25185da1ed35c`,
fingerprint `E71DB9C3CA6AC18075395CC3ED3A709C4F3E2F3C`. For each
template, `sqv` on the `.sha512.asc` exited 0 and printed the images key.
It also printed `Missing key 03041024F4B2C0C2F42DDDEA04906EAB77513310`
for a second signature. `sha512sum -c` passed (log 01).

| Template | sha256 |
|---|---|
| `debian-13-keel-lnmp_19.0-7_amd64.tar.zst` | `66aa6fb14aa69a80a73211035daadc6480d20e1e72933a9372051f30405b5319` |
| `debian-13-keel-core_19.0-13_amd64.tar.zst` | `e32029debdf15a852084a08f24d8187dd526bd3ceebc3cc1e6512a1bf7fb4401` |

Versions on the images: `keel` 0.23.96, `keel-core` 0.1.4, `confconsole`
2.2.3+keel24.

### The probes

- `probe.py` opens a TCP connection, or sends one UDP datagram and waits
  for an answer. It prints `open`, `refused` or `timeout` for TCP, and
  `reply`, `refused` (ICMP port unreachable) or `timeout` for UDP.
- On the target, 2 throwaway listeners: HTTP on TCP 9999 and a UDP echo
  on UDP 9999. No list names port 9999.
- Port 9998 has no listener. It is the control: without a filter it is
  `refused`, behind a drop it is `timeout`.
- Each probe ran on the IPv6 and the IPv4 address of the target, from 2
  sources:
  - **CT 9411**, a second container on `vmbr1`. The path is CT 9411,
    `vmbr1`, the target. With `firewall=1` on the target's network device,
    the path also goes through `fwpr`, `fwln` and `fwbr` of the target.
  - **The VM itself** (address on `vmbr1`). The path goes through the same
    `fwbr` hop.

  Both sources were filtered by the guest firewall (results below). Thus
  a probe from the Proxmox host to a guest on the same bridge is a valid
  probe for the guest firewall on this platform.

Secret handling: the VM made the secrets of 9410 and 9411 inside the file
system of each stopped CT, and no command printed them. The runner made
the secrets of the cloud nodes and wrote none to its record. The runner
records, with the console transcripts, stay on the
workstation and are not part of this file (log 90).

## Results, Test 1: the Proxmox guest firewall as a stopgap

### T1.0 The published node (tested, logs 10, 11, 12)

CT 9410, lnmp 19.0-7 in `simple`, as published. The facts are the facts
of the 0094 test: `keel-firewall.service` skipped, no
`/etc/keel/firewall/`, the empty `inet filter` table, legacy `INPUT
ACCEPT`.

| Port | From CT 9411 and from the VM, IPv6 | IPv4 |
|---|---|---|
| TCP 9999, UDP 9999 (undeclared) | **open**, **reply** | **open**, **reply** |
| TCP 22, 80, 443, 12321 | open | open |
| UDP 12321 (`miniserv.pl`) | refused: it listens on `0.0.0.0` only | **reply** |
| TCP 9998, UDP 9998 (no listener) | refused | refused |

Thus a UDP port of the node also answers from outside, and Webmin's UDP
12321 answers on IPv4. `apt-get update` passed. The mirror
`mirror.keellinux.org` answered on IPv6. It did not answer on IPv4 from
this VM, also before any change (log 12).

### T1.1 The state of the VM before the test (log 00)

`pve-firewall status`: `disabled/running`. No `cluster.fw`, no
`host.fw`, no guest `.fw`. The `bridge-nf-call` sysctls were 0. The VM
has its own nftables table `inet keel_test_fw` with a `forward` chain,
`policy drop`. It accepts `vmbr1` to `vmbr1`, and `vmbr1` to and from
`vmbr0` for the test prefixes.

The SSH source of the operator is not in the network of `vmbr0`. Thus the
default management rules of Proxmox VE would not cover it. These
precautions came before the datacenter switch:

1. `host.fw` with `enable: 0`, so the node firewall of the VM stays off.
2. `cluster.fw` with `policy_in: ACCEPT` and `IN ACCEPT` rules for TCP 22
   and 8006.
3. A rollback script, run once while the firewall was off, to prove it.
4. A `systemd-run --on-active=600` timer for the rollback.
5. After the switch: a new SSH connection and HTTP 200 on port 8006.
   Only then the timer was stopped.

### T1.2 Which levels must be on (tested, logs 30 to 37)

The guest file `/etc/pve/firewall/9410.fw` of the stopgap is in the
procedure below. The 4 levels were changed one at a time. "Rules" is the
number of lines that name `veth9410i0` in `iptables-save`.

| Step | Datacenter `enable` | Node `host.fw` `enable` | NIC `firewall=1` | Guest `.fw` `enable` | Rules | TCP and UDP 9999 | TCP 22, 80, 443 |
|---|---|---|---|---|---|---|---|
| L0 | 0 | absent | 1 | 1 | 0 | open, reply | open |
| L1 | 1 | 0 | 1 | 0 | 0 | **all traffic dropped, also 22 and ping** | dropped |
| L1b | 1 | 0 | 1 | 0, and the VM accepts the `fwbr` hop | 0 | open, reply | open |
| L2 | 1 | 0 | 1 | 1 | 20 | **timeout** | **open** |
| L3 | 1 | 0 | 0 | 1 | 0 | open, reply | open |

**Result for T1.2: 3 levels must be on: the datacenter, the network
device (`firewall=1`) and the guest file (`enable: 1`). The node level is
not necessary.** The node firewall stayed off for the whole test, and the
guest rules worked.

The datacenter switch set the sysctls `bridge-nf-call-iptables` and
`bridge-nf-call-ip6tables` from 0 to 1. These sysctls apply to every
bridge of the host. Then each bridged frame also goes through the
`forward` hook of iptables and nftables. With
`firewall=1`, the guest is behind its own bridge `fwbr9410i0`. In L1 the
`forward` chain of the VM's `inet keel_test_fw` saw `iifname` and
`oifname` `fwbr9410i0`, matched no rule and dropped the frame. All
traffic to the guest stopped, also neighbour discovery (IPv6 probes got
`EHOSTUNREACH`). The test added 1 rule, `iifname "fwbr*" oifname
"fwbr*" accept` (L1b), and removed it at the end. This is a fact of this
test VM. The guests without `firewall=1` (9411, and the pair while the
runner checked it) kept their traffic, because `keel_test_fw` accepts
`vmbr1` to `vmbr1`. Inference, not tested: on a host whose `forward`
chain has a drop policy and no such rule, the switch can also cut the
traffic of guests that have no firewall.

### T1.3 The stopgap (tested, logs 34, 35, 36, 39)

With L2, from CT 9411 and from the VM, on IPv6 and IPv4:

| Port | Before | With the stopgap |
|---|---|---|
| TCP 9999 | open | **timeout** |
| UDP 9999 | reply | **timeout** |
| UDP 12321 (IPv4) | reply | **timeout** |
| TCP 9998, UDP 9998 (no listener) | refused | timeout |
| TCP 22, 80, 443, 12321 | open | **open** |
| ping, IPv6 and IPv4 | 0% loss | 0% loss |

The probe from the VM itself was filtered in the same way. Thus the
firewall of Proxmox VE also filters the host's own traffic to a guest on
the same bridge.

Network functions behind the stopgap:

| Function | Result |
|---|---|
| DHCPv4 lease, DHCPv6 address | kept |
| `dhcpcd -n` (rebind of both leases) | `leased 10.189.0.145 for 7200 seconds`, `REPLY6 received` |
| Router advertisement | received. One captured RA: `M=1 O=1`, prefix `/120` with `A=0` |
| Default routes, IPv6 and IPv4 | kept |
| Neighbour discovery | works: the `ndp: 1` rules accept ICMPv6 types 133 to 136 |
| `apt-get update` (Debian and `archive.keellinux.org`) | exit 0 |
| `pct reboot` | the node came back with the same addresses, the rules applied again (20 lines), and each probe gave the same result |

The option `dhcp` is 0 by default for a guest. With `dhcp: 0`, a rebind
lost the IPv4 address at once (`DHCP lease expired`, `deleting default
route`). DHCPv6 failed to confirm its address. `dhcp: 1` and a new
rebind brought both back (log 38). A node with a static address does not
need the option.

SLAAC was not tested: the router advertisement of the test network has
no prefix with `A=1`.

### T1.4 A cloud_simple pair (tested, logs 40 to 46)

The runner made a `cloud_simple` pair, primary 9430 and replica 9431,
with the mode screen. Each check of the contract passed (log 40). The
spec has no `firewall:` key. The pair has the same exposure as the
`cloud_advanced` nodes (T2.4 and T2.5): an undeclared port answers, and
MariaDB 3306 and Syncthing 22000 answer to a neighbour on the same link
through the wg0 address and the VIP (log 42).

The stopgap went on both nodes, with one more rule: `IN ACCEPT -p udp
-dport 51820`, the WireGuard port. Results (logs 44 to 46):

| Check | Result |
|---|---|
| TCP and UDP 9999, UDP 12321, from CT 9411 | timeout, both families, both nodes |
| TCP 22, 80, 443, 12321 | open |
| TCP 3306, 22000 on the wg0 address and the VIP, from a neighbour on the same link | **timeout**: the stopgap also closes this path |
| A row written on the primary | arrived on the replica. `Slave_IO_Running: Yes`, `Slave_SQL_Running: Yes`, 0 s behind |
| Syncthing | the replica's peer is `connected: true` |
| `pct reboot` of the replica | a new WireGuard handshake after the reboot, `peers: 1`, replication runs, a new row arrived |

The guest rules see only the outer UDP packets of WireGuard. The mesh
ports inside the tunnel need no rule. A pair whose guest file does not
accept UDP 51820 was not tested.

## Procedure: the Proxmox VE firewall as a stopgap

For one Keel node in a Proxmox VE container, until a fixed `keel`
writes the rule set of 0097. Each step says if this test did it.

1. **Read the state first.** Run `pve-firewall status`. Read
   `/etc/pve/firewall/cluster.fw` and `/etc/pve/nodes/NODE/host.fw`. Read
   `nft list ruleset` and `iptables-save` of the host. Find each
   `forward` chain with a drop policy. **Tested.**
2. **Keep access to the host.** If the datacenter firewall is off, the
   switch also turns on the firewall of each node. Its input policy is
   `DROP`, and the management rules accept only the local network of the
   node. Read in code: `PVE/Firewall.pm` of `pve-firewall` 6.0.8, lines
   3228 and 4508 to 4518. Thus, before the switch, do one of these:
   - Write `enable: 0` in `host.fw`. The node is then not filtered.
     **Tested.**
   - Or write `IN ACCEPT` rules for TCP 22 and 8006 from the address that
     you use. **Tested together with the first item, not alone.**

   Then make a timer that turns the firewall off again after 10 min.
   **The rollback script was tested by a direct run. The timer was armed
   and stopped each time, and it never fired.**
3. **Write the guest file** `/etc/pve/firewall/VMID.fw`. **Tested.**

   ```
   [OPTIONS]
   enable: 1
   policy_in: DROP
   policy_out: ACCEPT
   dhcp: 1
   ndp: 1
   radv: 0
   macfilter: 1
   ipfilter: 0
   log_level_in: nolog

   [RULES]
   IN ACCEPT -p tcp -dport 22 -log nolog
   IN ACCEPT -p tcp -dport 80 -log nolog
   IN ACCEPT -p tcp -dport 443 -log nolog
   IN ACCEPT -p tcp -dport 12321 -log nolog
   IN ACCEPT -p ipv6-icmp -log nolog
   IN Ping(ACCEPT) -log nolog
   ```

   - Keep `dhcp: 1` if the node gets an address by DHCP. With `dhcp: 0`,
     the node loses its address at the next rebind. **Tested.**
   - Port 80 and 443 only for an image with a web server. The witness
     (core) needs 22 and 12321. **Not tested on the witness.**
   - For a node of a `cloud_simple` or `cloud_advanced` pair, add
     `IN ACCEPT -p udp -dport 51820 -log nolog`. **Tested on a
     `cloud_simple` pair. Not tested in `cloud_advanced`.**
   - Add a port of your own service the same way.
4. **Set `firewall=1` on the network device** of the guest, and keep its
   `hwaddr`: `pct set VMID --net0 '<the current net0>,firewall=1'`. A
   running container gets the change at once. **Tested.**
5. **Turn on the datacenter firewall:** `enable: 1` in `cluster.fw`.
   **Tested.**

   Caution: the switch sends the frames of every bridge of the host
   through the `forward` hook. If the host has a `forward` chain with a
   drop policy, add an accept for the bridged traffic first. If you do
   not, the guest loses all its traffic. **Tested for the `fwbr*` hop of
   the guest. For the other bridges: inference, not tested.**
6. **Check from a second machine:** an undeclared port gives a timeout.
   Port 22 and the application ports answer. The node keeps its
   addresses. `apt-get update` works. **Tested.**
7. **Remove the timer of step 2** when you have proved access to the
   host. **Tested.**
8. **Reboot the guest once** and do step 6 again. **Tested: addresses
   and probes. `apt-get update` was not repeated after the reboot.**

The stopgap does not replace the fix of 0097. It filters on the host,
so a copy of the guest to another host without the same files is open
again.

## Results, Test 2: a published node in cloud advanced

### T2.1 The setup (tested, logs 20, 24)

The runner made the trio with the mode screen of 0076: `CC` (cloud
advanced), then the role (`P`, `R`, `W`), then the invites. Each check of
the contract passed, `keel-commission` exit 0 (log 20): mesh with 2
peers on each node, etcd with 3 healthy voters, the VIP on 1 node, a row
written on the primary arrived on the replica, the replica is read-only,
Syncthing `sendonly` and `receiveonly`, `keel vip promote` and the return,
no failed unit. Thus the setup is a working `cloud_advanced` installation
as an operator makes it.

### T2.2 The firewall facts (tested, logs 21, 24)

The same on the primary 9420, the replica 9421 and the witness 9422, after
the first boot and again after the promote and the return:

| Fact | Result |
|---|---|
| `installation.mode` in `/etc/keel/instance.yaml` | `cloud_advanced` |
| `firewall:` key in the spec | **absent**. No file under `/etc/keel/` has a line `firewall:` |
| `keel inspect` | `firewall: {enabled: false}` |
| `/etc/keel/firewall/keel-manifest.nft` | **absent**. The directory does not exist |
| `keel-firewall.service` | enabled, `inactive (dead)`, `ConditionResult=no`: skipped, `ConditionPathExists=/etc/keel/firewall/keel-manifest.nft` |
| `nft list tables` | `inet filter` (the empty Debian table, policy accept), `ip crowdsec`, `ip6 crowdsec6` |
| legacy iptables | `-P INPUT ACCEPT` on IPv4 and IPv6 |

**Result for T2.2: the mode screen writes no `firewall:` key, keel writes
no rule file, and nothing filters input.** This confirms on a running
node what 0097 read in code.

### T2.3 Listeners (tested, log 21)

| Listener | Primary, replica | Witness |
|---|---|---|
| TCP 22, 12321 on all addresses. UDP 12321 on all IPv4 addresses | yes | yes |
| TCP 80, 443 on all addresses (nginx) | yes | no |
| UDP 51820 on all addresses (WireGuard) | yes | yes |
| MariaDB TCP 3306 on the wg0 address, and on the VIP | yes | no |
| etcd TCP 2379, 2380 on the wg0 address. 2379 and 2381 on `::1` | yes | yes |
| Syncthing TCP 22000 on the wg0 address. GUI 8384 on `127.0.0.1` | yes | no |
| Invite port TCP 51821, bound to the wg0 address with `%wg0` | yes | yes |
| MariaDB on `127.0.0.1` and `::1`, Postfix 25, CrowdSec 6060 and 8080, Anubis 8923 | loopback only | Postfix, CrowdSec: loopback only |

No Syncthing listener on a random port: the node has an overlay address.

### T2.4 Probes on the public address (tested, log 22)

From CT 9411, not a mesh member, to the IPv6 and IPv4 address of each
node on `vmbr1`. A throwaway listener on TCP and UDP 9999 ran on the
primary and the replica.

| Port | Primary, replica | Witness |
|---|---|---|
| TCP 9999 (undeclared) | **open**, both families | no listener: refused |
| UDP 9999 (undeclared) | **reply**, both families | no listener: refused |
| TCP 22, 12321 | open | open |
| TCP 80, 443 | open | refused |
| UDP 12321 | **reply** on IPv4, refused on IPv6 | the same |
| TCP 2379, 2380, 2381, 3306, 22000, 51821, 8384, 6060, 8080, 8923, 25 | refused | refused |
| UDP 22000 | refused | refused |
| UDP 51820 | timeout (WireGuard does not answer a datagram that is not a handshake) | the same |

**Result for T2.4: the node is open.** An undeclared TCP and UDP port
answers on both families. No mesh-only port answers on the public
address. The reason is the bind address of each service, not a filter.

### T2.5 Probes on the wg0 addresses from a neighbour on the same link (tested, log 23)

Linux accepts a packet for any local address on any interface. So CT
9411 added a `/128` route for the wg0 address of each node, through the
link-local address of that node on `vmbr1`, and probed it. CT 9411 has
no WireGuard key and is not a mesh member.

| Target | TCP 3306 | TCP 2379 | TCP 2380 | TCP 22000 | TCP 51821 | TCP 22 |
|---|---|---|---|---|---|---|
| Primary wg0 address | **open**, MariaDB greeting of 85 bytes | **open** | **open** | **open** | refused | open |
| VIP (on the primary) | **open** | | | | | |
| Replica wg0 address | **open** | **open** | **open** | **open** | refused | open |
| Witness wg0 address | | **open** | **open** | | refused | |

etcd 2379 sent no answer to a plain HTTP request. The test did not try
TLS or a login on any of these ports. The routes were removed after the
probe.

**Result for T2.5: the mesh-only services are reachable from a
neighbour on the same link, through eth0, on the wg0 addresses.** Only
the invite port refuses, because it binds to the device (`%wg0`). A
neighbour on the same link is, for example, another guest on the same
bridge or VLAN of the host, or the upstream router. A host that is not
on the link cannot do this unless a router sends the ULA prefix
`fd52:959a:bd28::/64` to the node. The `inet keel` rule set of 0097
accepts mesh ports on wg0 only (`iifname`), so it closes this path.
That is read in code, not tested here.

## Summary

| Question | Result |
|---|---|
| T1. Does the Proxmox guest firewall close a `simple` node? | **yes**: undeclared TCP and UDP ports give a timeout on IPv6 and IPv4. 22, 80, 443, 12321 answer. Survives `pct reboot` |
| T1. Levels | datacenter, network device `firewall=1`, guest file `enable: 1`. Not the node level |
| T1. Side effects | DHCPv4, DHCPv6, RA and neighbour discovery work with `dhcp: 1` and `ndp: 1`. `dhcp: 0` loses the address at the next rebind. The datacenter switch sets the `bridge-nf-call` sysctls to 1, and a `forward` drop on the host then drops all traffic of the guest |
| T1. `cloud_simple` pair | the stopgap plus UDP 51820: closed, replication, Syncthing and a reboot work |
| T2. Is a published `cloud_advanced` node open? | **yes**: no `firewall:` key, no rule file, `keel-firewall` skipped, undeclared TCP and UDP ports answer on both families |
| T2. Mesh-only ports on the public address | none answer: they bind to the wg0 address |
| T2. Mesh-only ports through eth0 on the wg0 address | **MariaDB 3306, etcd 2379 and 2380, Syncthing 22000 answer** to a neighbour on the same link. The invite port 51821 does not |

## What this means for 0097

These are proposals only. Note 0097 is not changed by this file.

1. Section 2, last item: "Thus a published node in `cloud_advanced` is
   also open. Read in code, not tested." This is now tested (T2.2,
   T2.4).
2. Section 7, the advisory text "The databases listen on the loopback
   only" is not true in the cloud modes. MariaDB listens on the wg0
   address and the VIP, and a neighbour on the same link reaches it
   (T2.5, T1.4). The advisory should name 3306, 2379, 2380 and 22000 in
   `cloud_simple` and `cloud_advanced`.
3. Section 7, the stopgap table: the Proxmox row can go from **not
   tested** to **tested** for `simple` and `cloud_simple`, with the 3
   levels of T1.2, `dhcp: 1`, and the caution about a `forward` drop.
4. Section 6, item 3 "Mesh only on wg0" should also probe the wg0
   address and the VIP through eth0 from a neighbour on the same link,
   as T2.5 did. A probe of the public address alone does not show this
   path.
5. "Not verified: UDP 12321 from outside." Tested: it answers on IPv4
   (T1.0, T2.4).

## What was not tested

- A node upgraded by `apt`. The images carry `keel` 0.23.96 and
  `confconsole` 2.2.3+keel24, not the `keel` 0.23.97 and `keel25` that
  0097 read.

- The nftables back end of the Proxmox firewall (`nftables: 1`).
- The stopgap in `cloud_advanced`, on a witness, and on a VM from the ISO.
- A stopgap with the node level on (`host.fw` `enable: 1`) and only the
  `IN ACCEPT` rules for 22 and 8006.
- SLAAC: the test network sends no prefix with `A=1`.
- A DHCP lease that expires by time. The test forced a rebind.
- A pair whose guest file does not accept UDP 51820.
- TLS or a login on the mesh ports in T2.5. The probe proved a TCP
  connection and the MariaDB greeting only.
- A neighbour that is not on the same link. The test VM routes no ULA
  prefix.
- The topology of the release test (2 sites, netem). All nodes were on
  one bridge of one VM.

## Logs

The logs and scripts are kept on the maintainer's workstation in
`repos/evidence-0097-2026-11-23/`. Numbers: 00 the VM before the test,
01 images, 02 and 03 create and first boot, 10 to 12 the published
`simple` node, 20 to 24 `cloud_advanced`, 30 to 39 the stopgap levels
and checks, 40 to 46 the `cloud_simple` pair, 90 secret scan, 99
cleanup and the VM after the test. The runner records (`runner/`,
`runner-cs/`) hold console transcripts and are not copied here.

## Cleanup

CTs 9410, 9411, 9420, 9421, 9422, 9430 and 9431 were destroyed (logs 24,
99). The rollback script removed `cluster.fw`, `host.fw` and the guest
files, removed the temporary rule of `inet keel_test_fw`, and set the
`bridge-nf-call` sysctls to 0. `pve-firewall status` is
`disabled/running` again. A diff of the VM state before and after
(`pve-firewall status`, the files of `/etc/pve/firewall` and of the node,
`iptables-save`, `ip6tables-save`, `ebtables-save`, `nft list ruleset`,
the sysctls, `pct list`, the links) without packet counters and time
stamps shows one line only: the time of `lrm_status`, which the HA
service of Proxmox VE writes by itself (log 99). The templates
`ev0097-*` and `/root/ev0097` were removed. The core template that was
on the VM before the test was not touched.
