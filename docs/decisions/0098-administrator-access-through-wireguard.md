# 0098: Administrator access goes through a Keel WireGuard network

Date: 2026-11-25
Status: **proposed.** The maintainer gave the direction on 2026-11-25
(see "What was asked"). The questions under "Questions for the
maintainer" are open. Nothing in this note is built or tested.

Sources. Each repository path was read on its default branch after
`git fetch` on 2026-11-25: `keel` `bece037` (main), `common` `18522b4`
(branch `19.x`), `confconsole` `a1abe09` (branch `master`), `keel-core`
`cfa5907` (branch `master`). The issues keel#74 and keel#303 were read
on git.pop.coop on 2026-11-25. "Read in code" means that nobody tested
it on a running node.

## What was asked

The maintainer decided this on 2026-11-25:

1. Administrator access to a Keel node goes **only** through a Keel
   WireGuard network. Keel builds it now.
2. Keel never uses SSH tunnels or TCP forwarding. `AllowTcpForwarding`
   stays `no`.
3. In his words: "SSH stays only for root login over IPv6. There is no
   IPv4 bastion and no forwarded port." This note reads "no forwarded
   port" as a rule for SSH. Questions 6 and 8 depend on that reading.
4. Webmin on TCP 12321, until 0094 retires it, and the database tool
   (DBeaver on the computer of the administrator, 0094) are reachable
   only from the WireGuard network. They are never reachable from
   outside.

The earlier rules stay: one pasted command with a token inside, as the
install command of `cloudflared` does (0094). The token is valid once.
The key pair is made on the computer of the administrator (0094,
answer 6). The premises stay: the access works at 250 ms RTT with
loss, IPv6 comes first, and many nodes can sit behind one shared public
IPv4 address.

## What is true today

### 1. The idea in keel#74

keel#74 (open since 2026-10-03, no comments, no labels) is the idea
`keel mesh invite --workstation`. It names a WireGuard peer for the
laptop of an operator, with limited `allowed_ips`, no etcd membership,
revocable and short-lived. It asks for its own decision: what the peer
can reach, the expiry and the revocation. 0094 un-parks only the basic
access peer of keel#74. The wider workstation options of 2026-11-19
stay parked. This note is that decision for the basic access peer.

### 2. The mesh WireGuard network

The mesh between Keel nodes already uses WireGuard (decisions 0024,
0025, 0029, 0048, 0049, 0051, 0057, 0058).

| Item | Value | Where |
| --- | --- | --- |
| Interface | `wg0` by default, `network.overlay.wireguard.interface` | `keel/network/wireguard.py:35`, `keel/docs/spec.md:292` |
| UDP port | 51820 by default, `listen_port` | `keel/constants.py:48`, `keel/docs/spec.md:295` |
| Private key | `/etc/wireguard/<interface>.key`, mode 0600, made by `wg genkey` on the node at the first converge, never in an image. The rendered file has no key: `PostUp` gives the key file to `wg set` | `keel/network/wgkeys.py:1-17`, `keel/network/wireguard.py:82-87`, `keel/docs/spec.md:296` |
| Address plan | A random unique local /64 (`fd00::/8`), the first node at `::1`. Region k, host n is `<prefix>::k:n`, one /112 for each region (0051). The top /112, `<prefix>::ffff:0/112`, is the VIP range | `keel/mesh/create.py:4-11`, `keel/mesh/allocate.py:1-29`, `keel/mesh/vip.py:50-58` |
| IPv4 on the overlay | Optional `ipv4_address`, RFC 1918 or `100.64.0.0/10` | `keel/docs/spec.md:294` |
| Peers | `network.overlay.wireguard.peers`, each with `public_key` and `allowed_ips`. keel refuses a prefix in the VIP range, because it routes a VIP to its holder at runtime | `keel/docs/spec.md:297-300` |
| The VIP | The primary carries it on `wg0` as a second address. A move changes the `allowed-ips` of a peer on each node | 0049, lines 111-124 |
| Join | `keel mesh invite` makes a `keel1:` or `keel2:` token: the public key of the inviter, its endpoints, a pinned certificate fingerprint, a one-use secret and an expiry. The join request goes to an HTTPS port that a timed nftables set opens | `keel/mesh/token.py:1-40`, `keel/mesh/invites.py:1-21` |
| Trust | `keel mesh create --adopt` and `keel mesh sync --adopt` make **each peer that the spec lists an operator root**. An operator root can remove a node, have a certificate revoked and sign a VIP pair record | `keel/docs/mesh.md:458-468`, and 0094 for the powers |

