# Public services host (keellinux.org)

Date: 2026-09-26. The VM requested in docs/infra/vm-request.md, provisioned
for the hosting split of decision 0005. Everything below is idempotent: the
script `/usr/local/sbin/keel-provision` on the host writes every file listed
here and can be rerun after any manual change to bring the host back to the
described state.

## 1. The machine

- Debian 13.7, 6 vCPU, 7.8 GB RAM, 99 GB disk, hostname `keellinux`.
- IPv6 `2804:710:d0:5::13` (public, all services). IPv4 `10.88.5.25` behind
  NAT; the public addresses `179.191.88.34` and `179.191.88.35` are what the
  A records point at and what the VM egresses from, but ports 80 and 443 on
  them do not reach the VM (checked from outside on 2026-09-26). The services
  are therefore IPv6-only in practice, which matches the brief; the A records
  are the cluster's business.
- Access: `ssh -6 popsolutions@keellinux.org`, passwordless sudo, root login
  refused. No other accounts log in; `site` and `runner` are service users.
- Firewall: nftables (`/etc/nftables.conf`), inbound policy drop, accepting
  22, 80, 443 on both families, ICMP and ICMPv6, DHCP client replies and the
  LXC bridge `lxcbr0` of the CI runner. Forwarding only for `lxcbr0`.
- Time: systemd-timesyncd, synchronized. Updates: unattended-upgrades with
  `APT::Periodic::Unattended-Upgrade "1"` (daily timers active).
- Packages added: nginx-light, dehydrated, nftables, rsync, zstd, gnupg,
  ca-certificates, git, wget, curl, bind9-host, and for the runner lxc,
  lxc-templates, kcov, bats, shellcheck, python3-yaml, libicu76, file.
  No Docker, no Kubernetes.

## 2. Names and what each serves

DNS as found on 2026-09-26 (authoritative ns1.pop.uy, confirmed through the
Google and Cloudflare public resolvers over IPv6): every name below is a CNAME
to the apex except the apex itself, and the apex has AAAA `2804:710:d0:5::13`
plus the two A records. `apt.keellinux.org` does not exist and is not used
(NXDOMAIN; the earlier plan of an APT CNAME to GitHub Pages was replaced by
`archive`). Certificates were requested only for names that resolve to this
VM over IPv6, which is all six.

| Name | Serves | Root | TurnKey Linux equivalent |
| --- | --- | --- | --- |
| `keellinux.org` (apex) | institutional site (same content as GitHub Pages) | `/srv/site` | `turnkeylinux.org` |
| `www.keellinux.org` | institutional site, same server block as the apex | `/srv/site` | `www.turnkeylinux.org` |
| `forum.keellinux.org` | community forum (NodeBB appliance, being built); placeholder page until then | `/srv/forum` | `www.turnkeylinux.org/forum` |
| `archive.keellinux.org` | APT archive: `dists/`, `pool/`, `keel-archive-keyring.asc` once signed | `/srv/archive` | `archive.turnkeylinux.org` |
| `mirror.keellinux.org` | images: `/layers/` now, `/images/` (templates, ISOs) later | `/srv/mirror` | `mirror.turnkeylinux.org` |
| `releases.keellinux.org` | Proxmox index `/pve/aplinfo.dat{,.gz,.asc}` and signed manifests `/meta/` | `/srv/releases` | `releases.turnkeylinux.org` |

Proof (from a workstation, 2026-09-26):

```
curl -6 -sI https://mirror.keellinux.org/layers/ | grep -iE '^(HTTP|x-keel)'
HTTP/2 200
x-keel-distribution: staging, unsigned
```

The apex and `www` serve the checkout of
`https://github.com/keel-linux/keel-linux.github.io.git` at `/srv/site`,
owned by the unprivileged user `site`; `keel-site-pull.timer` runs
`git -C /srv/site pull --ff-only` as that user 2 minutes after boot and every
15 minutes, so the VM and GitHub Pages serve the same content within that
window. A push to `main` of the site repository is the deployment for both.

## 3. nginx layout

