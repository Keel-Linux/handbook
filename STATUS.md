# Keel: M0 status

Updated 2026-09-24. Project and organization name: KeelLinux (decided, see docs/decisions/0001). Brief: BRIEF.md. Prior research on the upstream code, the
measurements and the bug fixes live in ../TKL (same machine), and are cited
where they apply.

## Forks with full history

Created under the maintainer's personal account (github.com/marcos-mendez) so
M0 can start; they can be transferred into the organization once it exists,
which preserves history, issues and redirects. GitHub has no API to create an
organization, so that one step has to be done in the browser.

| Repository | Upstream | Fork |
| --- | --- | --- |
| fab | turnkeylinux/fab | created 2026-09-24 |
| buildtasks | turnkeylinux/buildtasks | created 2026-09-24 |
| tklbam | turnkeylinux/tklbam | created 2026-09-24 |
| tklbam-python-boto | turnkeylinux/tklbam-python-boto | created 2026-09-24 |
| turnkey-pylib | turnkeylinux/turnkey-pylib | created 2026-09-24 |
| lapp | turnkeylinux-apps/lapp | created 2026-09-24 |
| nginx-php-fastcgi | turnkeylinux-apps/nginx-php-fastcgi | created 2026-09-24 |
| wordpress | turnkeylinux-apps/wordpress | created 2026-09-24 |
| redis | turnkeylinux-apps/redis | created 2026-09-24 |
| ejabberd | turnkeylinux-apps/ejabberd | created 2026-09-24 |
| tkldev | turnkeylinux-apps/tkldev | pre-existing |
| webmin | turnkeylinux/webmin | created 2026-09-24 |
| cdroots | turnkeylinux/cdroots | created 2026-09-24 |
| common | turnkeylinux/common | pre-existing |
| confconsole | turnkeylinux/confconsole | pre-existing |
| inithooks | turnkeylinux/inithooks | pre-existing |
| turnkey-chroot | turnkeylinux/turnkey-chroot | pre-existing |
| tklbam-profiles | turnkeylinux/tklbam-profiles | pre-existing |
| moodle | turnkeylinux-apps/moodle | pre-existing |
| lamp | turnkeylinux-apps/lamp | pre-existing |

Two cases that need the organization, because GitHub allows only one fork of a
given upstream per account:

- `turnkeylinux-apps/core`: the account already holds a fork of it, renamed
  `mastodon` (that is how the Mastodon appliance was built). Fork core into the
  organization instead.
- `turnkeylinux-apps/odoo`: the name `odoo` in the account is a fork of
  `odoo/odoo` (upstream Odoo). Fork the appliance into the organization.

Tier-1 entries with no upstream repository to fork, so they start as new
repositories holding the maintainer's existing work: OJS (the account's `ojs` is
a fork of `pkp/ojs`, the application, not an appliance), pdns-recursor, CoTURN,
NAT64. Mastodon exists as the renamed core fork above and should be moved or
re-created with a clear name.

## Blocked on the maintainer

1. Create the GitHub organization (browser only). Then the agent forks core and
   odoo into it, transfers the repositories above, and adds the upstream remote
   to each.
2. Name decision, with the keel.sh collision on the table: see
   docs/decisions/0001-name-and-hosting-options.md.

## Already done that M0 depends on, from ../TKL

- A TKLDev 19.0 build host exists (KVM VM) and builds core cleanly. The trixie
  bootstrap is missing from the upstream mirror and has to be built locally;
  a fix for that is in `fix/build-missing-bootstrap` on the tkldev fork.
- The 19.0 ISO of core is already bit-for-bit reproducible from the same
  root.patched with `SOURCE_DATE_EPOCH` set, measured twice, with three guarded
  lines in fab (`feat/source-date-epoch`, local branch, see ../TKL/plan/06).
  This is the M0 "reproduces upstream artifacts" requirement, partly met: what
  is not yet reproducible is root.patched itself, which needs the package freeze.
- Seven upstream bugs found and fixed on branches, six of them pushed; they are
  the "fix in place, keep history" part of M0 and are also worth upstreaming.