### 3. The overlay package

The package `keel-overlay-wireguard` is not a repository of its own. It
is `common/packages/wireguard` on branch `19.x`. It ships the overlay
manifest as `/usr/share/keel/overlays/wireguard.yaml` and depends on
`wireguard-tools` (`common/packages/wireguard/debian/control`,
`debian/rules`). It declares no process. `keel-core` pulls it in
(`keel-core/plan/main:1-10`). Thus each Keel image has `wg`.

The manifest names a confconsole screen that does not exist:
`screen: /usr/lib/confconsole/plugins.d/Networking/wireguard.py`
(`common/packages/wireguard/manifest.yaml:6`). The real screen is
`plugins.d/Instance/Overlay_network.py`.

### 4. The confconsole WireGuard screen

`confconsole/plugins.d/Instance/Overlay_network.py` opens
`confconsole/wgscreen.py`. The screen shows the key of the node, sets
the mesh address and adds or removes a mesh peer (`wgscreen.py:31-32`,
`:116-179`). It writes the spec through `keel` (0094, design rule 1).
It has no access peer, no token and no list of computers.

### 5. The firewall of 0097

`keel/manifest/firewall.py` at `bece037` writes one table, `inet keel`,
with `policy drop` on input in every mode.

| Rule | Where | What it means for access |
| --- | --- | --- |
| `expose: public` on every interface | `firewall.py:129`, `:144` | 12321 is `public` today (`keel-core/packages/keel-core/manifest.yaml:27`). Thus Webmin answers from outside |
| The sshd ports on every interface | `firewall.py:129`, and 0097 section 3 | TCP 22 is open on every interface and on both families. That is a fact of 0097, not a choice of this note |
| The WireGuard UDP port on every interface | `firewall.py:132-134` | Only when the spec declares `network.overlay.wireguard` |
| `expose: mesh` ports on `iifname "wg0"` | `firewall.py:151` | **Each** packet that comes in on `wg0` reaches each mesh port: etcd 2379, 2380, Syncthing 22000, MariaDB 3306, PostgreSQL 5432, Redis 6379. The rule has no source address |
| TCP 51821 on `iifname "wg0"` | `firewall.py:154` | `keel mesh sync` and the announcements of members |
| The invite set `mesh_invites` on every interface | `firewall.py:155` | A TCP port that is open only while an invite waits |
| `firewall.allow` | `firewall.py:93-100`, `:205-220` | `port`, `protocol` and an optional `from`, a list of source prefixes. It has **no interface field**. 0097 decision 8 matches mesh ports by input interface, not by address, because of the path through the uplink (0097 section 4a) |
| Output and forward | 0097 decision 1.3 | keel filters input only. keel sets no `ip_forward` (no match in `keel/keel/`) |

Without `network.overlay.wireguard`, as in `simple` mode, keel opens no
mesh port and no WireGuard port (`firewall.py:135-140`).

### 6. SSH and the database today

- `common/overlays/turnkey.d/sshd/etc/ssh/sshd_config.d/turnkey.conf`
  sets `PermitRootLogin yes` (line 5), `AllowTcpForwarding no`
  (line 16) and `MaxSessions 2` (line 19). This note keeps them.
- MariaDB listens on `::1,127.0.0.1`. Its `admin` account exists for
  `localhost`, `::1` and `127.0.0.1` only. PostgreSQL listens on
  `::1,127.0.0.1` (0094, "The database client"). In a pair, the
  database also listens on the `wg0` address for replication (0097,
  section 4). Whether `pg_hba.conf` accepts a password on TCP loopback
  is not checked.
- On a replica, keel takes `READ_ONLY ADMIN` from each account except
  the socket accounts (`keel/keel/system/dbreadonly.py`).

### 7. Open defects that touch access

- keel#303 (open): the CrowdSec whitelist does not have the mesh prefix.
  CrowdSec can ban a mesh address. The same can happen to the address of
  an administrator on the access network.

## Why (brief section 10)

1. **Why a change is necessary.** Webmin answers on TCP 12321 from
   outside in every mode today. 0094 chose an SSH tunnel for DBeaver,
   but the maintainer forbids TCP forwarding. Thus the database tool has
   no path today, and the only root web listener is public.
