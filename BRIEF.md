# Keel: Agent Brief

Working name: **Keel**. "TurnKeel" is a community nickname only and must never appear in package names, domains, repository names or file paths (trademark). Lineage is stated in prose: "compatible with TurnKey Linux appliances".

This brief is the standing instruction set for the agent responsible for the fork over the coming weeks. Read it fully before touching code.

## 1. Mission

Keel is a fork of TurnKey Linux 19 (Debian 13 "Trixie"). Its purpose is to make the TurnKey system-container appliance (LXC) behave like a cloud instance:

- declared in a single file, applied idempotently;
- built reproducibly from layers, addressed by content, signed;
- reachable end to end over IPv6 with its own certificate and identity;
- maintainable across years and across major versions.

**confconsole is the operator's single surface.** Every operation it exposes must also run headless, from the same code path, so that the TUI is a client of the library and never the place where logic lives.

## 2. Non-goals

- No Docker, no docker-compose, no Kubernetes, no OCI runtime: not in builds, CI, tests, examples or docs. The container model is the *system container*: full init (systemd), journal, cron, SSH, filesystem-level backup. That is a feature. We borrow OCI's *distribution* ideas (layers, content addressing, signed manifests), never its runtime model.
- No multi-host orchestration, fleet management or federation in this codebase. Keel describes and manages one appliance. Fleet tooling lives elsewhere and consumes Keel's spec format.
- No Alpine "micro" line yet. If it ever happens it is a parallel line, never a base swap.
- No rewrite. Fork, keep history, fix in place.

## 3. Diagnosis: what is being corrected

| # | Problem in TurnKey | Correction in Keel |
|---|---|---|
| 1 | Monolithic images (ISO, Proxmox `tar.zst`): no layers, no cache, no reuse | Three-layer builds (core / stack / app), published separately |
| 2 | No distribution standard: templates are tarballs in a catalog, no name+version+signature, no content addressing | Content-addressed layers, signed manifests tied to a git commit |
| 3 | Excellent day zero, absent day two: appliances drift through undocumented manual change; rebuilding an old one is archaeology | Declarative instance spec, inspector that describes a running machine, drift diff |
| 4 | No real path across major versions (18 to 19 means reinstall + TKLBAM restore); platform upgrade and application schema upgrade are conflated | Orchestrated upgrade with snapshot, upstream tool, validation, rollback; the two problems kept separate |
| 5 | Release cadence tied to very few maintainers; aging appliances presented as maintained | Honest catalog tiers; build and onboarding docs treated as part of the product |
| 6 | IPv4/NAT assumptions; IPv6 as an afterthought | IPv6-first, sovereign appliance (public address, own cert, own identity) |
| 7 | Hard dependency on the TurnKey Hub (TKLBAM, confconsole plugins) | Configurable S3-compatible endpoints; Hub becomes one optional backend |
| 8 | Interactive-only initialization (inithooks dialogs) | Declarative first; the interactive session is a generator of the same spec |

## 4. Target model: the LXC appliance as a cloud instance

Principles, in order of priority when they conflict:

1. **Declarative.** One spec file fully describes an instance. `apply` converges and is safe to re-run.
2. **Layered, immutable base.** Core, stack and app layers are read-only by convention; mutable state is explicit and mapped.
3. **Content-addressed and signed.** Every published artifact has a hash and a manifest signed by the project key, tying it to a commit.
4. **Reproducible.** Same commit + same manifest = same bytes.
5. **Sovereign by default.** Routable IPv6 address, ACME certificate, host identity keys. No NAT traversal required, no port mapping.
6. **Lifecycle-complete.** init, reconfigure, verify, backup, restore, upgrade, rollback are first-class operations.
7. **One code path.** confconsole and the headless CLI call the same library.

## 5. Architecture

### 5.1 Layers

- `core`: Debian base + Keel common (confconsole, inithooks, tklbam, security defaults, dhcpcd dual-stack).
- `stack`: LAMP, LAPP, Nginx + PHP-FPM, Ruby, Redis, and whatever verticals already exist in `common`. Start from what exists; do not invent new stacks in the first milestone.
- `app`: the appliance delta.
- Each layer is built by TKLDev/fab as a deterministic tarball with a content hash. An appliance manifest lists its layers.
- `keel pull` fetches only missing layers; assembly produces the Proxmox LXC template (`tar.zst`) and, optionally, the ISO.
- Constraint: existing `common` overlays and conf scripts must map onto stack layers without a rewrite. Refactor incrementally, one overlay at a time, with the build reproducing the previous artifact after each step.

