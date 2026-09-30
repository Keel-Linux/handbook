# 0041: The appliance manifest, version 1

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** ("I confirm and sign
off"), with the answers to its open questions under "Resolved". It answers
the review note of 0034 ("the manifest format is not specified, and it is
the pivot of everything after it"), tracker#39, and the manifest item of
Phase 0 of the roadmap (tracker#46). The format itself, with every field,
the worked examples and the validation rules, is
[docs/manifest-v1.md](../manifest-v1.md); this note records what was
decided.

Scope, as the maintainer set it on 2026-09-30: **start from the base.** The
manifest describes Keel Core and Keel Web first, which is what Phases 1 and
3 build. The WordPress, Odoo and Mastodon examples stay, short, in an
appendix of the format, to show that the schema's shape holds for
applications later; they are not a plan for any appliance built today, and
nothing here has to accommodate the current keel-wordpress.

## Why the format comes first

0032 (directory replication), 0037 (backup), 0039 (upgrades), 0040
(monitoring) and 0026 (discovery) all read the manifest of 0034. Built
before it, each would invent its own declaration of the same facts (which
paths hold data, which processes to watch, what a node offers) and they
would drift apart at the first appliance. Core and Web are where those
facts start: Monit's checks, the firewall, the states of CrowdSec, etcd,
Coraza and Anubis in each installation mode, and what every appliance above
them inherits.

## Decision

The choices the maintainer approved, each argued in the format document.

1. **Two kinds of file, one schema.** An **overlay manifest** ships in each
   overlay's `.deb` (0036, 0039) and says what the overlay runs: its
   processes, what they listen on, their checks, where its data is and how
   it is kept. An **appliance manifest** ships in each appliance's `.deb`
   and says what the appliance is built on (`base`), which overlays it adds
   with their default state per installation mode, and its own processes.
   An application is an appliance with the application sections added; there
   is no third kind.

2. **The manifest owns facts, the spec owns choices, and the reference runs
   one way.** The spec names the appliance and the names the manifest
   declares; the manifest never names a host, an address, a secret file or
   a count. Three facts belong to neither: the version (the package's),
   the Debian packages an overlay installs (its `Depends`), and
   configuration content (the package's and the installer's). The table of
   who owns what is in the format, under "Two files, two owners".

3. **Every overlay an appliance carries has a default state in each of the
   three modes of 0028**, `simple`, `cloud_simple` and `cloud_advanced`,
   all three written, each `enabled`, `disabled` or `ask` (not `on` and
   `off`, which PyYAML reads as booleans). The image content is the same in
   every mode (0013: never split by topology); the mode decides only what
   runs. `ask` shows the overlay's screen at installation and never
   reaches the spec, which records `enabled` or `disabled`.

4. **Inheritance is additive and fixed.** A child appliance inherits its
   base's overlays with their states, its processes, checks, ports, secrets
   and first boot hooks, and adds its own; it cannot change an inherited
   state or remove anything. A port is taken across the whole chain whatever
   the states, since an operator can turn a `disabled` overlay on. So "Keel Web
   in a simple installation" is one thing for every appliance built on it,
   and an operator can still depart from it on one machine, in the spec.

5. **Processes and checks are separate, and Monit restarts through
   systemd.** A process is a unit (what a state turns on and off, what Monit
   restarts); a check is a probe (`http`, `tcp`, a Monit protocol, or an
   argv command) with `on_failure: restart` or `alert`. Every process gets a
   unit check; the restart limit per process is the one 0040 asked for, so a
   restart loop is reported. Coraza shows why the two are separate: it has
   no process, and its check is that a Core Rule Set test payload gets 403.

6. **Every listening port carries an exposure class**, `loopback`, `mesh`
   or `public`, and the firewall is derived from it. The mesh address is
   the spec's, so a check names the class and the renderer resolves it.
   `WEBMIN_FW_TCP_INCOMING` in the recipes is replaced.

7. **Monit's checks, the firewall, the backup set, the Syncthing folders
   and the registry entry are derived, never declared.** Monit's file is
   always written, `/etc/keel/monit/keel-manifest.conf`, and included from
   `/etc/monit/conf.d/` only while the spec's monitor is enabled; the
   backup set is rendered as the TKLBAM overrides the client already reads
   (0037 keeps TKLBAM); the folders follow 0032's send-only and
   receive-only rule, in cloud advanced only. `keel manifest show
   --derived` prints each one with the code `apply` writes it with.

8. **Secrets are names with a policy**: `generate` (`allowed`, `required`,
   `never`) and `shared` (every node of a set holds the same value, generated
   by the primary as 0028 has it generate the rest). Keel Web needs one:
   Anubis's signing key, without which a failover makes every visitor solve
   the challenge again.

9. **Where it lives and who reads it.** `/usr/share/keel/overlays/<name>.yaml`
   and `/usr/share/keel/appliances/<name>.yaml`, from packages named
   `keel-overlay-<name>`, one source package per overlay, and after the
   appliance (`keel-core`, `keel-web`).
   Read by new commands `keel manifest validate` and `keel manifest show`;
   by `keel spec validate`, which becomes manifest-aware; by `keel spec
   apply --system`, which converges the overlays' units and writes the
   derived files; by `keel inspect` and `keel diff`; and by the installer.
   The spec gains `appliance`, `installation.mode` and `overlays`, plus
   manifest-declared names under `secrets` and `app.options`; all additive,
   so the spec stays `version: 1`.

10. **The format is versioned by an integer**, `manifest_version: 1`, with
    unknown keys refused at every level. Any new key raises it. A package
    shipping a manifest depends on the first keel that reads its version,
    so apt refuses the combination that cannot work.

## The base, in one table each

Keel Core (format, "Worked example: Keel Core"):

| Overlay | simple | cloud simple | cloud advanced | From |
| --- | --- | --- | --- | --- |
| installer | enabled | enabled | enabled | 0036 |
| wireguard | disabled | enabled | enabled | 0028, 0024 |
| etcd | disabled | disabled | enabled | 0036, 0028 |
| crowdsec | disabled | enabled | enabled | 0029, 0041 |

Its own processes: sshd (22), Webmin (12321), the web shell (12320), all
public, and postfix (25, loopback). In a simple installation Monit watches
those four and nothing else, the firewall opens 22, 12320 and 12321, and
the backup is TKLBAM's system delta as today.

Keel Web (format, "Worked example: Keel Web"), on Core:

| Overlay | simple | cloud simple | cloud advanced | From |
| --- | --- | --- | --- | --- |
| nginx | enabled | enabled | enabled | 0030 |
| coraza | disabled | enabled | enabled | 0030 |
| anubis | disabled | enabled | enabled | 0030 |

Web has no process of its own. Simple adds Nginx's `/keel-health` check and
ports 80 and 443; advanced adds Anubis (loopback only, behind Nginx) and
the WAF probe. The Phase 3 criterion of the roadmap reads straight off it.

## First implementation

In order. Each step is testable on its own and is done only when its
criterion holds on a built image or package, not on a machine assembled by
hand.

| # | Repository | Work | Done when |
| --- | --- | --- | --- |
| 1 | keel | `keel.manifest`: the reader, `keel manifest validate` and `keel manifest show`, with no consumer yet | the Core and Web manifests of the format validate as fixtures; each validation rule has a fixture it refuses; `show web --resolved` prints the format's resolved tables; coverage per 0003 |
| 2 | common | one source package per overlay, under `packages/<name>/`, each with its own changelog and version: `keel-overlay-installer` (inithooks, confconsole, keel), `keel-overlay-wireguard` (wireguard-tools 1.0.20210914 from trixie), `keel-overlay-etcd` (etcd-server 3.5.16 from trixie) and `keel-overlay-crowdsec` (crowdsec 1.4.6-10 and crowdsec-firewall-bouncer 0.0.25 from trixie, or a current CrowdSec if 0029's open task decides so), each with its manifest, into the testing track (0039) | installed on a trixie container, each leaves its units in its `simple` state, etcd and both CrowdSec units disabled and inactive whatever the Debian packages' own maintainer scripts did, and its manifest validates on the machine |
| 3 | keel | the spec's `appliance`, `installation` and `overlays`; `apply --system` converges the units and writes the Monit file and the firewall; `inspect` and `diff` read them | on a container with step 2's packages, CrowdSec disabled, enabled, disabled converges each time, a second apply changes nothing, `diff` is clean, the Monit file gains and loses exactly CrowdSec's checks, and `monit -t` accepts every file rendered |
| 4 | keel-core | the `keel-core` package (its manifest, and `Depends` on the four overlays and on step 3's keel); the recipe installs it | Phase 1's criterion of tracker#46, and on the booted image `keel manifest show --resolved` equals the Core table and Monit watches exactly sshd, Webmin, the web shell and postfix |
| 5 | new packaging repositories | Coraza's Nginx connector: no Debian package and no ITP, so Keel builds it (0030, 0039) as a dynamic module that depends on `nginx-abi-1.26.3-1`, as trixie's own `libnginx-mod-*` packages do, and is rebuilt whenever trixie's nginx moves to another upstream version. Anubis: ITP #1102132, so it is built from source into the Keel repository in coordination with the ITP's owner (tracker#15), the upstream `.deb` (v1.27.0) as a reference only. nginx 1.26.3 is trixie's, used as it is | both build from source in the Keel repository; the module loads into trixie's nginx (`nginx -t`); a Core Rule Set test payload gets 403 in the package's own test |
| 6 | common | `keel-overlay-nginx`, `keel-overlay-coraza`, `keel-overlay-anubis`, a source package each, with their manifests | on Core, nginx answers `/keel-health` with 204 on the loopback only; Coraza and Anubis are installed and disabled; turned on in the spec, the `waf-blocks` and `anubis` checks pass |
| 7 | keel-web | the `keel-web` package and its recipe, on the Core layer | Phase 3's criterion of tracker#46; `show --resolved` equals the Web table; Monit in simple is Core's plus Nginx, and advanced adds Anubis and the WAF probe |

Not needed for Core and Web, and left for the phases that use them:
syncthing 1.29.5 (data appliances, 0032), tayga 0.9.2 (rendezvous points,
0024), both in trixie; Garage, ITP #1118368 (the `s3` overlay, 0038);
libnginx-mod-http-modsecurity 1.0.3, in trixie, which stays the unused
fallback of 0030 unless a new decision chooses it.

## What this amends

- **0034, review note**: answered; the format is docs/manifest-v1.md.
- **0010, "The three levels"**: the recipe level, "a recipe would declare
  the components it composes with their versions", is the appliance
  manifest's `base` and `overlays`; a component's version stays its
  package's, as 0039 makes every overlay a `.deb`.
- **Brief section 5.1**, "an appliance manifest lists its layers": the
  layer chain is the `base` chain, one layer per appliance.
- **Brief section 5.4**: the file `bt-layer` writes is from now on always
  called the **layer manifest**, and this one the **appliance manifest**.
- **Brief sections 4.2 and 5.2**: the mutable state map is `data` and
  `state` of the manifests; the spec gains `appliance`,
  `installation.mode` and `overlays`, and `app.options` is checked against
  declared options instead of being an escape hatch.
- **0021 and 0040**: the checks of what an appliance runs come from the
  manifest, in a file of their own beside the resource monitor's, with the
  restart limit per process that 0040's "Resolved" asked for.
- **0027**: the emitted YAML carries the mode and the state of every
  overlay, written out.
- **0036**: every overlay is its own Debian source package in `common`
  (`packages/<name>/`), its `.deb` named `keel-overlay-<name>`, with its
  manifest beside its `debian/`.
- **0029, "Decision"**: the VIP is configured for database appliances only,
  for now, not in every advanced installation (see "Resolved"); 0029
  carries a one-line note saying so. 0036, which already puts the `vip`
  overlay only in the database appliances, is unchanged.
- **0034, workers**: unchanged and confirmed, a worker never writes to
  local disk; the format has no field that could grant it a path.
- **0037 and 0032**: the backup manifest of 0037 and the `replicate:` and
  `exclude:` lists of 0032 are the derived backup set and the application
  `state` section.

## Resolved (maintainer, 2026-09-30)

- **Cloud simple runs no etcd.** etcd is for cloud advanced only, which is
  what the Core table says (`disabled`, `disabled`, `enabled`). A cloud
  simple replica finds its primary by the address the primary hands it
  (0028), as it does today; discovery over etcd (0026) is a cloud advanced
  installation's.
- **The VIP is only for database appliances, for now.** Core and Web carry
  no `vip` overlay. This settles the conflict between 0029 (a VIP in every
  advanced installation) and 0036 (the `vip` overlay in the database
  appliances only) on 0036's side; 0029 is amended.
- **CrowdSec is `enabled` in the cloud modes**, not `ask`: the Core and Web
  tables say `disabled`, `enabled`, `enabled`. The overlay keeps its screen
  for an operator who wants to change its configuration.
- **Manifest checks are always written, and inactive while the monitor is
  off.** The derived file is rendered whatever the spec says, and Monit
  includes it only while `monitor.enabled` is true, so `diff` compares it
  either way and turning the monitor on activates checks that already
  exist.
- **Workers never write to disk**, as 0034 says. The format has no
  `writes` field; keel's drop-in gives every worker unit a read-only
  system. In the appendix this makes object storage required for
  Mastodon, whose Sidekiq writes media, and has Odoo's cron worker keep its
  attachments in a data service.
- **One source package per overlay**, each released on its own with its
  own changelog and version, at the cost of a CI and a changelog each.