2. **Whether it can be made to work.** Each part exists in Keel: the
   key made on the machine that uses it (`wgkeys.py`), a one-use token
   with an expiry and a pinned certificate (`token.py`), a timed open
   port for an enrolment (`mesh_invites`), and rules by input interface
   (`firewall.py:151`). WireGuard sends no answer to a packet that it
   cannot authenticate. Its handshake is 1 round trip and it retries by
   itself, which suits 250 ms RTT with loss.
3. **Why this is better.** The administration ports leave the public
   address. An access peer reaches only a short list of ports on one
   interface. It is not a mesh peer, so it cannot become an operator
   root and it cannot reach etcd, Syncthing or `keel mesh sync`.

## Decision

### 1. The access peer is a restricted peer, not a mesh member

1. The computer of an administrator is an **access peer**. An access
   peer is not in `network.overlay.wireguard.peers`. Thus `--adopt`
   never makes it an operator root, and `keel mesh sync` never sends it
   to other nodes.
2. An access peer has no etcd certificate, no Syncthing device and no
   right on the mesh.
3. The access peer is on its own interface, the **access interface**
   (question 1). Its default name is `keel-access`.
4. keel declares the access network in a new spec section,
   `network.access` (names to confirm in the keel design):
   - `interface`, default `keel-access`.
   - `listen_port`, the UDP port (question 2).
   - `address`, the address of the node on the access network.
   - `private_key.file`, default `/etc/wireguard/keel-access.key`, made
     on the node as `wgkeys.py` makes the mesh key. It is a different
     key from the mesh key.
   - `peers`, each with `name`, `public_key`, one `/128` address, and
     the date of the enrolment.
5. The access network works in every mode. It does not need
   `network.overlay.wireguard`. A `simple` node has an access network
   and no mesh.

### 2. Address plan

1. Each node makes its own random unique local /64 for the access
   network at its first enrolment (question 3). The node is `::1`.
   Each computer gets a random free address in the same /64.
2. keel refuses an access prefix that overlaps the mesh prefix, a
   region, the VIP range, `network.interfaces` or a peer endpoint, as
   it does for the mesh (`keel/docs/spec.md:293`, `:300`).
3. The addresses inside the tunnel are IPv6 only. The access network
   has no IPv4 address. A computer on an IPv4-only ISP still uses IPv6
   inside the tunnel, because the inner family does not depend on the
   outer family.
4. On the computer, the tunnel routes only the `/128` of the node. It
   does not route the access /64, the mesh prefix or `::/0`.

### 3. The enrolment

1. The administrator opens confconsole, menu "Administrator access",
   item "Add a computer". He types a name for the computer. For the
   first computer, he reaches confconsole by SSH over IPv6 or on the
   console of the host.
2. confconsole calls `keel access invite --name <name>` (name to confirm
   in the keel design). keel makes an enrolment token and opens the
   enrolment port in a timed nftables set, as `mesh_invites` does
   (`firewall.py:155`).
3. The token is valid once and for 15 minutes by default. It holds the
   public key of the node on the access network, the node endpoint, the
   fingerprint of a certificate for the enrolment, a one-use secret and
   the expiry. keel stores only a key derived from the secret, as
   `keel/mesh/invites.py` does.
4. confconsole shows one command. The administrator pastes it in a
   terminal on his computer. The command gets the enrolment script from
   the node over HTTPS and pins the certificate fingerprint
   (question 4).
5. The script makes the key pair on the computer with `wg genkey`. It
   sends only the public key and a proof of the secret to the node. The
   node never has the private key.
6. The node checks the proof, marks the token as used, adds the peer to
   `network.access.peers` through `keel`, and converges. It answers with
   the address of the computer.
7. The script writes the tunnel configuration on the computer with
   `PersistentKeepalive = 25`, and starts the tunnel. It then tests TCP
   22 on the address of the node inside the tunnel, and prints the
   result.
8. A second use of the token fails. An expired token fails. The
   enrolment port closes when the token is used or expires.

The node has no endpoint for the computer. The computer starts each
handshake, so a computer behind NAT works with no change on the node.

### 4. Ports on the access interface

