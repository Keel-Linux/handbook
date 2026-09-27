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

## The spec vocabulary says what it means (2026-09-26)

The first real appliance boot left four drift findings (5 same, 4 drift, 1
unknown, 6 not declared, 3 not compared, exit 14 on `forum2`). All four were
right about the file and wrong about the machine: the appliance was doing
what the description asked and the vocabulary could not say so. A drift
report that cries wolf teaches the operator to ignore it, so they are
defects in the contract, not cosmetics. Fixed in keel PRs 13, 14, 15 and 16,
with the three part justification for each in docs/decisions/0009.

What the vocabulary now says:

- **`network.interfaces.<name>.ipv6.method`** keeps both `auto` and `dhcp`,
  and they mean different things: an address formed from a router
  advertisement, an address from a DHCPv6 lease. ifupdown writes `inet6
  dhcp` for both, so the file settles nothing and inspect asks the machine: a
  lease file under `/var/lib/dhcpcd` or `/var/lib/dhcp` means `dhcp`, a
  global address marked `mngtmpaddr` means `auto`, neither is reported as not
  inferred with everything that was checked. `ip -6 addr show` runs on the
  live root only; lease files are read under `--root` too.
- **`tls.acme`** may declare `challenge` and `domains` while `enabled` is
  false, and diff does not compare them: it compares the switch and nothing
  else it governs. That is what lets an operator prepare a certificate
  configuration and turn it on later as a one word change. The switch itself
  is still compared, so ACME running behind the spec's back is drift.
  `enabled` is now validated as a boolean, because `"false"` as a string is
  truthy. The rule is a table, not a special case.
- **`security.updates` is now `security.updates_at_first_boot`**, values
  unchanged. It controls whether `95secupdates` installs the pending security
  updates during the first boot, and nothing else; the appliance keeps its
  updates current through cron-apt whichever value was set. diff does not
  compare it, for the same reason `app` and `preseed` are not compared: the
  machine keeps no record of the value. inspect still writes one, from the
  conf while it is there and otherwise from the appliance's update posture,
  saying which. The old name still loads with a warning naming the new one,
  so specs already on disk keep working (`keel.spec.compat`, one table).
- **`instance.fqdn`** is written, not only read: `keel spec apply --system`
  puts the entry in `/etc/hosts` that no upstream hook writes, at the
  declared static IPv6 address when there is one and `127.0.1.1` otherwise,
  replacing the `127.0.1.1 <short name>` line 09hostname leaves rather than
  appending after it. Whether there is anything to write is decided by the
  same reader inspect uses, so what apply writes is what diff calls same.
  Without `--system`, apply warns that the entry was not written.

Proved on `forum2`, the container that produced the findings, with the
library of the four pull requests installed: 6 same, 0 drift, 1 unknown, 5
not declared, 6 not compared, exit 13 straight after the install, then 7
same, 0 drift, 0 unknown, exit 0 after `keel spec apply --system` wrote
`/etc/hosts` and `hostname -f` answered `forum2.keellinux.org`. The second
apply changed nothing. `eth1`, which has no address and no lease, is now
reported as not inferred instead of as `dhcp`, which is the "no evidence"
case working as designed. Coverage 100 percent of lines and branches against
the committed gate of 95.

Two hand-offs, both in the inithooks repository and both in decision 0009:
the first boot chain still does not call `keel spec apply --system`, so the
`/etc/hosts` entry is not written at first boot yet, and the hook that calls
it must run after `09hostname`; and `libinithooks/declarative.py` is a second
implementation of this vocabulary that knows none of these four changes.

## Two more holes in the first boot, closed (2026-09-26)

inithooks PR #9 and PR #10, both found by pulling on the thread the forum
build left.

**The runner never gave the hooks the path of the conf file.** `run` exported
`INITHOOKS_CONF` inside the test that sources it, so the variable reached a
hook only when the file already existed. `29preseed`, the hook whose whole
job is to create that file on a headless machine, ran `cat>$INITHOOKS_CONF`
with an empty target, died with an ambiguous redirect and was logged as
failed on every headless first boot. That is the `29preseed` exit 1 the forum
log showed, and it is an upstream defect, recorded as issue H in the TurnKey
plan with a fix branch. `tests/test-run.bats` reproduces it with the real
overlay hook: three of its seven tests fail without the one line.

**The two readers of the instance description disagreed about the
vocabulary.** The tooling renamed `security.updates` to
`security.updates_at_first_boot` today; the hook library rejects an unknown
key under `security`, so a description written for the current vocabulary
would have been valid to the half that writes it and invalid to the half that
boots from it, leaving the instance with nothing declared. The rename is now
in both, the old name still loads with one warning naming its replacement,
and `tests/test_vocabulary.py` freezes the vocabulary and, with `KEEL_SRC`
pointing at the tooling, runs both readers over one document and compares
their rename tables. The duplication stays on purpose, since inithooks must
carry no dependency on us; the test is what keeps the copies honest.

Packaged as 2.3.6+keel3 and +keel4. Coverage: shell 112 bats, lowest file
98.44, total 99.55 against a gate of 98; Python 185 tests plus 3 skipped,
library 100, CLI 99, total 99 against a gate of 95.

## The TurnKey notes are in git too (2026-09-26)

`marcos-mendez/tkl-notes`, private: the brief, the roadmap, the eight plan
files, the defect reports with their fix branches and the draft issues. Same
reason as the handbook. Each defect in plan/02 was reproduced on a real 19.0,
which is work that no amount of reading the code gives back. Working clones
and build output stay untracked, and two headings in the brief were reworded
to name the work rather than the tool that read it.

## Every active repository now has a gate (2026-09-26)

An audit of the organization found twenty-six repositories, thirteen gated and
thirteen not. Eleven of the thirteen are deferred by decision: the eight
appliance forks wait for their layers, and the tklbam family is last by
decision 0002. The other two were the ones that mattered.

**The site had no check at all**, and nothing builds it: what is in the
repository is what the browser gets, so a link that resolved to nothing or an
asset that had been removed went straight to the public page. It is the most
visible repository we have. `tools/sitecheck.py` now does what a build step
would have done: internal links resolve, fragments name ids that exist
including on another page, referenced assets exist and every asset is
referenced (counting the social card of the og:image and twitter:image tags),
external links are https, and each page has a language, a title and one h1.
Two real findings came out of the first run: the dark and one colour marks
were served and referenced by nothing, so the guidelines page now has a
section for the mark offering all four variants with the rules for using them.
37 tests, 99 percent of the checker, `python / coverage` required on main.

**The workflow repository had no check and no protection**, while holding the
four reusable workflows every other repository calls at `@main`: a mistake
there breaks every gate at once and no caller can catch it. actionlint now
runs on it, pinned by version and sha256 the way test-shell pins kcov, with
shellcheck over every run block and no tolerance for informational findings.
Four real findings, fixed in the same change, one of them in the linting
workflow itself, which is the gate catching the commit that introduced it.
`actionlint` required on main.

The last two repositories have no coverage number, and the honest equivalent
of the coverage gate is a check of what they actually are. The guideline is
that every repository has a required check, not that every repository reports
a percentage.

## Today's fixes are packaged, and the archive is in git (2026-09-26)

The staging archive carried `+keel1` of inithooks and confconsole, so nothing
merged today could reach a machine. Built on the build host and published to
`trixie-staging`, which is unsigned and which no appliance may use until the
key rotation:

| Package | Version | What it carries |
| --- | --- | --- |
| inithooks | 2.3.6+keel4 | the instance description path, the conf path export, the vocabulary parity |
| confconsole | 2.2.3+keel2 | the Instance menu, the mark above the usage screen |
| keel-transition | 0.1.0 | the migration path, built earlier and waiting in incoming |
| keel-archive-keyring | 0.1.0 | the project public key |

confconsole needed a package entry of its own: the Instance menu and the mark
were merged with no changelog bump, so the newest installable confconsole was
`+keel1` and neither reached the forum image. That is the whole reason the menu
looked unwritten. `keel` moves from Suggests to Recommends there, since the
menu reports its absence rather than failing.

**The publication failed on its last step and taught us something.** reprepro
included the packages, exported the indices, and then the commit in the
published tree failed: root on the build host has no git identity. The archive
was correct and the record of it was not, which is the worst place to stop.
Fixed in the archive repository: the publication now passes its own name and
address, overridable through the environment, with two tests, one of which
points git at an empty global and system config. The harness had always
configured an identity, the way a workstation has one, which is why no test
caught it.