- A declarative instance reader already exists on the inithooks fork
  (`feat/declarative-instance`): it translates a YAML file into the variables
  the existing hooks read, with 31 tests. That is the seed of `keel apply`,
  written to stay compatible with TurnKey rather than replace it.

## Next steps the agent can take without a decision

1. DONE 2026-09-24: docs/hub-inventory.md. Inventory of every call to `hub.turnkeylinux.org` across tklbam, confconsole,
   inithooks and tklbam-python-boto (brief 5.6), as a document, no code change.
2. DONE 2026-09-24: docs/python313-survey.md. Python 3.13 compatibility survey across fab, common, tklbam, turnkey-pylib:
   what breaks today, per repository, with the failing output.
3. Build unmodified 19.0 core on the build host from the forks rather than from
   upstream, and compare the artifact hashes, which is the M0 gate.

## Development standard: test coverage (2026-09-24)

Minimum 90 percent for anything that runs in an organization repository, 95
percent for project-authored code, measured and enforced as in
docs/decisions/0003-test-coverage-standard.md. keel measured 83 percent at
decision time and reached 100 percent (lines and branches, 146 tests) the same
day, with fail_under = 95 committed in pyproject.toml.

## Priorities set by the maintainer (2026-09-24)

Order of work: **Core, TKLDev, Webmin, then the appliances people actually
use**. Accessories (tklbam, HubDNS, security alerts, initfence beacon) come
after; see docs/decisions/0002-tklbam-last.md. HubDNS note: the client is open
(github.com/turnkeylinux/hubdns, one API URL), so a fork pointed at a Keel DNS
service is cheap when its turn comes; the cost is the DNS service itself.

Webmin status in 19.0, verified on the build host and in the code: still part
of core through `common/plans/turnkey/base` (webmin, webmin-authentic-theme,
webmin-software), listening on 12321 in appliances; only the TKLDev appliance
dropped it. Webmin is therefore in scope from the start, and its packaging
repository has to be in the fork set.

## bt-layer: first layer tooling, done 2026-09-24

