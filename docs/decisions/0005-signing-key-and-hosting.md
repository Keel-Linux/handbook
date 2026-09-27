# 0005: Signing key custody and repository hosting: procedure and options

Date: 2026-09-26
Status: options prepared; the maintainer generates the key and picks the hosting

## Part 1: the signing key

What it signs: APT `Release` files, layer `.hash` files, the Proxmox
`aplinfo.dat.asc`, and later the manifests. Who verifies it: `apt` on Debian
13 appliances, Proxmox's `sqv` (Sequoia), and `keel verify`. All three accept
a plain OpenPGP key.

Recommended shape, from the brief (section 11: "root key offline, signing
subkey on the builder"):

- A **primary key** that only certifies (capability C), Ed25519, no expiry,
  generated and kept offline: it never touches the build host. It exists to
  issue and revoke subkeys and to prove continuity if a subkey is lost.
- A **signing subkey** (capability S), Ed25519, 2 year expiry, exported alone
  to the build host. This is what `BT_GPGKEY` in buildtasks and `reprepro` or
  `aptly` use.
- A **revocation certificate** for the primary key, generated at creation.
- Ed25519 is fine for apt on Debian 13 and for sqv. If a consumer older than
  Debian 11 must ever verify, RSA 4096 is the conservative alternative; the
  procedure below takes either.

Custody, minimum viable:

1. Generate on a machine that is offline for the duration (a live system, or
   a laptop with networking off), never on the agent host or the build host.
2. Store the primary secret key and the revocation certificate in two places
   the maintainer controls, for example an encrypted USB key kept at home and
   a printed paper copy (`paperkey` in Debian) in a separate location.
3. Only the signing subkey secret goes to the build host, into the `root` GPG
   keyring of the TKLDev VM, and it is the only key `bt-*` can use.
4. Publish the public key in three places: the `keel-archive-keyring` package,
   the repository web root, and the organization's GitHub (a `keys/` directory
   in `common`, as TurnKey does in `common/keys/`).
5. Rotation: a new signing subkey a few months before expiry; the old one is
   kept for verification of already published artifacts; the primary key is
   rotated only on compromise.

Procedure (run by the maintainer, offline; adjust the identity):

```
export GNUPGHOME=$(mktemp -d)
cat > primary.conf << 'GPG'
%no-protection
Key-Type: eddsa
Key-Curve: ed25519
Key-Usage: cert
Name-Real: Keel Linux Archive Signing Key
Name-Email: release@<domain>
Expire-Date: 0
%commit
GPG
gpg --batch --generate-key primary.conf
FPR=$(gpg --list-keys --with-colons | awk -F: '$1=="fpr"{print $10; exit}')
gpg --quick-add-key "$FPR" ed25519 sign 2y
gpg --output revoke-primary.asc --gen-revoke "$FPR"
gpg --armor --export "$FPR" > keel-archive-keyring.asc
gpg --armor --export-secret-keys "$FPR" > primary-secret.asc
gpg --armor --export-secret-subkeys "$FPR" > signing-subkey-secret.asc
```

`%no-protection` is only acceptable because the files are then moved to
encrypted storage; add a passphrase instead if the USB key is not encrypted.
`primary-secret.asc` and `revoke-primary.asc` go offline; only
`signing-subkey-secret.asc` is imported on the build host; the public
`keel-archive-keyring.asc` is what gets published. Test before use:

```
echo test > t; gpg --detach-sign --armor t; sqv --keyring keel-archive-keyring.asc t.asc t
```

The agent does not generate this key. Custody means the maintainer holds it
from the first second.

## Part 2: where the APT repository and the layers live

Constraint from the brief: IPv6-first. Checked on 2026-09-26 from this host:

| Endpoint | Native IPv6 |
| --- | --- |
| GitHub Pages (`*.github.io`) | yes |
| `raw.githubusercontent.com` | yes |
| `github.com`, `api.github.com` | no |
| Release assets (`objects.githubusercontent.com`) | no |
| `deb.debian.org`, `mirror.turnkeylinux.org` | yes |

So GitHub can host part of it, not all of it:

