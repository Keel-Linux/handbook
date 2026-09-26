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

## 7. The CI runner

GitHub Actions runner 2.337.0 at `/home/runner/actions-runner`, user
`runner`, registered at organization level as `keel-lxc-1` with labels
`self-hosted, Linux, X64, keel-lxc`, runner group Default. Service
`actions-runner.service` (`User=runner`, `run.sh`, `Restart=always`),
enabled. `gh api orgs/keel-linux/actions/runners` showed it online on
2026-09-26 and the organization variable `KEEL_LXC_RUNNER` was then set to
`true`. Sudo for `runner` is limited to `apt-get` and the `lxc-*` commands
(`/etc/sudoers.d/runner`); `lxc-net` provides `lxcbr0` for boot tests.

What the runner host does not have, on purpose: fab, deck, buildtasks, the
`/turnkey/*` trees and `/mnt/builds/layers`. Layer builds stay on the build
host (docs/build-host.md), which is the only place with the tooling and,
later, the signing subkey. `test-appliance.yml` in `keel-linux/.github`
therefore has to change before its first run: instead of calling `bt-layer`,
the job should fetch `<appliance>.tar.zst` and its `.sha256` from
`https://mirror.keellinux.org/layers/` over IPv6, verify, then run
`keel verify` and `tests/boot-test.sh` against a local layers directory.
Until that change lands, a caller of `test-appliance.yml` fails at the build
step on this runner. `build-deb.yml` (dpkg-buildpackage) needs
`build-essential devscripts equivs fakeroot dpkg-dev` on this host; they were
not installed here and should be added when the first package job is enabled.

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
- `test-appliance.yml`: fetch layers from the mirror instead of building
  (section 7); `build-deb.yml` build dependencies on the runner host.
- IPv4: the A records point at addresses that do not forward 80 and 443 to
  the VM; either the cluster adds the forwarding or the A records go.