Branch `feat/bt-layer` on the buildtasks fork (4 commits, pushed): `bt-layer`
builds one layer (core as a full rootfs, then stack and app layers on top of
their parent through fab's altstrap hook) and exports a deterministic tar.zst
with sha256 and a plain-text manifest (layer, parent and its sha256, product
and common commits, fab version, SOURCE_DATE_EPOCH, overlays and conf applied,
tarball sha256 and size). Logic lives in `bin/layer-lib` (19 functions), the
script is a thin caller, `tests/layer` exercises 40 of 40 code paths against
scratch directories, and kcov on the build host reports layer-lib 183/183
lines, bt-layer 99/100. First component built to the coverage standard.

Measured on the build host with SOURCE_DATE_EPOCH=1700000000:

| Layer | root.patched | pack | tar.zst | sha256 (12) |
| --- | --- | --- | --- | --- |
| core (full rootfs) | 309 s | 95 s | 326.4 MB | e08e8224aeea |
| lamp (delta on core) | 119 s | 30 s | 79.8 MB | 237188ea3339 |

The lamp export repeated three times from the same root.patched gave the
same hash every time. Two upstream facts found on the way and handled in the
script: fab-chroot needs TERM set (a detached run without it dies), and a
dangling altstrap symlink slips past `set -e` unless tested with -L.

## Coverage debt of the first fixes paid (2026-09-25)

Every touched file in the forks now has automated tests above 95 percent,
following decisions 0003 and 0004; per-branch numbers in
docs/coverage-baseline.md ("Update 2026-09-25"). All branches pushed to the
forks. Next structural step in progress: `keel verify` consuming the layer
manifests that bt-layer produces.

## keel verify: layers, done 2026-09-25

`keel verify --layers-dir DIR` reads the manifests bt-layer writes, checks
tarball sha256 and size, resolves the parent chain and compares each
parent_sha256, and reads the `.hash` file: it reports a signature as present
but never as verified while no project key exists (exit 8). Packages are still
not checked (exit 9 after the layers pass). Exit codes 6, 7, 8 added. 206
tests, 100 percent lines and branches. Run on the build host against the real
core and lamp layers (406 MB): 2 s, both reported, unsigned; a copy with one
byte removed from lamp.tar.zst is reported as a mismatch with the expected and
actual size and hash. Pushed (19 commits on main).

## Organization created, everything transferred (2026-09-26)

The organization exists as `keel-linux` (display name "Keel Linux", login
`Keel-Linux`, so URLs read github.com/keel-linux/<repo>; the spelling
`KeelLinux` from 0001 was not what GitHub kept). `tools-setup-org.sh` ran with
`ORG=keel-linux`: 20 forks transferred from the personal account, `core` and
`odoo` forked directly into the organization, the private `keel` library
repository transferred as well: 23 repositories. Local clones repointed at the
organization. Signing key procedure and hosting options: 0005.

## Organization guidelines applied (2026-09-26)

Decision 0006 and docs/org-plan.md. Done through the API: nine appliance
repositories renamed with the `keel-` prefix (GitHub redirects the old names),
issues enabled on all 24 repositories, org description, website and location
set. Blocked on token scopes: pushing workflow files (`workflow`) and
organization rulesets and runner registration (`admin:org`). Site being built
by an agent, guidelines page included.

## keel public and protected (2026-09-26)

The maintainer decided the library repository is public like the rest of the
organization. Branch protection on main now matches the other repositories
(check `tests / coverage`, one approval, linear history, admins included).
Open: the repository has no LICENSE file at its root; debian/copyright says
GPL, which was written as a placeholder and is a maintainer decision (brief
section 10: licensing of new components). To be settled before anyone is
invited to contribute.

## keel pull and keel assemble, done 2026-09-26

Pull request #1 on keel-linux/keel (branch feat/pull-assemble, merged with
the CI commit on main). `keel pull` fetches only missing layers from a
directory or an http(s) source, verifies sha256 and size, caches under
/var/cache/keel/layers; `keel assemble` extracts the chain applying overlay
whiteouts and opaque directories and packs a deterministic Proxmox template
with sha512. 270 tests, 100 percent. On the build host against the real
layers: 406 MB pulled in 2.4 s, second pull 0 bytes; 1.4 GB rootfs assembled
in 24 s; template 366 MB, identical sha512 on a second run. Exit codes 10,
11, 12. The distribution loop (bt-layer, verify, pull, assemble) is closed.

Domain: keellinux.org delegated to ns1.pop.uy and ns2.pop.uy on 2026-09-26.
A VM for releases.keellinux.org was requested from the cluster's agent
session (rudder), with the DNS records for apt and www to GitHub Pages.

## Merge policy settled (2026-09-26)

Decision 0007: GPL-3.0-or-later for new code (LICENSE in keel, PR #2);
zero required approvals while there is one maintainer; merge commits only,
squash and rebase merges disabled on all 25 repositories, linear history not
required, because the brief forbids rewriting history. keel PR #1 (pull and
assemble) merged with a merge commit.

## Fix branches merged into the forks (2026-09-26)

Twenty pull requests merged with merge commits across turnkey-chroot,
inithooks, tkldev, common, fab, tklbam-profiles and buildtasks, each through
the `tests / coverage` gate. Thresholds now committed on the default branches:
turnkey-chroot 95 (master at 100), inithooks shell 98 and python 95 (two
required checks), tkldev 99, common 100, fab 100, tklbam-profiles 100,
buildtasks 99, keel 95 (main at 100). tkldev-setup now maps an appliance to
`keel-<app>` when the remote is the organization (66 bats tests). One pipeline
fix on the way: Ubuntu 24.04 runners have no kcov package, so the shell
workflow builds kcov 43 from the pinned release. Details in
docs/merge-log-2026-09-26.md. Remaining for the guidelines: confconsole and
webmin baselines, the appliances (need the self-hosted runner), the tklbam
family (deferred by 0002).

## M0 gate run (2026-09-26): equivalence PASS, packing PASS for squashfs

