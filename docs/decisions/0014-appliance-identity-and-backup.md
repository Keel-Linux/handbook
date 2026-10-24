# 0014: What an appliance calls itself, and what it says about backup

Date: 2026-09-28
Status: proposed by the agent, for the maintainer to confirm or amend.
Implemented in Keel-Linux/common (`/etc/keel_version`) and
Keel-Linux/keel-core (the login), neither merged.

## The two questions

An appliance login welcomed the operator twice, and the second welcome
named TurnKey and advertised TKLBAM (Keel-Linux/tracker#6,
Keel-Linux/keel-core#7). Fixing the text was the small part. Two questions
had to be answered first, and they belong here rather than in a commit
message:

1. Does `/etc/turnkey_version` keep its name, now that the distribution has
   another one?
2. What does an appliance say about backup, now that TKLBAM is deferred?

## 1. The TurnKey file is an interface we honour; the Keel file is what we say we are

**Decision.** `/etc/turnkey_version` keeps its exact name and its exact
format, `turnkey-<app>-<version>-<codename>-<architecture>`, on every Keel
appliance, whatever the appliance's release package is called. Beside it,
Keel writes `/etc/keel_version`, the same four fields with the `keel-`
prefix. Everything Keel presents to an operator reads the Keel file and
falls back to the TurnKey one; everything that exists to be read by other
software keeps reading the TurnKey one.

**Why the name stays.** It is not branding, it is a published interface,
and this project states compatibility with TurnKey appliances as a
property of itself (decision 0008). Measured on a running appliance,
2026-09-28, these read it:

| Reader | What it does with it |
| --- | --- |
| `/usr/bin/turnkey-version` | prints it |
| `sysversion` (`turnkey-version` package) | `AppVer`, `get_turnkey_release`, `fmt_sysversion` |
| `keel.inspect.app.probe_appliance` | the appliance identity of a machine, used by `keel inspect` and `keel diff` |
| inithooks `firstboot.d/29tagid`, `lib/tagid.sh`, `bin/secalerts.sh` | the tag id of the machine |
| `/etc/tklbam/hooks.d/maria-db-changes` | a version comparison |

**Why the format stays too.** Every one of those parsers is prefix
sensitive, so renaming the *content* breaks them as surely as renaming the
file:

- `sysversion._parse_turnkey_release` matches `turnkey-.*?-(\d.*?)-[^\d]`,
  so a string with another prefix makes `get_turnkey_release()` return the
  empty string and the release number disappears from every version
  string built from it;
- `sysversion.AppVer` does `removeprefix("turnkey-")` and then splits, so
  the app name of `keel-core-19.0-trixie-amd64` comes out as `keel-core`
  rather than `core`;
- `keel.inspect.app.probe_appliance` requires the string to start with
  `turnkey-` and reports the appliance as **missing** otherwise, which
  costs `keel inspect` and `keel diff` the identity of the machine
  they are describing.

**This was not hypothetical.** keel-core's changelog was renamed to
`keel-core-19.0` on 2026-09-27, and fab's `turnkey-version.py` takes the
name for `/etc/turnkey_version` from the first line of the changelog. The
next core layer would therefore have written
`keel-core-19.0-trixie-amd64` into a file whose every reader rejects it.
The published layer predates the rename, so nothing shipped is affected;
the next build would have been. The rule is enforced rather than hoped
for: `common/bin/keel-version-files` normalises the prefix before writing
either file, so the compatibility file always begins `turnkey-` no matter
what a repository calls its release package.

**Where the files are written.** In `mk/turnkey.mk` of common, in
`root.patched/post`, and in its second copy, `mk/turnkey-desktop.mk`, which
desktop appliances use, both through one script. Those are the only places
the version string exists, they are shared by every appliance instead of
being repeated in each recipe, and the step runs after every overlay, conf script, patch and removelist of the
build, so neither file can be clobbered. An appliance conf script could
not do it: conf scripts run in `root.patched/body`, before
`/etc/turnkey_version` is written, so the value they would derive from is
the parent layer's, or nothing at all on a rootfs layer.

**Consequences.**

- Two files that must agree. They are written by one call, from one
  string, so they cannot drift; a reader that finds them disagreeing has
  found a bug, not a choice.
- A Keel appliance keeps answering `turnkey-version` correctly, which is
  what makes an upstream tool, an upstream hook and an upstream backup
  profile keep working on it.
- Nothing Keel shows an operator says TurnKey, because the operator-facing
  path reads `/etc/keel_version`.
- The fallback to `/etc/turnkey_version` in the console banner is not
  permanent scaffolding; it is what keeps a banner correct on a layer
  built before the Keel file existed, and it costs one line.

**What would change the answer.** If the upstream parsers become prefix
agnostic, or if the last reader of `/etc/turnkey_version` disappears from
a Keel image, the compatibility file becomes dead weight and can be
dropped. Until then it stays, and it stays in the shape its readers
expect.

**Where a change of this kind lives.** The identity files are written in
`common` and the login is changed in keel-core, and the two placements
follow one rule, proposed here so the next case does not need a note of
its own: **the compatibility surface goes in `common`, the operator facing
surface goes in the product.** What other software reads (a file, its
name, its format) is shared by every appliance and belongs where every
appliance gets it. What the operator is shown is this project's own
voice, and keeping it out of `common` keeps `common` offerable upstream
(decision 0008).

## 2. The appliance says it has no backup, and says it once

**Decision.** An appliance never tells the operator to initialise a backup
service. In the place the TKLBAM block occupied, the login says one line:
backup is not configured, there is no backup service yet, and it will be
configured from confconsole when there is one. As shipped:

    Backup:  not configured. Keel has no backup service yet; when one
             arrives it is configured from confconsole.

**Why not silence.** An operator who sees nothing about backup concludes
either that it is handled or that the appliance has no opinion. Neither is
true. The one thing worth saying is the true one: nothing on this machine
is backing it up.

**Why not the old line.** TKLBAM is deferred to the end of the port
(decision 0002) and its remaining coupling is to a Hub this project does
not host. `tklbam-init` links a machine to a TurnKey Hub account, so an
operator who follows the instruction is sent to another project's service
to register a machine that is not that project's. That is worse than
saying nothing.

**Why not a URL.** The project site serves two pages today and has no
documentation section; `keellinux.org/docs/` answers 404, measured
2026-09-28. A login that points at a page that does not exist is an
advertisement for a service that does not exist, in a different costume.
When there is a page, the line gets one.

**Why confconsole is named.** It is the configuration surface this project
already maintains and already puts on the console, and naming it tells the
operator where to look without promising a date. It promises a place, not
a service.

**Consequences.**

- The block is cut from the system information command's output by shape,
  not by matching the words TKLBAM prints, so whatever replaces that
  block upstream is cut too. A filter written against the current wording
  would let the next version of the same mistake through in silence.
- When a backup service lands, this note is what says where its line
  goes and what it may claim. Until then the appliance advertises nothing.

**What would change the answer.** A backup service in the archive, hosted
or self-hosted, configured from confconsole and declared in the instance
description. Then the line says what is configured and where its last run
was, and this section is superseded rather than amended.