**The archive repository had no remote at all.** It holds the reprepro
configuration, the publication, release, mirror and self check tooling, and it
doubles as the Pages checkout for archive.keellinux.org, so the state of what
the archive served lives in it. It is now `Keel-Linux/apt`, private, with the
build host's published state and the workstation's tooling merged into one
history, and gated at 99. It becomes public with the key rotation, as decision
0005 says.

## The gate that measures whether a change can be installed (2026-09-26)

The confconsole lesson of today deserved a check, not just a fix. The Instance
menu and the console mark were merged, the coverage gate was green, and the
newest installable confconsole stayed at the previous version, so neither
change reached an appliance and the image was read as evidence that the menu
had never been written. A coverage gate measures the code. Nothing measured
whether the code could be installed.

`require-changelog.yml` in the organization's workflow repository refuses a
pull request that changes a file the package ships without a changelog entry
whose version is greater. Tests, documentation and CI ship nothing and are
exempt. The rule is `bin/require-changelog`, a script with thirteen bats cases
at 100 percent of its lines, rather than shell inside a workflow: the entry
rewritten at the same version, the version that goes backwards, the changelog
the pull request itself adds, a caller with its own path and exempt
expression, a repository with no changelog, and the three ways the arguments
can be wrong.

It is required as `package / changelog` on the four repositories that produce
packages: confconsole, inithooks, keel and keel-transition. The workflow
repository gained a `tests / coverage` gate of its own for the tools it lends
the others, beside `actionlint`.

Where protection is not possible: a private repository cannot require a check
on this plan, so `apt` and `handbook` run their gates on every pull request
without being able to enforce them. `apt` becomes public with the key
rotation.

## The first boot writes the name it declares (2026-09-26)

`keel spec apply --system` converged `instance.fqdn`, `users` and `locale`,
and no boot ever called it, so a booted appliance still drifted from its own
description on the fully qualified name. That was the open hand-off of
decision 0009. It is closed: keel PRs 17, 18, 19, 20, 22 and 23, keel 0.2.1.

**The shape: a flag, `keel spec apply --system-only`.** The two phases run at
two moments of a boot, the conf before every hook and the system phase after
`09hostname`, so each needs its own way to be asked for. `--system-only`
runs the second and nothing else: the conf is neither read nor written and no
secret is resolved. That last part is the point of the flag, not a side
effect. Phase 1 resolves `secrets`, and a `generate: true` secret gets a
fresh value each time it is resolved, so a boot that ran phase 1 at hook 00
and again at hook 10 would hand the appliance a root password generated after
`30rootpass` had already set and shown the first one, and nobody would know
it. A flag rather than a subcommand because it selects which phases one run
of `apply` carries out, with the same spec, `--root` and `--dry-run`: a
subcommand would give one code path two names and confconsole two call sites
for one converge. It is mutually exclusive with `--system`, so asking for
both is a usage error and not a precedence rule to remember. On a machine
whose conf phase never ran it converges the same fields and exits the same
way, because its inputs are the spec and the machine, and it says on its
first line that the conf was not read or written: the run cannot tell a conf
that was never written from one `98finalize` blanked after a good boot, so it
claims neither.

**The hook: `firstboot.d/10keel-system`, shipped by the keel package.** The
package that owns the `keel` command owns the hook that runs it, so inithooks
keeps no dependency on keel and an image without keel has no hook there
(`debian/keel.install`). Position 10 is the only one that works: earlier and
the `sed` in `09hostname` edits or loses the entry, later and the certificate
at 15 and the fence at 29 and 30 are made on a name the appliance does not
carry. It is a no-op with exit 0 under `_TURNKEY_INIT`, with no description
(`INITHOOKS_DECL`, then `/etc/keel/instance.yaml`, then
`/etc/inithooks.yaml`, the order `00declarative` searches), and when the
description declares nothing the phase converges. It logs every line through
the inithooks log as the other hooks do, and exits 0 whatever `keel`
returned, with the failure and its code in the log: an appliance that cannot
converge one field must still finish booting, and the drift is then visible
in `keel diff`.

**What `keel diff` reports for a converged field: the ordinary verdicts.**
`instance.fqdn` stays compared and is never added to the not compared table.
Exit 0 after a boot is earned by writing the field, not by excusing it from
the comparison, and the comparison is the only signal that the converge
happened: `not compared` would read the same on an appliance that applied its
description, on an image too old to carry the hook, and on a machine somebody
edited afterwards. Where there is no trace the field is `unknown` and the
reason now names the command that writes it.

**Two defects found while proving it, both about `/etc/hosts`.** They are the
decision 0009 class again, a report saying all is well while the machine says
otherwise.

1. With a static IPv6 address declared, the phase wrote the entry at that
   address and left the `127.0.1.1 <short name>` line. A resolver answers
   from the first line that carries the name, so `hostname -f` answered the
   short name. A line that names the host and nothing else, without a fully
   qualified name, is now replaced wherever it stands. Debian's convention
   agrees: `127.0.1.1` is for a machine whose address is not permanent.
2. The reader walked past that short line and reported the name from a later
   line, so `inspect` reported a name the machine did not answer, `diff`
   called it `same`, and `apply` called the file settled and converged
   nothing. `fqdn_in_hosts` now stops at the first line that names the host,
   the way a resolver does, and the settled test asks whether the file the
   write would produce is the file that is there, because an entry can be
   present and shadowed.

A line that names the host beside another name (`127.0.0.1 localhost blog`)
is still kept, since rewriting a line that belongs to another name is not
this phase's business, and the plan now says on every run that such a line
answers first and has to be edited by hand.

**Measured:** 549 tests, 100 percent of lines and branches against the
committed gate of 95, plus 14 bats tests for the hook. The hook is shell, so
`tests/hook.bats` replaces `keel` with a script on `PATH` that records its
arguments; `tests/test_hook_bats.py` runs that suite from pytest so the
repository keeps one required check and a broken hook fails the same gate as
a broken module (`bats` and `shellcheck` are installed by the workflow, and
the test fails rather than skips in CI).

**Proved on `hooktest`**, a container built for this and destroyed
afterwards, from the published `core` layer
(`https://mirror.keellinux.org/layers`, 326,418,793 bytes, `keel pull` plus
`keel assemble`, 18 s), adapted the way `forum2` was, with
`inithooks 2.3.6+keel4` and `keel 0.2.0` built from the merged master of each
repository and installed as packages. The description declared
`hooktest.keellinux.org` with `managed_by: host` and `ipv6.method: auto`.
Nothing was applied by hand: `lxc-start`, then `/usr/lib/inithooks/run`.

| | before the boot | after |
| --- | --- | --- |
| `/etc/hostname` | `core` | `hooktest` |
| `/etc/hosts` | `127.0.1.1 core` | `127.0.1.1 hooktest.keellinux.org hooktest` |
| `hostname -f` | fails | `hooktest.keellinux.org` |
| `keel diff` | 5 same, 1 drift, 1 unknown, exit 14 | 7 same, 0 drift, 0 unknown, 5 not declared, 3 not compared, exit 0 |

The hook's own lines, from `/var/log/inithooks.log`:

```
INFO: [00declarative] /etc/keel/instance.yaml applied to /etc/inithooks.conf
INFO: [10keel-system] apply --system-only: /etc/inithooks.conf not read or written
INFO: [10keel-system] instance.fqdn: write /etc/hosts with '127.0.1.1 hooktest.keellinux.org hooktest' (mode 0644): done
INFO: [10keel-system] apply --system-only: 1 change(s), 0 failed
```

The runner ran the chain twice on this container, which proved idempotence on
a real machine for free: the second pass reported `unchanged (/etc/hosts maps
hooktest to hooktest.keellinux.org)` and `0 change(s), 0 failed`, after
`98finalize` had blanked the conf, which is the case the `--system-only`
notice is worded for.

Both defects were proved on the same container. With the shadowed file in
place `hostname -f` answered `hooktest`, `keel diff` reported the field
`unknown` and named the remedy, and one `apply --system-only` turned the file
into `127.0.0.1 localhost` plus `2001:db8:1::10 hooktest.keellinux.org
hooktest`, after which `hostname -f` answered the fully qualified name and a
second run changed nothing.

