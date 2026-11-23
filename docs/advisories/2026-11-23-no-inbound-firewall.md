# Advisory 2026-11-23: Keel nodes load no inbound firewall rule

Date: 2026-11-23
Status: open
Decision: [0097](../decisions/0097-keel-writes-the-firewall-in-every-mode.md)
(proposed), keel writes the firewall in every mode
Evidence:
[2026-11-23, the firewall loader](../../evidence/2026-11-23-webmin-removal-firewall-and-ssh-tunnel.md),
[2026-11-23, the stopgap and cloud advanced](../../evidence/2026-11-23-firewall-stopgap-and-cloud-advanced.md)

## What the defect is

A node made from a published Keel image loads no inbound packet filter
at boot. This is true in the 3 installation modes: `simple`,
`cloud_simple` and `cloud_advanced`.

- **No inbound filter.** Each port on which a service listens on a
  public address is reachable from the network.
- **Ports that you add.** If you install a service that listens on a
  public address, it is reachable from the network, also if you did not
  plan to open it.
- **The cloud modes.** A host on the same network link as the node can
  reach the database port of a pair on the inner (WireGuard) address of
  the pair.

The images were made to filter inbound traffic. The rules exist in the
image, but no unit loads them. keel loads its own rules only when the
spec says `firewall.enabled: true`, and no installer writes that line.

## Who is affected

Each node made from these images, in each mode, the etcd witness
included. The versions are the ones on the
[appliances page](https://keellinux.org/appliances.html) of the stable
channel (releases 2026-11-10, 2026-11-11 and 2026-11-12):

| Image | Version | Release |
| --- | --- | --- |
| Keel Core | 19.0-13 | 2026-11-10 |
| Keel Web | 19.0-14 | 2026-11-12 |
| Keel LNMP | 19.0-7 | 2026-11-12 |
| Keel LNPP | 19.0-10 | 2026-11-12 |
| Keel MariaDB | 19.0-12 | 2026-11-11 |
| Keel PostgreSQL | 19.0-9 | 2026-11-10 |
| Keel Redis | 19.0-13 | 2026-11-11 |
| Keel ntfy | 19.0-7 | 2026-11-12 |
| Keel WordPress | 19.0-22 | 2026-11-12 |
| Keel Laravel | 19.0-8 | 2026-11-12 |
| Keel Odoo | 19.0-19 | 2026-11-12 |

In the testing channel: Keel NodeBB 19.0-9 (pre-release of 2026-11-13).

The test ran on LNMP 19.0-7, LNPP 19.0-10 and Core 19.0-13, in
Proxmox VE containers. The other images have the same core layer and
the same `keel`. They were not booted for this advisory. Earlier
revisions of the images have the same code. They were not tested.

A node is not affected if its spec has `firewall.enabled: true` and
`installation.mode: cloud_advanced`, and `keel spec apply --system` ran
after the change. This was tested on earlier images on 2026-10-16.

## What is reachable on a node that nobody changed

- TCP 22 (SSH) and TCP 12321 (Webmin) on each image.
- UDP 12321 (Webmin) on IPv4.
- TCP 80 and 443 on the images with a web server.
- In `cloud_simple` and `cloud_advanced`: MariaDB 3306, etcd 2379 and
  2380, and Syncthing 22000 answer to a host on the same link. That host
  must send its packets for the inner address of the node through the
  node's own network interface. A host that is not on the link cannot
  do this, unless a router sends the inner prefix to the node.

## What is not affected

- In `simple`, MariaDB, PostgreSQL and Redis listen on the loopback
  only. They are not reachable from the network.
- etcd accepts a connection only with TLS 1.3 and a client certificate
  that the mesh signed.
- Syncthing accepts only the devices that keel configured.
- SSH, Webmin and the web server have their own login. Their ports were
  meant to be open.

## What to do now

If your node runs in a Proxmox VE container, turn on the Proxmox VE
firewall for that container. This was tested on a `simple` node and on
a `cloud_simple` pair. The full record is in
[the evidence file](../../evidence/2026-11-23-firewall-stopgap-and-cloud-advanced.md),
section "Procedure".

Not tested: a node in `cloud_advanced`, the etcd witness, a VM made
from the ISO, and the nftables back end of the Proxmox VE firewall
(`nftables: 1`). If your node is one of these, do the procedure on one
node first, and do step 6 on it before you do the next node.

Do not install `iptables-persistent` or `netfilter-persistent` as a
stopgap. The rules that they load have no WireGuard port, and a pair
then stops replication.

### Procedure

Do these steps on the Proxmox VE host, as root. `VMID` is the number of
the container.

1. Read the state first. Run `pve-firewall status`. Read
   `/etc/pve/firewall/cluster.fw` and `/etc/pve/nodes/NODE/host.fw`.
   Read `nft list ruleset` and `iptables-save` of the host. Find each
   `forward` chain with a drop policy.
2. Keep your access to the host. If the datacenter firewall is off, the
   switch in step 5 also turns on the firewall of each host. Its input
   policy is `DROP`, and its management rules accept only the local
   network of the host (read in the code of `pve-firewall` 6.0.8). Thus,
   before step 5, write `enable: 0` in
   `host.fw`. The host is then not filtered. Then make a timer that
   turns the firewall off again after 10 min.
3. Write the guest file `/etc/pve/firewall/VMID.fw`:

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

   - Keep `dhcp: 1` and `ndp: 1`, as tested. If the node gets its
     address by DHCP and the file has `dhcp: 0`, the node loses its
     address at the next rebind.
   - Write the lines for 80 and 443 only for an image with a web server.
   - For a node of a pair, add
     `IN ACCEPT -p udp -dport 51820 -log nolog`, the WireGuard port.
   - Add a port of your own service in the same way.
4. Set `firewall=1` on the network device of the container, and keep its
   `hwaddr`: `pct set VMID --net0 '<the current net0>,firewall=1'`. A
   running container gets the change at once.
5. Turn on the datacenter firewall: `enable: 1` in `cluster.fw`.

   Caution: this switch sets the sysctls `bridge-nf-call-iptables` and
   `bridge-nf-call-ip6tables` to 1 for every bridge of the host. Then
   each bridged frame also goes through the `forward` hook. If the host
   has its own `forward` chain with a drop policy, the container loses
   all its traffic. Before this step, add an accept for the bridged
   traffic of the guest to that chain. The test added
   `iifname "fwbr*" oifname "fwbr*" accept`.
6. Check from a second machine. A port that you did not open gives a
   timeout. Port 22 and the application ports answer. The node keeps its
   addresses. `apt-get update` works on the node.
7. Remove the timer of step 2 when you have proved that you can still
   get to the host.
8. Reboot the container once, and do step 6 again.

The stopgap filters on the host. If you copy the container to another
host that does not have the same files, the copy is open again.

## What comes next

A fixed `keel` writes an inbound rule set with a drop policy in each
mode. The allowed ports come from the declared state of the node
(decision 0097). New images are closed from their first boot. A node in
the field changes only when a person runs `keel spec apply --system`
after the upgrade. No date is promised. This advisory then gets the
status "closed" and the version of the fix.
