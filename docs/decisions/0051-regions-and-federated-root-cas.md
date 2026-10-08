# 0051: Regions and federated root CAs

Date: 2026-10-04
Status: **decided by the maintainer, 2026-10-04**, in two rounds the
same day: the six points of Keel-Linux/tracker#60 first, then the eight
questions the first draft of this note left open, six approved as
recommended, two changed, and one point added (the roots' status and
alerts). Both are under "Decision", and the sections after it carry
them out. Nothing here is implemented beyond the single region case of
keel#78; Keel-Linux/keel#79 tracks the code changes multi-region needs.

## What was asked

0048's third round made the mesh's etcd CA a single root on the first
node, and keel#78 narrowed it to "every intermediate signed by the root,
the request relayed by the inviter": the root's holder is the one place
that can let a node into etcd. 0050 makes 250 ms with loss, and a link
that is cut, the design case for everything that spans nodes. A mesh
whose nodes are on several continents then has one node, on one of
them, that every other continent needs in order to certify a new node,
and losing the long link stops certification everywhere but there. The
maintainer decided how that is lifted (tracker#60) and asked for the
design: how a region is declared, how roots vouch for each other, where
their keys live, how revocation and CRLs work across roots and across a
partition, how etcd's quorum meets regions, the threat model, and the
migration from keel#78.

## Why (brief section 10)

1. **Why the current approach is not enough.** keel#78 has one root key
   on one node. When that node, or the link to it, is down, a join still
   completes and etcd membership waits (tracker#60, point 1), which is
   right for one region and wrong for several: a region cut off from the
   holder for a day certifies nobody for a day, though its own nodes are
   all up. The single root is also a single point of compromise for the
   whole mesh, with nothing that can outvote it.
2. **Whether it can be made to work.** It can without changing etcd or
   the certificate chain keel#78 builds. etcd verifies a peer or a client
   against a pool made from every certificate in its trusted CA file, so
   several roots are several certificates in one file. Every chain stays
   leaf, intermediate, root, and every intermediate stays constrained to
   its member's own address. What is new is above etcd: a signed list of
   the roots (the trust bundle), a rule for changing it (a majority of
   the roots), and a rule for whose revocations count (each root's own).
3. **Why this is better.** Certification follows the hot path of 0050: a
   node is certified by a root in its own region, at local round trips,
   and the long link only carries the result. One root compromised is
   one region's problem and can be voted out by the others, rather than
   the mesh's problem with no way out. And the first release does not
   wait for any of it: keel#78 ships the single region case with the
   bundle and the region field already in its formats.

## Decision

Decided by the maintainer on 2026-10-04 (tracker#60):

1. **Each region has an autonomous root CA on its primary node.** New
   nodes in a region are certified locally, so certification survives the
   loss of the links between regions (0050's premise).
2. **If a region's root is down, its nodes ask another region's root.**
3. **etcd trusts the bundle of all region roots.** etcd stays one cluster
   across regions; only issuance and revocation are federated.
4. **A new region root is valid only with signatures from a majority of
   the existing roots.**
5. **Each root revokes only what it issued. Revoking a whole root needs a
   majority.**
6. **The first release (keel#78) is the single region case, built
   forward-compatible**: a trust bundle and a region field.

This supersedes the wording of 0048's third round, point 1 ("signed by
its inviter"): an intermediate is signed by a region root, the request
relayed by the inviter.

### Decided, second round (2026-10-04)

The questions the first draft left open, answered by the maintainer:

1. **The bundle's signatures do not expire.** A trust list that expired
   during a long partition would take etcd down on every member at
   once. Each active root countersigns the current bundle once a year
   instead, and a countersignature older than 13 months is overdue
   ("The roots' status, and alerts").
2. **Approving a bundle is an explicit operator act on each root's
   holder**, never automatic: a new root, a replacement and a revocation
   alike.
3. **A root's key is backed up only as an operator-held,
   passphrase-encrypted export**, which may be stored in a Keel Backup
   destination of another region, and is never in an automatic backup
   set.
4. **A region's root fails over only by a new root approved by a
   majority**, never by copying the key; the export is the only way back
   for a mesh of one root.
5. **Changed: each region gets a /112 of the overlay's /64**, not a /80.
   The first region keeps the range its existing nodes already use, so
   no node is renumbered ("How a region is declared").
6. **Changed: the root being revoked counts in the total, and its own
   signature is not required.** With three roots, the other two revoke
   the third. With two, neither can revoke the other alone, and a third
   region is needed ("Revoking a whole root").
7. **etcd has at most five voters, chosen so that losing any one region
   leaves a quorum**; the other cloud advanced members are etcd clients;
   keel warns, and does not refuse, when the regions cannot meet the
   rule. This changes keel#78's "every learner is promoted", after
   keel#78 merges.
8. **An intermediate signed by another region's root lasts 30 days** and
   re-anchors to the home root when it returns.
9. **Added: the roots' status is shown, and alerted by email.**
   confconsole shows each region root, reachable or not, its last
   countersignature, its certificate's and its CRL's expiries, and which
   root this node's certificate comes from; keel mails `security.alerts`
   through the monitor's path (0021) when a root is unreachable, a
   countersignature is overdue, a CRL is near expiry, or this node runs
   on a foreign root's certificate; `keel mesh status` and `keel diff`
   show the same ("The roots' status, and alerts").

Two words are kept apart in what follows. A **region root** is a CA
key of this note. A **trust root** is 0048's amendment's: a member
whose signing key vouches for admissions on a mesh built by hand. They
are unrelated, and nothing here changes trust roots.

## How a region is declared

**In the spec, the machine says which region it is in.** One field,
beside the mode, chosen at installation:

```yaml
installation:
  mode: cloud_advanced
  region: region-b          # optional; [a-z][a-z0-9-]*, at most 32
```

| Field | State | Notes |
| --- | --- | --- |
| `installation.region` | read | The region this machine is in. Chosen once, at installation, like `mode`, and nothing converges it: moving a machine to another region is `keel mesh remove` and a new join. Absent means the mesh's first region. Allowed in every mode; it matters only to cloud advanced members. The name is the operator's and generic; validation refuses nothing about its meaning |

A region is above 0025's site: a region holds one or more sites, and
0025's rule that two replicas of the same data are never in one site is
unchanged. The spec does not list regions, roots or keys; those are
state, in the trust bundle below (0048, third round, point 2: the spec
says what the machine is, state says what the mesh holds).

**Each region has its own /112 of the overlay's /64** (second round,
point 5), and an inviter allocates the next free address inside its
region's range, so two regions cut off from each other never give out
the same address. keel numbers a region's /112 in the seventh group of
the address, the fifth and sixth staying zero: region *k*'s host *n* is
`<prefix>::k:n`, so region 2's fifth node in `fd2a:9c41:7e03::/64` is
`fd2a:9c41:7e03::2:5`.

- **The first region keeps what its nodes already use.** Its range is
  index 0, `<prefix>::/112`, which is where every address keel and
  `suggest-address` have given out so far lies (`::1`, `::2`,
  `fd2a:9c41:7e03::3`). On a mesh built by hand whose addresses lie in
  several /112s, the first region holds each of them (the bundle lists
  a region's ranges), and a new region takes an index no member uses.
  No node is renumbered.
- **Limits.** A /112 is 65,536 addresses; keel never gives out host 0,
  so a region has 65,535. The mesh's /64 holds 2^48 /112s; numbered in
  one group, a mesh has at most **65,536 regions** (indexes 0 to
  65535), of which the first is the one that exists today.
- **The allocator.** 0048's allocator (the next free address from the
  inviter's own, its known peers and its pending invites) runs the same
  over the region's /112 instead of the /64. 65,535 is far above the
  256 peers a roster carries, so the range is never what limits a
  region.
- **Name constraints.** Every intermediate stays constrained to its
  member's own /128 and ::1 (keel#78), whatever the region's size; the
  roots are not constrained to their /112 (Issuance). A /112 is a valid
  IP name constraint should that ever be decided.
- **The /128 rule.** Each peer's `allowed_ips` is still its address as
  a /128, the overlay route still the /64, and the spec's
  `network.overlay.wireguard.address` still carries /64. The /112 is an
  allocation rule, never a route or an `allowed_ips` entry.
- **Grants.** A /112 ends on a group boundary, so a region's range can
  be written as a database host pattern under docs/spec.md's rule that
  a prefix stopping inside a group is refused.

**A region exists when the bundle names it.** The bundle binds each
region's name to its index, its root and the address of its holder.

**A node joins into a region by its invite.** `keel mesh invite` reserves
an address in the inviter's region; `keel mesh invite --region <name>`
reserves one in that region's /112, and for a region the bundle does
not name yet, in the next free index (the first node of a new region, below).
The token does not change: the region is read from the reserved address,
and the answer carries the bundle that names it. `join` refuses when the
node's spec names another region, before it applies anything (the token
is then spent, as any refused join's is); a spec that names none gets
the region written into it, as `join` writes the overlay address.

## The trust bundle

**A bundle document signed by a majority, not roots signing roots.**
Cross-certificates were considered and rejected:

- X.509 path validation accepts any one valid path. Three
  cross-certificates of a new root, by three existing roots, are three
  paths, and any one of them makes the new root trusted: a single root
  could add a root alone. A majority cannot be expressed in X.509, so
  keel would count signatures itself either way.
- etcd builds its pool from the trusted CA file once, at start, and
  every certificate in that pool is an anchor. A cross-certificate placed
  there is trusted as itself; placed in each member's presented chain
  instead, the chain would differ by verifier and grow with every root.
- A cross-certificate is revoked by a CRL of its issuer, and etcd's CRL
  check matches serial numbers only (below), so revoking one root's
  cross-certificate would need every other root's CRL to agree.

With a bundle, etcd's trusted CA file is the concatenation of the
bundle's root certificates, every chain stays leaf, intermediate and
root, and the majority rule lives in one place that keel checks.

**The document** is canonical JSON, signed by root keys (P-256 ECDSA,
the keys the roots already have) over `keel mesh trust bundle 1\n` and
the document:

| Field | Meaning |
| --- | --- |
| `mesh_id` | the mesh's identity (0048) |
| `epoch` | this bundle's number: the previous one's plus one |
| `previous` | the SHA-256 of the previous bundle's canonical document, empty at epoch 1 |
| `regions` | per region: `name`, `ranges` (its /112s), `root` (the certificate, PEM), `fingerprint` (SHA-256), and `state`: `active`, `retired` (still trusted to verify, signs nothing) or `revoked` |
| `time` | when it was proposed, UTC |

and beside the document, `signatures`: the root fingerprint and the
signature of each root that signed it.

**The holder's address is not in the bundle.** Where a root's key lives
says nothing about trust; it is a short notice signed by that root's
key alone (`holder`: region, overlay address, time), so a region can
move its holder without a vote.

**Taking a bundle.** A member takes a bundle only when its `mesh_id` is
its own, its `epoch` is one more than the bundle it holds, its `previous`
is the hash of that bundle, and it carries valid signatures from a
**majority of the roots that are `active` in the bundle it holds**: more
than half of them, counted over all of them, whether or not they can
sign. A bundle that adds a root carries that root's own signature as
well (it holds the key), which does not count towards the majority. A
member several epochs behind verifies each step in turn; bundles are
small and every one is kept, in etcd under the mesh's prefix and in the
members' rosters, as the CRL travels in keel#78. A member that cannot
build the chain from what it holds takes nothing and alerts.

**No expiry; a yearly countersignature** (second round, point 1). A
bundle stays in force until a newer one replaces it. Once a year each
active root's holder countersigns the bundle in force (`keel mesh etcd
tend` does it when the last is eleven months old): a signature by that
root over the bundle's hash and the time, kept beside the bundle and
carried with it. It changes nothing; it shows the root is alive and
still holds its key. A countersignature older than 13 months is
overdue and alerted.

**One bundle per epoch.** A root signs at most one bundle at each epoch
and records the epoch it signed last. Two majorities of the same set
share a root, so two different bundles can never both be valid at one
epoch, even when they are signed on two sides of a partition.

**Epoch 1** is the single region case: one region, range index 0, the first
root, signed by that root, which is a majority of the one root that
exists. This is the file keel#78 ships (below).

**Approval is an operator's act on each holder.** A proposal (a new
region, a replacement root, a revoked root) is sent to every active
root's holder over the members' channel and through etcd when it has a
quorum; it is signed only when the operator runs `keel mesh region
approve` on that holder, which shows the region, its ranges, the new
root's fingerprint and the proposing node, and asks. A root that signs
on request would let one compromised root collect a majority by asking
for it (second round, point 2).

## Issuance

Unchanged from keel#78 in what it signs: an intermediate per member,
signed by a root, path length 0, name constrained to the member's own
/128 and ::1, a year long; leaves issued by the member, 30 days. What
changes is which root:

- **A node is certified by its own region's root.** The inviter relays
  the request to that region's holder, as keel#78 relays it to the one
  holder.
- **When that root does not answer, the inviter asks another active
  root**, the one with the shortest measured round trip among those that
  answer. An intermediate signed this way lasts **30 days**, not a year,
  and is recorded by the root that signed it, with the member's region.
- **Re-anchoring.** Once the home root answers again, `keel mesh etcd
  tend` on the member asks it for a new intermediate, installs it, and
  then asks the foreign root to revoke the old one, as the node itself,
  which keel#78's revoke rule already allows.
- **Roots are not constrained to their region's /112.** The fallback
  needs a root that can certify another region's address, and the
  decision accepts it ("joining nodes mesh-wide", below). The /112 limits
  allocation, not certification.
- **Records.** Only the first region's root forms the cluster, once,
  with keel#78's record. After formation, the root that certified a node
  adds it as a learner and signs its `existing` record; the record's
  epoch is etcd's revision at the `member add`, which etcd itself orders
  across every root, instead of a counter per holder.

## Revocation and the CRLs

**Each root keeps its own CRL**, signed by its key, numbered by it, and
lists only intermediates it issued: keel#78's rule (a revocation names
no serial; the holder revokes what it recorded for the node's address
and key, asked by its admitter, a trust root or the node itself) is
applied by each root to what it signed. A revocation request goes to the
root that signed the certificate, which the registry's record of the
intermediate names.

**What etcd does with a CRL.** etcd 3.5 (client/pkg/transport,
`checkCRL`, as of 3.5.16) reads the CRL file at every handshake, parses
**one** CRL from it, and refuses a connection when the serial number of
any certificate in the presented chain is listed. It does not check who
signed the CRL, and it ignores `nextUpdate`. So several roots' CRLs
cannot be concatenated in the file, and the file need not be signed by
any root.

**So each member merges.** It keeps the latest CRL of each root
(`crl/<fingerprint>.pem`, by CRL number, as keel#78 keeps the one), and
writes to etcd's `--peer-crl-file` and `--client-crl-file` one merged
CRL, the union of their entries, signed with its own intermediate's key
(which carries `cRLSign`). The merged file is local and never leaves the
member. It is rewritten whenever any root's CRL changes, and etcd reads
it at the next handshake, with no restart.

**What the merge keeps.** Because etcd matches serials alone, a root
could list another root's serials. An entry from root R is dropped when
its serial is that of a certificate the member knows another root
issued (every intermediate is in the registry, with its issuer); serials
are 128 random bits, so a root can name another's only by having seen
it. An entry is kept until the certificate it names has expired.

**Epoch rules.**

| Counter | Scope | Rule |
| --- | --- | --- |
| bundle `epoch` | the mesh | one more per change, hash chained, a majority's signatures |
| CRL number | one root | grows with each CRL that root signs; a member keeps the highest it has verified for each root |
| formation record epoch | the first region's root | keel#78's, once |
| learner record epoch | the mesh | etcd's revision at `member add` |
| applied epoch | one member | the bundle epoch its etcd runs with, written to its registry key |

A root's CRL that a member cannot renew (its root has been down past
its 30 days) is kept, never dropped, and alerted through the monitor's
channels (0021): a revocation is never undone by silence.

**Revoking a whole root** is a bundle that marks it `revoked`, approved
by a majority as any bundle is (second round, point 6): more than half
of the active roots of the bundle in force, **the root being revoked
counted in the total, its own signature not required**.

| Active roots | Signatures needed | Who can revoke one root |
| --- | --- | --- |
| 1 | 1 | nobody but itself; a mesh of one root re-founds its CA instead ("When a region's root fails") |
| 2 | 2 | **neither, alone**: the other root is 1 of 2 |
| 3 | 2 | the other two |
| 4 | 3 | the other three |
| 5 | 3 | any three of the other four |

**Two regions cannot revoke each other's root, and a third region is
needed.** That is the price of the rule: with two, each could otherwise
revoke the other during a partition, and the mesh would split in two
trusts. Nor can a third root be added once one of two is suspect,
since adding one also takes 2 of 2. So:

- **A mesh of two regions adds a third root while both are healthy.**
  The third region can be one small data-less cloud advanced node in a
  third location, the same machine as the external arbiter of 0028 and
  of the placement table below, holding a root. `keel mesh status` and
  confconsole say, while a mesh has two active roots, that neither can
  be revoked.
- **If one of two roots is compromised anyway**, the operator distrusts
  it member by member: `keel mesh region distrust <fingerprint>`, as
  root, on every member that is to stop trusting it, an explicit local
  act as 0048's `--adopt` is. On that member the root's intermediates go
  into the merged CRL at once and the root leaves the trusted CA file at
  the next restart. On the healthy root's holder, the same command also
  signs the next epoch, the suspect root `revoked`, with its one
  signature; a member takes that one bundle without a majority only
  where its own operator has run `distrust` for exactly that root.
  Members where it has not been run keep trusting the suspect root,
  which `keel mesh status` reports on the others. The mesh then has one
  root, and the operator adds a second and a third the usual way.

Its certificate leaves the trusted CA
file at the next restart; before that, at once, every member puts the
serials of the intermediates the registry says it issued into its merged
CRL, so the revocation takes effect at the next handshake. etcd checks
at handshakes only: a peer stream already open lasts until the rolling
restart below closes it. The voters it certified are then failed
members; `keel mesh etcd form` and `tend` on another root bring in
replacements, and their removal follows 0048's rule.

## Changing etcd's trusted CA file

etcd builds its CA pool at start, so a bundle that adds or removes a
root restarts etcd on each member, **one at a time**: a member takes the
bundle, waits for an etcd lease under the mesh's prefix that only one
member holds at once and for the cluster to report healthy, restarts,
and writes its applied epoch. A member that holds no quorum (cut off)
restarts when it rejoins.

**A new root issues nothing for etcd until every voter has applied the
bundle that adds it**, which it reads from the applied epochs; until
then its region's nodes are certified by the fallback, and `keel mesh
status` says why. Without this, a member certified by the new root would
be refused by a voter that does not trust it yet.

## Where a root's key lives

**On its region's holder**, `/var/lib/keel/etcd/root.key`, root's, 0600,
made there with openssl and never copied by keel, as keel#78 has it.
Never in an image, a spec, or a backup set derived from the manifests
(0041, 0037; second round, point 3): Keel Backup holds many nodes'
data, and a backup destination that held every root's key would be the
one place that compromises the mesh.

**Backed up by the operator, encrypted, if at all.** There is no HSM.
`keel mesh etcd root export` writes the key encrypted with a passphrase
the operator types (PKCS#8, scrypt, AES-256), to standard output or a
file, and keel keeps neither the passphrase nor the file; the operator
may store that file anywhere, a Keel Backup destination in another
region included (0037's rule that a backup is never in the site of its
data holds). `import` restores it on the region's new holder. The
export is offered, and recommended while the mesh has
fewer than three active roots, the case where a majority cannot replace
a lost one.

## When a region's root fails

**Down for a while:** nothing moves. The region's nodes are certified by
another root (Issuance), for 30 days at a time, and re-anchored when it
returns.

**Lost, or moved on purpose:** a new root, not a copied key. On the
region's new holder, `keel mesh region reroot` makes a key and proposes
a bundle that makes the new root `active` and the old one `retired`; the
old one signs it too when it still can. With a majority it takes effect:
the region's members renew their intermediates under the new root at
their next `tend`, and once none chains to the retired root, a later
bundle removes it. A planned move is the same act. Copying a key between
nodes, even encrypted, makes two places that can sign and a moment when
it is in transit; a new root makes neither (second round, point 4).

**When no majority can replace it**, because the mesh has one or two
roots: with one, `import` the export on the new holder; with none, the
mesh starts its CA again, by `keel mesh etcd form` on a trust root with
an explicit act on each member, as an adopted mesh does in keel#78.

## The roots' status, and alerts

(Second round, point 9.) Every member knows the bundle, the
countersignatures, each root's CRL and its own chain, and `keel mesh
etcd tend` asks each root's holder over the members' channel every five
minutes (`probe`; reachable means it answered with a holder notice that
root signed). From that, three views show the same facts with the same
thresholds:

- **confconsole**, in the Overlay screen, **"Region roots"**: one line
  per root, with its region, the start of its fingerprint, its state,
  its holder's address, reachable or not and since when, its last
  countersignature, its certificate's expiry and its CRL's next update;
  then this node: which root signed its intermediate, home or foreign,
  and its intermediate's and leaf's expiries; and the bundle epoch held
  and applied. A mesh of two active roots shows that neither can be
  revoked.
- **`keel mesh status`**, the region section: the same lines, as text.
- **`keel diff`**: each condition below as drift of `etcd.roots`, beside
  keel#78's `etcd.certificates`, so a script that reads diff sees it.

**Alerts.** Each condition is raised through the monitor's path that
keel#78 already uses for a failed renewal (0021): `keel notify`, which
mails `security.alerts`' address when `monitor.notify.email` is true,
and sends to the other declared channels. When no email channel is
configured, the status views say the alerts go nowhere by mail.

| Condition | Threshold | Mailed |
| --- | --- | --- |
| A root unreachable | its holder has not answered this member for 1 hour | once when it crosses, daily while it lasts, once when it clears |
| A countersignature overdue | an active root's last one is older than 13 months (due at 12) | once, then weekly |
| A CRL near expiry | a root's CRL has less than 10 days to its next update (it is re-signed every 10 days with 30 of life, so two signings were missed) | once, then daily; an expired CRL is kept, and the alert says so |
| This node on a foreign root | its intermediate was signed by a root not of its region | when it takes it; again when 10 of its 30 days remain without re-anchoring |
| A root's certificate near expiry | less than a year left of its twenty | once, then monthly |

One hour is twelve rounds of `tend`: a link that drops for minutes, the
everyday case of 0050, mails nothing, while a day without a root is
covered by the fallback and still told. **Who mails.** A condition
about this node (a foreign root, its own certificates as in keel#78) is
mailed by this node. A condition about a root is mailed by the other
roots' holders, not by every member, so one root down is a few mails
and not one per node; every member still shows it.

## etcd's quorum and regions

etcd stays **one cluster across regions**, with keel#78's heartbeat of
300 ms and election timeout of 5000 ms, set for 250 ms with loss. Every
write is committed by a majority of voters, so with voters in several
regions every registry write costs at least one round trip between
regions. That is acceptable for a control plane (0025: a few writes a
minute) and is the reason the hot path never writes to etcd (0050).

**The rule: losing any one region leaves a quorum.** No region holds as
many voters as the quorum.

| Regions | Voters | A region lost |
| --- | --- | --- |
| 1 | 3 or 5, in distinct sites (0028) | keel#78's case; the region is the mesh |
| 2 | 2 + 2 + 1, the 1 a data-less voter in a third location (0028's external arbiter) | either region of two: 3 of 5 remain, no further loss tolerated; the arbiter: 4 of 5 |
| 2, and no third location | 2 + 1 | the region with 1: etcd goes on; the region with 2: **etcd stops mesh-wide**. Warned, not refused |
| 3 | 1 + 1 + 1 at least; **2 + 2 + 1 recommended** | 1 + 1 + 1: 2 of 3 remain, no further loss; 2 + 2 + 1: 3 or 4 of 5 remain, and a single node failing inside a region of two costs it no vote |
| 4 or more | 5, spread so that no region holds 3 (2 + 1 + 1 + 1, or 1 each) | 3 or 4 of 5 remain |

Five voters is what etcd's own guidance recommends for production
(seven at most), and every voter more adds a round trip to the slowest
majority. Today keel#78 promotes every learner; with regions, the voters are
chosen by the rule and the other cloud advanced members are etcd clients
with their own certificates, not members (second round, point 7).
etcd 3.5 allows one learner at a time by default, which a cluster that
kept every other node as a learner would exceed.

**A region lost or cut off, under this rule.** The rest keep a quorum,
writes and their leader. In the cut off region: joins to the WireGuard
mesh go on (they never needed etcd), its root certifies its new nodes,
and their etcd learner add waits for a quorum, queued as keel#78 queues
it while the holder is unreachable; its members serve nothing
linearizable, and serializable reads of the last state they hold are
what the monitor (0040) and discovery (0026) may use while cut off. On
heal, members catch up from the leader's log, the queued adds run, and
the CRLs and bundles below spread.

**A region lost for good** is removed member by member under 0048's
rule, by each node's admitter or a trust root, and its voters replaced
elsewhere by the rule. When bad placement lost the quorum itself, etcd
needs its own disaster recovery (a snapshot restored with
`--force-new-cluster` on a survivor, then a new formation record from a
root): an operator's act, which keel documents and does not automate.

## A partition between regions

- **Local issuance continues.** Each side certifies its own nodes with
  its own root, and a side with no reachable root certifies with none
  and waits, as keel#78's join does.
- **Revocations made during the partition** take effect at once on the
  side that made them, and reach the other side on heal, through the
  rosters and etcd. They never conflict: each entry has one writer (the
  root that issued the certificate), and a CRL only grows, so merging
  after a partition is a union, with nothing to choose. The node a
  revocation is about is cut off first by its tombstone (0048's
  amendment), which removes its WireGuard peer on every member that
  takes it, and etcd listens only on the overlay; the CRL is the second
  line.
- **Bundles change only on a side that holds a majority of the roots.**
  A minority side keeps its bundle and takes the newer ones on heal. The
  majority side can revoke a minority side's root during a partition;
  keel says, in `approve`, when the root to be revoked has not been
  heard from, because a root that is unreachable is not a root that is
  compromised.
- **Nothing undone on heal.** A certificate one side issued is not
  revoked because the other side did not see it.

## Threat model

**A compromised region root** (its key, or root on its holder) can do
everything within its region and join nodes mesh-wide:

- issue intermediates for any address, its region's or another's, and
  so certify into etcd, mesh-wide, any node it admits to the mesh;
- with that, read and write the whole registry, since etcd has no roles
  here and any client certificate is a full client (as any member's is
  today);
- revoke what it issued, so take its own region's nodes out of etcd;
- sign learner records for nodes it certified, which etcd still has to
  accept by quorum.

It cannot, because of the majority rule and the merge:

- add a root, revoke another root, or change the bundle at all: one
  signature is never a majority of two or more;
- revoke another root's certificates: the merge drops serials another
  root issued;
- certify a node into the WireGuard mesh without admission evidence
  (0048's amendment), or impersonate another member's address to etcd
  without that member's WireGuard key: etcd checks the peer's address
  against its certificate, and WireGuard binds the address to the key;
- outlast its revocation: a majority marks it `revoked`, every member
  puts its intermediates' serials in the merged CRL at once and drops it
  from the trusted file at the restart; the nodes it admitted stay in the
  WireGuard mesh until their admitter or a trust root removes them.

**A majority of the roots compromised is the mesh compromised.** With
one root (keel#78) the one root is the majority, as today; with two,
neither can be revoked without its own signature, and the way out is
`distrust` on each member ("Revoking a whole root"); from three, one
compromised root is outvoted by the others. **A compromised member** that
holds no root key is keel#78's case, unchanged: its intermediate is
constrained to its own /128. **A stolen export** is worth its
passphrase.

## The migration from keel#78

**What keel#78 ships, so that regions need no rework** (tracker#60,
point 1):

1. a bundle file, `/var/lib/keel/etcd/bundle.json`, at epoch 1, one
   region (the holder's `installation.region`, or `default` when its
   spec names none, index 0), signed by the root; etcd's trusted CA file
   rendered from the bundle's active roots, even when there is one;
2. the region in every record the root keeps (`issued.json`, revocations)
   and in the grant, the formation record and the `issue` message;
3. CRLs kept per root fingerprint (`crl/<fingerprint>.pem`), and the
   file etcd reads written from them;
4. every check that today says "the root" written as "a root of the
   bundle, active".

A keel#78 that merged without them is converted by the next keel on
each member: `root.crt` becomes bundle epoch 1, `crl.pem` that root's
CRL; nothing is reissued.

**Then, adding the second region**, on built images:

1. Every member runs the keel that knows regions; `region create`
   refuses while a member's `probe` (keel#78) says it does not.
2. The new region's first node is installed with `installation.region:
   region-b` and joins with a token from `keel mesh invite --region
   region-b` on any member: it gets an address in the next free /112 and,
   with no root in its region, an intermediate from the fallback.
3. On it, `keel mesh region create` makes the root key there and proposes
   bundle epoch 2: region-b, its range, its root, signed by its root.
4. The operator runs `keel mesh region approve` on each existing root's
   holder until a majority has signed (with one existing root, that one).
5. Members take epoch 2 and restart etcd one at a time; once every voter
   has applied it, region-b's root certifies, and the first node
   re-anchors its intermediate under it.
6. The first region is untouched: its root, its intermediates and its
   addresses, all in range index 0.

A third region is the same, with two approvals needed.

## How it is carried out

Keel-Linux/keel#79 tracks the code changes multi-region needs, items 2
to 10 below; item 1 is keel#78's own.

1. **keel#78**: the four forward-compatible points above, before it
   merges.
2. **keel, the spec**: `installation.region`, its validation, and docs/spec.md.
3. **keel, allocation**: the region's /112 in `invite`, `invite --region`,
   and `join`'s check of the spec's region against the answer's.
4. **keel, the bundle** (`keel.mesh.etcdtrust`, pure, with its tests):
   the document, its signatures, the majority, the chain of epochs; the
   trusted CA file rendered from it; the rolling restart and the applied
   epoch.
5. **keel, the commands**: `keel mesh region create`, `approve`, `reroot`,
   `revoke` and `distrust`; `keel mesh etcd root export` and `import`;
   the yearly countersignature in `tend`.
6. **keel, status and alerts**: the region section of `keel mesh
   status`, `etcd.roots` in `keel diff`, the alerts of "The roots'
   status, and alerts" through `keel notify`, and the voters per region
   against the placement rule; confconsole's "Region roots" screen.
7. **keel, CRLs**: one per root, the merge and its filter, the merged
   file.
8. **keel, issuance**: the fallback to another root, 30 days, and the
   re-anchoring in `tend`; learner records at etcd's revision.
9. **keel, voters**: at most five, placed by the rule, the others
   clients (second round, point 7), after keel#78 merges.
10. **The test harness** (0050's profiles): a netns test with three
   regions of two namespaces each, 5 ms inside a region and 250 ms ±25 ms
   with 2% loss between regions.

Done when, on built images and not on machines assembled by hand: a
second and a third region are added by the steps above with etcd healthy
throughout; a region cut off for two minutes certifies a new node
locally while the others keep their quorum and writes, and on heal the
node becomes a learner and a revocation made on each side reaches the
other; with a region's root stopped, its new node is certified by
another root and re-anchored when it returns; a root revoked by a
majority leaves its members refused at the next handshake; a root's
CRL listing another root's serial revokes nothing; one root alone cannot
add or revoke a root, and with two, `distrust` on each member takes the
suspect one out; a root stopped for over an hour and a node on a
foreign root each send their mail, and confconsole, `keel mesh status`
and `keel diff` show the same.

## Consequences

- The spec gains one field, `installation.region`. Everything else of
  regions is state.
- keel gains `keel mesh region` (`create`, `approve`, `reroot`,
  `revoke`, `distrust`), `keel mesh etcd root export` and `import`, and
  a trust bundle per member; confconsole gains "Region roots"; `keel
  diff` gains `etcd.roots`.
- An operator with `security.alerts` set gets mail about the roots, at
  the thresholds above, with no configuration of their own.
- Each region's addresses come from its own /112, 65,535 each, up to
  65,536 regions in a mesh; the first region's are the addresses
  already given out.
- Adding or removing a root restarts etcd on every member, one at a time.
- A mesh in several regions writes to etcd at the speed of its slowest
  majority, about one round trip between regions per write.
- Two regions with no third location cannot survive the loss of the
  larger one, and cannot revoke each other's root: a third region, if
  only one small node, is what makes both possible, and the screens say
  so while it is missing.
- etcd's roles (a certificate allowed only its own keys in the registry)
  would narrow what a compromised root, or member, can write; they are
  not part of this note and would need their own.

## What this amends

- **0048, "Decided, third round", point 1**: "signed by its inviter"
  becomes "signed by a region root, the request relayed by the inviter",
  as keel#78 had already narrowed it to the one root; "the root CA key
  stays on the first node" becomes "each region's root key stays on its
  region's holder". "Joining, step by step", the inviter's address
  allocation: the next free address in its region's /112. The token's
  format is unchanged. The amendment (admission evidence, trust roots,
  tombstones) is unchanged and applied.
- **0025**: one etcd cluster for the mesh, unchanged; the site label is
  unchanged and sits inside a region; voters are placed so that losing
  any one region leaves a quorum.
- **0028, "Cloud advanced assumes three distinct sites, or two plus an
  external arbiter"**: unchanged within a region, and applied to regions
  by the placement table.
- **0021**: the monitor's channels carry the roots' alerts, raised by
  keel, not by a Monit check; `keel notify` and its channels are
  unchanged.
- **0037**: a root key is never in a backup set derived from the
  manifests; an encrypted export the operator chooses to store there is
  the operator's file, not a set.
- **0050**: unchanged; regions are how certification follows its
  premise, and their tests run under its profiles.
- **keel docs/spec.md and docs/mesh.md**: `installation.region`, and the
  bundle, the merged CRL, the region commands and the roots' status,
  when they are built (keel#79).

## Amendment (decided 2026-10-07): a region root issues every certificate

**Status: decided by the maintainer, 2026-10-07** (Keel-Linux/keel#83,
recorded in 0048's amendment of the same date). Implemented for the
single region case in keel 0.22.0; forward-compatible with the rest of
this note, which keel#79 still tracks.

- **Issuance.** "an intermediate per member, signed by a root ...;
  leaves issued by the member" becomes "every member's certificate,
  signed by a root, 30 days". A region root signs its region's members'
  certificates, relayed by the inviter; when it does not answer another
  active root signs, as point 2 says, and that certificate's 30 days are
  already the foreign root's limit, so re-anchoring is the next renewal
  at the home root. Name constraints no longer apply: the root sets the
  CN (the member's mesh identity) and the SANs (its /128 and ::1)
  itself, whatever the request asks.
- **etcd's users.** The CN is etcd's user, and auth is on; each region
  root's holder holds an admin certificate (CN `root`) and manages users
  and roles, the same for every root. "etcd's roles ... are not part of
  this note and would need their own" (Threat model) is what keel#83
  decided.
- **The merged CRL (forward-compatible note).** Members sign nothing:
  no member holds a CA key, so "signed with its own intermediate's key"
  in "What etcd does with a CRL" no longer applies. Each root still
  signs its own CRL on its holder, distributed as today. Since etcd
  reads one CRL file and does not check its signer, the merged CRL is
  signed by a root's holder, with that root's key: it carries the union
  of every root's CRL it verified, under "What the merge keeps"; a
  member takes it only when its entries are exactly the union it
  computes itself from each root's own CRL, which it verifies as
  before, and writes it for etcd. A member that cannot reach a holder
  keeps the last merged CRL it took, as "a revocation is never undone
  by silence" says.
- **Threat model.** A compromised region root can still issue
  certificates for any address (unchanged), and now for any member's
  name, so act as any member in etcd; it can no longer be any member's
  intermediate, of which there are none. A compromised member can no
  longer certify itself or anyone else into etcd, nor name itself
  another user.