Unmodified 19.0 core built from the organization (keel-core, common,
buildtasks, cdroots, tklbam-profiles cloned by our tkldev-setup from
github.com/keel-linux) against a reference build from upstream, same day,
same SOURCE_DATE_EPOCH: 412 packages identical; 33,684 files each side, 49
differ, all install-time state (ssh host keys, logs, apt cache, initrd,
webmin generated configs and ids, postfix pid), none traceable to a commit.
Gate 1 passes. Gate 2 passes for the squashfs; the ISO still differs by 178
bytes (random isohybrid id and ISO9660 timestamps) because the build host
runs upstream fab 1.1.1 from apt, and the fix lives on our fab fork: next
step is building and installing the project's fab package on the build host.
Report: docs/m0-gate-run-2026-09-26.md; allow-list frozen in m0-gate.md.
Found missing from the fork set and forked: turnkeylinux/bootstrap.

## Correction and gate 2 passed with the project's fab (2026-09-26)

The build host now runs fab 1.1.1+keel1, built from keel-linux/fab and
pinned. Gate 2 passes for squashfs and ISO on a real tree: two packings of
core give squashfs 47ed341d... (385,662,976 bytes) and ISO ab615ac6...
(442,499,072 bytes). Correction to the record: the squashfs hash 8c339c02
reported on 2026-09-22 as reproducible was an empty squashfs (the deck was
unmounted); the conclusion held, the evidence did not. Recorded in
../TKL/plan/06 and in docs/m0-gate-run-2026-09-26.md.

## keel inspect merged (2026-09-26, PR #3)

Writes a spec from a running machine or from a mounted rootfs (`--root`),
one probe per section, every field reported with its source or "not
inferred" with the reason; secrets are never read, only placeholders written.
Exit 13 when required fields are missing, spec still written. Spec gained
`users` and `locale` (accepted, validated, not applied yet, apply warns).
354 tests, 100 percent. Tried on the agent host (no interfaces file: network
not inferred, exit 13, partial spec written) and on the build host and on the
core root.patched offline. This is the core of keel-transition (brief 7).

## confconsole: static IPv6 writer merged (2026-09-26, PR #3)

First 19.1 change of the sovereign appliance work (../TKL/plan/04): ifutil
gained set_static6 and set_dhcp6 (inet6 stanza written or restored, inet
stanza untouched, IPv4 refused in IPv6 fields with a clear message, IPv4
nameservers filtered out, header rule kept), the networking menu gained a
Static IPv6 form, IPv6-only interfaces are no longer shown as "not
configured". 175 tests, ifutil.py at 100 percent, threshold raised to 100.
Checked by hand against a scratch interfaces file and with ifquery on the
build host. Left for a follow-up: IPv6 in services.txt and the usage block.

## keel diff merged (2026-09-26, PR #4), with one defect found in review

`keel diff` compares the declared spec with the observed machine through the
same probes as inspect, text or JSON, exit 14 on drift, 13 when only unknown
fields remain, no writes. 389 tests, 100 percent. Defect found while trying
the inspect to diff round trip here: diff refused the spec inspect had just
written, because secret placeholders point at files that do not exist yet and
validation checks them, although diff never compares secrets. Fix in
progress on branch fix/diff-secret-files (validate gains
check_secret_files; diff uses it; spec validate gains --no-secret-files).

## confconsole: IPv6 first on the usage screen (2026-09-26, PR #4)

`$ipaddr6` placeholder, brackets in URLs, IPv6 block before the IPv4 block in
conf/services.txt, adapter list shows IPv6 then IPv4. Rendered on the build
host: Web, web shell, Webmin and SSH lines all on the global IPv6 address.
212 tests, ifutil at 100. Appliance repositories keep their own services.txt
and adopt the placeholder as they are onboarded.

Day summary, 2026-09-26: organization complete (26 repositories), 10 of 11
infrastructure repositories gated and protected, M0 gates passed, keel at
404 tests with spec, verify, pull, assemble, inspect and diff, confconsole
with static IPv6 and IPv6-first display, site published, key generated
(subkey rotation pending), VM for releases requested.