**Notes for the next container build:** `rm -rf` of a rootfs that has booted
fails on `/var/spool/postfix/dev/{random,urandom}`, which postfix's chroot
makes immutable; `chattr -i` first. `fab-chroot` needs `TERM` in the
environment and dies with a `KeyError` without it, which matters over `ssh`
without a tty. A conffile the container patch edited (`/etc/default/inithooks`,
`REDIRECT_OUTPUT=true`) makes `dpkg -i` of the inithooks package stop at the
prompt; `--force-confold` keeps the container's version, which is the right
one, and the new search order needs no `INITHOOKS_DECL` line.

**Left open:** the appliance layers still carry keel 0.1.0 and upstream
inithooks, so the chain reaches an appliance only when `core` is rebuilt with
`keel 0.2.1` and `inithooks 2.3.6+keel4`; and
`inithooks/libinithooks/declarative.py` is still a second implementation of
the spec vocabulary (decision 0009).

## A recipe that existed only on the build host (2026-09-26)

Rebuilding the forum chain with tonight's packages failed on its second layer:

    ERROR [layer-lib]: SOURCE_DATE_EPOCH not set and no git history in
    /turnkey/fab-keel/products/nodejs-nginx
    FATAL [bt-layer]: no usable SOURCE_DATE_EPOCH

`core` rebuilt because its recipe is a checkout of keel-core. The stack layer
between core and the forum was a plain directory on the build host: three
files, no history, no copy anywhere, and therefore no deterministic date to
build with. The reproducible build work assumes the recipe's own history
supplies that date, so a recipe that is not a repository cannot be built
reproducibly and cannot be rebuilt by anyone else.

It is now `Keel-Linux/keel-nodejs-nginx`, public, with its appliance gate
wired from the start, and the build host's directory is a checkout of it.

The nodebb recipe on the host was worse than missing: it was stale. It
predated the conffile fix that PR 1 of keel-nodebb merged, which is the fix
for the failed build that produced the broken layer in the first place. The
host now tracks the repository, and both directories are checkouts rather than
copies.

Mistake worth recording: to let git read a directory owned by another user I
ran `chown -R` on it, and that walked into the mounted deck of a previous
build before I stopped it. The published layer was not touched, because an
overlay sends writes to its upper directory and never to the lower one, and
the deck itself is discarded by the next build. The right remedy was
`git config --global --add safe.directory`, which touches no file, and that is
what is in place.

## The build host was running yesterday's build tooling (2026-09-26)

`/turnkey/buildtasks-keel`, the checkout `keel-release` calls, sits two merges
behind: it has neither the make status capture nor `layer_audit_packages` of
buildtasks PR 4, nor the signing identity fix of PR 5. So the rebuild running
tonight is driven by exactly the bt-layer that published a broken layer this
afternoon, and it carries one local commit that the fork already has under
another hash.

It is being left alone while a build is in progress, because a running bash
script is read as it executes. Two consequences, both handled:

- Nothing from this rebuild is published until the layers are audited by hand
  against what `layer_audit_packages` would have refused: a dpkg status with a
  package that is not installed, and the build time `systemctl` and `service`
  shims that a finished layer must not carry. The script is `/root/audit-
  layers.sh` on the host.
- The checkout is reset to `origin/19.x` as soon as the build ends, so the
  next release runs the audited builder. The local commit is a duplicate of
  b3d6232 on the branch, so nothing is lost.

The lesson is the same one as the recipes: what runs on the build host has to
be a checkout that someone keeps current, or it quietly becomes a fork of its
own.

## A build that installs yesterday's packages now fails (2026-09-27)

The forum chain rebuilt late on the 26th carried inithooks 2.3.6+keel1,
confconsole 2.2.3+keel1 and keel 0.1.0, hours after 2.3.6+keel4, 2.2.3+keel2
and 0.2.1 had been published to the staging archive. Every step of that build
succeeded, which is the part worth fixing.

**Why it passed.** `bt-layer` runs `make clean` and ignores its status. That
clean failed:

    deck -D build/root.patched
    rmdir: failed to remove '.../build/root.patched': Device or resource busy
    make: *** [product.mk:270: clean] Error 1

`root.patched` was mounted twice, so the `rmdir` inside `deck -D` failed and
make stopped before `rm -rf $(STAMPS_DIR)`. The stamps of `bootstrap`,
`root.spec` and `root.build` survived from 16:57, only `root.patched` was
rebuilt, and the archive the chroot read was the copy `bootstrap/post` had
made that morning. The recipe's own guard was `grep -c '+keel1$'`, a literal
that the stale packages satisfied exactly. Two independent defects that happen
to cancel out into a green build.

**What the recipe asserts now** (keel-nodebb pull request 7, merge ffb23e2):

- `bin/keel-archive-check` compares the package index copied into a build tree
  with the index of the live archive and stops the build when they differ. The
  Makefile calls it in `bootstrap/post`, where the copy is made, and again in
  `root.patched/pre`, which runs on every build and therefore catches a
  bootstrap that this build did not make. A stamped bootstrap can no longer
  smuggle an old archive into a rebuild; it fails loudly instead.
- `conf.d/zz-project-packages`, the new last conf script, replaces the
  literal. For each of inithooks, confconsole and keel it checks that the
  archive offers exactly one version, that apt's candidate is that version,
  that the version is served by `file:/srv/keel-apt/repo` rather than an
  upstream source, and that the installed package is that candidate with dpkg
  status `install ok installed`. It then removes the build time package
  source, which `conf.d/main` used to do. No version is written down anywhere,
  so a rebuild made after a publication either carries the new versions or
  fails.

Both scripts run for real in the tests against scratch trees, with `dpkg`,
`dpkg-query` and `apt-cache` as PATH stubs reading fixtures: 21 new tests,
both files at 100 percent under kcov, and both added to the measured set.
`tests / coverage` green at threshold 95.

keel-core was checked for the same pattern and does not have it: its plan
lists no project package, its `conf.d/main` is the upstream no-op and nothing
in it copies an archive. Its layer carries the upstream inithooks 2.3.6 and
confconsole 2.2.3, and the forum layer upgrades them. So there was nothing to
change there and no second pull request.

**The build host.** `/turnkey/buildtasks-keel` is reset to `origin/19.x`, so
`layer_audit_packages` and the make status capture of PR 4 and the signing
identity fix of PR 5 are now what builds run. The one local commit it carried
was **not** a duplicate of anything on the branch, and discarding it cost a
rebuild; that is the next section. The three product directories are checkouts
and were updated before the rebuild: `core` to
keel-core master 53d9fb5 (it had been sitting on the upstream 24c82ee, so the
core layer gained the keel banner overlay), `nodejs-nginx` to 648d6b6 and
`nodebb` to ffb23e2. `build/` stays out of git through `.git/info/exclude`,
and `.gitignore` in core.

The three stale build directories were removed before rebuilding, which is
the state `make clean` could not reach: every mount under
`/turnkey/fab-keel/products/*/build` was unmounted lazily first, then the
trees deleted. No `chown -R` anywhere near them.

**The rebuild**, `bin/keel-release --force --rebuild nodebb`, 00:34 to 00:59
UTC. The two checks fired and passed in the nodebb build log, and so did the
new conf script:

    [archive-check bootstrap] .../build/bootstrap/srv/keel-apt/repo/... is the archive at /srv/keel-apt/repo/...
    [archive-check root.patched] .../build/root.patched/srv/keel-apt/repo/... is the archive at /srv/keel-apt/repo/...
    inithooks 2.3.6+keel4, the candidate of the project archive
    confconsole 2.2.3+keel2, the candidate of the project archive
    keel 0.2.1, the candidate of the project archive

`/root/audit-layers.sh /mnt/builds/layers core nodejs-nginx nodebb` exits 0:
every package installed in all three, no `/usr/local/bin/systemctl` or
`service` shim left behind, and the nodebb rootfs carries inithooks
2.3.6+keel4, confconsole 2.2.3+keel2 and keel 0.2.1. core and nodejs-nginx
carry the upstream inithooks 2.3.6 and confconsole 2.2.3 and no keel, as their
recipes intend.

| Layer | sha256 | Bytes |
| --- | --- | --- |
| core | `b457aaac8b8be6f1d7c9584a27d60d211c60dc5c78c101b384f43c3e3778f025` | 326,426,823 |
| nodejs-nginx | `f588cb159c9732ffd0b50568ca0beccd9ae1f23dfe6fb805b343fa90fdf47785` | 148,868,412 |
| nodebb | `310147d9e32d0f446fc913433b36402f301988fc3a29809d53dbd6792aa9fd6d` | 166,185,619 |

