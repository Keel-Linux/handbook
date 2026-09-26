# Infrastructure recovery

Date: 2026-09-26. Two machines carry the project: the build host, which
builds the appliances and will hold the signing subkey, and the public
services VM, which serves everything a user fetches. This note says, for
each of them, what it is, what runs on it, what cannot be recreated, what
can and how, and how to rebuild it from a fresh Debian 13. It ends with
what is not backed up, and with the list of things that live on a machine
and in no repository.

It is a companion to build-host.md and releases-host.md, which describe
the machines as they are; this one is about getting them back.

## 0. The two machines

| | Build host | Public services VM |
| --- | --- | --- |
| Name | `tkldev` | `keellinux` |
| Access | `ssh root@2804:710:d0:5:bb3f:380a:f07b:7951` | `ssh -6 popsolutions@keellinux.org`, `sudo -n` |
| Base | TKLDev 19.0 (Debian trixie), 8 vCPU, 59 GB | Debian 13.7, 6 vCPU, 7.8 GB, 99 GB |
| Public | no: SSH only, nginx on the loopback | yes: 80 and 443 on IPv6, six names |
| Holds a key | the signing subkey, once imported (nothing today) | no signing key, ever |
| Rebuild cost | hours (builds), see section 1.5 | under an hour, section 2.5 |

Neither machine holds a credential that lets it write on the other. That
is deliberate and it is why publication is a pull driven by the
maintainer's own session (section 3).

## 1. Build host

### 1.1 What it is

A TKLDev 19.0 virtual machine on the maintainer's Proxmox cluster. TKLDev
is the appliance build environment: `fab`, `deck`, `pool`,
`turnkey-chroot`, `debootstrap`, `squashfs-tools`, `xorriso`. `postfix`
must stay inactive, and two builds must never run at the same time, both
because the build chroot shares the host network (build-host.md).

### 1.2 What runs on it

| Piece | Where |
| --- | --- |
| Appliance builds | `/turnkey/fab-keel` (project tree), `/turnkey/fab` (upstream reference), `/turnkey/buildtasks-keel`, `/turnkey/tklbam-profiles-keel` |
| Layer outputs | `/mnt/builds/layers` |
| Release path | `/srv/keel-apt/apt` (this tooling), staged releases in `/srv/keel-release` |
| APT repository | `/srv/keel-apt/repo` (reprepro), incoming and done beside it |
| Internal web server | nginx, `[::1]:8080` and `127.0.0.1:8080` only |
| Daily self check | `keel-selfcheck.timer`, rebuilding `core` into `/srv/keel-selfcheck/builds` |
| Forum appliance | LXC containers `forum` (running, proxied from the public VM) and `forum2` |

### 1.3 What is irreplaceable

**Nothing, today.** `gpg --list-secret-keys` in root's keyring is empty:
no signing key has been imported yet, so the machine holds no secret at
all. Everything under `/turnkey`, `/mnt/builds` and `/srv` is either in
git or rebuildable from it.

**Once the signing subkey is imported** (decision 0005), root's GnuPG home
`/root/.gnupg` holds the secret of the signing subkey. That is a secret,
but it is still not irreplaceable: the primary key and the revocation
certificate live offline with the maintainer and have never been on this
machine, so a lost subkey is replaced by issuing a new one from the
primary. What would be irreplaceable is the **primary key**, and the
correct answer to "where is it backed up" is "not here, and never here":
two copies the maintainer controls, one encrypted USB key and one paper
copy (`paperkey`), in different places.

The one file on this machine that no repository can produce is the
bootstrap, section 4.

### 1.4 What is reproducible from git, and how

| Thing | From | How |
| --- | --- | --- |
| `/turnkey/fab-keel` and the appliance products | `github.com/keel-linux` | `tkldev-setup <appliance>` with `GIT_REMOTE_URL=https://github.com/keel-linux` (it maps `core` to `keel-core`) |
| `/turnkey/buildtasks-keel`, `/turnkey/tklbam-profiles-keel` | keel-linux/buildtasks, keel-linux/tklbam-profiles | `git clone` |
| `/turnkey/buildtasks-aplinfo` | branch `feat/bt-aplinfo` of keel-linux/buildtasks | `git worktree add`, until the branch is merged |
| `/srv/keel-apt/apt` | the apt tooling repository | `git clone` (not on GitHub yet, section 5) |
| The `fab 1.1.1+keel1` package and the pin | keel-linux/fab branch `pkg/keel1`, which is pushed | build-host.md section 4 |
| The other project packages | the repositories they come from | `bin/build-package <repo>` |
| `/mnt/builds/layers` | the products and `common` at a commit | `bin/keel-release <appliance> --rebuild`, which is also what the daily self check proves still works |
| `/srv/keel-release` | the layers | `bin/keel-release` |
| nginx block, systemd units, `/etc/keel-apt.conf` | this repository | `infra/build-host/`, `systemd/`, section 1.5 |