## inithooks: IP6_* preseed keys merged (2026-09-26, PR #6)

IP6_CONFIG (dhcp default, static, manual), IP6_ADDRESS with prefix, IP6_GW,
IP6_DNS1, IP6_DNS2, validated in bash in lib/ipconfig.sh (IPv4 refused in
IPv6 fields). A preseed with only IP_* keys produces byte-identical output
to before, checked by hand and by a regression test. 105 bats tests, lib at
72/72 lines under kcov. Next: keel's spec render must emit these keys from
the network section so the spec drives static IPv6 end to end.

## Static IPv6 end to end (2026-09-26, keel PR #6)

`keel spec render` emits IP6_CONFIG, IP6_ADDRESS, IP6_GW, IP6_DNS1/2 from
the network section (IPv4 nameservers never reach IP6_*); the inithooks hook
writes the inet6 static stanza; inspect reads it back; diff reports no drift.
413 tests, 100 percent. The 19.1 minimum of ../TKL/plan/04 is implemented in
the three repositories. Critical path now: the project APT repository, so
appliance builds pull the project's inithooks and confconsole packages; it
needs the rotated signing subkey and the releases host. Tooling being
prepared in advance, unsigned and unpublished.

## APT repository tooling ready, unpublished (2026-09-26)

Local repository repos/apt (12 commits, not pushed): reprepro configuration
for `trixie` (signed with the project key) and `trixie-staging` (unsigned,
documented as never for appliances), build-package (builds on the build
host, refuses packages without a `+keel1` changelog entry), publish (refuses
without the signing subkey), verify-repo (IPv6, signature, sha256), pin-file
(`release o=Keel Linux`, priority 1001), 57 bats tests at 100 percent under
kcov, CNAME apt.keellinux.org for Pages. fab_1.1.1+keel1_all.deb built into
/srv/keel-apt/incoming on the build host; inithooks (2.3.6) and confconsole
(2.2.3) stopped for lack of a +keel1 changelog, being added by pull request.
The repository holds the public key, so it is pushed together with the
public key after the subkey rotation (decision 0005 note).

## Packaging: inithooks and confconsole versioned (2026-09-26)

inithooks PR #7 (2.3.6+keel1) and confconsole PR #5 (2.2.3+keel1) merged;
upstream generates its changelog at build time with verseek from git tags,
the fork now commits it. Built on the build host into /srv/keel-apt/incoming:
fab_1.1.1+keel1_all.deb, inithooks_2.3.6+keel1_all.deb (47 KB, with lib/,
00declarative and bin/declarative.py), confconsole_2.2.3+keel1_all.deb
(277 KB, with set_static6). keel is a native package (0.1.0) and the build
script's +keelN rule is being taught to tell native from rebuilt packages.

## Four project packages built (2026-09-26)

build-package now tells native packages (Source keel*, no upstream remote,
no debian/watch) from rebuilt ones (+keelN required); 67 bats tests, 100
percent. /srv/keel-apt/incoming on the build host: fab 1.1.1+keel1,
inithooks 2.3.6+keel1, confconsole 2.2.3+keel1, keel 0.1.0. Publication
waits for the rotated signing subkey; the tooling repository is pushed with
the public key at that moment.

## confconsole: Instance menu merged (2026-09-26, PR #6)

Four entries (View spec, Apply spec, Show drift, Export spec), 79 lines of
dialog code in total, all logic in keelcli.py (argv lists, exit code
messages, diff table renderer), measured at 100 percent with ifutil; 279
tests. Without the keel package installed every entry shows one clear
message. debian/control now Suggests keel. On the build host the drift path
rendered the table and the hostname change produced the drift line.

## Temporary IPv6 mirror on the build host (2026-09-26)

Layers, staging APT and the future pve index served from the build host on
port 8080 over IPv6, marked as unsigned internal staging, so keel pull over
HTTP and the forum evaluation do not wait for the releases VM. Documented in
docs/build-host.md with the reason it is temporary.

## keel pull over IPv6 HTTP, and a defect (2026-09-26)