- **APT repository on GitHub Pages: yes, it works.** An APT repository is
  static files (`dists/`, `pool/`), Pages serves them over HTTPS with IPv6,
  and the `Release` file is signed with our key, so the transport is not the
  trust anchor. Limits that matter: about 1 GB per site and 100 MB per file
  (git), and a soft 100 GB per month of bandwidth. Our packages are small
  (inithooks, confconsole, fab, keel, the keyring and transition packages),
  so this fits for a long time. The repository is generated on the build host
  with `reprepro` or `aptly` and pushed as a git commit to a `keel-linux/apt`
  repository with Pages enabled, which also gives every publication a git
  history. No CI service is needed for that, which keeps us inside the brief's
  "CI on LXC" rule.
- **Layer tarballs and templates: not on GitHub.** They are 80 to 330 MB each,
  above the Pages file limit, and Release assets have no IPv6. They need a
  plain HTTP server we control: an LXC container on the maintainer's Proxmox
  cluster running nginx (or a Keel appliance, once one exists, which is the
  right kind of dogfooding), with a public IPv6 address, serving
  `layers/<name>-<sha256>.tar.zst` and `pve/aplinfo.dat{.gz,.asc}`. The same
  container can later run the S3-compatible service brief 5.6 asks for
  (Garage or MinIO, both packaged for Debian), so one host serves layers,
  templates and backup targets.
- **A dedicated server is not required.** A container on the existing cluster
  is enough; what is required is a stable name under our domain, IPv6, TLS
  (ACME, like every appliance), and a mirror plan. GitHub Pages can also be a
  secondary mirror for the APT part only.

Recommendation: APT on GitHub Pages plus a layers host on the cluster, both
under `<domain>` names (`apt.<domain>` via a CNAME to Pages, `releases.<domain>`
to the container), so the URLs never change if the hosting does.

## What the maintainer decides

1. Key: Ed25519 (recommended) or RSA 4096; identity string; where the offline
   copies live.
2. Hosting: the split above, or everything on the cluster host.
3. The domain, which both depend on (0001).

## Key generated (2026-09-26)

Generated offline by the maintainer with docs/keys/keel-keygen.sh: primary
Ed25519, certify only, no expiry, fingerprint
AD0964BE3F09DED469A3B6B2148E951314703180, identity
"Keel Linux Archive Signing Key <release@keellinux.org>"; signing subkey
Ed25519, fingerprint 694DE5E8C17BF1F9B73EAE2BD276B62C2BD16F4E, expires
2028-09-25. Public key saved at docs/keys/keel-archive-keyring.asc, verified
against the fingerprint.

Custody note, acted on 2026-09-27 (see "Rotated" below): the passphrase-protected
secret of the signing subkey 694DE5E8 was transmitted through the chat
channel instead of scp, so that copy is treated as exposed. It was not imported anywhere. Agreed course:
revoke subkey 694DE5E8 with the offline primary, issue a new signing subkey,
re-export the public key, and deliver the new secret only by scp to the build
host. Until then, nothing is signed and the public key is not published, so a
single publication carries the definitive subkey. The primary key was never
exposed and stays valid.

### Rotated (2026-09-27)

Done, and the question below is closed by it. The maintainer revoked subkey
694DE5E8 with the offline primary, reason compromised, and issued a new
signing subkey. Measured afterwards, not assumed:

| Key | Fingerprint | State |
| --- | --- | --- |
| Primary, certify only | AD0964BE3F09DED469A3B6B2148E951314703180 | unchanged, never left offline custody, `sec#` on the build host |
| Old signing subkey | 694DE5E8C17BF1F9B73EAE2BD276B62C2BD16F4E | revoked 2026-09-27, kept for verification, never signed anything |
| New signing subkey | 03041024F4B2C0C2F42DDDEA04906EAB77513310 | Ed25519, expires 2028-09-26, secret on the build host only |

The procedure is `docs/keys/keel-rotate-subkey.sh`, rehearsed on a throwaway
key of the same shape before being used on the real one. The secret travelled
by scp and was destroyed with `shred` after the import; it did not pass
through a chat channel, which is what was being undone.

`trixie` is published and signed for the first time. It verifies against the
published keyring with gpg (`VALIDSIG 03041024...`) and with sqv, which is
what the Proxmox index check and our own tooling use. `bin/publish` refused
the first attempt because the keyring file still lacked the new subkey, which
is the check earning its place: a signature clients cannot verify is worse
than none.

