# 0012: Pinning the packages an image is built from

Status: **proposed**, 2026-09-27. Needed by 0010, which is judged on
equivalence between two builds, and by the reproducibility claim the project
makes about itself.

## What is wrong today

`SOURCE_DATE_EPOCH` makes the squashfs and the ISO reproducible from one
`root.patched`, and `root.patched` itself is not reproducible, because nothing
says which package versions go into it. The daily self check has reported
`drift` every morning since it was switched on, for that reason and no other.
A signal that is always red is a signal nobody reads.

It also makes 0010 unmeasurable. Two control builds of the same recipe already
differ in 173 files, so "equivalent" currently means "equivalent within a
noise floor we did not choose".

## The three ways, and what each one actually promises

**Record the versions only.** Write the exact version of every package into
the layer manifest and pin with apt preferences. Cheap, and it is a promise
that cannot be kept: Debian removes superseded versions from the archive, and
`archive.turnkeylinux.org` keeps no snapshots at all, so within weeks the
recorded versions are no longer fetchable and the record documents an image
nobody can rebuild.

**Build against snapshot.debian.org.** Authoritative and signed, and it costs
us no storage. It also makes every build depend on a third party service that
is slow, rate limited and periodically unavailable, and it covers Debian only,
not the TurnKey packages our images install.

**Capture what we install into our own archive, per release.** Self contained,
fast, and it works with the machine offline. It costs storage and a step that
captures. For a project whose stated goal is a sovereign cloud, this is the
only one of the three that makes the claim true: being able to rebuild an
image without asking anybody's permission is what sovereignty means here.

## Proposed

All three, in their proper roles:

1. The exact versions are recorded in the layer manifest. That is the record,
   and it is what a rebuild compares against.
2. The `.deb` files those versions name are captured into a per release pool
   in our own archive, and a rebuild of that release installs from that pool.
   Scale: `core` installs 412 packages, `nodebb` 830, an installed footprint of
   831 MiB for core. The implementation measures the pool size as its first
   step, because that number decides whether a pool is kept per release or per
   milestone.
3. `snapshot.debian.org` is the recovery path for a package that predates the
   capture, not a build dependency.

## Proof

The daily self check reports `match` for `core` on two consecutive mornings,
having reported `drift` every morning before. Then the same for one appliance
layer. No other evidence counts: passing once can be luck, and the check is
the instrument the project already trusts for this question.

## What this does not cover

Reproducing `root.patched` bit for bit also needs install time state out of
the image, which is a separate matter already measured by the M0 gate: 49
differing files, all of them install time state. Pinning is the prerequisite,
not the whole answer, and the gate's allow list stays the record of what is
legitimately allowed to differ.
