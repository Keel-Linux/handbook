# 0048: Joining the mesh with one command

Date: 2026-10-03
Status: **decided by the maintainer, 2026-10-03**, in two rounds the same
day: the goal, the commands, the token's contents and four questions
first, then the five points this note left open, each approved as
recommended. A third round, on 2026-10-04, settled four questions the
etcd implementation found (keel's etcd PR). All three are under
"Decision". The sections after it carry the decision out. An amendment,
admission evidence for what members learn of each other, was
**approved by the maintainer on 2026-10-04**; it is at the end of this
note.

## What was asked

0024 puts the WireGuard mesh in every Keel Core image, 0025 makes etcd its
registry, and 0028 has the primary generate the WireGuard key and endpoint
the replica uses. None of them says how the second node learns them. Today
it is typed: `keel network wireguard suggest-address` on the first node, a
public key read off each node with `wg`, an endpoint and a port, and a peer
block written by hand into each spec (docs/spec.md in keel, "overlay").
The maintainer asked that joining a node to the mesh, and later to etcd,
take one command, so that someone who is not a network engineer never
copies a key, an address or a port. That is the ease of use the project
keeps from TurnKey: a console menu and one line, not a procedure.

## Why (brief section 10)

1. **Why the current approach is not enough.** Every value the second node
   needs exists on the first one, and the operator is the transport. Four
   values per side, each of which fails in its own way when mistyped: a
   wrong key fails the handshake silently, a wrong address collides with
   another peer's (which `wg` resolves by keeping the last one), a wrong
   port is a timeout. 0026's discovery assumes a mesh already exists, and
   0046 (Keel Cloud) removes the copy and paste only for an operator who
   uses Keel Cloud, which is never required (0020).
2. **Whether it can be made to work.** It does work, for an operator who
   knows WireGuard, and it stays: the spec's `network.overlay.wireguard`
   fields are unchanged, and a peer typed by hand is as valid as one a join
   wrote. What does not work is asking it of everyone.
3. **Why one command is better.** The node that already knows the values
   writes them into one line, and the new node reads them back. The line
   carries the only value that is not public, a one use secret, so the
   operator's act of copying it is the authorization. The result is the
   same spec fields, converged by the same `apply` under the same
   confirmation window (0018), so there is no second code path on either
   node, and Keel Cloud can later carry the same line instead of the
   operator (Q4 below).

## Decision

- **Goal.** Joining a node to the WireGuard mesh, and later to etcd, takes
  one command. A non-expert never copies a key, an address or a port.
- **Commands.** On a node already in the mesh, `keel mesh invite` prints
  one line:

  ```
  keel mesh join keel1:<token>
  ```

  The token is valid for one hour and can be used once. Running that line
  on the new node joins it. confconsole offers the same thing under
  Overlay: **"Invite a node"** shows the line, and **"Join a mesh"** has a
  field to paste it into.
- **What the token carries.**
  - the inviting node's WireGuard public key, its public endpoint and
    port, and the overlay prefix;
  - the address assigned to the new node, which the inviter allocates as
    the next free one in its prefix, from its own address, its known
    peers and its other pending invites;
  - a one use secret and an expiry;
  - a version, in its prefix: `keel1:`.

  Public keys are not secret. The secret's role is authorization: whoever
  holds the token was given it by the inviting node's root.
- **Q1, the channel.** The new node sends its public key, its endpoint and
  the address the inviter assigned back to the inviter over a temporary
  HTTPS port. The inviter opens that port only while an invite is pending,
  and authenticates the request with the secret, by an HMAC over the
  request; the secret itself never crosses the wire, in clear or inside
  TLS. The inviter's TLS certificate fingerprint is in the token, and the
  new node pins it. On success the inviter adds the new peer to its spec
  and applies it, and so does the new node. When the port cannot be
  reached, `join` prints a second one line command to run back on the
  inviter. Both sides apply through 0018's confirmation window; the join
  confirms itself once the tunnel answers ("How the window is confirmed").
- **Q2.** The first node creates the mesh; every other node joins it.
- **Q3.** The WireGuard mesh works from two nodes. etcd forms at the third,
  and the screen says why: two etcd members have no fault tolerance (a
  majority of two is two, so losing either stops both). The same token
  carries what etcd needs, so the third join is the one that forms the
  quorum.
- **Q4.** The token is the mechanism Keel Cloud (0046) will carry later.
  Keel Cloud only removes the copy and paste; it does not add another way
  in.

### Decided, second round (2026-10-03)

The five points the first draft left open, approved as recommended:

1. **The first node confirms its own overlay.** The mesh's creation is an
   overlay change with no peer, so no peer can confirm it. `keel mesh
   create` confirms it itself once apply.md's route check finds every
   gateway, and the operator's SSH client, still leaving through the
   uplink: an overlay with no peer adds a route for its own private prefix
   only. This amends 0018, of the same kind as 0029's VIP exemption.
2. **The invite port is TCP 51820 by default**, the number of the UDP
   port, with `--port`. It is opened only where keel-firewall exists
   (cloud advanced, `firewall.enabled: true`); everywhere else keel touches
   no firewall it does not own, and the fallback applies.
3. **etcd uses its own TLS**, peer and client, with a CA made by the first
   node when it creates the mesh. The inviter issues the new member's
   certificate and sends it in the authenticated answer. WireGuard alone
   is not relied on, so a process on a member that is not etcd cannot
   write the registry.
4. **`keel mesh remove` removes the peer and the etcd member**, and lists
   the `shared` secrets of 0041 the removed node held, without rotating
   them: rotation is the operator's explicit step, since rotating them
   automatically would restart every service that uses them.
5. **A third node in cloud simple** (two nodes in 0028, no etcd in 0041):
   the WireGuard mesh grows, with peers learned through the inviter, and
   the screen says that etcd and automatic failover need cloud advanced.
   The mesh never changes the installation mode by itself.

### Decided, third round (2026-10-04)

Four questions the design of the etcd half raised, where the rounds above
disagreed with each other or with keel 0.18, each approved by the
maintainer as recommended:

1. **Each member issues with its own intermediate CA.** Second round,
   point 3, has the first node make the CA and the inviter issue the new
   member's certificate, while any member may invite ("The third node and
   after") and the answer carries only the CA's certificate, so a member
   other than the first could not issue. The answer: the root CA key
   stays on the first node; every etcd member receives, in its join
   answer, its own intermediate CA, signed by its inviter, and issues the
   certificates of the nodes it invites with it. Any member can then
   issue, and every certificate can be traced to the member whose
   intermediate signed it.
2. **The spec holds only `overlays.etcd: enabled`.** "etcd at the third
   node" writes the three member initial cluster "into its spec", which
   contradicts "The spec does not change" (Consequences) and keel's
   docs/mesh.md. The answer: the member list, the certificates and the
   cluster's state are state under `/var/lib/keel/etcd`, rendered into
   `/etc/default/etcd`; the spec says only that the overlay is enabled.
3. **Only cloud advanced members count, and an existing mesh forms by
   command.** A mesh that already has three or more nodes (built with
   keel 0.18, or by hand and adopted) never sees a third join, and a
   mesh may mix modes. The answer: only members whose
   `installation.mode` is `cloud_advanced` count towards the three; the
   join request says whether the joining node can run etcd; and `keel
   mesh etcd form` forms the cluster on an existing mesh, making the CA
   first when the mesh has none.
4. **`keel mesh remove` removes the etcd member under the amendment's
   rule.** etcd accepts `member remove` from any holder of a client
   certificate, while the amendment below lets only the member that
   admitted a node, a trust root, or the node itself remove it mesh-wide.
   The answer: `keel mesh remove` runs `etcdctl member remove` only under
   that rule; otherwise the removal is local only, as the amendment says
   of the peer.

## The token

`keel1:` followed by the base64url encoding, without padding, of a compact
serialisation of the fields below, with a checksum so that a truncated or
mistyped paste is recognised as such before anything is sent. A token is
about 250 characters: one line in a terminal, one field in confconsole.
A later format is `keel2:`, and a `join` that does not know a prefix says
which keel reads it rather than guessing.

| Field | Why the new node needs it |
| --- | --- |
| Inviter's WireGuard public key | its peer entry for the inviter |
| Inviter's endpoint, address and UDP port | where to send the handshake; an IPv6 literal when the inviter has one (brief section 10) |
| HTTPS port | where to send the join request, at the same address |
| TLS certificate fingerprint (SHA-256) | to pin the inviter's certificate |
| Overlay prefix and the assigned address | its own `network.overlay.wireguard.address`, and the inviter's `allowed_ips` for it |
| Mesh identity | a random value made when the mesh is created; it names the mesh in etcd and is etcd's cluster token |
| etcd state | none, forms at this join, or running (with the inviter's member URL) |
| Invite ID | which pending invite this is; derived from the secret, not the secret |
| Secret | 256 random bits; the HMAC key |
| Expiry | the time after which the inviter refuses it, in UTC |

Nothing in it names a host by a provider's name, a site or an account; the
site label of 0025 is set on the new node by its own installation, as
before.

## Joining, step by step

**On the inviter, `keel mesh invite`:**

1. On a node with no overlay, it first creates the mesh (Q2): the key pair
   made on the machine (keel-core#8), a random prefix inside `fd00::/8`
   and `::1` on it, as `suggest-address` does today, the mesh identity,
   and `listen_port` 51820. The overlay comes up under 0018's window like
   any first overlay, and `create` confirms it itself (second round,
   point 1). `keel mesh create` does this step
   alone.
2. It reserves the next free address, makes the secret, and a key pair and
   self-signed certificate for this invite only.
3. It writes the pending invite (below), opens the HTTPS port, and starts
   the listener as a transient unit, `keel-mesh-invite@<id>`, whose
   `RuntimeMaxSec` is the time left to the expiry. The invite closes by
   itself even if nothing else runs again.
4. It prints the `keel mesh join` line and returns. confconsole shows the
   same line on screen.

**On the new node, `keel mesh join keel1:...`** (or `keel mesh join -`,
reading the token on standard input, which is what confconsole uses):

1. It checks the prefix, the checksum and the expiry, and that the node
   has no overlay yet or one of the same mesh.
2. It makes its own key pair if it has none, and finds its own endpoint:
   its global IPv6 address, or IPv4 when it has no IPv6, or none when it
   cannot be reached from outside ("NAT and IPv4").
3. It sends the request to the inviter's HTTPS port, pinning the
   certificate: its public key, its endpoint, the assigned address, a
   nonce and the time, with an HMAC-SHA256 keyed with the secret over the
   method, the path and the body. The secret is not sent.
4. The inviter checks the HMAC, the expiry and that the invite is still
   pending, and marks it used, in one step under a lock, so a second
   request finds it used. It ignores any address but the one it reserved.
   It answers with its known peers (key, endpoint, overlay address), and
   for etcd what "etcd at the third node" lists, with the new member's
   etcd certificate and the mesh CA's (second round, point 3), and an HMAC
   over the
   answer, so the new node knows the answer came from the node that made
   the token as well as from the pinned certificate.
5. Each side writes the other into `network.overlay.wireguard.peers` of
   its own spec, the new node also its own `address`, and runs `apply
   --system`, which converges the overlay under 0018's window. Each node
   writes only its own spec (0013).
6. The new node opens a session to the inviter's overlay address, and the
   inviter answers over the overlay; each side confirms its window from
   that exchange (below). The listener exits, the port closes, the invite
   is removed.

`join` prints, at the end, the node's overlay address, the peers it has,
and the etcd state: at the second node, "the mesh is up with 2 nodes; etcd
starts when a third node joins, because 2 etcd members cannot lose one and
keep a majority". confconsole shows the same text.

A join that fails after the request was accepted (the tunnel never answers
within the window, say) reverts on both sides, and the token is spent:
the operator runs a new invite. A token is never valid twice, even for a
join that did not finish.

## The fallback when the HTTPS port cannot be reached

When the request gets no TCP answer within a few seconds, `join` does not
give up: it applies its own side (the inviter as a peer, its address from
the token) under 0018's window, lengthened to the invite's remaining time
up to 15 minutes with the window flag 0018 already has, and prints:

```
keel mesh accept keel1a:<answer>
```

to run on the inviter. The answer carries the new node's public key, its
endpoint if it has one, the assigned address, the invite ID and an HMAC
over them with the secret, so it is accepted only by the inviter that made
the token, once, before the expiry. `accept` adds the peer, applies, and
both windows are then confirmed over the tunnel exactly as in step 6.
The fallback costs one more paste, in the other direction, and nothing
else: no port is opened for it.

## How the window is confirmed

0018 confirms a change only from a session that started after it,
arrived over the new configuration, and came from another machine; for
the overlay, keel's docs/apply.md already accepts an SSH session over the
overlay or over the uplink, and asks the uplink's routes first with `ip
route get` whoever confirms. A join adds one source, and only for the
overlay change that join made:

- **A mesh session over the overlay counts as the new session.** It
  starts after the change, by construction; it arrives at this node's
  overlay address from the peer the change added (WireGuard binds that
  peer's address to its key, so the source is the new peer and no other);
  and it carries an HMAC with the invite's secret, so it is the join's own
  session and not any packet that happens to arrive. The inviter confirms
  on receiving it, the new node on receiving the inviter's authenticated
  answer: one round trip proves the tunnel in both directions.
- **The route check of apply.md runs first, unchanged.** If the new peer's
  `allowed_ips` capture the route to a gateway or to the operator's SSH
  client, the join is not confirmed and reverts, as any overlay change
  does.
- **It confirms only its own change.** A join refuses to start while
  another change waits in the window (one change at a time, as apply.md
  says), and the mesh session cannot confirm an uplink change.

So 0018's rule holds: what confirms a change is traffic that crossed the
new configuration after it was made. The operator does not have to open a
session; the two nodes do it.

## The third node and after

**A third and a fourth node join any member.** Whichever node prints the
invite is the inviter; there is no special first node after creation.

**Until etcd exists, members learn about each other through the
inviter.** The inviter's answer gives the new node every peer the inviter
knows, and the inviter sends each of its peers, over the overlay, an
announcement of the new peer (key, endpoint, address), which each of them
writes into its own spec and applies. The overlay authenticates the
announcement: it comes from a peer's address, which only that peer's key
can use. The new node's first session to each of them confirms their
windows, as above. In a two node mesh this case is the second join's
alone; it exists for a mesh whose installation mode never runs etcd
(second round, point 5).

**etcd at the third node.** etcd runs only in cloud advanced (0041,
"Resolved"). In that mode, the inviter accepting a third node writes a
three member initial cluster (the three overlay addresses, port 2380, the
mesh identity as the cluster token) into its spec, sends it in the answer
and in the announcement, and each of the three enables the `etcd` overlay
with `initial-cluster-state new`, each with a certificate from the mesh
CA the first node made (second round, point 3). From the fourth node on, the inviter
runs `member add` for the new node's overlay address before it answers,
and the answer says `existing` with the member list. The token's etcd
field is what tells the new node which of the three cases it is in.

**Once etcd exists, members learn about each other through etcd.** The
inviter writes the new peer's record under the mesh's prefix in etcd, the
registry of 0025, and every member watches that prefix and adds the peer
to its own spec. No member writes another member's spec; each reads the
registry and configures itself, which is 0025's division and 0013's rule.

## Revocation and removing a node

- **An invite** is cancelled with `keel mesh invite --cancel <id>`;
  `keel mesh invites` lists the pending ones (ID, reserved address,
  expiry, never the secret). Cancelling stops the listener, closes the
  port and frees the address. An expired invite is cancelled by its own
  unit, and a boot unit removes any whose expiry passed while the machine
  was down.
- **A node** is removed with `keel mesh remove <public key or overlay
  address>` on any member. It removes the peer from that member's spec and
  applies (a peer removed is under 0018's window, as 0029 keeps it). With
  etcd, it also runs `member remove` and deletes the node's record, and
  every member drops the peer when it sees the record go. It then lists
  the `shared` secrets of 0041 the removed node held, and rotates none of
  them (second round, point 4). Before etcd,
  the command removes the peer on the member it ran on and sends the same
  announcement as a join, so the others drop it too. A removed key is not
  readmitted by an old token, since every token is single use; joining
  again takes a new invite.

## NAT, and an inviter with only IPv4

0024 decides that tunnels are initiated from inside to outside and that
IPv4-only nodes enter through a rendezvous point (Tayga, NAT64).

- **The inviter behind NAT, the new node reachable.** The token's endpoint
  is the address the inviter sees on its uplink, which the new node cannot
  reach; `invite --endpoint` overrides it for a port forward. Without one,
  the HTTPS request fails and the fallback applies: `accept` gives the
  inviter the new node's endpoint with `persistent_keepalive` 25, the
  inviter initiates outward, and the new node keeps the inviter without an
  endpoint and waits for it, which the spec already allows.
- **Both behind NAT.** Neither can reach the other; `join` says so and
  names the rendezvous point of 0024 as the way, which the operator runs.
  It does not apply anything in that case.
- **The inviter with IPv4 only.** The token carries an IPv4 endpoint; the
  overlay stays IPv6 (and the optional `ipv4_address` beside it). A new
  node with IPv4 joins directly; an IPv6 only new node cannot reach it, and
  `join` says so before applying anything and names the rendezvous point.
  IPv6 is always preferred when the inviter has both.

## The firewall port

The HTTPS port is TCP, 51820 by default, the same number as WireGuard's UDP
port, so an operator's provider firewall needs one number for both
protocols (second round, point 2). `invite --port` changes it, and the token
carries whichever is used.

**When keel-firewall is enabled** (`firewall.enabled: true`, cloud advanced
only), the derived ruleset in `inet keel` gains, once, a named set of
pending invite ports with timeouts and the rule that accepts TCP to a port
in it. `invite` adds its port to the set with a timeout equal to the time
left to the expiry, and the listener's end removes it, so the port is open
exactly while an invite is pending and closes by itself even if keel dies.
Adding an element to a set is not a ruleset change, so it does not wait on
or disturb a network change in its window, which apply.md forbids for the
ruleset. **When keel's firewall is not enabled**, keel opens nothing and
says so in `invite`'s output; a closed port at the provider is the case
the fallback exists for.

## Where the pending invite lives

`/var/lib/keel/mesh/invites/<id>`, a directory root's and mode 0700, with
one file per invite, mode 0600: the secret, the expiry, the reserved
address, and the invite's TLS key and certificate. It is state, not
configuration: it is never in the spec, never emitted by 0027's YAML, and
never in a backup set (the set is derived from the manifests, 0041,
and none declares it). The listener runs as root and reads it; nothing
else does. A used, cancelled or expired invite's file is removed, not
kept.

## Logs

Every step is logged to the journal, as keel logs apply: the invite ID,
the reserved address, the new node's public key and endpoint, the outcome
of each check, and how each window ended. **Never the secret, the token,
an HMAC or the invite's TLS key.** The token is printed to the terminal of
the root who ran `invite`, or shown on confconsole's screen, and to
nothing else. A refused request is logged with its reason (bad HMAC,
expired, already used) and the client address, and after five refused
requests the invite is cancelled, which bounds what someone scanning the
port can learn and costs the operator one new invite.

On the new node the token is an argument of `join`, so it can land in
root's shell history and, while it runs, in the process list; it is
spent within seconds, which is why `join -` (standard input) exists and
confconsole uses it.

## What `keel inspect` and `keel diff` see

Only spec peers. A join writes `network.overlay.wireguard.peers`
entries, and an address on the new node, the same fields an operator would
write by hand; `inspect` reads them back from `/etc/wireguard/`, and
`diff` compares each peer with the peer of the same key, as docs/spec.md
already says. There is no `mesh` section in the spec and no field that
records how a peer was added. `inspect` reports pending invites, by ID and
expiry, as machine state beside the spec, never as a field `diff`
compares.

## Threat model

A token stolen within its hour lets the thief join once, at the reserved
address, as a peer of the mesh; the legitimate `join` then fails with
"already used", which is how the theft shows, and the inviter's log and
`keel mesh invites` name the key that joined, which `keel mesh remove`
takes out. A replayed request is refused because the invite is marked
used by the first valid one, under a lock, and the HMAC covers a nonce
and the time; the request travels inside TLS besides. A man in the middle
on the HTTPS port fails the pinned certificate, and without the secret it
can forge neither the request's HMAC nor the answer's; one that also holds
the token is the stolen token case. A malicious joiner that chooses
someone else's address gets nothing: the inviter ignores the address in
the request, allows only the reserved `/128` in `allowed_ips`, so
WireGuard drops traffic from any other source address of that key, and
spec validation already refuses a prefix given to two peers. What the
note does not defend against is a compromised inviter: its root can invite
anyone, which is what being a member means.

## Consequences

- keel gains `keel mesh create`, `invite`, `join`, `accept`, `invites` and
  `remove`, and the `keel-mesh-invite@` unit; confconsole's WireGuard
  screen (0041's `screen` of the `wireguard` overlay) gains "Invite a
  node" and "Join a mesh".
- The spec does not change. A mesh built by joins and one typed by hand
  are the same spec, and an operator can mix them.
- keel-firewall's derived ruleset gains one named set and one rule, empty
  while no invite is pending.
- 0028's "the primary generates the key, the password and the WireGuard
  endpoint the replica uses": the key and endpoint reach the replica in
  the token; the replication password and the other `shared` secrets of
  0041 go over the tunnel once it is up, never in the token.
- Phase 5 (mesh control plane, tracker#46) builds the etcd half;
  everything before "etcd at the third node" can be built with Phase 1's
  Core.
- Done when, on built Core images and not on machines assembled by hand:
  two containers on different bridges join with one line and ping over
  the overlay with no `keel network confirm` typed; a second use of the
  token, an expired token and a token with one character changed are
  refused, and the journal contains no secret; with the port closed, the
  fallback joins them; in cloud advanced a third join forms a healthy
  three member etcd, and a fourth joined through any member appears in
  every member's spec through etcd.

## What this amends

- **0018, "The converge, and why it reverts by itself"**, step 4, and
  keel's apply.md table for the overlay, on two points. A third confirming
  source is added, for an overlay change made by a join only: the join's
  own authenticated session over the overlay, from the peer the change
  added, after the route check. And the creation of a mesh, an overlay
  with no peer, is confirmed by `keel mesh create` itself after the route
  check (second round, point 1). Everything else in 0018 stands.
- **0026, "Review notes"** (the entry secret's lifetime and scope): for
  joining the mesh, the answer is a token used once, valid for one hour,
  that admits one public key at one reserved address. Discovery's
  selection of services (0026's decision) is unchanged and reads etcd
  after the join.
- **0028**: the WireGuard key and endpoint the primary generates reach
  the replica in the token (see "Consequences").
- **0046** (proposed, paused): Keel Cloud carries this token rather than
  defining its own enrolment for the mesh, which settles its open question
  4 in favour of the single use option for the mesh; the API key and the
  rest of 0046 are untouched.
- **0024 and 0025**: unchanged and applied; inside to outside, the
  rendezvous point for what cannot reach, and etcd as the registry from
  the third node.

## Amendment (proposed 2026-10-03, approved 2026-10-04): admission evidence

**Status: approved by the maintainer, 2026-10-04.** It comes
from the security review of keel#76, which builds "Until etcd exists".

**What was found.** "The overlay authenticates the announcement: it
comes from a peer's address, which only that peer's key can use." That
is true of who speaks, and says nothing of what it vouches for. A member
that pushes a roster can make every other member add any peer it names,
with no join behind it; the rogue key's own handshake then confirms
each member's window (0018), since it is a handshake from the peer the
change added. One compromised member could so add nodes mesh-wide under
nobody's name, and bring back a node another member removed.

**What is proposed.** Only an admitted join adds a peer, and each added
peer carries the evidence of its admission:

1. **A signing key per node.** Each node has a long-term Ed25519 key
   pair, made on the machine (as keel-core#8 has the WireGuard key made),
   kept as state under /var/lib/keel/mesh, never in an image, a spec or
   a backup set. Its public half goes in the join request and the
   fallback's `keel1a:` line, and the inviter's in the join's and the
   confirmation's answers, which the invite's HMAC authenticates.
2. **Evidence.** The inviter signs, with its key, the mesh identity, the
   invite id, the new node's WireGuard and signing keys, its overlay
   address and endpoint, and the time; it keeps that evidence, sends it
   in the answer, and joins it to the node's entry in the join's
   answers, the announcement and every roster.
3. **Trust.** A member takes an entry only when the evidence names an
   invite, the entry's key and address, is for its mesh, and is signed
   by a key it already trusts: its own, the inviter it joined through, a
   member admitted the same way (evidence chains), or a trust root. An
   entry without valid evidence is ignored, whoever sends it. Evidence
   always names an invite: no member vouches for a node it did not
   admit.
4. **Trust roots, for a mesh built by hand.** Such a mesh has no
   evidence. `keel mesh create --adopt` on one node and `keel mesh sync
   --adopt <its address>` on each other one, explicit acts of the
   operator, make the peers each node's spec lists its trust roots. A
   root's signing key is bound only from a roster the node fetched
   itself from the root's own overlay address, never from an
   announcement, whose source only the unprivileged listener reports.
   A root vouches for nobody: a peer that a hand-built node's spec lacks
   is written into that spec by its operator, as the mesh was built.
   The same two acts are the only way, besides a join, to set a node's
   mesh identity: no roster or announcement sets it.
5. **Tombstones, and removing a node before etcd.** `keel mesh remove`
   records the removal, signed with the remover's key, removes the peer
   from its own spec under 0018's window, and sends its roster, the
   tombstone in it, to the others, as this note's "Revocation and
   removing a node" asks ("so the others drop it too"). A member takes a
   tombstone only from a key that may remove that node: **the member
   that admitted it**, **a trust root**, or **the node itself**; it then
   drops the peer through one window, and never takes the key again.
   Any other member removes a node from its own spec only. Tombstones
   are kept for good (one that expired could let a stale roster bring
   the key back to a member that was offline), at most 1024 per node
   and 64 per signer, and every roster carries them all.
6. **The members' channel** is split as an invite's listener is: a root
   helper that holds the spec, the trust store and the signing key, and
   an unprivileged, sandboxed listener that faces the overlay, with the
   same limits (deadline, slots, per source, sizes, refusals), the
   announcements queued per sender, bounded, and applied in one 0018
   window.

**What it changes in the threat model** ("Threat model", whose last
sentence stands). **Any trusted member can vouch for a new node**, as
this note says any member can invite: the evidence it signs is enough
for every member that trusts it, directly or through the chain. So a
compromised member (its root, or its signing key) can admit any node
into the whole mesh, signed in its own name, and every member adds it;
it can remove the nodes it admitted, and any node if it is a trust
root. It can no longer add a node without evidence that names it and
the invite, add one under another member's name or to a member that
does not trust it, remove a node it did not admit (unless it is a
root), or bring back a key whose removal was taken. Every peer added
can be traced to the member that signed its admission. The way out of
a compromised member is to remove it, by its admitter or a root: its
tombstone makes it trusted no more; the nodes it admitted before stay,
and each is removed the same way. 0049's move of the VIP over "the overlay
announcement of 0048" is a different message, which this does not
cover; it needs the same rule before it is built: signed by a member's
key, verified by the receiver.

**What it amends in this note.** "The third node and after", second
paragraph: "The overlay authenticates the announcement" becomes "The
overlay authenticates who sends the announcement; each peer it names is
taken only with admission evidence signed by a key the receiver
trusts". "Revocation and removing a node": the removal leaves a signed
tombstone. "Consequences": keel also gains `keel mesh sync`, a signing
key and a trust store per node, and the `keel-mesh-members` service and
its listener. Once etcd exists (0025), the registry's records carry the
same evidence, and members verify it before configuring themselves.

**Left as follow-up, for the maintainer.** A node's signing key is not
rotated: it keeps the key it made. Rotation would be a new key signed by
the old one, which every member that trusts the old key then trusts in
its place, and a tombstone for the old key once the new one has spread.
Until then, a node whose key may be compromised is removed and joins
again with a new invite, which gives it a new key pair.

## Amendment (decided 2026-10-07): the root issues every certificate

**Status: decided by the maintainer, 2026-10-07** (Keel-Linux/keel#83,
after finding 4 of the keel#81 review). Implemented in keel 0.21.0.

**What was found.** Each etcd member held an intermediate CA (signed by
the root, name-constrained to its /128) and issued its own certificates.
etcd takes a client certificate's CN as its user, so any member could
mint a certificate with any CN, root's included, and per-user access
control in etcd was meaningless.

**What changes.**

- The root CA (the region root, 0051) issues every etcd client and peer
  certificate itself; the request is relayed by the inviter, as it was
  for intermediates, or sent by the member at a renewal. **Members hold
  no intermediate CA.**
- The certificate's CN is the member's mesh identity (`keel-` and its
  overlay address), fixed by the root; its SANs stay the member's /128
  and ::1. The root's holder alone also holds an admin certificate,
  CN `root`, etcd's root user.
- etcd's auth is enabled; users are the CNs. Every member reads the
  mesh's keys and writes its own (`/keel/<mesh>/etcd/`); a pair's VIP
  key prefixes are read-write for that pair's two members alone, read
  for the rest. The root's holder manages users and roles.
- A renewal (every 30 days) and a new membership wait while the root's
  holder cannot be reached; with several regions (0051) another root
  issues, as 0051's point 2 already says.
- keel asks etcd over gRPC with `etcdctl`, since etcd's JSON gateway
  calls etcd with the member's own certificate and refuses a client
  certificate with a CN once auth is on; the gateway is turned off, and
  keel-overlay-etcd depends on etcd-client.
- A running cluster of the old layout moves with `keel mesh etcd
  reissue` on the root's holder: one member at a time, every voter
  healthy before the next and nothing restarted, the intermediates then
  revoked by the root's CRL, then auth enabled; `--rollback` turns auth
  off again.

The VIP keeps its signed-claim checks as defence in depth (0049).

**What it amends.** "Decided, third round", point 1: "every etcd member
receives, in its join answer, its own intermediate CA ... and issues the
certificates of the nodes it invites with it" becomes "every etcd member
receives, in its join answer, its certificate, signed by the root, the
request relayed by its inviter"; the root CA key still stays on the
first node. Second round, point 3 is unchanged ("The inviter issues the
new member's certificate" was already the root's, relayed). 0051 is
amended with it (its "Issuance").