| File | Purpose |
| --- | --- |
| `/etc/nginx/conf.d/keel-distribution.conf` | the `map` that holds the `X-Keel-Distribution` value (section 5) |
| `/etc/nginx/snippets/keel-acme.conf` | `/.well-known/acme-challenge/` aliased to `/var/lib/dehydrated/acme-challenges/` |
| `/etc/nginx/snippets/keel-tls.conf` | certificate paths, TLS 1.2 and 1.3 only, ECDHE ciphers, OCSP stapling |
| `/etc/nginx/snippets/keel-distribution.conf` | the header, `autoindex on`, and `/STATUS` |
| `/etc/nginx/sites-available/keel-http` | `[::]:80` and `0.0.0.0:80`, default server: ACME path, everything else 301 to `https://$host` |
| `keel-www` | apex and www on 443, default HTTPS server, `try_files $uri $uri/ $uri.html` |
| `keel-forum` | forum on 443, reverse proxied to the appliance container over IPv6 (section 3.1) |
| `keel-archive`, `keel-mirror`, `keel-releases` | one file per host, `autoindex on`, distribution header |

Every HTTPS server listens on `[::]:443` and `0.0.0.0:443` with HTTP/2. The
Debian default site is removed.

### 3.1 The forum reverse proxy, and why it binds its source address

`keel-forum` proxies `forum.keellinux.org` to the NodeBB appliance container
on the build host, over IPv6 on port 80. The block preserves `Host`, sends
`X-Forwarded-Proto https` and the WebSocket upgrade headers NodeBB needs.
The certificate already covers the name, so nothing else changes when the
container address changes.

The first line of that `location` block is the one that is easy to lose:

```
proxy_bind 2804:710:d0:5::13;
proxy_pass http://[<container address>]:80;
```

This VM has two global IPv6 addresses: the static `2804:710:d0:5::13`, which
every name resolves to, and a SLAAC address
(`2804:710:d0:5:be24:11ff:feeb:ed35` on 2026-09-26) that the kernel picks by
itself for outgoing connections. The appliance trusts exactly one proxy, the
static address, declared as `app.options.trusted_proxy` in its instance spec.
Without `proxy_bind` the appliance sees the SLAAC address, does not recognise
it, refuses to believe `X-Forwarded-Proto: https`, and answers 307 to https,
which comes straight back here: a redirect loop, with nothing in either log
that names the cause. Note there are no brackets around the literal address:
nginx rejects a bracketed address in `proxy_bind`, unlike `proxy_pass`.

The appliance side of the same problem is recorded in
`repos/keel-nodebb` (the `geo` block matches `$realip_remote_addr`, not
`$remote_addr`) and in docs/forum-build-2026-09-26.md. Both halves have to be
right: fixing either one alone still leaves the loop.

The address and the switch live in `/usr/local/sbin/keel-provision` as two
variables near the top, so a rerun keeps the proxy instead of restoring the
placeholder page:

```
PUBLIC_IPV6=2804:710:d0:5::13
FORUM_CONTAINER=<container address>
```

An empty `FORUM_CONTAINER` writes the placeholder site instead. After
changing either, run `keel-provision`, or `nginx -t && systemctl reload
nginx` if the site file was edited by hand.

## 4. Certificates

ACME client: `dehydrated` 0.7.2 from Debian (the client TurnKey's confconsole
uses), HTTP-01 over IPv6 (`IP_VERSION=6`). One certificate, directory
`/var/lib/dehydrated/certs/keellinux.org/`, ECDSA P-384, SANs
`keellinux.org`, `www`, `forum`, `archive`, `mirror`, `releases`, issued by
Let's Encrypt on 2026-09-26, `notAfter` 2026-12-25. Chain verified:

```
echo | openssl s_client -6 -connect mirror.keellinux.org:443 -servername mirror.keellinux.org
   i:C=US, O=Let's Encrypt, CN=YE2
   i:C=US, O=ISRG, CN=Root YE
Protocol: TLSv1.3
Verify return code: 0 (ok)
```

TLS 1.1 is refused (`no protocols available`). Configuration:
`/etc/dehydrated/conf.d/keel.sh` (contact `admin@keellinux.org`, hook,
key algorithm), `/etc/dehydrated/domains.txt` (one line, all names: adding a
name there and running `dehydrated -c` reissues, dehydrated detects the SAN
change itself), `/etc/dehydrated/hook.sh` (reloads nginx on `deploy_cert`).
Renewal: `dehydrated.timer`, daily with up to 6 hours of jitter, persistent,
running `dehydrated --cron`, which renews 30 days before expiry.
`keel-provision` writes the HTTPS sites only when the certificate exists, so
if issuance ever fails on a rebuilt host the HTTP sites keep serving the ACME
path and nothing else.

