# The appliance manifest, version 1

Decided in [0041](decisions/0041-the-appliance-manifest-version-1.md) by
the maintainer, 2026-09-30. Nothing here is implemented yet. This is the
reference a reader and an author of manifests work from. Every example uses
IPv6.

## Contents

1. [Two files, two owners](#two-files-two-owners)
2. [Kinds, and where each file lives](#kinds-and-where-each-file-lives)
3. [Top level](#top-level)
4. [The overlay manifest](#the-overlay-manifest)
5. [The appliance manifest](#the-appliance-manifest)
6. [Processes and checks](#processes-and-checks)
7. [Resolution: what a consuming appliance inherits](#resolution-what-a-consuming-appliance-inherits)
8. [What is derived, and how](#what-is-derived-and-how)
9. [The instance spec side](#the-instance-spec-side)
10. [Who reads it](#who-reads-it)
11. [Worked example: Keel Core](#worked-example-keel-core)
12. [Worked example: Keel Web](#worked-example-keel-web)
13. [Worked example: Keel PHP inherits Web](#worked-example-keel-php-inherits-web)
14. [Validation rules](#validation-rules)
15. [Out of scope for version 1](#out-of-scope-for-version-1)
16. [Appendix: the application sections](#appendix-the-application-sections)
17. [Appendix: WordPress, Odoo and Mastodon](#appendix-wordpress-odoo-and-mastodon)

## Two files, two owners

| | Appliance manifest | Instance spec |
| --- | --- | --- |
| Describes | what an appliance **is** and what it **consumes** | what **this machine chose** |
| Scope | per appliance, the same on every machine that installs it | per machine (brief section 5.2, 0027) |
| Shipped by | the appliance's or the overlay's `.deb` (0039) | written at installation, re-emitted after every upgrade (0027) |
| Path | `/usr/share/keel/appliances/<name>.yaml`, `/usr/share/keel/overlays/<name>.yaml` | `/etc/keel/instance.yaml` |
| Edited by | the author of the appliance, in its repository | the operator, the installer, `keel inspect` |
| Changes | only with the package version | with `keel spec apply` |
| Holds values of secrets | never | never; references only (docs/spec.md in keel) |

**One owner per fact.** A fact about what the appliance is (which overlays
it carries, what a process listens on, which paths hold its durable state,
what its health check asks) has the manifest as its owner. A choice made for
one machine (the installation mode, whether CrowdSec runs, where the
database is, which file holds a password) has the spec as its owner. A
default belongs to the manifest; the value the emitted spec writes out is
the machine's choice, even when it is equal to the default, because 0027
makes the emitted file record every choice explicitly.

**The reference runs one way.** The spec names the appliance
(`appliance.name`) and the names the manifest declares (overlays, services,
workers, secrets, options). The manifest never names anything in the spec,
never holds a host, an address, a path of a secret file or a count chosen
for a machine. Where a manifest needs a value only the machine knows (the
overlay address a check connects to), it names a class of address
(`loopback`, `mesh`) and the renderer resolves it from the spec.

**What neither of them says.** Three facts have a third owner and appear in
neither file:

| Fact | Owner | Why not in the manifest |
| --- | --- | --- |
| The version of an appliance or an overlay | the package (`dpkg-query`) | a second copy would drift at the first upload |
| Which Debian packages an overlay installs | the overlay package's `Depends` | the same |
| The content of a configuration file (`nginx.conf`, CrowdSec's acquisitions) | the overlay package, and the installer screens that write the spec | a manifest that templated configuration would be a second configuration system |

## Kinds, and where each file lives

One schema, two kinds of file.

| Kind | What it describes | Shipped by | Path |
| --- | --- | --- | --- |
| `overlay` | one overlay of `common` (0036): its processes, what they listen on, their checks, where its data is and how it is kept | the overlay's `.deb`, `keel-overlay-<name>` | `/usr/share/keel/overlays/<name>.yaml` |
| `appliance` | a named combination with an identity (0036): the appliance it is built on, the overlays it adds and their default state in each installation mode, its own processes, and, for an application, what it consumes | the appliance's `.deb`, named after its repository (`keel-core`, `keel-web`) | `/usr/share/keel/appliances/<name>.yaml` |

An application (WordPress, Odoo, Mastodon) is an appliance whose manifest
also carries the application sections of the appendix. There is no third
kind, because 0023 makes every appliance a publishable overlay of the next
one, and a kind per level would have to be split again at the first level
nobody foresaw.

In the source repositories the files sit at:

| Repository | Path |
| --- | --- |
| `common` | `packages/<name>/manifest.yaml`: one Debian source package per overlay (`packages/<name>/debian/`, its own changelog and version, released on its own), beside `overlays/<name>/` and `conf/<name>` |
| an appliance (`keel-core`, `keel-web`) | `keel/appliance.yaml` |

`common/overlays/<name>/` is the tree fab copies onto the root filesystem,
so the manifest cannot live inside it: it would land at the root of the
image.

**"Manifest" already names another file.** Brief section 5.4 and keel's
docs/layers.md call the key-value file `bt-layer` writes beside every layer
tarball the layer manifest (`<layer>.manifest`: digests, commits, units).
That file records how a layer was **built**; this one says what an appliance
**is**. The two are always written with their qualifier, "layer manifest"
and "appliance manifest", and the appliance manifest's top-level `kind` key
makes a file of one kind unmistakable for the other.

## Top level

```yaml
manifest_version: 1
kind: appliance            # or overlay
name: web
title: Keel Web
summary: Nginx, Coraza and Anubis, the base of every web appliance (0030)
```

| Field | Required | Notes |
| --- | --- | --- |
| `manifest_version` | yes | The integer `1`. A reader refuses a version it does not know, and a newer one than it reads, naming both |
| `kind` | yes | `overlay` or `appliance` |
| `name` | yes | `[a-z][a-z0-9-]*`, at most 32 characters, equal to the file's name without `.yaml`. Unique within its kind on a machine |
| `title` | yes | What confconsole and the installer show |
| `summary` | yes | One line |

**Unknown keys are errors at every level**, as in the instance spec (docs/spec.md
in keel), so a typo fails validation instead of being ignored. There is no
`version` field: the version is the package's (see "Two files, two owners").

**Versioning.** `manifest_version` is an integer. Any new key, any new
allowed value and any change of meaning raises it; there are no minor
versions, because a reader that met an unknown key would have to guess
whether ignoring it is safe. A keel release reads every version up to the
one it was built for. A package that ships a manifest declares
`Depends: keel (>= V)`, where `V` is the first keel that reads its
`manifest_version`, so apt, not the reader, refuses the combination that
cannot work.

## The overlay manifest

```yaml
manifest_version: 1
kind: overlay
name: etcd
title: etcd
summary: The mesh registry (0025); control plane only
requires: [wireguard]
processes:
  - name: etcd
    unit: etcd.service
    listen:
      - {port: 2379, protocol: tcp, expose: mesh}      # clients
      - {port: 2380, protocol: tcp, expose: mesh}      # peers
checks:
  - name: etcd-health
    process: etcd
    type: http
    address: mesh
    port: 2379
    path: /health
    expect: 200
    on_failure: restart
data:
  - path: /var/lib/etcd
    replication: native
    backup: none
```

| Field | Required | Notes |
| --- | --- | --- |
| `requires` | no | Overlays that must be `enabled` whenever this one is `enabled`. Checked in every mode of every appliance that carries it, and used to order starts and stops |
| `provides` | no | For a data overlay: `{engine: mariadb}`, one of `mariadb`, `postgresql`, `redis`, `opensearch`, `elasticsearch`, `s3`. What lets an application embed it (appendix) |
| `processes` | no | See "Processes and checks". An overlay with none (a library, an Nginx module) is valid |
| `checks` | no | See "Processes and checks" |
| `data` | no | Where the overlay keeps state, and how it is kept |
| `data[].path` | yes | Absolute |
| `data[].replication` | yes | `native` (the engine replicates it: databases, etcd, a search index rebuilt on join) or `none` (nothing needs it on another node). Never `files`: data with its own replication is never replicated by file (0032) |
| `data[].backup` | yes | `dump` (the engine's own dump, taken from the hot standby when there is one, 0037), `none` (derived or rebuildable), or `files` (copied as files, for an engine with no dump) |
| `secrets` | no | See "The appliance manifest": the same shape |
| `hooks.first_boot` | no | See "The appliance manifest": the same shape |
| `hooks.state` | no | `{path, timeout}`, for an overlay that is not a unit (Coraza): the executable `keel spec apply --system` runs with `enabled` or `disabled` to turn it on and off. `path` is always `/usr/lib/keel/overlays/<name>/state`; `timeout` is 1 to 600 seconds, 120 by default. Other packages may put hooks of their own in `/usr/lib/keel/overlays/<name>/state.d/`, which keel runs after it (errata below; keel's docs/apply.md, "State hooks") |
| `screen` | no | The confconsole plugin that configures this overlay. An appliance may give the overlay the default state `ask` only when this is set |

An overlay says nothing about installation modes. Whether it runs in a
simple installation is a property of the appliance that carries it: the same
`vip` overlay is `disabled` in every mode of one appliance and `enabled` in cloud
advanced of another (0029).

## The appliance manifest

```yaml
manifest_version: 1
kind: appliance
name: web
title: Keel Web
summary: Nginx, Coraza and Anubis, the base of every web appliance (0030)
base: core
overlays:
  nginx:  {simple: enabled,  cloud_simple: enabled, cloud_advanced: enabled}
  coraza: {simple: disabled, cloud_simple: enabled, cloud_advanced: enabled}
  anubis: {simple: disabled, cloud_simple: enabled, cloud_advanced: enabled}
```

| Field | Required | Notes |
| --- | --- | --- |
| `base` | yes | The appliance this one is built on, whose manifest must be installed; `none` only for Keel Core, which is built on Debian. The layer chain of the image (brief section 5.1) is this chain: one layer per appliance, each the delta of its overlays |
| `overlays` | no | The overlays this appliance adds, each with its default state in the three installation modes of 0028 |
| `overlays.<name>.simple`, `.cloud_simple`, `.cloud_advanced` | all three | `enabled`, `disabled` or `ask`. All three are written, always: the two advanced modes differ exactly where it matters (etcd, 0028), and a shorthand would hide that |
| `overlays.<name>.version` | no | A constraint on the overlay package's version, `>= 1.26` style (Debian's comparison, `dpkg --compare-versions`), for when the appliance needs more than any version the Keel repository could carry |
| `processes`, `checks` | no | The appliance's own, for what is not an overlay (Core's sshd and Webmin). See "Processes and checks" |
| `secrets` | no | The secrets the appliance or its hooks need, by name. See below |
| `options` | no | Typed inputs to the appliance's first boot hook. See below |
| `hooks.first_boot` | no | A list of absolute paths of first boot hooks this package ships, under `/usr/lib/inithooks/firstboot.d/`. inithooks runs them in its own order, by file name; the manifest names them so `validate` checks they exist and are executable, and so `show` can say what an appliance adds to a first boot |
| application sections | no | `services`, `state`, `workers`, `web`, `hooks.migrate`: see the appendix |

**The three states.**

| State | At installation | Afterwards |
| --- | --- | --- |
| `enabled` | the overlay's units are enabled and started | kept by `apply` while the spec says `enabled` |
| `disabled` | installed, units disabled and stopped; its configuration is the package's inert default | kept `disabled` while the spec says `disabled` |
| `ask` | the installer shows the overlay's `screen`, and the answer is `enabled` or `disabled` | the spec records the answer; `ask` never appears in a spec |

The image content is the same in every mode, as 0013 requires (an image is
never split by topology): every overlay an appliance carries is installed,
and the mode decides only whether it runs.

The words are `enabled` and `disabled`, not `on` and `off`, because a YAML
1.1 reader (PyYAML, which keel uses) turns an unquoted `on`, `off`, `yes` or
`no` into a boolean, and a state that arrives as `True` is a typo the
format could not report.

**Secrets.**

```yaml
secrets:
  - name: anubis_signing_key
    description: The key Anubis signs its challenges with
    generate: required
    shared: true
```

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | `[a-z][a-z0-9_]*`. The spec binds it as `secrets.<name>` (below) |
| `description` | yes | What the installer shows when it asks for the file |
| `generate` | yes | `allowed` (the spec may say `generate: true`), `required` (nobody types it: a key, a salt), or `never` (a person must choose it) |
| `shared` | no, default `false` | `true`: every node of a replicated set must hold the same value. The primary generates it and the replica receives it with the rest of what 0028 has the primary generate for the replica. `false`: each node has its own |

A secret is a name and a policy, never a value and never a path.
`root_password`, `db_password` and `app_password` keep the conf variables
they have today (`ROOT_PASS`, `DB_PASS`, `APP_PASS`, docs/spec.md in keel);
any other name renders as `KEEL_SECRET_<NAME>`, upper cased.

**Options.**

```yaml
options:
  - name: site_title
    type: string
    default: WordPress
    pattern: '^.{1,80}$'
```

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | `[a-z][a-z0-9_]*`, rendered as `APP_<NAME>` as `app.options` is today |
| `type` | yes | `string`, `integer`, `boolean`, or `enum` with `values` |
| `default` | no | Of the declared type. Without one the option is required in the spec |
| `pattern` | no | For `string`: a regular expression the value must match in full |

Declaring options turns `app.options` of the spec from an escape hatch into
a checked section: a key the installed manifests do not declare is an error,
not a variable nobody reads.

## Processes and checks

A **process** is a systemd unit the overlay or appliance owns: the thing a
state turns on and off, and the thing Monit restarts. A **check** is a probe
Monit runs. They are separate because a check does not always belong to a
process (Coraza is an Nginx module and has none) and a process does not
always need more than "its unit is active".

```yaml
processes:
  - name: crowdsec
    unit: crowdsec.service
    listen:
      - {address: 127.0.0.1, port: 8080, protocol: tcp, expose: loopback}  # LAPI
      - {address: 127.0.0.1, port: 6060, protocol: tcp, expose: loopback}  # metrics
    restart: {attempts: 3, within_cycles: 5}
  - name: firewall-bouncer
    unit: crowdsec-firewall-bouncer.service
checks:
  - name: crowdsec-lapi
    process: crowdsec
    type: tcp
    address: loopback
    port: 8080
    on_failure: restart
```

| Field | Required | Notes |
| --- | --- | --- |
| `processes[].name` | yes | Unique in the resolved chain (see "Resolution") |
| `processes[].unit` | yes | A systemd unit name ending in `.service`. Every process gets a unit check whether or not it declares a check: "active" is the least a watched process must be |
| `processes[].listen` | no | What it listens on. `port` and `protocol` (`tcp`, `udp`) are required |
| `...listen[].expose` | yes | `loopback`, `mesh` or `public`. `loopback`: `::1` and `127.0.0.1`, nothing opened. `mesh`: the node's overlay address, opened on the WireGuard interface only. `public`: every address, opened on the uplink. The firewall is derived from this (see "What is derived") |
| `...listen[].address` | no | A literal loopback address, for a process that binds one family only (CrowdSec's LAPI binds `127.0.0.1`). Never a name: `localhost` is refused with the reason docs/spec.md in keel gives |
| `processes[].restart` | no | `{attempts: N, within_cycles: M}` with `N <= M`, default `{attempts: 3, within_cycles: 5}`; or `never`. After `N` restarts within `M` Monit cycles, Monit stops restarting and alerts: a restart loop is reported, not hidden (0040, "Resolved") |
| `checks[].name` | yes | Unique in the resolved chain. It is the name Monit shows and the name the summary in etcd carries (0040) |
| `checks[].process` | no | The process the check belongs to. Required for `on_failure: restart` |
| `checks[].type` | yes | `http`, `tcp`, `protocol` or `command` |
| `checks[].address` | for network types | `loopback` or `mesh`, resolved by the renderer; never a literal, because the mesh address is the spec's. `loopback` is `::1`, or the literal the process's `listen` declares for that port when it binds one family only |
| `checks[].port` | for network types | |
| `checks[].path`, `.expect`, `.tls` | `http` | `path` starts with `/`; `expect` is one status code; `tls: true` for HTTPS |
| `checks[].protocol` | `protocol` | One of Monit's own: `mysql`, `pgsql`, `redis`, `ssh`, `smtp` |
| `checks[].command` | `command` | An argv list; exit 0 is healthy. Never a shell string |
| `checks[].every_cycles` | no | Default 1. For a probe that costs something (the WAF probe of Keel Web) |
| `checks[].on_failure` | yes | `restart` or `alert` |

## Resolution: what a consuming appliance inherits

A machine runs one appliance, and that appliance's manifest is resolved
along its `base` chain down to Core. The resolved manifest is what every
consumer reads; `keel manifest show --resolved` prints it.

| What | Rule |
| --- | --- |
| Overlays and their states | Inherited as they are. A child adds overlays; it cannot change the state of an inherited one or remove it. An overlay name appears once in a chain |
| Processes and checks | Inherited; names are unique across the chain |
| Ports | Inherited; a `(port, protocol)` pair is unique across the whole chain, **whatever the states**, because the operator can turn a `disabled` overlay on and two processes cannot both bind the port |
| Secrets, options | Inherited; names are unique across the chain |
| First boot hooks | Inherited: a child's image carries its parent's hooks, and inithooks runs them all |
| Application sections | Declared by at most one appliance of a chain, the application at its top |

Why a child cannot change an inherited state: the parent's states are the
platform the child was tested on. Keel PHP and Keel Python both inherit
Coraza `disabled` in a simple installation from Keel Web; if either could turn it
on by default, "Keel Web in simple mode" would stop being one thing. An
operator can still turn it on, in the spec, on one machine. A child that
needs another default is a case for a new decision, which is why it is out
of scope for version 1.

## What is derived, and how

These are computed from the resolved manifest and the spec, and are never
declared anywhere.

| Artefact | From the manifest | From the spec | Written to |
| --- | --- | --- | --- |
| Monit checks (0040) | every process and check of an overlay or appliance whose state is `enabled` | the state of each overlay; the overlay address for `mesh` checks; `monitor.enabled` | always written to `/etc/keel/monit/keel-manifest.conf`, and included from `/etc/monit/conf.d/` only while `monitor.enabled` is true, so the checks exist, and `diff` compares them, whether the monitor is on or off |
| Firewall | every `listen` with `expose: public` or `mesh`, of every process whose overlay is `enabled` | the overlay's interface and its UDP port (`network.overlay.wireguard`) | the rules the build writes today from `WEBMIN_FW_TCP_INCOMING`, which the manifest replaces |
| Backup set (0037) | `data[]` with `backup: dump` or `files`; for an application, `state` and the durable services (appendix) | the backup destination (0037); where each service is | the TKLBAM overrides (`/etc/tklbam/overrides`), whose include, exclude and database lines are what the TKLBAM client already reads |
| File replication (0032) | an application's `state.replicate` and `state.exclude` (appendix) | the mode (only `cloud_advanced` replicates files, 0028) and the role | one Syncthing folder per path, its ignore list from the excludes, send-only on the primary and receive-only on the standby |
| Overlay units' state | the default per mode, at installation | `overlays.<name>` | systemd: enabled and started, or disabled and stopped |
| Registry entry (0025) | the appliance's name, the `provides` of every `enabled` overlay, every `mesh` port | the site label, the overlay address | the node's key in etcd (Phase 5 of the roadmap) |

**Monit, rendered.** A process becomes a `check program` on its unit, with
the unit's own start and restart commands, so Monit restarts through
systemd and never around it:

```
check program keel-crowdsec with path "/bin/systemctl is-active --quiet crowdsec.service"
    start program = "/bin/systemctl start crowdsec.service"
    restart program = "/bin/systemctl restart crowdsec.service"
    if status != 0 for 2 cycles then restart
    if 3 restarts within 5 cycles then unmonitor
    # every event also runs keel notify, as 0021's checks do

check host keel-crowdsec-lapi with address 127.0.0.1
    depends on keel-crowdsec
    if failed port 8080 type tcp for 2 cycles then restart
```

A check with `on_failure: alert` renders `then alert` instead of `then
restart`. The alert goes to the channels of the spec's `monitor.notify`
through `keel notify`, as 0021's checks do. The exact text is the renderer's;
what the manifest fixes is which checks exist, what they ask, and what
Monit does when one fails.

## The instance spec side

The spec (docs/spec.md in keel) gains three sections, `appliance`,
`installation` and `overlays`, and its `secrets` section accepts the names
the manifests declare. All of it is additive, so
the spec stays `version: 1`, as it did when `monitor` and `database` were
added.

```yaml
appliance:
  name: web
installation:
  mode: simple              # simple, cloud_simple or cloud_advanced (0028)
overlays:                   # written out complete by the installer and by inspect (0027)
  wireguard: disabled
  etcd: disabled
  crowdsec: disabled
  installer: enabled
  nginx: enabled
  coraza: disabled
  anubis: disabled
secrets:
  root_password: {file: /etc/keel/secrets/root_password}
  anubis_signing_key: {generate: true}
```

| Field | Notes |
| --- | --- |
| `appliance.name` | The appliance manifest this machine runs. Must be installed. `inspect` writes it from the one installed appliance manifest that no other one has as its `base` |
| `installation.mode` | Chosen once, at installation. It selects which column of the manifest gives the defaults the installer starts from. Changing it later is not a field edit: moving a machine between modes is out of scope (see below). `inspect` reads it from the spec the installer emitted and reports it as not inferred otherwise, since a machine's units do not say which mode chose them |
| `overlays.<name>` | `enabled` or `disabled`, for every overlay of the resolved chain. `apply --system` converges the units; `diff` compares them with systemd; `inspect` reads them from systemd. A name the resolved chain does not carry is an error. Turning on an overlay whose `requires` are `disabled` is an error |
| `secrets.<name>` | The names the three existing fields have, plus every name a resolved manifest declares. The backends are the existing ones (`file`, `generate`), and `generate` is refused where the manifest says `never`. A secret a manifest marks `generate: required` and the spec leaves out is generated at installation and written out as a file reference by the emitter |

The application sections add `services`, `workers` and the checked
`app.options` (appendix).

**Nothing is declared twice: the check.** For every field of the spec
above, the manifest holds the question and the spec the answer:

| Manifest (owner of the fact) | Spec (owner of the choice) |
| --- | --- |
| which overlays exist, and their default per mode | which are on, on this machine |
| which secrets are needed, and whether they are shared | which file holds each one |
| which options exist, their types and defaults | the value of each |
| the process, its port and its exposure class | nothing: the port is not a choice |
| the check and what it does on failure | whether the monitor is enabled, and who is told (`monitor`, 0021) |

## Who reads it

| Reader | What it does with it |
| --- | --- |
| `keel manifest validate [FILE...]` | Checks one file, or with no argument the installed ones and their resolution. Every error at once, exit codes as `spec validate`. Run by each package's build, by the CI of `common`, `keel-core` and `keel-web`, and on a machine |
| `keel manifest show [NAME] [--resolved] [--derived monit\|firewall\|backup\|replication]` | Prints a manifest, the resolved chain, or what a consumer would derive from it on this machine. The derived output is the same code `apply` renders with, so what `show` prints is what `apply` writes |
| `keel spec validate` | Becomes manifest-aware: the keys `overlays`, `secrets`, `app.options`, `services` and `workers` may take are the ones the installed manifests declare |
| `keel spec apply --system` | Converges the overlays' units to the spec's states, in `requires` order, and writes the Monit file and the firewall rules above. It never writes an overlay's configuration content: that is the package's and the installer's |
| `keel inspect` | Writes `appliance`, `overlays` and the application sections from the manifests and systemd, and reports what it could not infer |
| `keel diff` | Compares the states with systemd, and the derived Monit file and firewall with what is on disk, so a hand edit of either is drift |
| The installer (the `installer` overlay: inithooks and confconsole) | Reads the resolved manifest for the mode the operator chose: shows the `screen` of every `ask` overlay, asks for every secret that is not generated, writes the spec, and emits it complete (0027) |
| TKLBAM, through the derived overrides (0037) | Reads the backup set |
| The Syncthing overlay (0032), the registry (0025), the Monit summary agent (0040) | Read what is derived for them, above |

A manifest is read, never executed: no field is a template, no field is
evaluated. The `command` of a check is an argv list run by Monit.

## Worked example: Keel Core

Core is Debian, wireguard, etcd, crowdsec and the installer (0036). Four
overlay manifests and one appliance manifest.

```yaml
# /usr/share/keel/overlays/wireguard.yaml, from keel-overlay-wireguard
manifest_version: 1
kind: overlay
name: wireguard
title: WireGuard
summary: The mesh overlay (0024); the interface itself is the spec's (0018, 0020)
screen: /usr/lib/confconsole/plugins.d/Networking/wireguard.py
```

It declares no process and no check, on purpose. The interface, its unit
(`wg-quick@<interface>`), its address and its port are chosen per machine
and live in `network.overlay.wireguard` of the spec, converged under 0018's
confirmation window. What the overlay contributes is `wireguard-tools` (its
package's `Depends`) and the screen. Its health is the link check of the
spec's `monitor.checks.network.<interface>.link`, which the installer
writes for the overlay interface in the cloud modes. A manifest that named
`wg0` would be declaring a machine's choice.

```yaml
# /usr/share/keel/overlays/etcd.yaml, from keel-overlay-etcd
manifest_version: 1
kind: overlay
name: etcd
title: etcd
summary: The mesh registry (0025); control plane only, never application data
requires: [wireguard]
processes:
  - name: etcd
    unit: etcd.service
    listen:
      - {port: 2379, protocol: tcp, expose: mesh}
      - {port: 2380, protocol: tcp, expose: mesh}
checks:
  - {name: etcd-health, process: etcd, type: http, address: mesh,
     port: 2379, path: /health, expect: 200, on_failure: restart}
data:
  - {path: /var/lib/etcd, replication: native, backup: none}
```

```yaml
# /usr/share/keel/overlays/crowdsec.yaml, from keel-overlay-crowdsec
manifest_version: 1
kind: overlay
name: crowdsec
title: CrowdSec
summary: Bans first, before anything else sees the request (0029, 0030)
screen: /usr/lib/confconsole/plugins.d/Security/crowdsec.py
processes:
  - name: crowdsec
    unit: crowdsec.service
    listen:
      - {address: 127.0.0.1, port: 8080, protocol: tcp, expose: loopback}
      - {address: 127.0.0.1, port: 6060, protocol: tcp, expose: loopback}
  - name: firewall-bouncer
    unit: crowdsec-firewall-bouncer.service
checks:
  - {name: crowdsec-lapi, process: crowdsec, type: tcp, address: loopback,
     port: 8080, on_failure: restart}
data:
  - {path: /var/lib/crowdsec/data, replication: none, backup: none}
```

The two ports are the ones Debian's `crowdsec` 1.4.6 package configures
(`/etc/crowdsec/config.yaml`, `listen_uri: 127.0.0.1:8080`, and the
Prometheus endpoint it enables), both IPv4 loopback only. Declaring them
here is what makes them occupied for every appliance built on Core, whether
CrowdSec runs or not.

```yaml
# /usr/share/keel/overlays/installer.yaml, from keel-overlay-installer
manifest_version: 1
kind: overlay
name: installer
title: Installer
summary: The simple and advanced installation, discovery, YAML emission (0028, 0026, 0027)
hooks:
  first_boot:
    - /usr/lib/inithooks/firstboot.d/00declarative
    - /usr/lib/inithooks/firstboot.d/10keel-system
    - /usr/lib/inithooks/firstboot.d/75keel-role
    - /usr/lib/inithooks/firstboot.d/80keel-cloud
```

```yaml
# /usr/share/keel/appliances/core.yaml, from keel-core
manifest_version: 1
kind: appliance
name: core
title: Keel Core
summary: Debian, the mesh, CrowdSec and the installer (0036)
base: none
overlays:
  installer: {simple: enabled,  cloud_simple: enabled,  cloud_advanced: enabled}
  wireguard: {simple: disabled, cloud_simple: enabled,  cloud_advanced: enabled}
  etcd:      {simple: disabled, cloud_simple: disabled, cloud_advanced: enabled}
  crowdsec:  {simple: disabled, cloud_simple: enabled, cloud_advanced: enabled}
processes:
  - name: sshd
    unit: ssh.service
    listen: [{port: 22, protocol: tcp, expose: public}]
  - name: webmin
    unit: webmin.service
    listen: [{port: 12321, protocol: tcp, expose: public}]
  - name: postfix
    unit: postfix.service
    listen: [{address: 127.0.0.1, port: 25, protocol: tcp, expose: loopback}]
checks:
  - {name: sshd, process: sshd, type: protocol, protocol: ssh,
     address: loopback, port: 22, on_failure: restart}
  - {name: webmin, process: webmin, type: http, tls: true, address: loopback,
     port: 12321, path: /, expect: 200, on_failure: restart}
  - {name: postfix, process: postfix, type: protocol, protocol: smtp,
     address: loopback, port: 25, on_failure: restart}
secrets:
  - name: root_password
    description: The root password, for SSH and Webmin
    generate: allowed
    shared: false
```

Postfix binds `127.0.0.1` alone on a TurnKey appliance: its `main.cf` says
`inet_interfaces = localhost`, and Debian resolves `localhost` to the IPv4
loopback only (docs/spec.md in keel says why). So its port declares that
literal, as CrowdSec's do, and the SMTP probe connects to `127.0.0.1`; at
`::1` it failed on every cycle and Monit restarted postfix until its
restart limit (errata, 2026-09-30, found by step 3's test of 0041).

Core has no web shell. TurnKey removed shellinabox (port 12320) in 18.0,
Webmin's own terminal taking its place, and common 19.x installs none. A
`webshell` process naming `shellinabox.service` failed `keel manifest
validate` on the built Core image (rule 5: no unit file), and with it every
spec naming the appliance, so it is not declared (errata, 2026-09-30,
found by step 4's image test of 0041).

Where each state comes from:

| Overlay | simple | cloud simple | cloud advanced | Source |
| --- | --- | --- | --- | --- |
| installer | enabled | enabled | enabled | 0036: it is what installs |
| wireguard | disabled | enabled | enabled | 0028: a simple installation has no mesh; 0024: every appliance can join one |
| etcd | disabled | disabled | enabled | 0036: stopped by default; 0028: the quorum is cloud advanced's |
| crowdsec | disabled | enabled | enabled | 0029: installed and disabled in simple; enabled in the cloud modes (0041, "Resolved") |

**What Core derives, simple installation.**

| Consumer | Result |
| --- | --- |
| Monit | `sshd`, `webmin`, `postfix`: three unit checks, and the ssh, HTTPS and SMTP probes above. Nothing for etcd or CrowdSec, which are off |
| Firewall | 22 and 12321 incoming. The Core recipe's `WEBMIN_FW_TCP_INCOMING` says 22, 80, 443 and 12321 today, which the derived firewall replaces |
| Backup | TKLBAM's system delta, as today (`/etc`, the spec and its secret files among it, and the package list). etcd and CrowdSec contribute nothing (`backup: none`) |
| File replication | none |
| Registry | none: no etcd in a simple installation |

**Cloud advanced**: Monit adds `etcd` with
its `/health` probe, `crowdsec` with the LAPI probe and
`firewall-bouncer`; the firewall adds 2379 and 2380 on the WireGuard
interface only, and the overlay's UDP port from the spec on the uplink;
backup is unchanged; the node writes its registry entry.

## Worked example: Keel Web

Keel Web is Core plus nginx, coraza and anubis (0036), Nginx only in a
simple installation and the full pipeline in an advanced one (0030).

```yaml
# /usr/share/keel/overlays/nginx.yaml, from keel-overlay-nginx
manifest_version: 1
kind: overlay
name: nginx
title: Nginx
summary: Terminates TLS and serves static files (0030)
processes:
  - name: nginx
    unit: nginx.service
    listen:
      - {port: 80, protocol: tcp, expose: public}
      - {port: 443, protocol: tcp, expose: public}
checks:
  - {name: nginx, process: nginx, type: http, address: loopback, port: 80,
     path: /keel-health, expect: 204, on_failure: restart}
```

`/keel-health` is a location the overlay's own configuration ships, allowed
from the loopback addresses only, answering 204 without touching an
application. A check against `/` would measure whatever application sits
behind Nginx, and restart Nginx for that application's failure.

```yaml
# /usr/share/keel/overlays/coraza.yaml, from keel-overlay-coraza
manifest_version: 1
kind: overlay
name: coraza
title: Coraza
summary: A WAF inside Nginx with the OWASP Core Rule Set (0030)
requires: [nginx]
hooks:
  state: {path: /usr/lib/keel/overlays/coraza/state}
checks:
  - name: waf-blocks
    type: http
    address: loopback
    port: 80
    path: "/keel-health?keel-waf-probe=%3Cscript%3Ealert(1)%3C%2Fscript%3E"
    expect: 403
    every_cycles: 10
    on_failure: alert
```

Coraza is a module loaded into Nginx: no unit, so no process. Its check is
not "is it loaded" but "does it block": a request carrying a script tag,
which the Core Rule Set refuses, must get 403. A WAF that loaded and blocks
nothing passes every other test there is. The failure is an alert, not a
restart, because restarting Nginx does not fix a rule set; and it runs every
tenth cycle, because each probe is a log line in the WAF and in the access
log. The loopback addresses must be in CrowdSec's whitelist, or the probe
teaches CrowdSec to ban the machine's own loopback; that is the overlay
package's configuration, and its gate tests it.

Errata, 2026-10-01, found by step 7 of 0041 (Keel-Linux/keel#62 and
#63): with no unit there was nothing for `apply` to start, so turning
Coraza on in the spec wrote the `waf-blocks` check and loaded nothing.
The overlay therefore declares `hooks.state`, the hook its package ships
to link the module, test and reload Nginx, check the probe and roll back.
It is a new key of version 1 rather than version 2: no manifest that
carries it existed before, and the package declares `Depends: keel (>=
0.15.0)`, the first keel that reads it. `validate` checks it as rule 12
checks a first boot hook; `apply` runs it, and every executable of
`state.d/` beside it, within its timeout, only when they and their
directories are root's, not writable by group or others, and inside
`/usr/lib/keel/overlays`, and records the
state with a digest of the hooks so that a hook installed later runs too.

```yaml
# /usr/share/keel/overlays/anubis.yaml, from keel-overlay-anubis
manifest_version: 1
kind: overlay
name: anubis
title: Anubis
summary: Proof of work behind Nginx, never at the edge (0030)
requires: [nginx]
processes:
  - name: anubis
    unit: anubis@keel.service
    listen:
      - {address: "::1", port: 8923, protocol: tcp, expose: loopback}
checks:
  - {name: anubis, process: anubis, type: tcp, address: loopback, port: 8923,
     on_failure: restart}
secrets:
  - name: anubis_signing_key
    description: The key Anubis signs its challenge cookies with
    generate: required
    shared: true
```

The signing key is the case `shared` exists for. Anubis generates a random
key at start when none is given, so two nodes of a set, or one node after a
restart, would each refuse the cookies the other signed, and every visitor
who solved a challenge would solve it again after a failover. One key per
set, generated by the primary, avoids that. The port is Anubis's documented
default, bound to the loopback, since Nginx is its only client (0030:
Anubis sits behind Nginx).

Errata, 2026-10-01, found by step 6 of 0041 (Keel-Linux/common#21): the
unit was `anubis.service`. Keel's anubis package (step 5) ships the
template `anubis@.service`, one instance per environment file in
`/etc/anubis`, so the overlay runs the instance `anubis@keel.service`
(rule 5 finds an instance by its template file). The port declares the
literal `::1`, the one family it binds: Keel is IPv6 first, and the TCP
check reaches it there.

```yaml
# /usr/share/keel/appliances/web.yaml, from keel-web
manifest_version: 1
kind: appliance
name: web
title: Keel Web
summary: Nginx, Coraza and Anubis, the base of every web appliance (0030)
base: core
overlays:
  nginx:  {simple: enabled,  cloud_simple: enabled, cloud_advanced: enabled}
  coraza: {simple: disabled, cloud_simple: enabled, cloud_advanced: enabled}
  anubis: {simple: disabled, cloud_simple: enabled, cloud_advanced: enabled}
```

Keel Web adds no process of its own: everything it runs is an overlay's.
Its manifest is three lines of states over Core's.

**Resolved**, as `keel manifest show web --resolved` prints it:

| Overlay | From | simple | cloud simple | cloud advanced |
| --- | --- | --- | --- | --- |
| installer | core | enabled | enabled | enabled |
| wireguard | core | disabled | enabled | enabled |
| etcd | core | disabled | disabled | enabled |
| crowdsec | core | disabled | enabled | enabled |
| nginx | web | enabled | enabled | enabled |
| coraza | web | disabled | enabled | enabled |
| anubis | web | disabled | enabled | enabled |

| Port | Process | From | Exposure |
| --- | --- | --- | --- |
| 22/tcp | sshd | core | public |
| 25/tcp | postfix | core | loopback, IPv4 |
| 80/tcp, 443/tcp | nginx | web (nginx) | public |
| 2379/tcp, 2380/tcp | etcd | core (etcd) | mesh |
| 6060/tcp, 8080/tcp | crowdsec | core (crowdsec) | loopback, IPv4 |
| 8923/tcp | anubis | web (anubis) | loopback, IPv6 |
| 12321/tcp | webmin | core | public |

**What Web derives.**

| Consumer | Simple installation | Cloud advanced |
| --- | --- | --- |
| Monit | Core's three, and `nginx` with `/keel-health` | also etcd, crowdsec, firewall-bouncer, anubis, and `waf-blocks` every tenth cycle |
| Firewall | 22, 80, 443, 12321 | also 2379 and 2380 on the WireGuard interface, and the overlay's UDP port |
| Backup | Core's; Web adds nothing: its configuration is in `/etc`, already in TKLBAM's delta | the same |
| File replication | none | none: nothing Web holds is data |
| Secrets | `root_password` | also `anubis_signing_key`, shared, generated on the primary |

The phase 3 criterion of the roadmap (tracker#46) reads straight off this
table: in advanced mode the WAF blocks a Core Rule Set test payload, which
is the `waf-blocks` check; in simple mode Keel Web is plain Nginx, which is
the `disabled` states.

## Worked example: Keel PHP inherits Web

```yaml
# /usr/share/keel/appliances/php.yaml, from keel-php
manifest_version: 1
kind: appliance
name: php
title: Keel PHP
summary: Keel Web and PHP-FPM; replaces LAMP and LAPP (0036)
base: web
overlays:
  php-fpm: {simple: enabled, cloud_simple: enabled, cloud_advanced: enabled}
```

It inherits, without restating any of them: the seven overlays and their
states from Web and Core, every process and check, every port (so a
`php-fpm` overlay that declared port 8080 would fail validation against
CrowdSec's LAPI even though CrowdSec is off in a simple installation), the
secrets, and the installer's first boot hooks. Its layer is the delta of
`php-fpm` on the `web` layer. It cannot turn Coraza on in simple mode; an
operator can, on one machine, in the spec.

## Validation rules

`keel manifest validate` reports every error it finds, never only the
first.

**Every file**

1. `manifest_version` is `1`; `kind` is `overlay` or `appliance`; `name`
   matches the file name and `[a-z][a-z0-9-]*`, at most 32 characters.
2. Unknown keys are errors at every level; so are keys of the other kind
   (`base` in an overlay, `provides` in an appliance).
3. Every name (process, check, secret, option, service, worker) matches
   `[a-z][a-z0-9_-]*` and is unique in its list.
4. Paths are absolute and normalised: no `..`, no `//`, no trailing `/`.

**Processes and checks**

5. A unit is a systemd unit name (systemd.unit(5): no `/`) ending in
   `.service`. On a machine, and in the package build, the unit file
   exists, or an init script of the same name in `/etc/init.d/`, a
   regular executable file, from which systemd's SysV generator makes
   the unit at boot. trixie's shellinabox, for one, ships only
   `/etc/init.d/shellinabox`. A systemd that drops SysV support will
   need a unit file shipped by Keel for such a package. An instance of
   a template unit (`anubis@keel.service`) is found by its template's
   file (`anubis@.service`), which is how instances ship.
6. A port is between 1 and 65535. A literal `address` is `::1` or
   `127.0.0.1`; `localhost`, `ip6-localhost` and every name are refused,
   with docs/spec.md's reason.
7. A check's `process` names a process of the same chain; `on_failure:
   restart` requires it; the fields of its `type` are present and no
   others.
8. `restart.attempts` is at most `restart.within_cycles`.
9. A `command` is a non-empty argv list whose first element is an absolute
   path.

**Overlays**

10. `requires` names overlays that are installed, and the graph has no
    cycle.
11. `data[].replication` is `native` or `none`; `data[].backup` is `dump`,
    `files` or `none`; `dump` only with a `provides` engine that has one,
    which in version 1 is `mariadb` (`mariadb-dump`) and `postgresql`
    (`pg_dump`). `redis`, `opensearch`, `elasticsearch` and `s3` keep
    their data as files (`backup: files`) or not at all (`none`).
12. `hooks.first_boot` entries are under
    `/usr/lib/inithooks/firstboot.d/`, exist, are executable, are owned by
    root and are not writable by group or others. In a package build the
    check runs on the tree `dh_fixperms` leaves, under `fakeroot`
    (`dpkg-buildpackage` uses it by default), where the files read as
    owned by root just as they will be installed; a build without
    fakeroot cannot pass the owner check and must not skip it. An
    overlay's `hooks.state.path` is its own
    `/usr/lib/keel/overlays/<name>/state` and passes the same checks;
    `hooks.state.timeout` is a whole number of seconds from 1 to 600; an
    appliance has no `hooks.state` (errata of the Coraza example).

**Appliances**

13. `base` names an installed appliance manifest, or is `none` for `core`
    only; the chain has no cycle and ends at `core`.
14. Every overlay listed has an installed overlay manifest, and all three
    mode keys, each `enabled`, `disabled` or `ask`; `ask` only for an overlay with a
    `screen`.
15. In every mode, an overlay that is `enabled` (or `ask`, which can become
    `enabled`) has every overlay of its `requires` `enabled` in that mode, across the
    whole chain.
16. An overlay name appears once in the resolved chain.
17. `(port, protocol)` is unique across every process of the resolved
    chain, whatever the states.
18. Process, check, secret and option names are unique across the resolved
    chain.
19. The application sections appear in at most one manifest of a chain.
20. A secret with `shared: true` has `generate: required` or `allowed`:
    a person cannot be relied on to type the same value twice.

**Application sections** (appendix)

21. A service's `engine` is a `provides` engine, or a list of them; a
    placement is `embedded`, `discovered`, or `none` only when `required:
    false`; `embedded` in any mode needs an overlay that `provides` the
    engine, and that overlay is `enabled` wherever the service is `embedded`.
22. A service's `secret`, and every name in `hooks.migrate.needs` and in a
    worker's `queue`, is declared in the same manifest.
23. `state` paths follow the rules of the `state.replicate` row; each
    `exclude` is inside a replicated path; an `unless` names a service with
    `required: false`.
24. A worker has a `unit` and no writable path (there is no `writes`
    field); `scaling.default` is at most `scaling.max`; `singleton: true`
    means `max: 1`.

**The spec against the manifests** (run by `keel spec validate`)

25. `appliance.name` is installed; `overlays` names exactly the overlays of
    the resolved chain, each `enabled` or `disabled`; the `requires` of every `enabled`
    overlay are `enabled`.
26. `secrets.<name>` is one of the three existing names or a name a
    resolved manifest declares; `generate: true` is refused where the
    manifest says `never`.
27. `app.options` keys are declared options, of the declared type; a
    required option is present.

## Out of scope for version 1

Each of these is a reason for version 2 or for a decision of its own, not
an omission:

- **A child changing or removing what it inherits.** States, processes and
  ports are inherited as they are.
- **Moving a machine between installation modes.** The mode is chosen once
  (0028); converting a simple installation into a cloud one is a migration
  with data, not a field.
- **Configuration content.** No manifest field templates `nginx.conf`,
  CrowdSec's acquisitions or etcd's cluster membership.
- **A VIP outside the database appliances.** For now the `vip` overlay is
  carried by the database appliances only (0041, "Resolved"), so Core and
  Web have none.
- **etcd's key layout, its TLS, and the entry secret of 0026.** The
  registry entry above lists what is announced, not how it is keyed.
- **More than one application on a machine.**
- **Resource sizing** (memory or disk a mode needs), which would let the
  installer warn; it is a hint nobody reads yet.
- **Prometheus**, which 0040 leaves optional.
- **The application sections' finer points**: the Nginx vhost beyond the
  routes in `web`, cross-major upgrades, workers placed on other nodes,
  object storage buckets and the search engine choice of 0033.
- **Signing the manifest.** It is a file of a signed package; apt already
  verifies it.

## Appendix: the application sections

These sections exist so that the schema's shape is known to hold for
applications. They are not needed by Core or Web, and they are the part of
version 1 most likely to move when the first application is built from a
manifest (Phase 4 of the roadmap).

```yaml
services:
  database:
    engine: mariadb                 # or a list: [opensearch, elasticsearch]
    version: ">= 10.11"
    required: true
    placement: {simple: embedded, cloud_simple: embedded, cloud_advanced: discovered}
    durable: true
    secret: db_password
    defaults: {name: wordpress, user: wordpress}
state:
  replicate:
    - /var/www/wordpress/wp-content
  exclude:
    - /var/www/wordpress/wp-content/cache
workers:
  - name: wp-cron
    unit: wordpress-cron.service
    every: 5min
web:
  root: /var/www/wordpress
  routes:
    - {path: /, to: php}
  health: {path: /wp-login.php, expect: 200}
hooks:
  first_boot: [/usr/lib/inithooks/firstboot.d/40wordpress]
  migrate:
    command: [/usr/lib/keel-wordpress/migrate]
    needs: [database]
```

| Field | Notes |
| --- | --- |
| `services.<name>.engine` | One of the `provides` engines, or a list of them when the application accepts either (Elasticsearch or OpenSearch is undecided, 0033). The spec records which, only when there is a choice |
| `services.<name>.version` | A constraint on the engine's upstream version. Embedded: checked against the installed overlay's package. Discovered: the installer lists only offers in the registry that satisfy it (0026) |
| `services.<name>.required` | `false` adds a third placement, `none` |
| `services.<name>.placement` | Allowed default per mode: `embedded` (the engine's overlay is `enabled` on this machine, 0033), `discovered` (on another node: chosen from the registry in an advanced installation, 0026, or typed where there is none, 0013 phase 1), or `none`. An engine that is ever `embedded` puts its overlay in the image |
| `services.<name>.durable` | `true`: the application keeps data there that nothing can rebuild, so it is backed up. `false`: a cache, sessions, or derived data |
| `services.<name>.rebuild` | For `durable: false` derived data: the argv that rebuilds it when a node joins (0033: a search index is rebuilt, never replicated) |
| `services.<name>.secret` | The name of a declared secret, the credential for this service |
| `services.<name>.defaults` | `name` and `user` within the service, which the spec may change |
| `state.replicate` | The paths of the application's durable state on a filesystem (0032), each a path or `{path: P, unless: S}`. Replicated by file in cloud advanced, backed up in every mode. A path may not be inside another, nor inside any `data[].path` of an overlay (a database's directory is never replicated by file, 0032), nor under `/etc`, `/usr`, `/tmp`, `/var/tmp`, `/var/cache`, `/var/log` or `/run` |
| `state.exclude` | Paths inside a replicated one that are not: caches, sessions, tmp, locks, logs, rebuildable indexes (0032) |
| `state.replicate[].unless` | Written `{path: P, unless: objects}`: the path is not replicated or backed up by file when the optional service named is placed, because the data is in object storage then (0038) |
| `workers[]` | Either `unit` alone (a long running consumer) or `unit` with `every` (a periodic job, rendered as a systemd timer). Workers run only on the active node: the hot standby serves nothing (0031), and a periodic job on it would write into a read-only database |
| `workers[].queue` | The service the worker reads its work from |
| `workers[].scaling` | `{default: N, max: M, singleton: bool}`: a hint the installer and the spec's `workers.<name>.instances` are held to |
| (no `writes`) | A worker never writes to local disk (0034, confirmed in 0041's "Resolved"): it reads a queue and writes to data services. There is no field to grant a path; keel's unit drop-in sets `ProtectSystem=strict` and `PrivateTmp=yes` with no `ReadWritePaths=`, so a worker that tries fails loudly instead of writing to one node |
| `web` | What Keel Web routes to the application: `root`, `routes` (`to: php`, or `to: {port: N}` with `websocket: true` where needed), `max_body` for a runtime that is not PHP (PHP's comes from its `post_max_size`), and one `health` probe through Nginx |
| `hooks.migrate` | What the package's post-installation runs after an upgrade (0039), on the active node only, after a return point is taken; `needs` names the services that must be writable. A major version of an application is a different package, so apt never crosses one |

**Derived for an application.** Backup: the `state.replicate` paths minus
the excludes, plus every `durable` service that is `embedded`, kept as its
overlay's `data[].backup` says (a dump for `mariadb` and `postgresql`, the
files for the others, rule 11); a
`discovered` service is backed up by its own appliance, from its standby
(0037), and the application's backup records which service and which
database it used. File replication: one Syncthing folder per replicated
path, in cloud advanced only. Monit: each worker's unit, the `web.health`
probe, and every process of the embedded services' overlays.

On the spec side an application adds:

```yaml
services:
  database:
    placement: embedded
    host: "::1"
    port: 3306
    name: wordpress
    user: wordpress
workers:
  wp-cron: {instances: 1}
app:
  options:
    site_title: WordPress
```

`services.<name>` takes the fields of today's `database.client.primary`
plus `placement`, and `database.client` becomes the alias for the service
named `database`, through the compatibility table docs/spec.md in keel
already uses for renamed fields. The credential stays in `secrets`, bound to
the name the manifest's `secret` gives. `database.server` keeps describing
the server this machine runs, and its `engine` must agree with the embedded
service's. The service renders as `KEEL_SVC_<NAME>_PLACEMENT`, `_HOST`,
`_PORT`, `_NAME` and `_USER` for the first boot hook.

## Appendix: WordPress, Odoo and Mastodon

Short on purpose: each shows one shape the schema must hold. None is a plan
for the appliance as it is built today.

### WordPress: PHP, one database, one volume

```yaml
manifest_version: 1
kind: appliance
name: wordpress
title: WordPress
summary: Blog and site publishing
base: php
overlays:
  mariadb: {simple: enabled, cloud_simple: enabled, cloud_advanced: disabled}
services:
  database:
    engine: mariadb
    version: ">= 10.11"
    required: true
    placement: {simple: embedded, cloud_simple: embedded, cloud_advanced: discovered}
    durable: true
    secret: db_password
    defaults: {name: wordpress, user: wordpress}
state:
  replicate: [/var/www/wordpress/wp-content]
  exclude:
    - /var/www/wordpress/wp-content/cache
    - /var/www/wordpress/wp-content/upgrade
    - /var/www/wordpress/wp-content/upgrade-temp-backup
workers:
  - {name: wp-cron, unit: wordpress-cron.service, every: 5min}
web:
  root: /var/www/wordpress
  routes: [{path: /, to: php}]
  health: {path: /wp-login.php, expect: 200}
secrets:
  - {name: db_password, description: The WordPress database account, generate: allowed, shared: true}
  - {name: app_password, description: The WordPress administrator, generate: allowed, shared: false}
  - {name: auth_salts, description: The eight keys and salts of wp-config.php, generate: required, shared: true}
options:
  - {name: site_title, type: string, default: WordPress}
  - {name: admin_user, type: string, default: admin, pattern: '^[A-Za-z0-9._@+-]+$'}
  - {name: db_prefix, type: string, default: wp_, pattern: '^[A-Za-z_][A-Za-z0-9_]*$'}
hooks:
  first_boot: [/usr/lib/inithooks/firstboot.d/40wordpress]
  migrate: {command: [/usr/lib/keel-wordpress/migrate], needs: [database]}
```

| Derived | Result |
| --- | --- |
| Backup | `wp-content` without the three excludes; the `wordpress` database dumped when it is embedded |
| Monit | the embedded `mariadb` overlay's process and check; the `wp-cron` timer; `/wp-login.php` through Nginx; and Keel PHP's, Web's and Core's |
| Replication | one folder, `wp-content`, in cloud advanced |
| Firewall | nothing added: MariaDB's 3306 is `loopback` when embedded |

The `mariadb` overlay is carried because the database is `embedded` in the
two simple modes, and rule 21 needs an overlay that provides the engine
`enabled` wherever a service is embedded. It is `disabled` in cloud
advanced, where the database is `discovered` on another node; it is in the
image all the same (0013), so an operator can still turn it on.

`auth_salts` is `shared` because a visitor logged in on the primary is
logged out by a standby that signed its cookies with other salts.
`wp-cron` is a worker rather than a cron line so that it runs on the active
node only: on a read-only standby it writes into a database that refuses
it.

### Odoo: Python, a filestore, workers

```yaml
manifest_version: 1
kind: appliance
name: odoo
title: Odoo
summary: Odoo Community with the OCA (0022)
base: python
overlays:
  postgresql: {simple: enabled, cloud_simple: enabled, cloud_advanced: disabled}
services:
  database:
    engine: postgresql
    version: ">= 13"
    required: true
    placement: {simple: embedded, cloud_simple: embedded, cloud_advanced: discovered}
    durable: true
    secret: db_password
    defaults: {name: odoo, user: odoo}
  sessions:
    engine: redis
    required: false
    placement: {simple: none, cloud_simple: none, cloud_advanced: discovered}
    durable: false
state:
  replicate: [/var/lib/odoo/filestore, /var/lib/odoo/addons]
processes:
  - name: odoo
    unit: odoo.service
    listen:
      - {port: 8069, protocol: tcp, expose: loopback}
      - {port: 8072, protocol: tcp, expose: loopback}
checks:
  - {name: odoo, process: odoo, type: http, address: loopback, port: 8069,
     path: /web/health, expect: 200, on_failure: restart}
workers:
  - name: cron
    unit: odoo-cron.service
    queue: database
    scaling: {default: 1, max: 4, singleton: false}
web:
  routes:
    - {path: /, to: {port: 8069}}
    - {path: /websocket, to: {port: 8072}, websocket: true}
  max_body: 128M
  health: {path: /web/health, expect: 200}
secrets:
  - {name: db_password, description: The Odoo database role, generate: allowed, shared: true}
  - {name: admin_passwd, description: The database manager's master password, generate: required, shared: true}
  - {name: app_password, description: The Odoo administrator, generate: allowed, shared: false}
options:
  - {name: localization, type: string, default: ""}
hooks:
  first_boot: [/usr/lib/inithooks/firstboot.d/40odoo]
  migrate: {command: [/usr/lib/keel-odoo/migrate], needs: [database]}
```

| Derived | Result |
| --- | --- |
| Backup | the filestore and the addons; the `odoo` database when embedded; Redis never, it is not durable |
| Monit | `odoo` with `/web/health`; `odoo-cron`; PostgreSQL's overlay when embedded |
| Replication | two folders in cloud advanced: the filestore must move with its database (0020, hard part 3), which the promotion of 0032 does |

Only `postgresql` is carried: the `sessions` service is never `embedded`,
so rule 21 asks for no `redis` overlay.

Odoo's `data_dir` (`/var/lib/odoo` in Debian's package) holds three
directories: `filestore/` (attachments, per database), `addons/` (modules
installed from the interface) and `sessions/`. Only the first two are
replicated. `sessions/` needs no exclude, since it is inside neither
replicated path (rule 23), and it is not state to move: sessions live in
the database or in Redis (0032).

Odoo is the case the worker rule bites: cron jobs create attachments, and
Odoo writes them to the filestore by default. Since a worker never writes to
disk, the cron worker's attachments have to go to a data service, the
database (Odoo's `ir_attachment.location` set to `db`) or object storage
(0038). The manifest cannot set that; the worker's unit refuses the write if
it is not done, and the first Odoo built from a manifest settles which.

### Mastodon: Ruby and Node, media, Sidekiq, optional search

```yaml
manifest_version: 1
kind: appliance
name: mastodon
title: Mastodon
summary: The reference appliance of the composition model (0035)
base: ruby
overlays:
  nodejs: {simple: enabled, cloud_simple: enabled, cloud_advanced: enabled, version: ">= 20"}
  postgresql: {simple: enabled, cloud_simple: enabled, cloud_advanced: disabled}
  redis: {simple: enabled, cloud_simple: enabled, cloud_advanced: disabled}
  s3: {simple: enabled, cloud_simple: enabled, cloud_advanced: disabled}
services:
  database:
    engine: postgresql
    version: ">= 13"
    required: true
    placement: {simple: embedded, cloud_simple: embedded, cloud_advanced: discovered}
    durable: true
    secret: db_password
    defaults: {name: mastodon, user: mastodon}
  redis:
    engine: redis
    required: true
    placement: {simple: embedded, cloud_simple: embedded, cloud_advanced: discovered}
    durable: true
  search:
    engine: [opensearch, elasticsearch]
    required: false
    placement: {simple: none, cloud_simple: none, cloud_advanced: discovered}
    durable: false
    rebuild: [/usr/lib/keel-mastodon/tootctl, search, deploy]
  objects:
    engine: s3
    required: true
    placement: {simple: embedded, cloud_simple: embedded, cloud_advanced: discovered}
    durable: true
processes:
  - name: web
    unit: mastodon-web.service
    listen: [{port: 3000, protocol: tcp, expose: loopback}]
  - name: streaming
    unit: mastodon-streaming.service
    listen: [{port: 4000, protocol: tcp, expose: loopback}]
checks:
  - {name: mastodon-web, process: web, type: http, address: loopback,
     port: 3000, path: /health, expect: 200, on_failure: restart}
  - {name: mastodon-streaming, process: streaming, type: http, address: loopback,
     port: 4000, path: /api/v1/streaming/health, expect: 200, on_failure: restart}
workers:
  - name: sidekiq
    unit: mastodon-sidekiq.service
    queue: redis
    scaling: {default: 1, max: 8, singleton: false}
web:
  root: /usr/share/mastodon/public
  routes:
    - {path: /, to: {port: 3000}}
    - {path: /api/v1/streaming, to: {port: 4000}, websocket: true}
  max_body: 99M
  health: {path: /health, expect: 200}
secrets:
  - {name: db_password, description: The Mastodon database role, generate: allowed, shared: true}
  - {name: secret_key_base, description: Rails session and cookie key, generate: required, shared: true}
  - {name: otp_secret, description: Two-factor secret key, generate: required, shared: true}
  - {name: vapid_private_key, description: Web push key, generate: required, shared: true}
  - {name: active_record_encryption, description: The three Active Record encryption keys, generate: required, shared: true}
options:
  - {name: local_domain, type: string, pattern: '^[a-z0-9.-]+$'}
  - {name: admin_user, type: string, default: admin}
hooks:
  first_boot: [/usr/lib/inithooks/firstboot.d/40mastodon]
  migrate: {command: [/usr/lib/keel-mastodon/migrate], needs: [database]}
```

| Derived | Result |
| --- | --- |
| Backup | PostgreSQL, Redis and the object store when embedded, all durable (Sidekiq's queues live in Redis, the media in the object store): PostgreSQL by its dump, Redis and the object store by their files (`backup: files` in their overlays, since neither engine has a dump in the sense of rule 11); search never; no file on the application's disk |
| Monit | `web`, `streaming` and their health endpoints; `sidekiq`; the embedded PostgreSQL, Redis and object storage overlays |
| Replication | none by file: Mastodon keeps no state on its own disk |
| On join | `tootctl search deploy` rebuilds the index on a node that joins with search placed |

Object storage is required, not optional, because of the worker rule:
Sidekiq downloads and resizes media, and a worker never writes to disk, so
the media go to the `s3` overlay (Garage, 0038), embedded in the simple
modes and discovered in cloud advanced. That removes Mastodon's only
filesystem state, so it has no `state` section at all.

`local_domain` has no default and so is required: Mastodon cannot change
it after the first account exists, which makes it a choice the installer
must ask for rather than one the manifest could make.
