# 0074: Vaultwarden as Debian packages in the Keel archive

Date: 2026-11-05
Status: **decided by the maintainer, 2026-11-05** (the .deb option). The
toolchain point below is decided by the coordinator under the maintainer's
delegation.

## What was found

- Debian trixie has no Vaultwarden package.
- Upstream (dani-garcia/vaultwarden) publishes no server binary. Its only
  binary distribution is a container image. Keel uses no container runtime,
  so that path is closed.
- Vaultwarden 1.37.5 (2026-11-01) sets `rust-version = "1.97.1"` in
  `Cargo.toml`. Debian trixie has rustc and cargo 1.85.1, so the Debian
  toolchain cannot build it.
- The web vault (dani-garcia/bw_web_builds v2026.10.1) is published as a
  tarball with a detached signature (`.tar.gz.asc`) and `sha256sums.txt`.
- The first keel-vaultwarden build failed at `conf.d/main`, because no
  binary was in the layer.

## Decision

1. Two packages in the Keel archive, source in `Keel-Linux/vaultwarden-deb`:
   - `vaultwarden`: the server, built from the upstream tag with the
     `sqlite` and `postgresql` features. It ships the binary, a system user
     and a systemd unit.
   - `vaultwarden-web-vault`: the web vault, unpacked into
     `/usr/share/vaultwarden/web-vault`. The build checks the `.asc`
     signature and the sha256 against a key that the source repository pins
     by fingerprint.
2. The build uses the official Rust toolchain at the exact version that
   upstream's `rust-version` names, from `static.rust-lang.org`, with its
   GPG signature checked before use. The toolchain exists only in the build
   chroot on the build host. No package and no image contains it.
3. The packages go to `trixie-testing` first, signed with the archive key,
   like every other Keel package.
4. `keel-vaultwarden` installs both packages from its `plan`. Its
   `conf.d/main` builds nothing.
5. A new upstream release of either part is rebuilt and published again.
   Vaultwarden holds passwords, so an upstream security release follows
   the 7-day rule of decision 0073 for network-facing packages.

## Not chosen

- Build with cargo inside the layer build (`conf.d/main`): slow, puts a
  compiler and a crate download into every layer build, and the result is
  not a versioned package that cron-apt can upgrade.
- An older Vaultwarden that builds with Rust 1.85: a password vault must
  not stay on old releases.
- The upstream container image: no container runtime in Keel.

## Consequences

- The build host needs about 2 GB free and some minutes of CPU per
  Vaultwarden build. Disk on the build host is tight (under 7 GB free on
  2026-11-05).
- Each new upstream Rust requirement changes the pinned toolchain version
  in the source repository.