## 5. The staging header and how to flip it

archive, mirror and releases send `X-Keel-Distribution: staging, unsigned` on
every response and answer `GET /STATUS` with the same text. The value lives
in one place, `/etc/nginx/conf.d/keel-distribution.conf`:

```
map "" $keel_distribution {
	default "staging, unsigned";
}
```

After the first signed publication, edit that one line (for example to
`"release, signed"`), then `nginx -t && systemctl reload nginx`. Header and
`/STATUS` change together on all three hosts. The README.txt files under
`/srv/archive`, `/srv/releases` and `/srv/mirror` explain the state in words
and are edited separately when the signed content lands.

## 6. Content and how it gets there

| Path | Content today | How it arrives |
| --- | --- | --- |
| `/srv/mirror/layers/` | `core.tar.zst` (326,418,793 bytes), `lamp.tar.zst` (79,807,121), `nodejs-nginx.tar.zst` (148,864,072), each with `.sha256`, `.manifest`, `.log` | `bin/keel-publish-mirror` of the apt tooling |
| `/srv/mirror/images/` | `debian-13-keel-core_19.0-1_amd64.tar.zst` (326,418,793 bytes) with `.sha512` and, while nothing is signed, `.sha512.UNSIGNED` | the same |
| `/srv/mirror/bootstrap/` | `bootstrap-trixie-amd64.tar.gz` (81,659,452 bytes) with `.sha256`, `.sha512` and `.sha256.UNSIGNED` | packed on the build host, carried by hand (the subsection below) |
| `/srv/mirror/selfcheck/` | the daily reproducibility result, `reproducibility.json` and `STATUS` | carried from the build host by the same publication |
| `/srv/archive/` | `README.txt`, and `staging-unsigned/` with the reprepro `trixie-staging` tree | `bin/keel-publish-mirror --unsigned-staging`; the signed tree goes to the root of `/srv/archive` and needs no flag once the key exists |
| `/srv/releases/pve/` | `aplinfo.dat`, `aplinfo.dat.gz` and, while nothing is signed, `aplinfo.dat.UNSIGNED` | the same |
| `/srv/releases/meta/<date>/` | the release `MANIFEST` and its signature or `UNSIGNED` note | the same |
| `/srv/site/` | git checkout | `keel-site-pull.timer` |

Nothing unsigned other than the staging content is served, and the header
says so. `/usr/local/sbin/keel-sync-layers` is superseded and now exits 3
with a message: the build host's port 8080 no longer answers publicly
(docs/build-host.md), so nothing can pull from it by itself.

The build host's root key is not authorized on this VM and this VM's key is
not authorized there, so the transfer is a pull by this host over a loopback
forward that the maintainer's session opens: `ssh -L` to the build host and
`ssh -R` here, then `wget -6` from `http://[::1]:18080/`. Every staged file
is checked against the release `MANIFEST` before anything is installed, and
the public names are verified afterwards with `keel verify` and
`bin/verify-repo`. What a push direction would require is written in
docs/infra-recovery.md.

### Publishing a layer

The appliance gate reads `/srv/mirror/layers/` and nothing else, so a layer
that is not published here cannot be tested: `appliance / build-and-boot`
skips with a notice and passes. Publishing a layer is therefore what turns
that check from a skip into a real run.

What a published layer is, all of it under `/srv/mirror/layers/`:

| File | Why it is needed |
| --- | --- |
| `<name>.manifest` | what `keel pull` reads first, and what names the parent, the digest and the size |
| `<name>.tar.zst` | the layer itself, digest and size as the manifest records |
| `<name>.tar.zst.sha256` | the `sha256sum` line the publication verifies after the transfer |
| `<name>.tar.zst.hash` | only once a signing key exists: it names the key that signed the layer, so it is written only when one did. None is served today and `keel verify` exits 9 |

The whole chain has to be there, not only the top: `nodebb` is useless on the
mirror without `nodejs-nginx` and `core`, because `keel pull` follows
`parent` manifest by manifest and refuses to substitute anything.

