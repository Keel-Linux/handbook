# 0063: keel-ntfy, one alert server per site, outside the cluster that it watches

Date: 2026-10-22
Status: **decided by the maintainer, 2026-10-22** ("sim manda bala",
after the proposal in chat): a standalone `keel-ntfy` appliance, one per
site, as part of the infrastructure layer, and alerts sent to all of
them. The tenant model in section 4 was asked by the maintainer the same
day and is decided by the coordinator under the maintainer's delegation.

## What was asked

The maintainer asked how an alert of Monit or keel reaches a phone, then
whether an ntfy server can run in more than one place, then whether a
`keel-ntfy` server that is highly available across clusters is worth it.
The maintainer then decided on a standalone `keel-ntfy`, and asked for
the names `ntfy-br1.pop.coop`, `ntfy-br2.pop.coop` and `ntfy-br3.pop.coop`.

## Why (brief section 10)

1. **Why the current approach is not enough.** keel sends alerts by
   email, Telegram, ntfy and a webhook (0021, keel notify). The ntfy
   channel takes one URL. The only ntfy server that Keel can use today is
   the public `ntfy.sh`, where the name of a topic is the only protection:
   whoever knows it reads the alerts and can send false ones. One server
   is also one point of failure.
2. **Whether it can be made to work.** It can, with no new package: the
   ntfy server is in Debian (`ntfy` 2.11.0 in trixie, 2.27.0 in sid). It
   keeps its state in SQLite files: a message cache and a user database.
   The phone app subscribes to the same topic on several servers at once.
3. **Why this is better.** An alert must not depend on what it reports.
   An ntfy server on a pair would depend on the VIP, etcd, the mesh and
   the replication: the parts whose failures it must report. When etcd
   loses quorum, such a server can fail with it. Three servers that know
   nothing of each other deliver while any one of them is up, and a cut
   between sites cannot stop all three.

## Decision

### 1. One standalone server per site

- **`keel-ntfy` is an appliance of one node.** It has no pair, no VIP, no
  etcd and no Syncthing: its manifest turns those overlays off in every
  mode. It is never a member of the mesh that it watches.
- **One instance per site**: `ntfy-br1.pop.coop`, `ntfy-br2.pop.coop` and
  `ntfy-br3.pop.coop`, each in a small container (256 to 512 MiB).
- **Not highly available across clusters.** Rejected for the reasons in
  "Why" item 3, and because SQLite files cannot be replicated by file
  while they are open (a copy can be corrupt; 0050 replicates no database
  by file).

### 2. The layer

- **Base: `web`.** Keel Web's nginx terminates HTTPS, which the phone app
  needs, and proxies to ntfy on the loopback, with the long timeouts that
  a subscription stream needs.
- **The package is Debian's `ntfy`**, from trixie. No Keel package.
- **Access is closed by default**: `auth-default-access: deny-all`. An
  account publishes, and each person who reads has an account with read
  access to the topics of their tenant. Tokens are secrets of the
  instance description (`secrets`), never in the image.
- **Anubis does not challenge ntfy.** The clients are apps and keel, not
  browsers.

### 3. keel sends to every server

The `ntfy` channel of `monitor.notify` accepts a list of servers as well
as one. keel sends each alert to every server in the list, and the alert
counts as taken when at least one server took it. Each server has its own
token file. One URL, as today, stays valid.

### 4. Tenants

- **A tenant is a set of topics with a common prefix**, `<tenant>-...`,
  and accounts whose access is limited to that prefix by ntfy's access
  control.
- **The three servers serve every tenant.** Each tenant's spec lists the
  same three URLs with its own publish token.
- **A tenant that needs its own servers gets its own `keel-ntfy`
  instances**, as a later step, with the same image. Nothing in this
  decision blocks it.

## How it is carried out

1. `Keel-Linux/keel-ntfy`: the layer on `web`, the manifest, the nginx
   route, the first boot (the admin account, the publish account and its
   token from the instance description), the boot test, and the image
   gate (0061).
2. `Keel-Linux/keel`: the list form of the `ntfy` channel, with tests.
3. Three containers, one on each of BR1, BR2 and BR3, from the built
   image. The names point to them through the pop.coop edge.
4. The Keel nodes of the migration send their alerts to the three
   servers, and the responsible people subscribe on their phones.

Done when an alert from a Keel node reaches a phone through each of the
three servers, and still reaches it with any two of them stopped.

## Consequences

- Each person gets each alert up to three times. For alerts this is
  accepted: none is lost.
- The message cache is per server. A phone that was offline sees, on each
  server, the messages that server kept.
- Three more small containers to update, one per site.

## Amendment of 2026-11-10: the alert topic of the Keel project

Decided by the coordinator under the maintainer's delegation
(2026-11-10), before step 4 of "How it is carried out" starts. Evidence:
`evidence/2026-11-10-alert-topic-and-image-ci-timer.md`.

1. **The alert topic of the Keel project is `keel-alerts`.** Its prefix
   is `keel-`, so it is in the Keel tenant (section 4). Each node of the
   migration sends its alerts to this topic on each server. The notice
   of an upgrade that waits (0085) goes to the same topic, because it
   uses the channels that the node already has.
2. **One topic for all nodes, not one topic for each node.** A message
   of `keel notify` gives the name of the node. A person subscribes one
   time on each server, and a new node needs no change on a phone. A
   second topic is added only when a group of people must get only a
   part of the alerts.
3. **The accounts.** The account `publisher` can write and cannot read.
   A node sends with a token of this account, from a secret of its
   instance description. Each person who reads has an account that can
   read `keel-*` and cannot write. The first such account is that of
   the maintainer.
4. **A message stays 12 hours on a server** (`cache-duration` of the
   image). A phone that was offline for a longer time does not get the
   message. This is accepted for alerts. It is a reason for the 7-day
   reminder of 0085.
5. **The Android app needs no change on the servers.** It holds its own
   connection to each server. The iOS app needs `upstream-base-url` on
   each server to deliver immediately. That setting is not on, and it is
   not decided here.

State on 2026-11-10: ntfy-br1 and ntfy-br2 take and deliver a message on
`keel-alerts`. ntfy-br3 does not answer. No node of the migration sends
alerts yet, thus step 4 is open.