### 5.2 Instance spec (declarative inithooks)

- One file per instance, proposed path `/etc/keel/instance.yaml` (final name is a maintainer decision, see section 11).
- Contents: hostname; IPv6 networking (static, SLAAC or DHCPv6); IPv4 optional; domain and certificate policy (ACME); enabled services; users and SSH keys; timezone and locale; secrets by reference (never inline); appliance-specific inithook parameters; backup target.
- Spec sources, in order: file on disk; container config pass-through (Proxmox/LXC); interactive confconsole session that writes the file. Interactive mode is preserved, but it becomes a generator of the same spec, not a separate path.
- Operations: `keel apply` (converge), `keel inspect` (write a spec from a running machine, reporting what it could not infer), `keel diff` (drift between declared and running).
- The per-appliance map of "what is configuration, what is data, what is derived" starts from TKLBAM's `dirindex.conf` profiles. Extend that, do not replace it.

### 5.3 Identity and network

- dhcpcd dual-stack replaces udhcpc (existing work). confconsole displays IPv6 correctly (existing branch, see section 8).
- Every appliance gets: a routable IPv6 address, a DNS name, an ACME certificate, SSH host keys, and a Keel identity key generated at init. Fingerprints are visible in confconsole and via CLI.
- IPv4 is optional and never assumed. All examples and docs use IPv6 addresses.

### 5.4 Distribution and verification

- Manifest fields: git commit, layer hashes, `SOURCE_DATE_EPOCH`, Debian snapshot timestamp (`snapshot.debian.org`), signature.
- A layer repository serves layers by hash; a project APT repository serves packages. Both over IPv6.
- `keel verify` checks installed layers and packages on a running appliance against its manifest.
- Determinism: fixed `SOURCE_DATE_EPOCH`, deterministic tar (sorted entries, fixed mtime, fixed owner), packages pinned to the snapshot.

### 5.5 Lifecycle operations

- **init** (first boot): apply spec, run appliance inithooks non-interactively, obtain certificate.
- **reconfigure**: edit spec, apply.
- **upgrade**: two distinct problems that must stay distinct.
  - *Platform upgrade*: Debian and Keel packages via apt.
  - *Application schema upgrade*: the upstream tool. Keel never claims that `apt upgrade` migrates an application's schema. It orchestrates: snapshot or return point, run the upstream tool, validate, roll back on failure.
  - Design reference (hardest case): Odoo, where the filestore lives on disk with references in the database and crossing a major version requires OpenUpgrade. First deliveries (simpler cases): WordPress (`wp-content`, wp-cli) and OJS (its upgrade script).
- **backup / restore**: tklbam against any S3-compatible endpoint.

### 5.6 Hub decoupling

- Inventory every call to `hub.turnkeylinux.org` in tklbam, confconsole and inithooks.
- Make the endpoint configurable; default to a project-owned S3-compatible target; keep the Hub selectable.
- `tklbam-python-boto` (the boto fork) is the first piece to study.

## 6. confconsole as the single operator surface

- confconsole becomes a thin TUI over `keel` (library + CLI). No business logic in dialogs.
- Proposed menu structure:
  - **Networking**: IPv6 first (address, prefix, gateway, DNS), IPv4 optional.
  - **Identity**: hostname, DNS name, certificate status and renewal, fingerprints.
  - **Instance**: view, edit, apply spec; show drift; export spec.
  - **Layers**: list installed layers, verify, pull updates.
  - **Upgrade**: platform upgrade, application upgrade (with return point), rollback.
  - **Backup**: targets, run, restore.
  - **About**: manifest, commit, hashes, signature status.
- Every menu action has a headless equivalent: `keel <op> --spec <file> --non-interactive`. Tests exercise the CLI; the TUI is a client.
- Keep the existing plugin structure. Add plugins; do not restructure existing ones in the first milestone.

## 7. Migration from TurnKey 19.0

- Two packages: `keel-archive-keyring` (only the key) and `keel-transition`.
- `keel-transition`: depends on the keyring; adds `keel.list`; disables `turnkey.list`; installs `/etc/apt/preferences.d/keel` pinning the Keel origin high; runs `keel inspect` to produce the instance spec; prints what it could not infer.
- Versioning: `+keel1` suffix on rebuilt packages plus the origin pin. Epoch only as a last resort, because it cannot be undone.
- Test bench: a clean Core 19.0, and long-lived appliances with years of manual change. Passing means `inspect` on the old machine followed by `apply` on a fresh container reproduces the service.