How it gets here is section 6 above: the release is staged on the build host
and published by `bin/keel-publish-mirror`, which is the only supported path
now that the build host serves nothing publicly. Check afterwards, from a
workstation, over IPv6:

    curl -6 -s -o /dev/null -w '%{http_code}\n' https://mirror.keellinux.org/layers/nodebb.manifest
    curl -6 -s https://mirror.keellinux.org/layers/nodebb.manifest | head -4

Published on 2026-09-26 so the gate had something to boot: `nodebb`
(122,535,134 bytes, sha256
`40e3f4da7882b21ffda26ac18a3f14cf75c9e8935892695002c80c5bf149665f`, parent
`nodejs-nginx`), pulled from the build host and verified with `sha256sum -c`,
which reported `OK` for it and for the three layers already here. `core` had
been published on 2026-09-24 and was not transferred again. The mirror now
serves `core`, `lamp`, `nodejs-nginx` and `nodebb`.

### The trixie bootstrap, and why we publish one

`/srv/mirror/bootstrap/bootstrap-trixie-amd64.tar.gz` is the minimal Debian 13
root filesystem every TKLDev build is seeded from, the file
`https://mirror.keellinux.org/bootstrap/bootstrap-trixie-amd64.tar.gz` now
serves. TurnKey publishes none for trixie: `images/bootstrap/` on
`mirror.turnkeylinux.org` stops at bookworm, which is issue A of
../TKL/plan/02 and what stops a fresh TKLDev 19.0, since `tkldev-setup` there
downloads `bootstrap-trixie-amd64.tar.gz` and aborts on the 404.

Packed on 2026-09-26 from the working bootstrap on the build host
(`/turnkey/fab/bootstraps/trixie-amd64`, Debian 13.7, 109 packages) with the
command the bootstrap repository's Makefile uses, and nothing else, so the
tarball is the same shape `bt-bootstrap` publishes:

    tar -C /turnkey/fab/bootstraps/trixie-amd64 -zcf bootstrap-trixie-amd64.tar.gz .

Neither that Makefile nor `bt-bootstrap` passes any determinism flags, so this
tarball is not reproducible byte for byte and is not claimed to be.

| | |
| --- | --- |
| Size | 81,659,452 bytes, 8,036 members |
| sha256 | `e3dfbde707e1ac88fc67015aa61998d0ab5975c849c6a1ff95f09b80be1ac868` |
| sha512 | `3c66c3396b34e87c3b279c4fb41f2bafbef46fbabd92d47473cb375be380cbf79c3f10e344147828b781890d087161ceeefe0a9448c6986df45dfbb5b1e569dc` |

Checked before publication: unpacked as root on the build host into a scratch
directory and compared with the source tree by `rsync -aHAXn --delete
--itemize-changes`, which reported no difference at all, same 8,036 paths and
237 MB. Checked after publication from a workstation over IPv6: the file
fetched from the public name has that sha256, and `/bootstrap/` answers with
`X-Keel-Distribution: staging, unsigned` like the rest of the tree.