From the agent host: `keel pull lamp` from the build host mirror fetched core
and lamp (406 MB) in 4.3 s into a content-addressed cache. `keel verify` on
that cache reported every layer invalid: pull names files `<layer>-<sha>`,
verify required `<layer>`; each command had been tested only against its own
output. Fix in progress on branch fix/verify-cache-names (one naming rule
shared by verify, pull and assemble; pull then verify becomes a test).

## bt-aplinfo and keel-core onboarding (2026-09-26)

buildtasks PR #3: `bt-aplinfo` writes the Proxmox appliance index from
assembled templates (records in the exact TurnKey field order, gzip -n,
optional detached signature with a clear warning when unsigned); 18 test
sections, kcov 100 on the new files; verified in pve-storage that Proxmox
accepts .tar.zst templates (VZTMPL_EXT_RE_1), so no .tar.gz switch.
keel-core PR #1 merged: LICENSE, README lineage, COVERAGE.md, appliance
workflow (skips until KEEL_LXC_RUNNER is true), boot-test skeleton with 26
bats tests at 100 percent, services.txt IPv6 first; recipe untouched;
master protected with the coverage check. One incident: two agents shared
the buildtasks checkout and one's commits landed on the other's branch;
sorted out by resetting the unpushed branch to its own commit and merging
the rebuilt PR; future agents work in worktrees only.

## Public services VM and names (2026-09-26)

VM provisioned by the cluster: 2804:710:d0:5::13, Debian 13, 6 vCPU, 7 GB,
99 GB, user popsolutions with sudo. Names follow the TurnKey pattern
(archive, mirror, releases, apex for the forum, www for the site), decision
0005 addendum; releases.keellinux.org created but not yet resolving from
here. Provisioning in progress: nginx per name, ACME over IPv6, layers
synced to mirror, site checkout on www, placeholder at the apex, GitHub
Actions runner with label keel-lxc. apt tooling renamed to archive.

## keel apply --system merged (2026-09-26, PR #8)

`spec apply --system` converges users (create, shell, groups,
authorized_keys 0600), timezone and locale, idempotently, with `--dry-run`
and `--root`; exit 15 needs root, 16 failed; passwords untouched by design.
Round trip inspect, apply, diff as a test. 490 tests, 100 percent. Dry run
on a scratch root here: 6 changes planned, nothing written. On the build
host the real run created the user and keys, set timezone and locale, and a
second run changed nothing.

Naming, final (2026-09-26): keellinux.org and www.keellinux.org serve the
institutional site; forum.keellinux.org (created in the zone) is the forum;
archive, mirror, releases as in the TurnKey pattern.

## Public services VM provisioned (2026-09-26)

keellinux.org (2804:710:d0:5::13): nginx per name, one Let's Encrypt
certificate for the six names (HTTP-01 over IPv6, valid to 2026-12-25,
daily renewal timer), nftables 22/80/443, unattended upgrades. apex and www
serve the site checkout (15 minute pull timer); forum serves a placeholder
with the reverse-proxy block ready; archive and releases hold only a README
until the key rotation; mirror serves core, lamp and nodejs-nginx layers
(530 MB, sha256 verified) with the staging header. Runner keel-lxc-1 online
with label keel-lxc, KEEL_LXC_RUNNER=true; it has no fab, so the appliance
workflow must fetch layers from mirror instead of building. Everything is
written by /usr/local/sbin/keel-provision on the VM. Found: the two public
IPv4 addresses do not forward 80/443 to the VM, so service is IPv6-only
until the cluster forwards them. Docs: docs/releases-host.md.

## The forum is up (2026-09-26): https://forum.keellinux.org

First real Keel appliance: NodeBB 4.10.3 on the nodejs-nginx stack on core,
three layers built by bt-layer (326 + 149 + 165 MB), assembled with keel
assemble, booted in LXC on the build host with a global IPv6 address, first
boot from an instance spec through keel spec apply and the inithooks runner,
reverse-proxied by the public VM with TLS. Findings recorded in
docs/forum-build-2026-09-26.md: the core layer still carries upstream
inithooks and confconsole (rebuild in progress), and keel diff exposed four
spec vocabulary issues to fix.