The public key is updated in the handbook, the archive repository and the
`keel-archive-keyring` package (0.1.1). The `common` fork's `keys/` directory
still holds only TurnKey's keys.

Operational consequence, decided 2026-09-27: the agent's cache lifetime is
eight hours (`default-cache-ttl` and `max-cache-ttl` 28800 in
`/root/.gnupg/gpg-agent.conf`, mode 600), chosen by the maintainer after three
passphrase moments were spent on releases that expired mid-flight. The cost,
accepted knowingly: during that window anything running as root on the build
host can sign without being asked, and the window resets only on reboot.

Worth revisiting, because the reason has weakened. `keel-release` became
resumable the same day and signing is now a separate phase, `--sign-only`,
measured at 35 seconds for all five appliances. A typed passphrase therefore
has to survive seconds rather than twenty minutes, which the default ten
minute cache covers comfortably. Reverting is `rm -f
/root/.gnupg/gpg-agent.conf && gpgconf --reload gpg-agent`. Kept at eight
hours for now by the maintainer's decision.

The original statement of the problem: the subkey is passphrase protected and
the gpg agent caches the passphrase for ten minutes after the maintainer
types it at a terminal, so a publication that signs more than ten minutes
later fails with `Inappropriate ioctl for device`. Three ways out, the choice
being the maintainer's: prime the agent immediately before each signed
publication; raise the agent's cache lifetime, which leaves the passphrase in
memory until reboot and lets anything running as root on that host sign; or
strip the passphrase from the copy on the build host, which makes publication
fully unattended and puts an unprotected key into every snapshot of that
machine.

### The rotation was questioned (2026-09-27, superseded by the section above)

The maintainer does not agree that the subkey needs rotating and asked for the
reasoning to be checked against the session that provisioned the hosts. This
note records the question as open rather than settled, so nobody acts on the
paragraph above as if it were decided.

The case for rotating, as it stands here:

- the exposure is not hypothetical. Secret key material that has been through
  a chat window exists in that channel's history, its logs and its backups,
  which is a different custody from "offline, on the maintainer's machine".
  The passphrase raises the cost of using that copy; it does not remove it;
- it is cheap today and expensive later. Nothing has been signed, the public
  key is not published, and the archive serves only the unsigned staging
  distribution, so a replacement costs one subkey and one scp. After the
  first signed publication it costs a revocation, a republished key and an
  explanation to everyone who already trusted it;
- the primary key never left its offline custody, so only the subkey is in
  question and the project's identity does not change.

The case against is the maintainer's to make, and it is a legitimate one: if
the channel and its history are considered private enough, the exposure can be
accepted. If that is the conclusion, this note should say so, with the reason,
because as written the document tells a future reader to revoke.

Until it is settled, nothing is signed, which is also what the release tooling
enforces: `bin/publish` refuses the signed distribution while no secret
signing subkey is present, and `keel-release` says in its log that nothing
will be signed.

## Hosting names decided (2026-09-26): the TurnKey Linux pattern

The maintainer chose the upstream naming, which every TurnKey user already
knows, and provisioned the zone accordingly:

| Name | Serves | TurnKey equivalent |
| --- | --- | --- |
| archive.keellinux.org | APT archive (signed `trixie`) | archive.turnkeylinux.org |
| mirror.keellinux.org | images: layers, LXC templates, ISOs | mirror.turnkeylinux.org |
| releases.keellinux.org | Proxmox `pve/aplinfo.dat` and release metadata (hashes, buildenv, manifests) | releases.turnkeylinux.org |
| keellinux.org and www.keellinux.org | institutional site, same content as keel-linux.github.io | www.turnkeylinux.org |
| forum.keellinux.org | the project forum (NodeBB appliance), when ready | the forum on www.turnkeylinux.org |

All on the public services VM (2804:710:d0:5::13, plus two public IPv4
addresses), not on GitHub Pages: the earlier split (APT on Pages) is
superseded, since the VM exists and has IPv6 and IPv4. GitHub Pages remains a
mirror of the institutional site only. apt.keellinux.org is not used; the apt
tooling's CNAME and README were changed to archive.keellinux.org. In the
Proxmox index the `Location` URLs point at mirror.keellinux.org and the index
itself lives under releases.keellinux.org/pve/, exactly as upstream does.