**Published** with `bin/keel-publish-mirror --unsigned-staging 2026-09-27`
from a workstation, both tunnels open, exit 0. The release staged under the
27th because the build crossed midnight UTC. `keel verify` over the public
names reports 3 layers checked, 3 ok (exit 9, packages not implemented); the
archive still has no `InRelease`, which is what an unsigned archive returns.
`https://archive.keellinux.org/staging-unsigned` now offers inithooks
2.3.6+keel4, confconsole 2.2.3+keel2 and keel 0.2.1, where it had been serving
the `+keel1` set. `keel pull nodebb --source https://mirror.keellinux.org/layers`
follows the chain and fetches all three layers, 641,480,854 bytes.

One practical note for the next publication: the ControlMaster socket
`keel-publish-mirror` opens lives under `$TMPDIR`, and a long `TMPDIR` fails
with `unix_listener: path ... too long for Unix domain socket` before any
transfer starts. `TMPDIR=/run/user/$(id -u)` is short enough.

**Still open.** `make clean` failing silently is the defect that let this
happen at all, and it is in buildtasks, not in the recipe: `bt-layer` should
treat a failed clean as fatal, or remove the build directory itself, rather
than building on top of whatever the failure left. The recipe now refuses the
result, which is the safety net, not the fix.

## The commit that was only on the build host (2026-09-27)

`/turnkey/buildtasks-keel` carried one commit that was not on `origin/19.x`:
`bt-layer: run zz-ssl-ciphers when a child overlay carries the mark`. It looked
like a duplicate of `b3d6232`, and it was: of a **local branch**
`fix/layer-ssl-ciphers-overlay` in the workstation fork that had never been
pushed and had no pull request. `git branch -r --contains` would have said so
in one line. Resetting the build host threw the only running copy away.

What it fixes: `layer_child_conf` added `turnkey.d/zz-ssl-ciphers` to a child
layer only when one of the conf scripts the child runs mentioned
`ZZ_SSL_CIPHERS`, which is how the apache conf reads it. nginx keeps the mark
in an overlay, `overlays/nginx/etc/nginx/snippets/ssl.conf`, and the nodebb
layer adds no conf script over its parent, so the rebuilt layer shipped

    ssl_ciphers 'ZZ_SSL_CIPHERS';

and the first boot died where it runs `nginx -t`:

    [emerg] SSL_CTX_set_cipher_list("ZZ_SSL_CIPHERS") failed
    (SSL: error:0A0000B9:SSL routines::no cipher match)

The running `forum` container, assembled from the layer built while the local
commit was in place, has the real cipher list. That is the comparison that
proved the regression rather than a new defect.

It is now buildtasks pull request 7, merged as 1dfc12d: the scan moves into
`layer_needs_ssl_ciphers`, which checks the child's conf scripts as before and
then the overlays it applies, with two cases in `tests/layer` and the gate
green at 99 (bin/layer-lib 207 of 208, bt-layer 101 of 102). The build host
runs that merge now.

The lesson is narrow and worth keeping: a commit that exists only on a machine
is not a duplicate of a commit that exists only on a laptop. Before resetting
a checkout, ask git which *remote* refs contain the commit, not which local
ones.

## What the appliance gate found once the layer booted (2026-09-27)

With the republished chain the gate got much further than it ever had: it
pulls, verifies, assembles, boots, and the first boot runs to completion
(`98finalize`, `Inithooks run completed`). The build shims are gone, so the
`10regen-sshkeys` hang of the afternoon is fixed. It still fails, on two
defects that the hang had been hiding, both reproduced by hand on the build
host against `/mnt/builds/layers`:

1. `redis-server.service` will not start in the test container:
   `status=226/NAMESPACE`. The unit's namespace hardening needs an apparmor
   profile the boot test's LXC config does not ask for. The running `forum`
   container has `lxc.apparmor.profile = generated` and
   `lxc.apparmor.allow_nesting = 1`; the config `bt_lxc_config` writes has
   neither. Adding both to the container made redis come up. So this is the
   test harness in `tests/lib/boot-test-lib.sh`, not the layer.
2. The cipher list above, which is fixed in buildtasks now.

`15regen-sslcert` and `95secupdates` also report a non-zero exit in the
container and are not yet explained; neither stops the first boot from
finishing.

The verdict after the fix and the republication is in the release log of the
run that follows this note.

## The archive signing subkey is live (2026-09-27)

The maintainer rotated the signing subkey while this work was in flight:
`694DE5E8` is revoked with the offline primary and the signing subkey is now
`03041024F4B2C0C2F42DDDEA04906EAB77513310`, Ed25519, expiring 2028-09-26.
`AD0964BE3F09DED469A3B6B2148E951314703180` is unchanged and its secret stays
offline (`sec#`). `/srv/keel-apt/apt` on the build host carries the rotated
`keys/keel-archive-keyring.asc`, and `dists/trixie` is published and signed.

Three consequences for a release from now on:

- `keel-release` signs, so `release_sign ... || die 9` is a real failure mode.
  The subkey is passphrase protected and the agent caches the passphrase for
  ten minutes, so a release whose signing step lands more than ten minutes
  after the maintainer typed it dies at exit 9 with `Inappropriate ioctl for
  device`. That is the cache, not the key. The recovery is cheap: the layers
  are already built and match their manifests, so `bin/keel-release --force
  nodebb` without `--rebuild` reuses them and reaches the signing step in a
  few minutes. Nothing about this may be worked around, and no passphrase goes
  on a command line.
- `keel verify` stops exiting 9 for a missing signature once layers carry
  `.hash`; `release_keel_verify` already accepts 8 and 9, so the release path
  needs no change.
- With the release signed and `dists/trixie` signed, `keel-publish-mirror`
  takes the signed path and installs the APT tree at the root of
  `/srv/archive` instead of `/srv/archive/staging-unsigned`. That is what the
  tooling documents for the day a key exists, and `--unsigned-staging` becomes
  a no-op rather than a downgrade.

## The first two database layers, and the password that reached nothing (2026-09-27)

`Keel-Linux/keel-mariadb` and `Keel-Linux/keel-postgresql`, both public,
both a small recipe built as a layer on `core` (decision 0006: the
repository carries the `keel-` prefix, the layer name does not, so the
layers are `mariadb` and `postgresql`). They are the database and nothing
else. LAMP and LAPP are built on them next.

**What they leave out, and why it is written down.** Upstream's `mysql`
appliance bundles Adminer, lighttpd and php-fpm; upstream's `postgresql`
appliance adds postgis and, in its `conf.d/main`, `listen_addresses = '*'`
with `host all all 0.0.0.0/0 md5`. None of that is here. Adminer needs a
web server and which web server differs by context, lighttpd upstream and
Apache in LAMP and LAPP, so putting it in the database layer forces a
choice the layers above would undo and make again; it arrives with the web
stack, which is where upstream puts it for those products. Remote access
is the change of behaviour worth naming: on an IPv6 first, publicly
routable appliance (brief section 5.3) a database that accepts password
authentication from anywhere is not a default to inherit quietly, so both
layers listen on the loopback of both families and the PostgreSQL recipe
asserts at build time that neither of upstream's two changes is present.
An appliance with real remote clients opens the port, says who may connect
and terminates TLS. If the maintainer later wants literal parity with the
upstream `mysql` appliance, that is a different artefact built on this
layer, not this layer.

Batteries included stays: Webmin comes from `core` and answers on 12321,
and each layer adds the module for its database, `webmin-mysql` and
`webmin-postgresql`, both `2.660.turnkey0` in the TurnKey trixie archive
that `core` reads. The boot tests check the module and the panel, not only
the database.

### The defect these two exposed

`secrets.db_password` of an instance description renders to `DB_PASS` and
to nothing else. Measured on a rendered description with the current
library:

```
export HOSTNAME=mariadb
export FQDN=mariadb.example.org
export ROOT_PASS=[masked]
export DB_PASS=[masked]
export APP_DB_USER=admin
```

`MYSQL_PASS` and `PGSQL_PASS`, which `mk/turnkey/mysql.mk` and
`mk/turnkey/pgsql.mk` add to `CONF_VARS`, never appear there: they are
build time variables fab passes to the conf scripts inside the chroot,
which is where `conf/pgsql` reads `PGSQL_PASS`. So the two halves of the
defect are not the same defect.