1. A new manifest exposure class, `access`: keel opens an `access` port
   only for a packet that comes in on the access interface
   (`iifname "keel-access"`), as it opens `mesh` ports on `wg0`. This
   does not use `firewall.allow`, because `firewall.allow` matches the
   source address and has no interface (section 5 of "What is true
   today").
2. The `access` ports:

   | Port | Service | Note |
   | --- | --- | --- |
   | TCP 22 | SSH | Open already on every interface by 0097 section 3. If question 6 is B, 22 is also an `access` port, so that the access interface keeps it |
   | TCP 12321 | Webmin, until 0094 removes it | The `webmin` process in `keel-core/packages/keel-core/manifest.yaml:27` changes from `public` to `access`. Thus 12321 closes on the public address |
   | TCP 3306 | MariaDB, images with MariaDB | Through a local relay (question 5) |
   | TCP 5432 | PostgreSQL, images with PostgreSQL | Through a local relay (question 5) |

3. TCP 12320 (the web shell) and TCP 12322 are in no Keel manifest.
   12320 is only in the `WEBMIN_FW_TCP_INCOMING` list of the `Makefile`
   of `keel-laravel` (`19.x`, line 14) and `keel-loops` (`main`,
   line 15). The firewall of 0097 does not read that list. This note
   opens nothing for 12320 or 12322.
4. No other port opens on the access interface: not etcd, Syncthing,
   Redis 6379, 51821, 80 or 443.
5. keel adds a forward rule: keel drops each packet that comes in on
   the access interface in the forward hook. Thus a computer cannot use
   a node as a router into the mesh or the uplink, also on a node that
   has `ip_forward` on. This amends 0097 decision 1.3 for the access
   interface only.
6. The UDP port of the access interface is open on every interface, as
   the mesh port is (`firewall.py:132-134`).
7. CrowdSec must not ban the access prefix of the node. This depends on
   keel#303.

### 5. SSH

1. `AllowTcpForwarding` stays `no`. Keel adds no `Match` block for
   forwarding. 0094 design rule 4 and its work items 2 and 5 end.
2. SSH on the public IPv4 address: question 6.
3. The root login over IPv6 stays as it is.

### 6. Modes

| Mode | Access network |
| --- | --- |
| `simple` | One access interface on the node. No mesh is necessary |
| `cloud_simple` | One access interface on each node, independent of `wg0` |
| `cloud_advanced` | The same. The etcd witness of 0057 has no database and no Webmin, so it gets an access network only if the administrator asks for one |

A pair: question 7. The VIP is not on the access network in each option
of question 7. DBeaver connects to the access address of the primary.
confconsole shows the role of each node, and the guide tells the
administrator to connect to the primary for a write. On a replica, the
database refuses writes (`dbreadonly.py`).

### 7. Listing and revocation

1. confconsole, menu "Administrator access", item "Computers", lists each
   access peer: name, address, date of the enrolment, and the time of
   the last handshake from `wg show`.
2. Item "Remove a computer" calls `keel access remove <name>`. keel
   removes the peer from the spec and converges. WireGuard then drops
   each packet from that key at once.
3. Item "Waiting enrolments" lists each token that is not used and not
   expired, and can cancel it.
4. A removal on one node does not remove the peer on another node.
   Question 7 says how a pair handles it.
5. `keel diff` reports a peer on the access interface that the spec does
   not declare.

## Questions for the maintainer

Each question has a recommendation: the option with the least power,
strict over comfortable.

1. **Which interface does the access peer use?**
   - A. A separate interface, `keel-access`, with its own key and UDP
     port. The firewall opens only the `access` ports on it.
   - B. The mesh interface `wg0`, with source-address rules for the
     access peers. Each mesh rule must then also match the source,
     `--adopt` must skip the access peers, and `keel mesh sync` must not
     send them.

   Recommendation: **A**. On `wg0`, today each packet reaches each mesh
   port (`firewall.py:151`, `:154`), and a listed peer can become an
   operator root (`keel/docs/mesh.md:466-468`).

2. **Which UDP port does the access interface use?** 0094 decision 4
   says that Keel opens no new public port.
   - A. A fixed default, UDP 51822, that the spec can change. This
     amends 0094 decision 4: one new UDP port, which gives no answer to
     a packet that WireGuard cannot authenticate.
   - B. A random port for each node, written in the spec at the first
     enrolment.

   Recommendation: **A**. One known port is easier to document and to
   forward at an edge. WireGuard is silent to a scan in both options.

3. **Which address plan?**
   - A. A random unique local /64 for each node, the node at `::1`.
   - B. A /112 inside the mesh prefix, beside the VIP range. This needs a
     mesh, and the nodes of a pair must agree on the addresses.

   Recommendation: **A**. It works with no mesh, and two nodes never
   share a prefix. Thus the computer can have one tunnel to each node
   with no route conflict.

4. **Who serves the enrolment script?**
   - A. The node serves it on the enrolment port, over HTTPS. The
     command pins the certificate key, for example
     `curl --pinnedpubkey sha256//<pin>`. It needs no web PKI and no
     external site.
   - B. A signed Keel source, for example keellinux.org, serves a fixed
     script. The node serves only the enrolment request.

   Recommendation: **A**. The command proves the node by the pin, and
   the enrolment needs no access to an external site.

5. **How does DBeaver reach the database?**
   - A. A local relay: a systemd socket on the access address of the
     node, port 3306 or 5432, with `systemd-socket-proxyd` to the
     loopback. The database configuration and its accounts do not
     change, because the connection comes from the loopback.
   - B. The database also listens on the access address, and gets an
     account for the access prefix.

   Recommendation: **A**. It changes no database bind address and no
   account. The test must show the login of `admin` and `postgres`
   through it, and `pg_hba.conf` on TCP loopback. In a pair, MariaDB
   also listens on the `wg0` address and on the VIP (0097 section 4a).
   A relay socket on the access address does not collide with these.
   If the database binds a wildcard address on some image, the relay
   cannot bind 3306 there, and the test must show it.

6. **Does SSH stay open on the public IPv4 address?** 0097 section 3
   opens the sshd ports on every interface and both families.
   - A. No change: 22 stays open on IPv4 and IPv6.
   - B. 22 opens on the public IPv6 address and on the access interface
     only. keel refuses B on a node that has no global IPv6 address, so
     that the node is never closed.

   Recommendation: **B**. This is the reading of "SSH stays only for
   root login over IPv6" in "What was asked". It changes 0097 section 3
   and needs its own lock-out test.

7. **How does a pair handle the access peer?**
   - A. One enrolment for each node. The administrator runs the command
     once for each node and gets 2 tunnels. He removes a computer on
     each node.
   - B. One enrolment gives one configuration with both nodes. keel
     copies `network.access.peers` to the replica with the settings
     sections (0094 decision 8, not built).

   Recommendation: **A**. It needs no copy between the nodes, it keeps
   working when the link between the sites fails, and each node shows
   its own list. B waits for 0094 decision 8, and a removal does not
   reach a replica that is cut off.

8. **What happens behind a shared public IPv4 address?**
   - A. The enrolment and the tunnel use IPv6 only. A node with no
     global IPv6 address gets no access network. A computer on an
     IPv4-only ISP cannot enrol.
   - B. As A, and the operator can forward one UDP port and one TCP
     enrolment port for each node at the edge. The spec names the
     external endpoint for the token. A forward at the edge is an
     infrastructure request, outside Keel. B is possible only if "no
     forwarded port" is a rule for SSH alone (see "What was asked").
   - C. A relay node with a public address carries the access traffic
     to the other nodes.

   Recommendation: **A** first, and B only when a real customer needs
   it. C gives one node power over the others. This note rejects C.

9. **Which platforms does the first version support?**
   - A. Linux and macOS, with `wg` and `wg-quick` from the system
     packages.
   - B. Linux, macOS and Windows at the same time.

   Recommendation: **A**, then Windows after its own real test.
   Windows needs the WireGuard application and a separate PowerShell
   script.

10. **How long is the enrolment token valid?**
    - A. 15 minutes, which the administrator can change from 5 to 60.
    - B. 60 minutes.

    Recommendation: **A**.

11. **When does 12321 close on the public address of a node in the
    field?** 0094 decision 5 says that the removal of Webmin is an act
    of the administrator. Closing the port is not a removal.
    - A. At the first apply after the upgrade of `keel-core` that moves
      12321 to `access`. Webmin then answers only on the access
      interface. SSH and confconsole stay.
    - B. At the first enrolment of a computer on that node. Until then
      12321 stays public, and `keel diff` and the boot banner warn.
    - C. Only by an explicit act in confconsole.

    Recommendation: **A**, because the direction is "never from
    outside". New images have 12321 on `access` from the first boot.
    The release notes and the advisory of 0097 tell the administrator
    to enrol a computer. This amends 0094 transition step 6, which
    expects 12321 to answer after the upgrade.

## Real tests before acceptance

Each test writes an evidence file (0053). The tests run in the test VM
of each site (not on the cluster), at 250 ms RTT with 2 % loss by
netem, on IPv6, and on IPv4 where option 8B applies.

1. **Enrolment.** confconsole makes a token, the command enrols a Linux
   computer and a macOS computer, and SSH works on the access address.
   The private key is not on the node (search of `/etc`, `/var/lib/keel`
   and the logs).
2. **Single use and expiry.** A second use of the token fails. A token
   after its expiry fails. The enrolment port is closed after each case.
3. **Isolation.** From the access peer: etcd 2379 and 2380, Syncthing
   22000, 51821, Redis 6379, 80 and 443 on the access address give a
   timeout. A packet to the mesh address or the VIP through the tunnel
   gives a timeout. A forward to the uplink fails.
4. **Not from outside.** 12321, 3306 and 5432 give a timeout on the
   public IPv6 and IPv4 addresses, and from a neighbour on the same link
   that adds a route to the access address (as 0097 test 4).
5. **Database.** DBeaver connects to MariaDB as `admin` and to
   PostgreSQL as `postgres` on the access address of the primary. On
   the replica, a write fails.
6. **Webmin.** 12321 answers on the access address and not on the public
   address, until the removal act of 0094.
7. **Revocation.** After "Remove a computer", the next packet from that
   computer gets no answer, and the list no longer shows it.
8. **Pair.** The test of the option that question 7 chooses, with a
   failover between the 2 sites. The guide steps work after the
   failover.
9. **Reboot and upgrade.** After a reboot, the access interface and the
   rules come back. The 0090 upgrade test on a published image shows
   the option of question 11. With A: after the upgrade and the next
   apply, 12321 is closed on the public address, SSH works, and an
   enrolment makes 12321 answer on the access address.
10. **CrowdSec.** Failed SSH logins from the access address do not ban
    it, after the fix of keel#303.
11. **SSH on IPv4.** If question 6 is B: the refusal on a node with no
    global IPv6 address, and the session that runs the apply stays open.

## What this amends

This note changes these notes when it is accepted. It does not edit
them.

- **0094**: decision 3 (DBeaver through the access network, not an SSH
  tunnel), decision 4 (one new UDP port, if question 2 is A), design
  rule 4 (no `Match` block, no forwarding), work items 2 and 5 (they
  end), transition step 6 (DBeaver connects through the access network),
  and "The WireGuard access peer: a later step" (it is now this note).
- **0097**: decision 1.3 (a forward drop for the access interface), the
  allow list of decision 2 (a new `access` class), and section 3 if
  question 6 is B.
- **0049**: the text "SSH tunnel, for now" for a workstation (lines 180,
  416, 562, 582) ends.
- **0041**: the manifest gets the exposure class `access`.
- **0075**: commissioning reaches Webmin through the access interface,
  not through the public address, until the removal act of 0094.

The index row of each amended note will say "amended by 0098".

## Work list

In order. Nothing is started.

1. The real test of the relay of question 5 and of `pg_hba.conf` on TCP
   loopback, by hand, before the design. Evidence file.
2. keel: `network.access` in the spec, its validation and its render.
3. keel: the `access` exposure class and the forward rule in
   `keel/manifest/firewall.py`.
4. keel: `keel access invite`, `list`, `remove`, and the enrolment
   listener.
5. The enrolment script for Linux and macOS.
6. confconsole: the menu "Administrator access".
7. common: correct `screen:` in `common/packages/wireguard/manifest.yaml`
   to `plugins.d/Instance/Overlay_network.py`.
8. keel-core: 12321 from `public` to `access`. In the same change:
   each test that reaches 12321 from outside, as 0094 lists them
   (`tests/commission*.yaml`, the boot tests, `tests/firewall.bats`, and
   the screenshots of `dot-github/lib/commission/`).
9. keel#303: the CrowdSec whitelist with the mesh and access prefixes.
10. The guide for each platform.
11. The real tests above.

## Related notes

0018 (the confirmation window), 0024 and 0048 (the mesh and its join),
0029 (WireGuard in Core), 0041 (the manifest), 0049 (the VIP), 0051
(regions), 0053 (evidence), 0057 (the witness), 0090 (the upgrade test),
0094 (Webmin retired), 0097 (the firewall).