It is not signed and it carries no `.hash`. A hash file names the key that
signed it, and no signing subkey exists yet (decision 0005), so the digests
travel alone and `bootstrap-trixie-amd64.tar.gz.sha256.UNSIGNED` says in words
what is missing, the same way `/srv/mirror/images/` marks its `.sha512`. This
is also what buildtasks `bin/generate-signature` writes now without
`BT_GPGKEY`: `.sha256` and `.sha512`, no hash file, no key named
(keel-linux/buildtasks#5).

Consequence for `tkldev-setup`: it verifies the download with
`bin/signature-verify --force-gpg`, which needs a signed hash file, so it will
not consume this tarball until the bootstrap is published signed. That is not
a hole in the appliance path, because our `tkldev-setup`
(keel-linux/tkldev, `setup_bootstrap`) no longer dies when a mirror has no
bootstrap: unless `--strict` or `--transition` was given it warns "building it
locally instead" and calls `build_bootstrap`, which clones
`turnkeylinux/bootstrap` beside `$FAB_PATH` and runs `make install`, about 70
seconds on the build host, then checks that `bin/bash` is really there. The
published tarball is for a person or a script that fetches it by hand with the
digest above, and it is what the mirror will serve signed once the subkey
lands.

Removed from the mirror while publishing this, for the same reason the tarball
has no hash file: `lamp.tar.zst.hash`, `nodejs-nginx.tar.zst.hash` and
`nodebb.tar.zst.hash` were still served and each one told the reader to import
TurnKey's trixie release key (`DEE9 0D99 70AE 35D5 5B7C 6C2D C6D2 54B7 6A9D
9430`) and verify with it, while carrying no signature at all. The three are
gone from `/srv/mirror/layers/` (all four names now answer 404) and the four
copies in `/mnt/builds/layers/` on the build host are gone too, so the next
publication cannot carry them back. `keel verify` now exits 9 for the mirror
instead of 8.

Transfer, this once, was a copy through the maintainer's workstation
(`scp` from the build host, `rsync` over IPv6 to this VM, `sha256sum -c` at
every hop, then `install -m 0644 -o root -g root`) instead of the loopback
forward of section 6, because nothing about a single file needs the release
machinery. `/srv/mirror/README.txt` was rewritten to list `/bootstrap/` and to
say that nothing here carries a `.hash` while nothing is signed;
docs/infra/keel-provision.pending carries the same text, so a rerun of the
provisioning script keeps it.

## 7. The CI runner

GitHub Actions runner 2.337.0 at `/home/runner/actions-runner`, user
`runner`, registered at organization level as `keel-lxc-1` with labels
`self-hosted, Linux, X64, keel-lxc`, runner group Default. Service
`actions-runner.service` (`User=runner`, `run.sh`, `Restart=always`),
enabled. `gh api orgs/keel-linux/actions/runners` showed it online on
2026-09-26 and the organization variable `KEEL_LXC_RUNNER` was then set to
`true`. Sudo for `runner` is limited to `apt-get`, the `lxc-*` commands and
the two appliance gate entry points below (`/etc/sudoers.d/runner`);
`lxc-net` provides `lxcbr0` for boot tests.

What the runner host does not have, on purpose: fab, deck, buildtasks, the
`/turnkey/*` trees and `/mnt/builds/layers`. Layer builds stay on the build
host (docs/build-host.md), which is the only place with the tooling and,
later, the signing subkey. `test-appliance.yml` in `keel-linux/.github` was
rewritten on 2026-09-26 to match: it fetches the layers from
`https://mirror.keellinux.org/layers` over IPv6, verifies them, assembles the
chain into a scratch rootfs, boots it and runs the appliance repository's
`tests/boot-test.sh` against it. It builds nothing. `build-deb.yml`
(dpkg-buildpackage) still needs `build-essential devscripts equivs fakeroot
dpkg-dev` on this host; they are not installed and should be added when the
first package job is enabled.

### What the appliance gate may do here

Assembling a rootfs and starting a container need root, and the boot test is
code from the appliance repository, so the rule is that the runner user may
start two fixed commands and nothing else. Both are written by
`keel-provision` and both check their own arguments before acting:

| Command | What it does |
| --- | --- |
| `/usr/local/sbin/keel-ci-boot-test WORKSPACE SCRATCH APPLIANCE [options]` | runs `WORKSPACE/tests/boot-test.sh` as root with the job's keel checkout (`WORKSPACE/.keel/bin`) first in `PATH`. Refuses a workspace outside `/home/runner/actions-runner/_work`, a scratch directory outside `/var/tmp/keel-ci`, any path holding `..`, an appliance name outside `[a-z0-9-]`, and a missing or non executable boot test |
| `/usr/local/sbin/keel-ci-cleanup NAME SCRATCH` | `lxc-stop -k`, `lxc-destroy -f` and `rm -rf` of that one scratch tree. Same path and name checks. Safe to call twice and after a failure, which is how the workflow's cleanup step uses it |

There is no `ALL` command in `/etc/sudoers.d/runner`. `/var/tmp/keel-ci` is
owned by `runner`, so a job creates its own scratch tree without root, and
each run uses its own container name and its own tree
(`keel-<appliance>-ci-<run id>-<attempt>`), so two runs never collide.

Container networking: the boot test joins `lxcbr0`. The dnsmasq `lxc-net`
starts runs with `--dhcp-range=fc42:5009:ba4b:5ab0::1,ra-only`, so a container
gets a global scope IPv6 address in that ULA prefix by SLAAC within about five
seconds, reaches the outside through the IPv6 masquerade rule `lxc-net`
installs, and is reachable from the host, which is what an appliance's HTTP
checks need. A macvlan interface on `eth0` would hand out an address from the
VM's public `2804:710:d0:5::/64`, as the build host does for its long lived
containers, but a host cannot talk to its own macvlan children, so those
checks would have nowhere to run from; the bridge is the right choice for a
throwaway CI container and it adds no MAC to the public segment. `apparmor`
4.1.0 is installed, which `lxc-start` needs for the generated profile.

Verified by hand on 2026-09-26 as the `runner` user, the whole sequence the
workflow runs, against `core`: `keel pull` from the mirror 3 s (the mirror is
this same host), `keel verify` exit 8 while nothing is signed, assemble 13 s,
container started with a global IPv6 address in 5 s, first boot finished 5 s
later, `keel diff` 8 same and 0 drift, 23 s in total. Against `nodebb`:
`keel pull` of the three layers, 598 MB, 7 s, assemble 43 s, container up in
5 s, then a real failure of the published layer (docs/ci-cd.md section 7).
Both containers and both scratch trees were removed with `keel-ci-cleanup`;
nothing else on the VM was touched.

## 8. Units and timers

| Unit | Role |
| --- | --- |
| `nginx.service` | all six sites |
| `nftables.service` | firewall |
| `dehydrated.timer` -> `dehydrated.service` | daily renewal check |
| `keel-site-pull.timer` -> `keel-site-pull.service` | site checkout, every 15 minutes, user `site` |
| `actions-runner.service` | GitHub Actions runner |
| `lxc.service`, `lxc-net.service`, `lxc-monitord.service` | LXC for the runner |
| `apt-daily.timer`, `apt-daily-upgrade.timer` | unattended-upgrades |

## 9. Pending

- `mirror.keellinux.org/bootstrap/`: publish it signed (a `.hash` written by
  `bin/generate-signature` with `BT_GPGKEY` and `BT_SIGN_KEY_URL` set) after
  the subkey rotation, so `tkldev-setup` can verify and use it instead of
  building a bootstrap locally.
- Signed APT archive at the root of `archive.keellinux.org`: after the
  signing subkey rotation of decision 0005 (nothing signed exists; the
  public key is not published). The tooling is ready for it:
  `bin/keel-publish-mirror` publishes to the root and needs no flag as soon
  as the release and the archive are signed, and refuses otherwise.
  `staging-unsigned/` is removed the day that happens.
- `releases.keellinux.org/pve/aplinfo.dat.asc`: written by `bt-aplinfo` as
  soon as the subkey is in the build host's keyring; `aplinfo.dat` and
  `.gz` are already served, with an `UNSIGNED` note beside them.
- Flip the staging header (section 5) and rewrite the three README.txt files
  at the first signed publication; `/srv/mirror/README.txt` also still says
  `/images/` "appears with the first release", which it now has.
- Retiring the build host's temporary mirror on port 8080: done on
  2026-09-26. It listens on the loopback only and the port does not answer
  from outside (docs/build-host.md).
- **`keel-provision` has not been updated yet.** The live
  `/etc/nginx/sites-available/keel-forum` carries the reverse proxy and the
  `proxy_bind` of section 3.1, edited by hand on 2026-09-26, but the
  provisioning script still writes the placeholder site with the proxy block
  commented out, so the next run of `keel-provision` would take the forum
  down. The rewritten script is `docs/infra/keel-provision.pending`; it
  passes `sh -n` and shellcheck and only has to be installed:
  `install -m 0755 -o root -g root keel-provision.pending
  /usr/local/sbin/keel-provision`. Until then, do not run `keel-provision`.
- **The Default runner group refuses public repositories.**
  `allows_public_repositories` is `false` on runner group 1 and every
  repository of the organization is public, so GitHub accepts an
  `appliance / build-and-boot` job and then leaves it queued while
  `keel-lxc-1` is online and idle. One call by the maintainer fixes it:
  `gh api -X PATCH orgs/keel-linux/actions/runner-groups/1 -F allows_public_repositories=true`.
  Worth doing in the same sitting: set the fork pull request policy to
  require approval for all outside contributors, because a self-hosted
  runner on this VM must never run code from an unreviewed fork.
- `build-deb.yml` build dependencies on the runner host (section 7).
- IPv4: the A records point at addresses that do not forward 80 and 443 to
  the VM; either the cluster adds the forwarding or the A records go.