**MariaDB: nothing read `DB_PASS`.** The only hook that calls
`bin/mysqlconf.py` is `firstboot.d/35adminer-mysqlpass`, which ships in the
**Adminer** overlay of `common` together with the account it configures,
and these layers leave Adminer out. A declared password reached nothing on
an appliance whose whole purpose is the database, and `keel diff` would
have said nothing, because the `secrets` section is never compared on
either side.

**PostgreSQL: the vocabulary was right and the layer shipped a password.**
`overlays/pgsql` `firstboot.d/35pgsqlpass` already reads `DB_PASS`. But
`conf/pgsql` opens with `set ${PGSQL_PASS:=postgres}`, so a build that
names no `PGSQL_PASS` gives the superuser of the database the password
`postgres`. For an appliance that is a bad default; for a published layer
it is worse, because a layer is fetched by name and reused, so every
appliance built on it would carry the same known superuser password and
one whose first boot hook failed would keep it. And nothing said whether
the declared password had arrived: `35pgsqlpass` reports on setting it,
not on whether the database will accept it.

### Where it is closed, and why there

In the appliance layers, on the `DB_PASS` side. Not in the renderer, and
the three parts brief section 10 asks for:

1. *Why the renderer does not work.* `MYSQL_PASS` and `PGSQL_PASS` are
   build time `CONF_VARS`. Emitting them from the renderer would write two
   more copies of a secret into a root readable file that nothing consumes.
2. *Whether it could be made to work.* Mechanically yes, but the renderer
   would have to know which database the image carries in order to choose
   between the two names. The description does not declare that and
   `inspect` only guesses it from `/etc/mysql` or `/etc/postgresql`
   (`DATABASE_DIRS`). One secret, two possible variables, decided by the
   image: appliance knowledge in the one component that has to stay
   appliance agnostic, landing on every appliance including those with no
   database.
3. *Why the layer is better.* The vocabulary is already right; both first
   boot hooks `common` ships read `DB_PASS`. What was missing is a hook on
   the MariaDB side, and only because the one that exists ships with
   Adminer. The repair is one hook in the layer that has none, the shared
   vocabulary is untouched, and an appliance with no database is unchanged:
   it ships no such hook and `DB_PASS` stays out of its conf unless the
   description declares it.

What landed: `keel-mariadb` `firstboot.d/35mysqlpass`, at the position
upstream uses, reads `DB_PASS`, hands it to the shared `bin/mysqlconf.py`
once per host of the administrative account (`localhost`, `::1`,
`127.0.0.1`, because MariaDB matches a socket connection against
`localhost` and a TCP connection against the literal address), then
connects as a client and runs a query. The account is `admin`, created by
`conf.d/main` with a hash no input produces. `keel-postgresql`
`conf.d/main` removes the build time password (`ALTER ROLE postgres
PASSWORD NULL`, then a check that `rolpassword` is null in `pg_authid`)
and `firstboot.d/36pgsqlverify` runs after `common`'s `35pgsqlpass` and
proves the password over TCP on `[::1]`. Neither layer chooses a build
time password and neither generates one: a value chosen at build time
would be identical on every appliance built from the layer, and a random
one would make the layer irreproducible (brief section 5.4).

### Measured

| Repository | Tests | Coverage | Gate |
| --- | --- | --- | --- |
| keel-mariadb | 61 bats | 99.51 (204/205): `lib/mariadb.sh` 100 (43/43), `35mysqlpass` 95.45 (21/22), `boot-test-lib.sh` 100 (140/140) | 95 |
| keel-postgresql | 58 bats | 100 (197/197): `lib/postgresql.sh` 100 (41/41), `36pgsqlverify` 100 (15/15), `boot-test-lib.sh` 100 (141/141) | 100 |
| apt | 124 bats, 27 in release.bats | 99.71 of executed lines | 99 |

The one uncovered line in `35mysqlpass` is the process substitution that
feeds the dialog loop, which kcov attributes to no line; the loop itself is
covered. It is the same line `keel-nodebb` records for `40nodebb`.

### The boot tests

Each repository has `tests/boot-test.sh` in the shape of `keel-nodebb`'s,
and each proves the declarative path rather than a listening port. A
database appliance is not proved by a port: the database listens whatever
password it ended up with, and `keel diff` never compares secrets. So the
verdict is a client connection. A random password is written to
`etc/keel/secrets/db_password` (0600); `tests/instance.yaml`, which
declares `secrets.db_password` from that file, is installed at both paths
the first boot reads; `keel spec apply` renders it; the container boots and
the first boot runs through the inithooks runner alone; then
`mysql --user=admin --host=::1 --protocol=TCP --execute='SELECT 1'` with
`MYSQL_PWD`, or `psql --username=postgres --host=::1 --no-password
--command='SELECT 1'` with `PGPASSWORD` (`--no-password` so a password that
did not arrive is an error and not a hung test), inside the container. Then
the Webmin module and Webmin over IPv6 on 12321, then `keel diff`.

### State, and what is waiting

| Repository | Pull request | Checks |
| --- | --- | --- |
| keel-mariadb | #1 the layer and the password fix | three green |
| keel-mariadb | #2 the boot test and the coverage gate, stacked on #1 | three green |
| keel-postgresql | #1 the layer, the password it shipped and the one nobody checked | three green |
| keel-postgresql | #2 the boot test and the coverage gate, stacked on #1 | three green |
| apt | #4 `mariadb core` and `postgresql core` in conf/appliances | running |

`main` of both new repositories is protected, requiring `tests / coverage`
and `package / changelog`, with merge commits only and squash and rebase
turned off. `appliance / build-and-boot` is in place and skips with a
notice while the layer is not on the mirror; it becomes required the day
the first layer reaches it. Each repository was bootstrapped with the gate
and nothing else, at threshold 0, which is `test-shell.yml`'s bootstrap
case, so protection was on before the first line of recipe.

**Nothing was built.** The build host was running the other agent's
`keel-release --force --rebuild nodebb` (`bt-layer --parent core
nodejs-nginx` at 01:47 UTC), and two builds must never run at once, so it
was left alone. When it is free, and after the pull requests above are
merged and `/srv/keel-apt/apt` and the two product checkouts on the host
are current:

    cd /srv/keel-apt/apt && bin/keel-release --force --rebuild mariadb
    cd /srv/keel-apt/apt && bin/keel-release --force --rebuild postgresql
    /root/audit-layers.sh

A layer is published only once the audit passes and its project packages
are the current ones, which each recipe's `conf.d/main` already enforces as
a floor at build time: inithooks 2.3.6+keel4, confconsole 2.2.3+keel2,
keel 0.2.1. The `conf.d` pattern that installs them is keel-nodebb's, not a
second version of it; the archive freshness check itself stays in
keel-nodebb's `conf.d/zz-project-packages`, and these two carry the minimum
that publishing them requires.

## Where this stops, and the one step that needs the maintainer (2026-09-27)

The chain is rebuilt with the cipher fix and audited, and it is staged on the
build host, but it is **not published**, because the release cannot sign:

    INFO [bt-aplinfo]: signing /srv/keel-release/2026-09-27/pve/aplinfo.dat
      with 03041024F4B2C0C2F42DDDEA04906EAB77513310
    gpg: signing failed: Inappropriate ioctl for device
    FATAL [bt-aplinfo]: cannot sign .../pve/aplinfo.dat
    keel-release: bt-aplinfo failed

That is the ten minute passphrase cache, not the key. The build takes about
twenty five minutes and the signing step is the last thing it does, so a run
started right after the passphrase is typed will always arrive too late. It
was not worked around, and no passphrase went near a command line.

What is on the build host right now:

| | |
| --- | --- |
| `/mnt/builds/layers` | core `7acf2c53`, nodejs-nginx `f57917cb`, nodebb `6d2d622f`, each with its manifest and sha256 |
| audit | `/root/audit-layers.sh` exits 0; nodebb carries inithooks 2.3.6+keel4, confconsole 2.2.3+keel2, keel 0.2.1 |
| cipher list | real, no `ZZ_SSL_CIPHERS` left in `etc/nginx/snippets/ssl.conf` |
| `/srv/keel-release/2026-09-27` | layers, the Proxmox template and an unsigned `aplinfo.dat`; **no MANIFEST**, so `keel-publish-mirror` refuses with exit 3 |
| the mirror | still the first rebuild of tonight: right package versions, broken cipher list |