## The layer builder no longer publishes a broken build (2026-09-26)

buildtasks PR #4. The forum appliance exposed it: its layer was published
from a build that had failed, so the container came out with confconsole
unpacked but unconfigured, which is why the Instance menu was missing from
the image although it is on confconsole master. Two holes: `make ... | tee
|| true` discarded the status under pipefail, and the only remaining guard
was the stamp, which says nothing about the state of the packages inside.
Now the status is fatal and `layer_audit_packages` reads the rootfs's own
dpkg status and refuses any package that is not installed. Proved against
the real layers: the nodebb rootfs is refused naming confconsole, core is
clean. The coverage gate caught my first version at 97.96 against the 99
threshold, which is the gate doing its job; the audit paths are covered now.

Correction to the record: the Instance menu was written and merged
(confconsole PR #6, plugins.d/Instance and keelcli.py on master); the
appliance image predates that merge. A rebuilt nodebb layer will carry it.

## The migration path exists and is proved (2026-09-26)

New repository keel-linux/keel-transition, public, gated (`tests / coverage`
required, 98 bats tests, kcov 100 percent of 332 lines). Two packages:
`keel-archive-keyring` 0.1.0, which ships the project public key and whose
build fails if the fingerprint is not AD0964BE..., and `keel-transition`
0.1.0, which surveys, applies and rolls back, and never touches packages.

Proved on `tkl-core-bench`, a container built from the stock TurnKey Core
19.0 ISO (hash and signature verified), now stopped on the build host:

1. Survey wrote the instance spec and a report, 14 fields inferred, 5 not,
   `/etc/apt` unchanged.
2. `--apply` refused because archive.keellinux.org has no signed Release
   today, exit 4, nothing changed. With `--force-unsigned` against the
   staging tree, apt showed the project packages at priority 1001 over
   TurnKey's 999.
3. `--rollback` restored `/etc/apt` byte for byte, and is idempotent.

Finding that changes the design: a stock 19.0 has no `turnkey.list`. Its
TurnKey entries sit in deb822 files shared with Debian, so disabling them by
renaming would disable Debian too. The tool names those files in its report
and relies on the pin instead, and still renames a `turnkey.list` where one
exists.

## The first boot reads the description again (2026-09-26)

inithooks PR #8. The forum build left a defect that made every declarative
promise unreliable: the description is written to `/etc/keel/instance.yaml`,
which the tooling writes and the operator edits, and `00declarative` read
`/etc/inithooks.yaml` and nothing else. The hook found no file, exited 0 as
designed, and the instance came up from an empty conf. Hostname, network and
secrets were ignored on a boot that reported success.

Both paths carry the same document and the same schema version, so the fix
is a search, not a rename: `INITHOOKS_DECL` names a file outright when set,
otherwise the first of `/etc/keel/instance.yaml` and `/etc/inithooks.yaml`
that exists is read, and when both exist the first wins and the other is
named in a warning. `declarative.py --which` prints the path that would be
read, which is how the hook asks, so the order lives in one place and is
tested there. `default/inithooks` no longer sets `INITHOOKS_DECL`, which
would have won over the search on every machine. A reader that cannot run
leaves the boot alone with a warning instead of aborting it.

`DECL_PATHS` is built from `DECL_DEFAULT`, so the upstream form of the patch
keeps the second path alone and everything else applies unmodified.

Measured: 169 tests, declarative library 100 percent, CLI 99, total 99 with
branches against a gate of 95. Packaged as 2.3.6+keel2. Still to prove on a
machine: a rebuilt core layer with +keel2 and an appliance whose description
sits at the instance path, with `keel diff` reporting the declared values.

## The handbook is in git (2026-09-26)

This tree was the largest single point of failure in the project: the brief,
the status log, the decisions and the whole operational record existed in one
directory on one workstation, with no history and no copy. It is now
`Keel-Linux/handbook`, private, because it records host addresses, the sudo
policy of the CI runner and the recovery procedures. README.md says which
documents are promoted to the public site.