### 1.5 Rebuild from a fresh Debian 13

A plain Debian 13 is not enough by itself: the build tools come from the
TurnKey archive, and the bootstrap comes from a TKLDev image (section 4).
The honest procedure is "install TKLDev 19.0, then apply the project's
deltas"; from a bare Debian 13 the extra step is adding the TurnKey
archive and its keyring.

```
# 1. Base. Either deploy the TKLDev 19.0 appliance (preferred), or on a
#    plain Debian 13 add the TurnKey archive and install the build tools:
apt-get install -y fab deck pool turnkey-chroot debootstrap squashfs-tools \
                   xorriso syslinux-utils reprepro gnupg gpgv dpkg-dev \
                   rsync git zstd bats kcov shellcheck nginx-light lxc

# 2. The trees. tkldev-setup from keel-linux/tkldev, not the system copy,
#    which stays upstream's. raw.githubusercontent.com has IPv6 (0005).
curl -6 -fsSL https://raw.githubusercontent.com/keel-linux/tkldev/master/tkldev-setup \
     -o /root/keel-tkldev-setup && chmod +x /root/keel-tkldev-setup
export FAB_PATH=/turnkey/fab-keel RELEASE=debian/trixie FAB_ARCH=amd64
export GIT_REMOTE_URL=https://github.com/keel-linux
export BT_PATH=/turnkey/buildtasks-keel TKLBAM_PATH=/turnkey/tklbam-profiles-keel
mkdir -p $FAB_PATH/bootstraps
cp -a <bootstrap source>/trixie-amd64 $FAB_PATH/bootstraps/   # section 4
/root/keel-tkldev-setup core
git clone https://github.com/keel-linux/buildtasks /turnkey/buildtasks-keel
git clone https://github.com/keel-linux/tklbam-profiles /turnkey/tklbam-profiles-keel
cp /turnkey/buildtasks-keel/config.example/common.cfg /turnkey/buildtasks-keel/config/
#    then edit that copy: BT_PRODUCTS, BT_BUILDS and BT_GPGKEY must read
#    ${VAR:-default} and BT_GPGKEY must default to empty, never to the
#    TurnKey fingerprint the example ships (build-host.md).

# 3. The project's fab, and the pin (build-host.md sections 2 to 4).

# 4. The release tooling and its host configuration.
git clone <apt tooling> /srv/keel-apt/apt
mkdir -p /srv/keel-apt/incoming /srv/keel-apt/done /srv/keel-apt/repo
cp /srv/keel-apt/apt/infra/build-host/keel-apt.conf.example /etc/keel-apt.conf
git -C /turnkey/buildtasks-keel worktree add --detach /turnkey/buildtasks-aplinfo \
    origin/feat/bt-aplinfo
ln -sfn /turnkey/buildtasks-keel/config /turnkey/buildtasks-aplinfo/config

# 5. The internal web server and the daily self check.
install -m 0644 /srv/keel-apt/apt/infra/build-host/nginx-keel-internal.conf \
    /etc/nginx/sites-available/keel-releases
ln -sfn /etc/nginx/sites-available/keel-releases /etc/nginx/sites-enabled/
install -m 0644 /srv/keel-apt/apt/infra/build-host/sshd-00-keel-release.conf \
    /etc/ssh/sshd_config.d/00-keel-release.conf
nginx -t && systemctl restart nginx && sshd -t && systemctl reload ssh
install -m 0644 /srv/keel-apt/apt/systemd/keel-selfcheck.* /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now keel-selfcheck.timer

# 6. The signing subkey, by scp from the maintainer, never through a chat
#    channel (decision 0005). Then bin/publish and bin/keel-release start
#    signing by themselves; nothing else changes.

# 7. Rebuild the layers and stage a release.
/srv/keel-apt/apt/bin/keel-release --rebuild all
```