To finish, with the passphrase typed immediately before:

    cd /srv/keel-apt/apt && bin/keel-release --force nodebb

without `--rebuild`. The three layers match their manifests, so
`release_layer_current` skips every build and the run reaches the signing step
in a few minutes rather than twenty five. Then, from a workstation:

    cd repos/apt && TMPDIR=/run/user/$(id -u) bin/keel-publish-mirror 2026-09-27

`--unsigned-staging` is no longer needed and would be a no-op: with the
release signed and `dists/trixie` signed, the APT tree goes to the root of
`/srv/archive`. `TMPDIR` matters: the ControlMaster socket path has to be
short or ssh fails before any transfer with `unix_listener: path ... too long
for Unix domain socket`.

After that, re-run `appliance / build-and-boot` on keel-nodebb `main`. Both
defects it found are fixed: the cipher list in buildtasks 1dfc12d, and the
container apparmor profile in keel-nodebb pull request 8 (merge 6693fbd),
which gives the boot test container `lxc.apparmor.profile = generated` and
`lxc.apparmor.allow_nesting = 1` so `redis-server.service` can start.

## The first boot hook that never returned (2026-09-27)

With the signed republication in place the gate pulls, verifies, assembles
and boots, and then stops: `[40nodebb] running` is the last line of the
container's inithooks log. Reproduced on the build host against the published
chain, the node process running `./nodebb setup` is asleep in a write to the
terminal:

    [<0>] wait_woken+0x52/0x60
    [<0>] n_tty_write+0x406/0x500
    [<0>] file_tty_write.isra.0+0x175/0x2c0

with `/proc/<pid>/fd/1 -> /dev/lxc/tty1`.

The layer ships the plain appliance `inithooks.service`, which runs the hooks
with `StandardOutput=tty` on `/dev/tty1`. A container image does not run that
unit: buildtasks' headless patch carries
`ConditionPathExists=!/var/lib/turnkey-info/inithooks.service/lxc` and
`patches/container/conf` sets `REDIRECT_OUTPUT=true`. Nothing reads tty1 in a
container nobody has attached to, so the terminal buffer fills and the write
blocks forever. `./nodebb setup` prints well past that buffer.

The boot test wrote only the marker file, so its container was a container to
`keel inspect` and an appliance on a console to systemd. `bt_mark_container`
now does all three things a container build does: the marker,
`REDIRECT_OUTPUT=true`, and a drop-in giving the unit `StandardOutput=journal`
(keel-nodebb pull request 9). Six tests; `boot-test-lib.sh` stays at 100
percent, 137 of 137.

Measured with it in place, on the chain the mirror serves: the first boot runs
to `98finalize`, `[40nodebb] successfully completed`, port 80 answers 307 to
https and port 443 answers 200 with `<title>Home | NodeBB</title>` over IPv6.
`15regen-sslcert` and `95secupdates`, which had also reported failures while
the console was blocked, complete as well. Nothing in the layer changes, so no
rebuild and no new release were needed for this.

The order the three defects came in is the point worth keeping: the build
shims hid the cipher list, the cipher list hid the apparmor profile, and the
apparmor profile hid the console. Each fix bought exactly one more step, and
none of them was visible until the one before it was gone.

## A defect the container journal exposed: 00declarative dies (2026-09-27)

Every boot of the test container logs this before the hooks get going:

    File "/usr/lib/inithooks/bin/declarative.py", line 121, in main
        log(f"reading {path}, ignoring {other}", "warning")
    libinithooks.inithooks_log.InitLogError: invalid log level 'warning'
    warning: declarative.py --which failed, no description read

`InitLog.write` accepts `err|warn|info|debug`; line 121 passes `warning`. The
`log()` helper catches `OSError` only, so `InitLogError` propagates and kills
the script. It fires exactly when `resolve_path()` has something to ignore,
which is when both `/etc/keel/instance.yaml` and `/etc/inithooks.yaml` exist.
The boot test installs the spec at both paths, so the gate triggers it on
every run.

It does not stop the boot test, because the test renders `/etc/inithooks.conf`
with `keel spec apply` before booting, so nothing depends on `00declarative`
having read anything. On a machine that ships both files and expects the hook
to render the conf, the render silently does not happen.

The fix is one word in `bin/declarative.py`, and `log()` should catch
`InitLogError` as well so a bad level degrades to stderr instead of killing
the hook. It is not fixed here: it lives in the inithooks fork and shipping it
means a new package, an archive publication and a signed release, which needs
the passphrase arranged. Worth doing in the same pass as the next inithooks
change.

## The appliance gate is green (2026-09-27)

Run 36290439227 on keel-nodebb `main`, against the chain published that
morning:

    keel verify exited 9: every layer matches
    boot-test: assembling nodebb from https://mirror.keellinux.org/layers
    boot-test: container address fc42:5009:ba4b:5ab0:351f:6b8e:bd1c:9e24
    boot-test: first boot finished
    boot-test: http://[fc42:...:9e24]/ answered 307 https://[fc42:...:9e24]/
    boot-test: the forum answered 200, title 'Home | NodeBB'
    keel diff: no drift
    boot-test: nodebb boot test passed

Measured on the runner: assemble 33 s, a global IPv6 address 5 s after the
start, first boot finished 50 s later, the whole job under two minutes once
the layers were pulled. `tests / coverage` green in the same run. The chain on
the mirror is core `7acf2c53`, nodejs-nginx `f57917cb`, nodebb `6d2d622f`, and
`archive.keellinux.org/dists/trixie/InRelease` answers 200 with the rotated
key, listing inithooks 2.3.6+keel4, confconsole 2.2.3+keel2 and keel 0.2.1.

So an appliance now travels the whole chain for the first time: packages
published to a signed archive, a layer built from a recipe that refuses stale
packages, published to the mirror with a signed manifest, pulled, verified,
assembled, booted, set up headless from an instance description, serving over
IPv6, and matching the description afterwards. That is the M0 loop closed end
to end.

Four defects had to be cleared, and the order is the lesson, because each one
hid the next:

| Defect | What it broke | Fixed by |
| --- | --- | --- |
| build time `systemctl` and `service` wrappers left in the layer | first boot stopped at `10regen-sshkeys` | keel-nodebb 1, and the rebuild |
| no apparmor profile on the test container | `redis-server.service` exit `226/NAMESPACE` | keel-nodebb 8 |
| `ssl_ciphers 'ZZ_SSL_CIPHERS'` unsubstituted | nginx refused to start | buildtasks 7, and the rebuild |
| first boot writing to a `/dev/tty1` nobody reads | `./nodebb setup` blocked in `n_tty_write` | keel-nodebb 9 |

`appliance / build-and-boot` is a candidate for the protection rule of `main`
now that it passes; that is a maintainer decision and has not been made here.

## The layer builder knows what a unit is (2026-09-27)

Decision 0010 was accepted with a prerequisite: nothing moves out of the
shared tree until `bt-layer` records units in the layer manifest. The
prerequisite holds. Three pull requests, all merged with their gates green:

| | | |
| --- | --- | --- |
| keel-linux/fab 4 | merge `2fc6120` | the units move to their place in the order, and a build can select which of them to apply |
| keel-linux/fab 5 | merge `16730a5` | a unit may carry a removelist and name the variables its conf script reads |
| keel-linux/buildtasks 8 | merge `dd0dcb5` | the two manifest fields and the subtraction |
| keel-linux/keel 24 | merge `4579aba` | the fields documented, and the rule for any other, held by tests |

### The field, and the rule

Two fields, next to the two pairs that were already there:

    units         mariadb@1.0.0
    build_units   none

`units` is every component the finished layer carries as a fab unit, as
`name@version` sorted by name, or `none`. `build_units` is what this build
applied: `default` without a parent, else the difference, or `none`.

`units` is cumulative, the parent's record merged with this build's own. The
`common_*` fields are cumulative too, but only by accident, because a child
recipe includes its parent's makefile fragments. Here `bt-layer` keeps it so
on purpose, and it is the part of the design that took the longest to settle:
a child that carries no database content of its own still sits on the
database, and its own child has to be able to subtract it. A record that only
listed what this recipe declares would lose the component one layer down,
which is the same bug one level deeper.