## 8. Repositories and existing work

Fork with **full git history**, upstream kept as a remote for cherry-picks in both directions:

`tkldev`, `fab`, `common`, `buildtasks`, `inithooks`, `confconsole`, `tklbam`, `tklbam-python-boto`, `turnkey-pylib`, plus the appliance repositories of the tier-1 catalog.

Existing work to carry in and finish:

- Python 3.13 compatibility across fab / common / tklbam / turnkey-pylib.
- dhcpcd dual-stack replacing udhcpc.
- confconsole IPv6 display fixes on branch `dhcpcd-ipv6-support`.
- IPv6 support already contributed upstream.
- Appliances already built: Mastodon, Moodle, ejabberd, pdns-recursor, CoTURN (`turnkey-nat64`), NAT64.
- Clean Ruby and Redis verticals for `common`, enabling non-LAMP stacks.

Tier-1 catalog (maintained): Core, LAMP / LAPP / Nginx stacks, Odoo, WordPress, Moodle, OJS, Mastodon, ejabberd, pdns-recursor, CoTURN, NAT64. Everything else is labeled **inherited, unmaintained**, honestly and visibly.

## 9. Milestones

- **M0 (weeks 1-2), baseline.** Forks with history. The project build of *unmodified* 19.0 reproduces upstream artifacts before any change. APT repository and keyring package. Inventory of Hub calls. Nothing else ships until this passes.
- **M1 = 19.1.** Declarative spec with `inspect / apply / diff`; confconsole Instance and Identity menus; `keel-transition`; dhcpcd and IPv6 work merged; Hub endpoint configurable.
- **M2 = 19.1 if it fits, otherwise 19.2.** Layered builds in TKLDev with hashed layers and signed manifests; `keel pull / verify`; reproducible-build tooling.
- **M3 = 19.2.** Public verification of reproducibility; orchestrated upgrade for WordPress and OJS; Odoo upgrade design document built around OpenUpgrade.
- **Long term.** Upgrade across major versions as the flagship feature. Debian 14 ("Forky") planning starts now, to avoid the historical lag between versions.

Ordering rationale: the spec first because it is the least invasive change and unlocks inspection, transition and testing; layers second because they change the build; upgrade last because it depends on both.

## 10. Conventions (mandatory)

- Commits, code comments, documentation and PR descriptions in **English**.
- **IPv6-first** in every command, example, config and default.
- **No Docker, no docker-compose, no Kubernetes.** CI and tests run on LXC with native systemd; test databases are real PostgreSQL or MariaDB instances on LXC.
- Shell: never use inline `#` comments inside commands (zsh reports "bad pattern"); separate commands into blocks. Write files with `cat > file << 'EOF'` or `tee`, never with Python heredocs.
- Git: never squash, never rewrite history; keep the upstream remote; cherry-pick with attribution.
- A change of technical direction requires written justification with three parts: (1) why the previous approach does not work, (2) whether it can be made to work, (3) why the new approach is better. No exceptions.
- Process over result: if the process fails, fix the process. Never bypass it.
- Licensing: forked code stays GPL. Licensing of new components is a maintainer decision.
- Documentation typography: no em dashes; use commas, colons, parentheses or semicolons; plain hyphen in numeric ranges.
- **Language standard: ASD-STE100** (Simplified Technical English) for every project text: documentation, decision notes, commits, PR and issue text, console and log messages, reports. The rules are in `docs/writing.md`; the agent summary is in `AGENTS.md`.

## 11. Decisions reserved for the maintainer

The agent prepares options and proposals for these, and does not decide them:

- Final project name, domains, trademark review.
- Key custody and rotation policy (root key offline, signing subkey on the builder).
- Hosting of the APT and layer repositories.
- Governance and decision policy document.
- Public announcement: timing and content.
- Final file names and paths for the spec (`/etc/keel/...`) and the CLI name.

## 12. Working mode and reporting

- Small PRs, one repository at a time. Each PR states the problem, the diagnosis and the fix, and links the section of this brief it serves.
- Direction changes go into `docs/decisions/` as dated notes using the three-part justification from section 10.
- Weekly summary: done, blocked, decisions needed (referencing section 11).
- When in doubt between preserving upstream behavior and improving it, preserve it and open a decision note.
