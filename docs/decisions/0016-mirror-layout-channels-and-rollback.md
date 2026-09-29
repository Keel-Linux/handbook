# 0016: Mirror layout, channels and rollback

Date: 2026-09-28
Status: **accepted**, decided by the maintainer 2026-09-28. Implemented in
Keel-Linux/keel (client) and Keel-Linux/apt (publisher); the client landed
first on purpose, see "Order of work" below.

What the maintainer decided is the layout and the expiry rule
(Keel-Linux/apt#13). "Which key signs a channel", and with it an
unattended signing key on the build host, is key custody, which BRIEF
section 11 reserves for the maintainer: that section is a proposal until
the maintainer confirms it, and until then no refresh timer is installed.

## What was wrong

`https://mirror.keellinux.org/layers/` was flat and mutable. Measured on
2026-09-28:

    core.manifest   core.tar.zst   core.tar.zst.sha256
    lamp.manifest   lamp.tar.zst   lamp.tar.zst.sha256
    ...

One name per layer. Publishing a new `core` overwrote what every appliance
resolves. There was no pin, no rollback, and no way to say which layer set a
running instance was on. The manifest pinned the *packages* (`pool
2026-09-27`, `packages_sha256`) and nothing pinned the layer, so "an
appliance updatable from Keel upstream" meant an appliance following a moving
name, with `keel pull` free to change the base under it and no way back.

## The layout

Exactly one object in the mirror is mutable, and it is a signed pointer.

1. **Blobs** at `layers/sha256/<digest>`. Immutable, never overwritten,
   never deleted, deduplicated across releases. The layer was already
   content addressed in its manifest; this makes the storage obey the model.
2. **Releases** at `layers/<release>/<rev>/<name>.manifest`. Immutable and
   human readable, referring to blobs by digest.
3. **Channels** `layers/stable` and `layers/testing`. The only mutable
   files, each clear signed and carrying a timestamp and an expiry.

The flat names stay, as hard links to the blobs, until their removal is its
own change. That hard link is only compatible with "a blob is immutable"
because the publisher validates the name it links from: `tarball` must be a
plain file name ending `.tar.zst`, since `ln -f` unlinks what it names and
`tarball sha256/<digest>` would otherwise replace a published blob, or
`tarball stable` a channel pointer.

**The pointer is one clear signed file, not a file beside a detached
signature.** Two files are two mutable objects, and a mirror could serve a
new pointer with an old signature or the reverse; one file cannot be skewed
against itself. It is the same reason apt has `InRelease`. The consequence
is worth stating because it shapes both implementations: clear signing dash
escapes the body and does not cover trailing whitespace, so the bytes on the
mirror are not the bytes that were signed. A reader must therefore take the
body from the verifier's own output and never parse the file, which is what
made the two verification bugs found in review possible, and what both sides
now do.

### Why the revision, and not the release alone

Versioning by release alone is insufficient because two publications of the
same release overwrite each other. Our releases are dated, and a second
publication on one date (a rebuild to pick up a security update, a
correction to a layer that went out wrong) is exactly the case that matters
and exactly the one a date cannot distinguish. The revision is what makes
`<release>/<rev>` name one set of bytes for good. It is recorded in the
release's own `MANIFEST`, inside what the release key signs, so the release
carries its own identity rather than having one assigned later by whoever
publishes it.

### Why a signed pointer with an expiry is not optional

Without it, a mirror that is stale, hostile or simply broken can freeze a
client on an old and vulnerable release **just by not updating**, and the
client cannot tell the difference between "nothing new" and "I am being held
back". Those two must not look the same, and only a timestamp inside a
signature separates them. That is the freeze attack, and it is why TUF
exists.

So the pointer carries `signed_at` and `expires_at`, and **an expired
channel is an error at the client, never a warning.** `keel pull` exits 19,
`CHANNEL_EXPIRED`, and fetches nothing. A warning would be read once and
then filtered, which is the same as not having it.

The pointer also carries the sha256 of every layer manifest in the revision,
so the signature covers the content and not merely a directory name. The
chain is then complete and nothing along it is the mirror's word: signature
→ manifest digest → blob digest.

### Rollback is moving a pointer

Because a blob is never deleted, every revision that was ever published can
still be assembled. Rolling back is `keel-channel set stable <release>
<rev>` on the publishing side, and `keel pull --release <release> --rev <N>`
on a single instance.

A rollback by revision verifies too, and not against a channel, because by
then no channel names that revision. Each revision keeps the pointer that
was first signed for it, at `layers/<release>/<rev>/revision`, written by
the publisher when it installs a channel and never replaced. `keel pull
--release R --rev N` verifies that file by the same chain and requires it
to name the revision it is filed under; only its expiry is not enforced,
because an earlier revision is old on purpose. Two limits follow and are
accepted: a revision no channel ever named has no such file and cannot be
pulled by revision, and on the publishing side `set` can move a channel
back only to a release whose tree is still staged on the build host, since
the layer digests come from that tree.

The client refuses a *pointer* that goes backwards (exit 20,
`CHANNEL_ROLLBACK`): a mirror does not move an appliance backwards, an
operator does, with `--allow-rollback` or by naming the revision. Reclaiming
space is a policy decision to be taken deliberately, and never an overwrite.

## Which key signs a channel

**The channel key**: the key that lives unprotected on the build host, which
today is the key of the `trixie-staging` distribution (decision 0011). It is
named as a role, `KEEL_CHANNEL_KEY`, so it can be split into a key of its own
later without a code change. **Not the release key.**

The reason is the expiry. A pointer must be re-signed before it expires, and
with a seven day expiry that is a daily job. The release signing subkey is
passphrase protected and the agent forgets the passphrase ten minutes after
it is typed (decision 0005). A design that needs the maintainer at a terminal
every day is a design that will be bypassed inside a week, by lengthening
the expiry until it means nothing, which is worse than not having one. So the
pointer is signed by a key that needs nobody, and a systemd timer does it.

What that key may say is deliberately narrow:

- It **cannot make a release.** Every revision it can name is one the
  maintainer staged and signed, and every manifest it names is pinned by its
  sha256 inside the pointer's signature.
- It can say **which of those is current, and until when.** That is all,
  and "until when" is bounded; see the ceiling below, without which it is
  not a narrow claim at all.

This extends decision 0011 rather than contradicting it, and the distinction
is worth stating plainly because the wording there is strict. 0011 says the
staging key means only that the build host produced the bits, and that no
appliance may be configured to read the staging *archive*. Both still hold.
Signing a channel is a strictly weaker claim than signing a release: it
selects among artefacts a person already stood behind. An unattended key can
make that claim honestly.

**The threat the expiry actually closes is the mirror**, which is a
different machine (`keellinux.org`, the public services VM) and holds no
key. Stale, broken or hostile, it cannot hold an appliance on an old release,
because the pointer it is serving stops being believable. The expiry does
**not** close a compromised build host: whoever holds the online key can keep
re-signing a stale pointer. Nothing signed on the build host could close
that, and saying so here is better than implying a guarantee we do not have.

**Seven days, refreshed daily, and never more than thirty.** That ratio is
the whole of the operational design: six consecutive failures of the refresh
are survivable and a seventh is not. Long enough to sleep through a weekend
outage, short enough that a build host left broken for a week stops
appliances updating rather than quietly holding them still.
`keel-channel-refresh.timer` runs at 04:30 and `refresh` never changes which
revision a channel names: it re-signs the digests the pointer already
carries, so a build tree that has moved on cannot be slipped into the mirror
by a job nobody watches. Moving a channel is `set`, and `set` is a person.

### The ceiling on "until when", which the first draft of this note left off

An unbounded expiry is not a weaker version of the freeze attack, it is a
better one. One signature with `expires_at 2126-01-01` pins an appliance to
an already published, known vulnerable revision indefinitely; the attacker
need not keep re-signing, and the client's rollback refusal never fires
because the revision does not go backwards. Both the client and the
publisher accepted that, and `KEEL_CHANNEL_TTL_DAYS=100000000` produced a
pointer expiring in the year 275817 without a word.

That is this note's own stated failure mode, "lengthening the expiry until
it means nothing", offered two paragraphs earlier as the reason a person
must not be in the loop daily. The design identified the lever, removed the
human who would pull it, and left the lever unguarded.

So: **`expires_at - signed_at` is at most 30 days, enforced by the client**,
which is the side that has to be convinced, and by the publisher too so this
host cannot write a pointer a client will refuse. The bound does not live in
an environment variable on the machine holding the key. A pointer signed
more than an hour ahead of the client's clock is refused as well; the only
honest reasons for any gap are drift and the moment of signing.

### How the channel key is retired

Putting a key online makes its theft the event to plan for, and the plan has
to be written down because the obvious one does not work by itself.

**Revoke, rotate, and ship the revocation in the keyring.** For that to mean
anything the client must refuse a revoked key, and this is exactly where the
implementation was wrong: `gpgv` exits 0 for a signature by a revoked or
expired key and still prints `VALIDSIG`, with "Good signature from" on
stderr, withholding only `GOODSIG`. Both halves accepted it, so revocation
did nothing, and a revoked subkey of a pinned primary passed as well,
which is not hypothetical, since `apt/keys/keel-archive-keyring.asc` already
carries a signing subkey this project has revoked once. Both now require
`GOODSIG` and refuse the retirement lines by name. `docs/traps.md` records
the measurement.

**The awkward part, stated rather than left to be discovered.** A thief who
holds the channel key can delay the very keyring that would retire them, by
signing a pointer at the ceiling and freezing appliances on an old revision
until it expires. The ceiling is what bounds that to thirty days rather than
for ever, and it is the reason the ceiling is not a detail. Retiring the key
therefore has two parts that must both happen: a new keyring reaching
appliances, which travels as a package through the archive and not through
the channel, and the old key's pointers ageing out. Nothing in the mirror
makes the first happen; that is an archive problem, and it is why the
keyring is not shipped over the channel it protects.

**Rotation without theft** is the easy case and works today: `set` a pointer
with the new key, ship the new keyring, and appliances that have the old
keyring keep working until their pointer expires. Because `--channel-signer`
and `$KEEL_CHANNEL_SIGNER` accept several fingerprints, a rotation can be
overlapped deliberately.

### The expiry is only as good as the client's clock

The check is `now >= expires_at` against the appliance's own clock, and
nothing in the design can check a clock. Both directions were considered and
neither is obvious:

- **clock ahead:** every pointer expires, `keel pull --channel` fails on
  every appliance at once, and the first version of the message said only
  "the mirror is not being updated, or is holding this instance back", so a
  fleet-wide NTP failure would send the operator to the mirror. The message
  now prints what the machine thinks the time is and names a wrong local
  clock as one of the three explanations. The appliance is stalled, not
  bricked: the flat layout and an explicit revision still work.
- **clock behind:** dead pointers still look fresh and the freeze attack the
  expiry exists to stop succeeds. A container restored from a snapshot is
  exactly that case.

We accept this, because the alternative is trusting the mirror to say what
time it is, which is the thing being defended against. What the design owes
in return is a message that does not misdiagnose it, and that is now the
case.

## The refresh has no delivery path yet, and publication is manual

This is the one part of the operational design the implementation does not
have, and it is recorded here rather than implied away.

`keel-channel refresh` re-signs the pointers **on the build host**, in
`$KEEL_RELEASE_ROOT/channels`. Nothing ships them to the public host: the
only thing that installs a pointer publicly is `keel-publish-mirror`, which
takes a release date and a tunnel the maintainer opens. So the pointer
clients actually read expires seven days after the last **publication**,
however faithfully the daily timer runs, and "six consecutive failures are
survivable" measures a refresh no client sees.

**The decision.** A channels-only publication is the right mechanism and is
deferred, because it is a second way to write the public mirror and wants
its own thinking about who may run it and what it may touch. Until it
exists the rule is: **a release is published at least as often as the time
to live, or the time to live is raised to cover the gap, within the thirty
day ceiling.** The timer is still correct and still wanted: it keeps the
build host's copy fresh so that a publication has something current to
carry, and it fails loudly when the key is gone, which is worth knowing
before a release rather than during one.

What this must not become is a reason to raise the ceiling. The ceiling
exists because of the attack above; the delivery gap is an operational
inconvenience. If publication cannot keep up, the answer is the delivery
path, not a longer expiry.

## Order of work, and why it mattered

The **client** landed before the publisher wrote the new layout. A client
that cannot read the flat layout, shipped before the mirror is converted,
strands every appliance already in the field: it would look for
`layers/stable` on a mirror that has none. So `keel` reads both layouts, the
flat one is unchanged, and a `keel pull` that names no channel behaves
exactly as it did. Removing the flat layout is a separate, later change, and
it needs its own decision about how long an un-updated appliance is
supported.

## What `main` is, and the branches

`main` stays the trunk and is always the latest. Release branches are cut
only when the next Debian opens, not per milestone and not per release
revision: a release revision is a published artefact, not a branch. The forks
keep `master` as their default branch so they stay mergeable with upstream
TurnKey; only the project's own repositories use `main`.

## What this does not decide

- **When a blob may be deleted.** Never, by this note. Reclaiming space is a
  policy decision with its own note, and it must start from which revisions
  are still reachable from a pointer anyone might roll back to.
- **Removing the flat layout.** Separate change, separate note.
- **A third channel.** `stable` and `testing` are the two there are; a third
  is a decision, not a configuration value, and both implementations refuse
  anything else rather than creating it.
- **How the channel keyring reaches an appliance.** No repository packages
  `keel-channel-keyring.gpg` yet, so `keel pull --channel` on a stock
  appliance refuses for want of a keyring. It fails closed, which is right,
  but the feature is not usable until the keyring ships, and it must ship
  through the archive, not through the channel it protects, which is the
  same constraint the retirement paragraph above runs into.
- **A channels-only publication**, which is what the delivery gap above
  needs.

## Traps found while implementing this

Both are in `docs/traps.md` in full; recorded here because each one would
have shipped a check that passes over code that does not work.

- **`gpgv` writes the plain text of a document whose signature it refused**,
  and neither its exit status nor a `VALIDSIG` line establishes that the
  signing key is good: a revoked or expired key gives exit 0 and
  `VALIDSIG`, withholding only `GOODSIG`. The first version of that entry
  recorded the insufficient rule, which is the trap sprung inside the file
  that exists to prevent it.
- **In one `local` declaration, bash expands every word before it assigns
  any of them**, so `local a="$1" b="$dir/$a"` gives `b` the value `a` had
  *outside* the function, which is usually nothing. It cost a publication
  step that silently did nothing under `set -u`.

## Implementation

- Client: Keel-Linux/keel#34 (`keel/layers/channel.py`,
  `keel/layers/signature.py`, `keel/layers/layout.py`, `keel pull
  --channel`, `keel inspect --check-channel`). The suite asserts each
  refusal above against real revoked and expired keys; the coverage figure
  is in the pull request, where it can be qualified, because a green gate
  was compatible with the verifier never running at all.
- Publisher: Keel-Linux/apt#14 (`bin/keel-channel`, `lib/channel.sh`, the
  content addressed publication in `lib/mirror.sh`, the `revision` field in
  the release `MANIFEST`, `keel-channel-refresh.timer`).