A version comes from the first of three sources that answers: the unit's
`version` file, the pin an assembly step writes; the unit's own git HEAD, but
only when the directory is the top of that work tree, so the commit of an
enclosing product repository is never passed off as the component's;
otherwise `sha256-` and the first 16 digits of a digest of the directory
content, so a scratch or assembled unit still has an identity.

The subtraction is by name. Same name and same version means the parent
applied it, so it is skipped. Same name at a different version **fails the
build**: a conf script runs once, there is no way to move a component from
one version to another inside a child layer, and the parent is the thing to
rebuild. `bt-layer` also refuses a unit directory that carries none of
`plan`, `overlay/`, `conf`, `removelist`, and one whose `conf` is not
executable, which `fab` skips without a word.

A parent manifest written before these fields existed reads as `none`, so
every layer already on the host stays usable as a parent. `keel` needed no
change: it validates by its required keys and writes back what it read, which
is now a documented property with tests behind it rather than an accident.

### The other two findings, and the order

A unit may now carry a `removelist`, and a `conf-vars` file naming the
build-time variables its conf script reads, which is the unit form of
`CONF_VARS += MYSQL_PASS` in `mk/turnkey/mysql.mk`. Both slots are used by
the mariadb unit built below.

The position is fixed and stated. In `root.patched`:

    common overlays, common conf, common patches,
    unit overlays, unit conf scripts, unit removelists,
    common removelists,
    product overlay, conf.d, product patches, product removelist

The units move from last to here, which fixes both inversions the experiment
found: a common removelist can now remove a file a unit brought in, and a
unit's conf script runs before the common removelists. Every unit overlay is
applied before any unit conf script, the two phases the common inputs go
through, so a recipe composing several units does not depend on which one
`fab` reaches first. Each command in the three loops gained `|| exit`: a
phase is one shell line, so a unit failing in the middle of it was swallowed
and the image shipped half applied.

One caveat stands. A recipe whose own overlay must win over a unit's relies
on `ROOT_OVERLAY`, which is applied after the units; `COMMON_OVERLAYS +=
$(CURDIR)/overlay` alone is now applied before them. For mariadb the two
overlays share no path, five files against six, so it does not bite, but it
is a per-component check and not a guarantee.

### The measurement

Five builds on the build host, all at `SOURCE_DATE_EPOCH=1700000000`, against
`common` f3de96a, product `ac3c3cd`, parent layer `core` `7acf2c53`, with the
merged `share/product.mk` supplied through `FAB_SHARE_PATH`. Two recipes: the
`mariadb` layer, and `dbapp`, a child that carries no database content of its
own beyond one file of its own overlay. The two versions of each recipe
differ only in the two lines that pull the component from the shared tree.

| Pair | Packages | Symlinks | Directories | Regular files differing |
| --- | --- | --- | --- | --- |
| parent, two control builds | 438 identical | 3,380 identical | 5,291 identical | 173 of 35,315 |
| parent, control against unit | 438 identical | 3,380 identical | 5,291 identical | 173 of 35,315 |
| child, two control builds | 438 identical | 3,380 identical | 5,313 identical | **0** of 35,338 |
| child, control against unit | 438 identical | 3,380 identical | 5,313 identical | 173 of 35,338 |

No path exists on one side and not the other, in any pair.

Attributable to the unit form, in the parent: **zero**. The 173 paths of the
control against the unit are the same 173 paths by which the control differs
from itself.

Attributable to the unit form, in the child: **zero**, and this one is
sharper. Two builds of the monolithic child differ in no file at all, so the
child layer has no noise of its own to hide behind. Its 173 differing files
are exactly the parent's 173, path for path: the child inherits the install
time state of the database from whichever parent it was built on, and adds
nothing. The 173 are the ones decision 0010 named and explained, 167 of them
under `/var/lib/mysql/**`, the rest `/etc/webmin/mysql/config`,
`/var/webmin/module.infos.cache`, `/var/log/alternatives.log`,
`/var/log/webmin/webmin.log`, `/var/cache/ldconfig/aux-cache` and
`/root/.wget-hsts`.

### The thing that used to break

The unit child did not re-run the component's conf script, and its rootfs has
the database:

| | |
| --- | --- |
| its manifest | `units mariadb@1.0.0`, `build_units none` |
| its build log | the only mention of `unit.d` is the plan resolution; no overlay, no conf, no removelist |
| `mysqltuner` downloaded | 0 times, against 6 in the parent build that ran the script |
| `mariadb-server` | 1:11.8.6-0+deb13u1, installed |
| `/var/lib/mysql` | 205 files, 143M, 31 system tables |
| `/etc/init.d/mysql` | the symlink to `/etc/init.d/mariadb` that a second `ln -s` under `bash -e` would have failed on |
| the component's overlay and the recipe's | both present, byte identical to the monolithic child |

The monolithic child subtracts `mysql` from `common_conf` and
`common_overlays`; the unit child subtracts `mariadb@1.0.0` from `units`.
Both end at `build_conf turnkey.d/hostname`. The two mechanisms agree.

### Where this leaves the host

`/mnt/builds/layers` holds core `7acf2c53`, nodejs-nginx, nodebb and mariadb
`63680d3b`, the last rebuilt from the git product with the installed fab once
the measurement was done, so no layer there came from a scratch tree. The
audit passes on all four. The test recipes stay in `/turnkey/unit-test` and
`/turnkey/mono-test` with their decks released, and the measurements in
`/turnkey/unit-test/m` for anyone who wants to repeat the arithmetic.

### What is still missing before a component moves

The gate is open, not walked through. Still to come: the assembly and pinning
step that materialises `unit.d/` from a recipe's declared components, the
first component repository, and the package pinning of decision 0012, which
is what would take the parent's 173 file noise down and make the parent
comparison as sharp as the child's already is.

## The two database layers are built and audited (2026-09-27)

`keel-mariadb` and `keel-postgresql` were merged tonight and nothing had been
built from either. Both layers exist now, both pass the audit, and neither is
published: publication signs, and the signing subkey's passphrase cache had
expired by the time the layers were ready.

### The product directories

`bt-layer` reads the product's git HEAD twice: for `product_commit`, and
through `layer_epoch` for the `SOURCE_DATE_EPOCH` that stamps every tarball
entry. A recipe without git history is refused outright, which is the lesson
that cost a release earlier tonight. So both products are checkouts, the way
`nodebb` and `nodejs-nginx` are:

| Directory | At | Epoch |
| --- | --- | --- |
| `/turnkey/fab-keel/products/mariadb` | `f8eebf6`, merge of pull request 3 | 1790476250 |
| `/turnkey/fab-keel/products/postgresql` | `af5ea60`, merge of pull request 2 | 1790474064 |

`mariadb` was already there at `ac3c3cd`, left by the unit experiment, and was
fast forwarded; nothing local had to be discarded, the tree was clean and the
only untracked path was `build/`. `postgresql` was cloned. `build/` is in
`.git/info/exclude` in both, so the deck a build leaves behind is not an
untracked file the next reader has to weigh.

### Why core was not rebuilt

`keel-release --rebuild` rebuilds every layer of the chain, and the chain of
each of these recipes is `core` and then the layer. Rebuilding core was not
wanted, for three reasons. The stale `mariadb` tarball was invalidated instead
(its manifest moved to `/root/stale-mariadb-ac3c3cd.manifest`, which is what
`release_layer_current` reads), and both builds ran as `bin/keel-release
--force <layer>`, each reporting `core: tarball matches its manifest, not
rebuilt`.

- Nothing yet shows that core rebuilds to the same digest. `SOURCE_DATE_EPOCH`
  is the product's commit date and core's has not moved, but the
  reproducibility check only seeded its first reference this morning, and at a
  different epoch. A core with a new digest orphans the published
  `nodejs-nginx` and `nodebb`, whose manifests name the old one as parent.
- `core.rootfs` is the lower directory of the mounted decks of
  `nodejs-nginx`, `nodebb` and `mariadb`. `bt-layer` rewrites it with
  `rsync --delete`, and changing the lower layer of a mounted overlay is
  undefined.
- These two layers have to sit on the core the mirror serves, `7acf2c53`, and
  both manifests record exactly that as `parent_sha256`.

Both builds used `FAB_PATH=/turnkey/fab`, which is what the host's environment
exports and therefore what `keel-release` resolved, so `common_commit` is
`b60dd23`, the same common every published layer was built against.
`/turnkey/fab-keel/common` is a different tree and was being committed to
while these builds ran, so it would have been the wrong choice twice over.
docs/build-host.md line 29 still tells a reader to export
`FAB_PATH=/turnkey/fab-keel`, which no layer on the mirror was built with;
that line and the host disagree and one of them should move.

