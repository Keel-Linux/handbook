# 0058: Link profiles for a mesh of 3 sites, and the etcd and TCP settings that follow

Date: 2026-10-16
Status: **proposed, for later evaluation.** Nothing in this note is
decided. The note frames an evaluation that comes later: what to
measure, which questions are open, and which criteria decide. Until a
decided note replaces it, the 0050 amendment of 2026-10-15
(`net.ipv4.tcp_retries2 = 5`) stays as it is.

## What was asked

The maintainer asked for a note for the future. It must evaluate the
type of connection between the 3 nodes of a mesh in different regions.
From that, it must evaluate the type of installation, the speed at
which etcd gets updates, and a fine adjustment of how the containers in
the mesh communicate with each other.[^ask]

The cause is the 0050 amendment, implemented by keel#182 (keel
0.23.31) for keel#167. On each node that runs etcd, keel sets
`net.ipv4.tcp_retries2 = 5`. etcd then ends a stalled peer connection
after about 14 s of retransmissions, and a new leader comes 8 to 13 s
after a cut. The amendment states the side effect: each TCP connection
in the network namespace of the node now ends after about 14 s of
outage, instead of about 15 minutes. These connections include SSH and
the replication of a database pair (0054).

## Why (brief section 10)

1. **Why the current approach is not enough.** One kernel value now
   sets the outage limit for all TCP connections of a node. The value
   is correct for etcd's peer connections. It is not necessarily
   correct for an SSH session of the operator, or for PostgreSQL
   replication that can wait out a short cut. Also, keel renders one
   set of etcd timings for every mesh (heartbeat, election timeout
   with pre-vote), and no measurement of the real links selects it.
2. **Whether it can be made to work.** The links are measurable. The
   BR3-THIN evidence already has RTT and loss for 3 sites, at base and
   under netem (see "What we know"). 0050 already gives the profiles of
   the design case. A small set of install profiles can map the
   measured link to the etcd timings, the TCP behaviour and the MTU of
   the overlay.
3. **Why this is better.** The operator measures once, keel selects a
   profile, and each setting has a reason that a reviewer can check.
   The outage limit applies only to the connections that need it, so a
   short cut does not end an SSH session or a replication stream.

## What we know

Overlay RTT from `docs/evidence/2026-10-15-br3-thin-etcd-witness.md`,
section 3:

| Sites | Base | Under netem |
| --- | --- | --- |
| BR1 to BR2 | 4.3 ms (3.5 to 5.7) | 253.9 ms (233.3 to 278.0), 1.67 % loss |
| BR1 to BR3 | 42.6 ms (25.7 to 139.9) | 284.0 ms (258.1 to 326.3), 2 % loss |
| BR2 to BR3 | 44.6 ms (30.2 to 131.0) | 285.4 ms (260.9 to 326.7), 2 % loss |

MTU facts from the evidence:

- BR3-THIN reaches the mesh through a WireGuard tunnel, `pop`. The CT
  has `mtu=1420`. The keel overlay `wg0` has MTU 1280. A ping of 1232
  bytes with "do not fragment" passed between all 3 nodes.
- The path from BR1 to BR2 is 1492 bytes (PPPoE at BR2). keel writes
  no MTU for `wg0`, so `wg-quick` takes it from the route: 1420 on one
  node and 1412 on another. A full segment was dropped on the path,
  and the ICMPv6 "packet too big" came 26.6 s late (keel#119, keel
  `evidence/2026-10-09-br2-channel.md`).
- The path MTU of BR3-THIN is reported to be below 1380 bytes. No
  evidence file records this value yet. Measurement M3 confirms it.

## Install profiles

The profiles use the names of 0050's table. This note adds no new
network names. The measured link of a mesh is its worst pair of sites.

| Profile | Round trip | Loss | Example |
| --- | --- | --- | --- |
| ideal | about 5 ms | none | BR1 to BR2 at base |
| regional | up to about 100 ms ±10 ms | none | BR3 at base (43 ms, spikes to 140 ms) |
| design case | up to about 250 ms ±25 ms | none | Brazil to Europe |
| design case, lossy | up to about 250 ms ±25 ms | up to 2 % | all 3 pairs under netem |

The limits between profiles are open (question Q1). The evaluation can
also find that 2 profiles are enough.

## What to evaluate

### (a) etcd timing

For each profile, the evaluation finds values for these settings and
measures their effect:

- heartbeat interval and election timeout (the bench of 0050 used
  300 ms and 3 s; keel#167 saw 5 s with pre-vote at base);
- snapshot count and compaction of the history;
- the time from a write on one member to its read on the 2 other
  members, the propagation;
- the time to a new leader after a cut of the leader's site, and the
  time until all members are back after the heal.

### (b) TCP behaviour for the connections that need it

There are 2 different failures. Each option addresses one, both, or
neither.

- **Failure 1, a stalled connection after a cut** (keel#167). The
  retransmission timeout doubles up to 120 s, and the sender sees no
  error. Only a limit on retransmissions ends it.
- **Failure 2, a black hole for full segments** (keel#119). The path
  drops segments above its MTU, and the ICMPv6 comes late or never.
  Only a correct MTU or MSS ends it.

| Option | Scope | Failure 1 | Failure 2 | Open point |
| --- | --- | --- | --- | --- |
| `tcp_retries2 = 5` (today) | the network namespace | yes | no | ends SSH and replication after about 14 s |
| `TCP_USER_TIMEOUT` on etcd's peer sockets | one socket | yes | no | etcd has no setting for it today (Q4) |
| a network namespace for etcd only | one service | yes | no | can keel set it up in an unprivileged CT (Q5) |
| `TCP_USER_TIMEOUT` set by a cgroup BPF program | one cgroup | yes | no | needs privileges that the CT may not have (Q5) |
| WireGuard `PersistentKeepalive` | the tunnel | no | no | keeps NAT state only; see below |
| TCP keepalive (`SO_KEEPALIVE`) | one socket | no | no | does not fire while data waits for an ACK |
| a fixed MTU on `wg0` | the overlay | no | yes | one value for all sites, or one value per path (Q6) |
| MSS clamping on `wg0` | the overlay | no | yes | needs nftables rules from keel (Q6) |

The WireGuard keepalive and the TCP keepalive do not end a stalled
connection. They keep NAT and endpoint state, or they detect a dead
peer on an idle connection. An etcd peer connection is not idle in a
cut, because raft writes to it. Thus neither option is a replacement
for the current value.

The kernel has no per-cgroup value for `tcp_retries2`. A narrower scope
than the network namespace needs one of these: a socket option, a
namespace of its own, or a BPF program.

### (c) how containers in the mesh communicate

- the MTU of `wg0` on each node, from the measured path, and the same
  value on both ends of each path;
- MSS clamping for TCP that crosses `wg0`;
- which services go across sites: etcd peers, database replication,
  Syncthing (0050), the VIP controller, SSH of the operator;
- for each service, the outage that it must survive without a new
  connection, and the outage after which it must dial again.

## Open questions

- **Q1.** Where are the limits between the install profiles? Is a
  profile per mesh enough, or does each pair of sites need its own?
- **Q2.** Does keel measure the link itself at install, or does the
  operator give the profile in the spec?
- **Q3.** Must etcd's timings change when the link changes after the
  install, and how does keel detect the change?
- **Q4.** Does etcd 3.5 or 3.6 set `TCP_USER_TIMEOUT` on its peer
  connections, or accept a setting for it? If not, what does a patch
  to the Debian package cost to keep?
- **Q5.** Which options work from inside an unprivileged CT (the
  witness 9071 is one), and which need the Proxmox host?
- **Q6.** Does keel write the MTU of `wg0` from a measurement, or one
  safe value (1280) for all nodes? What does 1280 cost in throughput
  on the ideal profile?
- **Q7.** Which outage must SSH and PostgreSQL replication survive
  without a new connection? Is 14 s acceptable for them?

## Measurements to take

Each measurement runs on the real nodes BR1, BR2 and BR3-THIN, under
each profile of 0050's netem table, and leaves an evidence file (0053).

- **M1.** RTT, jitter and loss for each pair of sites, at base, for at
  least 24 h, with the 50th, 99th and maximum values.
- **M2.** The same under each netem profile, to confirm that the
  profile is the one that netem sets.
- **M3.** Path MTU for each pair of sites, on the uplink and on `wg0`,
  with `ping -M do`. This confirms or corrects the BR3-THIN value.
- **M4.** The time to a new etcd leader after a cut of the leader's
  site, and the time until all members are back after the heal. Run
  this for each set of etcd timings and each TCP option.
- **M5.** The propagation time of an etcd write to the 2 other
  members.
- **M6.** The time until a stalled connection ends, on real links,
  for each TCP option. The 0050 amendment states about 14 s from the
  netns harness at the design case; M6 measures it on real links.
- **M7.** False drops: the count of working connections that end at
  the lossy design case, over a run of at least 6 h.
- **M8.** SSH and PostgreSQL replication during cuts of 5 s, 10 s,
  20 s and 60 s: does the connection survive, or dial again?

## Criteria to decide

An option or a set of timings is accepted for a profile only if it
meets all of these. The values are proposals for the evaluation.

1. A new etcd leader within 15 s after a cut of the leader's site, in
   each run of M4.
2. All members back within 20 s after the heal, in each run of M4.
3. No false drop in M7.
4. An SSH session and PostgreSQL replication survive a cut shorter
   than their limit from Q7, in M8. This is the side effect that the
   current value causes.
5. No full segment lost to the MTU in M3, at the `wg0` MTU that keel
   writes.
6. The option works on the unprivileged CTs that keel supports, or
   the note says which host change it needs.
7. The least power that meets 1 to 6: a setting keel already owns
   before a patch to etcd, and a patch to etcd before a kernel
   program.

## What stays until then

`net.ipv4.tcp_retries2 = 5` in `/etc/sysctl.d/90-keel-etcd.conf` stays
on each node that runs etcd. It stays until a decided note replaces it
with an option that meets the criteria above.

## What this amends

Nothing. This note is a proposal. A later decided note will amend the
0050 amendment of 2026-10-15, and possibly 0057's placement rule.

[^ask]: The maintainer, 2026-10-16, in Portuguese: "A nota como uma ADR
    para o futuro avaliarmos o tipo de conexão entre uma rede de três
    nós diferentes regiões para avaliar o tipo de instalação e
    velocidade com que atualizamos o etcd e fazemos um ajuste fino
    digamos em como os containers dentro da rede se comunicam entre
    si."
