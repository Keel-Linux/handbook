# 0055: One key per purpose, signed on the build host

Date: 2026-10-14
Status: **decided 2026-10-14 by the maintainer** ("Podemos adotar esse
método do TurnKey Linux? ... Sim"). The coordinator designed the details
under the maintainer's delegation of design calls. This note supersedes
the "keep the release key human" paragraph of 0005 and the words "Not the
release key" in 0016's "Which key signs a channel". It extends 0011
(the staging key).

## The problem

A signed release needs the maintainer. The release signing subkey on the
build host has a passphrase. The gpg agent keeps the passphrase for 240
hours (0005), and after that time the next signature waits for a person.
The cache ran out on 2026-10-12, and the step-12 pre-releases went out
unsigned. The subkey itself stays valid until 2028-09-26.

The maintainer wants releases signed without them each time. The model is
TurnKey Linux's `turnkey-keys` repository: one public key for each suite
and purpose (main, security, testing, images), and the build
infrastructure signs with them unattended.

## The decision

1. **Four signing roles, each with its own certificate.** `signed-by`
   trusts every subkey of a certificate, so subkeys of one certificate
   cannot keep the roles apart. Each role has its own primary key:

   | Role | Signs | Certificate |
   |---|---|---|
   | **main** | the `Release` file of the `trixie` suite | the existing `AD0964BE3F09DED469A3B6B2148E951314703180` |
   | **security** | the `Release` file of a new `trixie-security` suite | new |
   | **testing** | the `Release` file of a new `trixie-testing` suite, which an appliance can opt in to | new |
   | **images** | the layer `.hash` files, the release `MANIFEST`, the Proxmox `aplinfo.dat.asc` | new |

   main keeps the existing certificate, so installed appliances need no
   keyring change.

2. **One keyring file for each role.** Each suite's `Signed-By` names the
   file of its own role, and no other:
   `/usr/share/keyrings/keel-archive-keyring.gpg` (main, the name stays),
   `keel-security-keyring.gpg`, `keel-testing-keyring.gpg`,
   `keel-images-keyring.gpg`. Do not merge them into one keyring.
   TurnKey 19.x merges its three apt keys into one
   `tkl-archive-keyring.gpg` (`common/conf/bootstrap_apt`), so on TurnKey
   any of the keys can sign any suite. Keel does not copy that.

3. **The primary keys stay offline.** Each primary key only certifies
   (capability C) and has no expiry, as in 0005. The maintainer keeps them.
   They issue and revoke subkeys, and that is all they do.

4. **The signing subkeys are on the build host, with no passphrase.**
   Each role has one signing subkey (capability S). The subkey is on the
   build host only, in root's keyring, and its copy there has no passphrase.
   `bt-*`, `reprepro` and `keel-release` sign with it, and nobody types
   anything. 0005 already said that a long cache is "indistinguishable
   from having no passphrase", and that it is "more honest to remove the
   passphrase and record that decision". This note takes that option.

5. **The subkeys never go on a CI runner.** They do not go on the
   Keel-Linux-Runner VM (`keel-lxc-2-*`), into GitHub secrets, or into any
   CI job. Pull request code runs on the runners.

6. **The expiry is 3 years, and an alert comes 90 days before it.** A
   subkey that never expires stays valid for ever after a leak. The 20
   years of TurnKey's keys are too long for that reason. Three years with
   an alert give one rotation by the maintainer in each 3 years, and no
   routine work. The alert is a check in the publisher. It fails the
   publish, with the date, when a subkey has less than 90 days left.

7. **The public keys are in one repository, `Keel-Linux/keel-keys`.**
   It holds the four `.asc` files and builds the `keel-archive-keyring`
   package. The package installs the four keyring files. A rotation is a
   commit and a new package version. The repository holds public keys
   only. The secret keys, the passphrases and the procedure that handles
   them are discussed with the maintainer in chat only. They are not
   written in this repository, in an issue or in a note.

8. **The staging key and the channel key do not change.** The
   `trixie-staging` key (0011) means only that the build host produced the
   bits. No appliance reads it, and it is not in `keel-archive-keyring`.
   The channel key of 0016 (`KEEL_CHANNEL_KEY`) stays the staging key.
   **testing** is a different thing: a suite that an appliance can opt in
   to, made of packages that the publisher promotes from staging.

## Why a security suite

An appliance installs updates every day by itself. The `cron-apt` action
of `common/conf/turnkey.d/cronapt` runs `dist-upgrade` with only
`/etc/apt/sources.list.d/security.sources.sources`. Today that file names
Debian's security suite and no Keel suite. So a fix to a Keel package
reaches an appliance only when somebody upgrades it by hand. A
`trixie-security` suite in that file, with its own `Signed-By`, makes a
Keel fix arrive the same way a Debian fix arrives.

## The cost, accepted

Root on the build host can sign everything that an appliance installs and
verifies, with nobody asked. A snapshot or a backup of the build host can
do the same. Before this note, that was true only during the 240 hour
cache (0005). After this note, it is always true. The maintainer accepts
this cost. The limits that stay:

- a leak of one subkey is a leak of one role, not of four;
- the offline primary key revokes a leaked subkey, and a new
  `keel-archive-keyring` version carries the revocation;
- the subkeys are not on the CI runners, where outside code runs;
- a subkey expires in 3 years.

## Order of work

1. This note.
2. **main**: the maintainer removes the passphrase from the build host's
   copy of the existing subkey (valid until 2028-09-26), in chat. This
   unblocks signed releases, and it needs no new key. The subkey is
   rotated to the 3 year rule when it is next due.
3. `Keel-Linux/keel-keys` with the public key of main, and the
   `keel-archive-keyring` package built from it.
4. **images**: the maintainer makes the certificate and its subkey. Every
   verifier must trust the new key **before** anything is signed with it
   alone: `keel pull` and `keel verify` (the layer `.hash` files and the
   `MANIFEST`), and Proxmox (`aplinfo.dat.asc`). Until then the publisher
   signs with main and images both. Signatures that main already made stay
   valid.
5. **security**: the certificate, the `trixie-security` suite in
   `Keel-Linux/apt`, and the suite in `security.sources.sources` in
   `Keel-Linux/common`.
6. **testing**: the certificate and the `trixie-testing` suite, opt-in.
7. The expiry alert in the publisher.