### The two layers

| | mariadb | postgresql |
| --- | --- | --- |
| size | 65,443,671 | 104,170,947 |
| sha256 | `0adca4341e2f9cef784ed8060f6ef243af6984fb37ef7b29f33838e463e89b0a` | `e67f883bc80f4ac4d007f98580dee1e5dd15976efae92a8da73f37dc62745735` |
| parent | core `7acf2c53` | core `7acf2c53` |
| product commit | `f8eebf6` | `af5ea60` |
| root.patched | 62 s | 76 s |
| packed | 22 s | 31 s |
| database | mariadb-server 1:11.8.6-0+deb13u1 | postgresql-17 17.11-0+deb13u1 |
| webmin module | webmin-mysql 2.660.turnkey0 | webmin-postgresql 2.660.turnkey0 |

`keel verify` read each staged chain and answered `2 checked, 2 ok, 0
unverified, 0 mismatch, 0 invalid`.

### The audit

`/root/audit-layers.sh /mnt/builds/layers mariadb postgresql` exits 0. Every
package in each rootfs is `install ok installed`, neither carries a build time
`systemctl` or `service` shim under `/usr/local/bin`, and both carry
inithooks 2.3.6+keel4, confconsole 2.2.3+keel2 and keel 0.2.1, the floors
`conf.d/main` asserts at build time. Nothing was refused, so nothing had to be
explained away.

Checked beside the audit, because these are the two properties the recipes
exist for: `mariadb` ships `firstboot.d/35mysqlpass` and the bind file that
holds the server to `::1` and `127.0.0.1`; `postgresql` ships
`firstboot.d/36pgsqlverify` next to common's `35pgsqlpass` and keeps Debian's
commented `listen_addresses = 'localhost'`, so neither of upstream's two
remote access changes is present. In both rootfs trees the build time package
source is gone: no `/srv/keel-apt`, no `keel-staging.list`, and
`keel.sources` disabled.

### What is left, and what the maintainer walks into

Both runs ended at the same line, which is the step that needs a person:

    gpg: signing failed: Inappropriate ioctl for device
    FATAL [bt-aplinfo]: cannot sign .../pve/aplinfo.dat

That is the expired passphrase cache and not a broken key, so no workaround
was attempted and `keel-release` exited 8 without writing a MANIFEST. Two
consequences for whoever runs the publication:

- `--force` wipes the dated staging directory, so the signed metadata of this
  morning's nodebb release was copied first to
  `/srv/keel-release/archive/2026-09-27-nodebb/`: `MANIFEST`, `MANIFEST.asc`,
  the template's `.sha512` and `.asc`, and `pve/`. Those signatures cannot be
  remade without the passphrase. `/srv/keel-release/2026-09-27/` now holds
  only the postgresql chain and no MANIFEST.
- `core.manifest` in `/mnt/builds/layers` gained `packages`,
  `packages_sha256` and `pool` at 04:58, and a `core.packages` file is staged
  beside it. That is the pinning work in flight, not these builds, but it
  means the core manifest on the host no longer matches the one the mirror
  serves, and the publication has to decide which it publishes.

The layers themselves are ready: `<name>.manifest`, `<name>.tar.zst` and
`<name>.tar.zst.sha256` are in `/mnt/builds/layers` for both, on the core the
mirror already serves. Publishing them turns `appliance / build-and-boot` in
each repository from a skip into a real run, which is the first time either
boot test proves a declared `secrets.db_password` reaching a database.

## A release can be finished in seconds instead of staged again (2026-09-27)

The signing subkey is passphrase protected and the gpg agent holds the
passphrase for ten minutes. A release of five appliances takes longer than
that, so `keel-release --force all` reached its first signature after the
passphrase had gone and died there, at `bt-aplinfo`, with `gpg: signing
failed: Inappropriate ioctl for device`. `--force` empties the dated
directory before it starts, so five staged templates, their `.sha512`
signatures and the signed `MANIFEST` went down with it. Three attended
moments had been spent that way.

Merged as [apt#6](https://github.com/Keel-Linux/apt/pull/6).

### What a rerun is now allowed to skip

Each step asks the artifact on disk whether it has anything left to do,
never a stamp saying the step ran:

| step | redone only when |
| --- | --- |
| build a layer | the tarball does not match its manifest (as before) |
| stage a layer | the staged copy is not that same layer: manifest, tarball digest, published `.sha256`, package list |
| capture packages | the manifest does not already record this pool and the list beside it |
| assemble a template | it is missing, or its `.sha512` is not its digest |
| write the index | it is not the index of exactly these templates at this URL |
| sign | what is there does not verify |

`--resume` works in a dated directory that already exists and never empties
it. `--force` is kept as the old name and now means the same thing, so the
runbooks need no change and nothing wipes a directory holding signatures
again. Copying a previous release aside to `/srv/keel-release/archive/` by
hand, as was needed this morning, is no longer needed.

### Signing is the last phase, and only the last phase

`bt-aplinfo` is no longer given `BT_GPGKEY`. The index is signed by the same
phase that signs the template digests and `MANIFEST`, so no step before the
signing can fail for want of a passphrase, which is precisely what happened.
`--sign-only DATE` runs that phase alone over what is staged and takes no
build lock: it builds nothing, and waiting behind a build would spend the
moment it exists to use. Run twice it signs nothing a second time, and
`MANIFEST` is rewritten only when it would say something else, so the
signature keeps standing over the bytes it was made on.

Two ways a signature could be lost are closed. `release_sign` writes
`<file>.asc.new` and moves it into place only after gpg succeeds, because
gpg empties its `--output` before it asks the agent for the passphrase: a
failed signing used to truncate a good signature. And a run with no key in
the keyring now leaves an earlier run's signatures where they are, and says
so, instead of replacing them with an `UNSIGNED` note it cannot undo.

### The wait for the build lock

`keel-release` used to exit 4 the moment the build lock was held, and the
daily self check held it for eight minutes right after the maintainer had
typed the passphrase. It now waits `KEEL_BUILD_WAIT` seconds, 600 by
default, and says on the first look what it is waiting for and for how long.
600 is the life of the passphrase in the agent: a release is attended, so
waiting a few minutes for a build that is going spends that moment better
than refusing at once, and waiting longer than the passphrase lives would
gain nothing. `--wait SECONDS` sets another ceiling and `--no-wait` refuses
immediately. The daily self check still skips rather than waits: nobody is
waiting for it, it runs again tomorrow, and a check queued behind a release
would hold the lock the release wants next.

### The gate

`tests/coverage.sh` at threshold 99: **99.55 percent** over `bin/` and
`lib/`, `lib/release.sh` 99.10, every measured file at or above 99. 54 cases
in `tests/release.bats`. Two `layout.bats` cases failed in CI on teardown
rather than on an assertion (`rm: cannot remove '.../pages/.git': Directory
not empty`, a git housekeeping run outliving the test); the scratch checkout
now turns off `gc.auto` and `maintenance.auto`, and teardown no longer fails
a test that passed.

### The staged release 2026-09-27 needs no passphrase moment

While this was being written, a `keel-release --force all` started on the
build host at 06:06, wiped the staged tree and rebuilt all five templates
from the layers. That run completed at 06:17 and signed everything, so
`/srv/keel-release/2026-09-27/` now holds five templates, five signed
`.sha512`, a signed `pve/aplinfo.dat` and a signed `MANIFEST`, all verifying
against subkey `03041024F4B2C0C2F42DDDEA04906EAB77513310`. It was the last
release that had to be staged twice.

The new tooling was carried to `/srv/keel-apt/apt` by git bundle and merged
there (the checkout also carries the publishing commits, so it is merged and
never reset), then run against that release as the proof:

    bin/keel-release --date 2026-09-27 --sign-only all

Exit 0 in 35 seconds over 3.2 GB. It read every digest and verified every
signature, wrote nothing, asked for no passphrase, and reported each
artifact as already signed and `MANIFEST: unchanged`. `MANIFEST`,
`MANIFEST.asc` and all six other signatures are byte for byte what they
were, and no `.asc.new` or `.UNSIGNED` was left behind.

What is left is the publication: `bin/keel-publish-mirror 2026-09-27` moves
the release to the public services VM. Nothing about it needs the signing
subkey any more.