The proof that step 7 restored the same machine is the self check: it
compares the rebuilt `core` against the digest recorded for
`SOURCE_DATE_EPOCH=1700000000`.

## 2. Public services VM

### 2.1 What it is

A Debian 13.7 virtual machine with a public IPv6 address,
`2804:710:d0:5::13`, serving six names over HTTPS. Its IPv4 addresses do
not reach it from outside (releases-host.md section 1).

### 2.2 What runs on it

nginx (apex, www, forum, archive, mirror, releases), dehydrated for the
Let's Encrypt certificate, `keel-site-pull.timer` for the institutional
site, the GitHub Actions runner `keel-lxc-1`, LXC for its boot tests, and
nftables.

### 2.3 What is irreplaceable

| File | Why it matters | Really irreplaceable? |
| --- | --- | --- |
| `/var/lib/dehydrated/accounts/...` | the ACME account key | No. A new account registers in seconds and reissues the certificate; losing it costs one `dehydrated --register --accept-terms`. |
| `/var/lib/dehydrated/certs/keellinux.org/` | the live certificate and its private key | No. Reissued by `dehydrated -c` over HTTP-01 once the names resolve here. |
| `/home/runner/actions-runner/.credentials`, `.runner` | the runner registration | No, but it needs the maintainer: a registration token requires `admin:org`, and the runner must be re-registered (ci-cd.md section 6). |
| `/srv/archive`, `/srv/mirror`, `/srv/releases` | what the world fetches | No. Republished from the build host by `bin/keel-publish-mirror`; the signatures come from the signing subkey, not from here. |
| `/srv/site` | the institutional site | No. A checkout of keel-linux/keel-linux.github.io, pulled every 15 minutes. |

So the VM holds nothing that cannot be recreated, and that is the point of
the split: the public machine is disposable.

### 2.4 What is reproducible, and how

`/usr/local/sbin/keel-provision` writes every configuration file on this
host and is idempotent: firewall, users, trees, nginx sites and snippets,
the distribution header, dehydrated, the site timer and the README files.
It is now in git as `infra/public-host/keel-provision`; until 2026-09-26
it existed only on the machine, which is what made this note necessary.

### 2.5 Rebuild from a fresh Debian 13

```
# 1. Install Debian 13, give it the static IPv6 2804:710:d0:5::13, make
#    the six names resolve to it (they are CNAMEs to the apex today).
apt-get install -y nginx-light dehydrated nftables rsync zstd gnupg \
    ca-certificates git wget curl bind9-host lxc lxc-templates kcov bats \
    shellcheck python3-yaml libicu76 file

# 2. Provision. It writes everything and refuses nothing it can check.
scp infra/public-host/keel-provision popsolutions@keellinux.org:/tmp/
sudo install -m 0755 /tmp/keel-provision /usr/local/sbin/keel-provision
sudo /usr/local/sbin/keel-provision

#    The first run has no certificate, so only the HTTP sites are written
#    and the ACME path is served; dehydrated then issues, and a second run
#    writes the HTTPS sites. Check:
curl -6 -sI https://mirror.keellinux.org/STATUS

# 3. The content. Nothing is restored from a backup: it is republished.
./bin/keel-publish-mirror <date>          # from a workstation, per release

# 4. The CI runner, which needs the maintainer (ci-cd.md section 6): a
#    registration token with admin:org, piped into the VM, then the unit.
```

## 3. If a push direction is ever wanted

Today the public VM pulls, over a loopback forward that the maintainer's
session opens (build-host.md). Nothing on the build host can write on the
public VM, which is the property worth keeping once that machine holds the
signing subkey: a key that can write on the public host would sit on the
same disk as the key that signs.

If a push is wanted anyway, this is exactly what the maintainer has to do,
and it is four things, not one:

1. On the public VM, create a service account that owns nothing else:
   `useradd -r -m -d /var/lib/keel-publish -s /bin/sh keel-publish`, and a
   directory it may write: `install -d -o keel-publish /srv/keel-publish`.
2. On the build host, as root, generate a key that exists only for this:
   `ssh-keygen -t ed25519 -f /root/.ssh/id_keel_publish -C keel-publish`.
3. On the public VM, authorize it with a forced command and no other
   privilege, in `/var/lib/keel-publish/.ssh/authorized_keys`:

   ```
   command="rrsync -wo /srv/keel-publish",restrict ssh-ed25519 AAAA... keel-publish
   ```

   `rrsync` ships with rsync; `-wo` makes it write only, into that one
   directory. `restrict` turns off forwarding, ptys and agent forwarding.
