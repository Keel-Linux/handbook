# 0095: Two promise levels, a parked state for notes, and one work queue

Date: 2026-11-23
Status: **accepted 2026-11-23.** The maintainer approved the content in
chat on 2026-11-23: "já tô aprovando, pode mandar bala" (I approve it,
go ahead).

## What was asked

Keel is also the laboratory of the maintainer. Each application that he
asks for is a real demand of real customers in a real data centre. Thus
many fronts are correct work. Until now, each front got the same promise.
A decision note that stopped before the end then looked like a promise
that Keel did not keep.

## Why (brief section 10)

1. **Why a rule is necessary.** One promise for every front makes each
   stop a broken promise. The stable catalogue then grows at the speed
   of demand, and Keel cannot maintain it.
2. **Whether it can be made to work.** It can. The testing channel
   (`trixie-testing` and `layers/testing`, 0016) and the stable channel
   already exist. The repository `Keel-Linux/tracker` and its roadmap
   issue tracker#1 already exist.
3. **Why this is better.** The laboratory moves at the speed of demand.
   The product grows only when Keel can maintain it. The gates and the
   security rules stay the same for both.

## Decision

### 1. Two promise levels

- **Laboratory.** This is what the data centre needs now. It is in the
  testing channel only. Keel gives no promise to people outside: no
  support, no upgrade path, no place in the catalogue. A laboratory
  image can have fewer functions than its note describes.
- **Product.** This is the stable channel and the Proxmox index. An
  image goes to this level only when Keel can maintain it:
  1. Its third-party packages are in the automatic update pipeline of
     0096 (in work).
  2. It has an upgrade test (0090): its layer has its file of upgrade
     checks, and it is on the list of 0090 item 2.
- The stable catalogue grows slowly. The laboratory grows at the speed
  of demand.

### 2. The same gates and the same security at both levels

1. Real customers use laboratory images. Thus the security rules are the
   same at both levels: the node is closed by default, and its
   third-party packages are up to date (0073).
2. The laboratory level changes only the promise. It does not change a
   gate. No image is published before it passes commissioning (0075) on
   BR1 and BR2, a testing pre-release included. Each function that a
   laboratory image ships passes commissioning.
3. "Fast" means that a laboratory image does not wait for item 1 of the
   product level. It does not mean that a gate is skipped.

### 3. The parked state for a decision note

A note that stopped gets the status **parked**. Its status line gives
one line: why it stopped, and what is missing to continue. The index
shows the state in this form:

`parked YYYY-MM-DD: <why it stopped>; missing: <what is missing>`

A parked note is not a rejected note. It goes back to its earlier state
when the missing item comes.

### 4. One work queue

1. One front is "now". An ordered list of fronts is behind it.
2. Tracker#1 of `Keel-Linux/tracker` holds the order. Each front has one
   issue in `Keel-Linux/tracker`.
3. An urgent demand of a customer can go before the front that is "now".
   Before the change, write the stop point of the interrupted front as a
   comment on its tracker issue: what is done, what is next, and where
   the work is.

### 5. Each new request gets a level

When a request enters the queue, its tracker issue names its level in
the first line: laboratory or product.

## What this amends

- 0083: an image goes to stable only when it also meets the product
  level of section 1.
- 0090 item 4: a new application joins the list of item 2 when it goes
  to the product level.
- 0073: its rules also apply to laboratory images.

## Open points

1. The images that are in stable today do not meet item 1 of the
   product level, because 0096 is not built. They stay in stable. Each
   one joins the pipeline when 0096 is built.
2. This note changes the status of no existing note. The maintainer
   decides which notes become parked.
