# 0072: A release that publishes layers and writes no Proxmox index

Date: 2026-10-29
Status: **decided by the maintainer, 2026-10-29** (option A2 in chat).

## What was asked

The appliance gate (`test-appliance.yml` in `Keel-Linux/.github`) boots
the layer that the public mirror serves at
`https://mirror.keellinux.org/layers/<appliance>.manifest`. The gate
compares the parent of that layer with the core manifest at the same
source. Stable 1 (2026-10-26) published core, web, lnmp, lnpp and ntfy
again. It did not publish mariadb, postgresql and redis again. Their
layers on the mirror still name the old core as parent, so the gate
fails on every pull request of these three repositories.

To publish a layer, the build host runs `keel-release`. Every release
that is not staged writes Proxmox index records into
`releases.keellinux.org/pve/aplinfo.dat`. The index is cumulative, and
there is only one: no testing index exists. Stable 1 removed
keel-postgresql and keel-redis from the index on purpose (stable-1 plan,
answer 5), and keel-mariadb was never in it. A release of the three
layers would put them in the index that stable users see.

A staged release (`--staging`, decision 0061) writes no index, but it
signs with the staging key and never goes to the public mirror. The gate
must not trust the staging key.

## Decision

1. `keel-release` gets the option `--no-index`. With it, the release
   builds, stages and signs the layers, the templates and the MANIFEST as
   usual, with the main and images keys. It does not read an index base,
   it does not write `pve/aplinfo.dat` and it does not sign one. The
   MANIFEST records `index none`.
2. `keel-publish-mirror` needs no change. A MANIFEST that lists no
   `pve/` file installs no index and records no index base. Give it
   `--no-channels`, so that no channel pointer moves.
3. `--no-index` cannot be given with `--drop-from-index`, because it
   writes no index to drop a record from. It also cannot be given with
   `--staging`, which already writes no index.
4. The release logs `no-index: no pve/aplinfo.dat; the Proxmox index on
   the mirror stays as it is` once at the start and once before signing.
5. Before and after the publication, the operator records the sha256 of
   `releases.keellinux.org/pve/aplinfo.dat`. The two values must be the
   same. The evidence file of the release holds both values.

## What this does not do

- It does not make a testing index or a testing channel.
- It does not make the layers private. The flat manifests and the
  tarballs are public on the mirror. The templates are public files in
  `images/`, but no index lists them, so Proxmox does not offer them.
- It does not change the gate, its source or the keys it trusts.
- It does not decide which pool and which track a layer is built from.
  A release with `--no-index` uses the same pool rules as any other
  release.

## Why (brief section 10)

1. **Why the current approach is not enough.** The only way to put a
   layer on the mirror also changes the Proxmox index. To unblock a
   repository gate, the operator must publish an appliance that the
   maintainer took out of the index.
2. **Whether it can be made to work.** The publication path already
   handles a release without `pve/` files. The change is one option and
   its checks in `lib/release.sh`.
3. **Why this is better.** The index changes only when the maintainer
   decides to put an appliance in it or to take it out. A layer can be
   published for the gate and for `keel pull` without that decision.