4. Give `keel-publish` a sudo rule for one command only, the installer that
   moves a checked staging directory into `/srv`, and never for `rsync`
   itself:
   `keel-publish ALL=(root) NOPASSWD: /usr/local/sbin/keel-install-release`.

With that, and only that, the build host can push into a staging area it
cannot read back, and a separate privileged step on the VM decides what
becomes public. Anything less, in particular a plain key with a shell,
means a compromise of the build host is a compromise of the public host,
and the signing subkey is on the build host.

## 4. What is not in git and not reproducible

Checked on both machines on 2026-09-26.

| Thing | Machine | State |
| --- | --- | --- |
| `/turnkey/fab-keel/bootstraps/trixie-amd64` | build | **Not in git, not reproducible from the project.** Copied by hand from `/turnkey/fab` of the TKLDev image; the organization has no `bootstrap` repository and the mirror does not publish the tarball (m0-gate.md). A rebuild needs a TKLDev 19.0 image or a `bootstrap` repository, and creating one is the fix. |
| The `forum` LXC container's live data | build | **Not in git, not reproducible, not backed up.** The rootfs comes from the `nodebb` layer and a spec, but the forum's database and uploads do not. It serves `forum.keellinux.org` today. |
| `/turnkey/buildtasks-keel/config/common.cfg` | build | Not in git (buildtasks ignores `config`). Reproducible from `config.example/common.cfg` plus the three edits described in build-host.md. |
| `/etc/apt/preferences.d/keel-fab` | build | Not in git. Three lines, quoted in build-host.md. |
| `/root/gate2.sh`, `/root/forum2-assemble.sh`, `/root/bt-layer-fix.patch` | build | Not in git. One-off scripts of earlier work; the procedures they run are in m0-gate.md and forum-build-2026-09-26.md. |
| `/root/src/*.deb` and `/root/src/*` clones | build | Reproducible: `bin/build-package <repo>` rebuilds each one from its repository. |
| `/root/.ssh/authorized_keys` on the build host, the maintainer's keys on the VM | both | Not in git, and should not be. Losing them costs console access to re-add a key. |
| The signing subkey secret, once imported | build | Not in git, never will be. Replaceable from the offline primary. |
| `/var/lib/dehydrated/accounts` | public | Not in git. Replaceable by registering again. |
| `/home/runner/actions-runner` registration | public | Not in git. Replaceable only with a token the maintainer creates. |
| The apt tooling repository itself | both | **In git, but only locally.** It is not on GitHub yet: it carries the public archive key and is published together with the key rotation (section 5). The only copies are the workstation checkout and `/srv/keel-apt/apt` on the build host. |
| `BRIEF.md`, `STATUS.md` and this `docs/` tree | neither | **Not a git repository at all.** The project's own documentation exists only in one directory on the maintainer's workstation. Putting it in a repository is the single cheapest recovery improvement available. |

## 5. Backups

**There is no backup of anything described here, today.** No snapshot
schedule on either virtual machine, no copy of `/srv` anywhere, no export
of the forum container. The only reason this is survivable is that almost
everything is reproducible; the exceptions are the four rows above marked
not reproducible.

What should be backed up, in the order the loss would hurt:

| What | Where it should go | Why |
| --- | --- | --- |
| The OpenPGP primary key and its revocation certificate | two places the maintainer controls, offline, one of them paper (`paperkey`) | It is the only thing that cannot be regenerated by anyone, ever. It is not on either machine and must stay that way. |
| The forum container's data | a nightly dump to the public VM or the cluster's backup store | The only live user data the project has. |
| The `trixie-amd64` bootstrap | a `bootstrap` repository in the organization, or an artifact on the mirror with a digest | Without it no machine can build anything from scratch. |
| This documentation tree | a git repository in the organization | It is the map; it currently has one copy. |
| `/srv` on the public VM | nothing: republish instead | Cheaper to republish from a staged release than to restore. |
| Both virtual machines | the cluster's own snapshot or backup schedule | Cuts a rebuild from hours to minutes. It does not replace any row above. |

The self check (build-host.md) is the only thing that continuously proves
a rebuild would produce the same bytes; it is a recovery test that runs
every day, and its result is at
`https://mirror.keellinux.org/selfcheck/STATUS`.
