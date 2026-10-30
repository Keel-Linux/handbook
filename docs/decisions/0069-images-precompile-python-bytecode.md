# 0069: Images precompile Python bytecode, with timestamp invalidation

Date: 2026-10-21
Status: **decided by the maintainer, 2026-10-21; confirmed by the
maintainer in chat, 2026-10-30**: every appliance image
ships Python bytecode, compiled at build time. It reverses the image
build's py3clean policy and costs about 18 MiB unpacked. Evidence:
common/evidence/2026-10-21-bytecode-precompile.md.

## What was decided

- `common/mk/turnkey.mk` compiles `.py` in `/usr/lib/python3.[0-9]*`,
  `/usr/lib/python3/dist-packages`, `/usr/lib/confconsole` and
  `/etc/python3.13`, after the product deb and before `seal-root`.
- Timestamp invalidation (`--invalidation-mode=timestamp`), as Debian,
  Arch and Fedora use; not the hash mode, which hashes on every import.
- The source mtimes are set to `SOURCE_DATE_EPOCH` before compiling, and
  the `.pyc` mtimes after, so the header matches the layer tar's
  `--mtime` and the result is byte-identical across builds.
- Default optimization only. Nothing in the image runs `python -O`, so
  `-o 1` and `--hardlink-dupes` would double the bytecode for nothing.
- The step runs only when `SOURCE_DATE_EPOCH` is set: without it the
  layer uses the product's git time, and the unclamped `.pyc` would be
  stale at the first import.
- `conf/turnkey.d/zzz-clean-pycs` stays, so the base is clean before the
  late compile. The inithooks `bin/*.py` are `__main__` and are not
  compiled.

## Why

The image shipped no `.pyc` anywhere, so every first import compiled its
modules. `keel --help` took 632 ms on the first call and 184 ms after;
importing confconsole's modules took 320 ms cold and 61 ms warm. Debian,
Arch and Fedora all ship bytecode; Fedora's timestamp mode plus the
`SOURCE_DATE_EPOCH` clamp is the reproducible form of what they do.

## Consequences

- About 18 MiB unpacked (1089 files) and about 1.2 s of build time.
- The first call of keel drops to about 191 ms, and confconsole's imports
  to about 68 ms, on the first boot.
- An image built without `SOURCE_DATE_EPOCH` keeps the old behavior.
- Package-level notes that a package excludes bytecode (tklbam, fab,
  turnkey-chroot release notes) are about their own `.deb`, not the
  image, and are unchanged.

## What this amends

The image build's py3clean policy. No earlier note decides it; 0021's
`python3 -B` is about a running resource monitor and still holds.
