#!/bin/bash
set -euo pipefail

usage() {
    cat >&2 << 'USAGE'
Syntax: keel-keygen.sh [--rsa] "<identity email>"

Generates the Keel Linux archive signing key pair on THIS machine, which must
be offline for the duration:

  - primary key, certify only, no expiry (Ed25519, or RSA 4096 with --rsa)
  - signing subkey, 2 year expiry
  - revocation certificate for the primary key

Writes everything to ./keel-key-<date>/ and prints what goes where.
Run as a normal user, not root. Requires gpg (2.2 or newer) and optionally
sqv for the verification test.
USAGE
    exit 1
}

algo=ed25519
if [ "${1:-}" = "--rsa" ]; then
    algo=rsa4096
    shift
fi
[ $# -eq 1 ] || usage
email="$1"

if [ -z "${KEEL_ALLOW_ONLINE:-}" ] && ip -6 route show default 2>/dev/null | grep -q . ; then
    echo "This machine has a default route. Disconnect it first, or set KEEL_ALLOW_ONLINE=1 if you accept the risk." >&2
    exit 1
fi
if [ -z "${KEEL_ALLOW_ONLINE:-}" ] && ip -4 route show default 2>/dev/null | grep -q . ; then
    echo "This machine has a default route. Disconnect it first, or set KEEL_ALLOW_ONLINE=1 if you accept the risk." >&2
    exit 1
fi

out="keel-key-$(date -u +%Y%m%d)"
mkdir -p "$out"
chmod 700 "$out"
export GNUPGHOME="$out/gnupg"
mkdir -p "$GNUPGHOME"
chmod 700 "$GNUPGHOME"

if [ "$algo" = ed25519 ]; then
    keytype="Key-Type: eddsa
Key-Curve: ed25519"
    subkey_algo=ed25519
else
    keytype="Key-Type: RSA
Key-Length: 4096"
    subkey_algo=rsa4096
fi

read -r -s -p "Passphrase for the primary key (kept offline): " pass1; echo
read -r -s -p "Repeat: " pass2; echo
[ "$pass1" = "$pass2" ] || { echo "passphrases differ" >&2; exit 1; }

cat > "$out/primary.conf" << CONF
%echo generating the primary key
$keytype
Key-Usage: cert
Name-Real: Keel Linux Archive Signing Key
Name-Email: $email
Expire-Date: 0
Passphrase: $pass1
%commit
CONF
gpg --batch --generate-key "$out/primary.conf"
shred -u "$out/primary.conf" 2>/dev/null || rm -f "$out/primary.conf"

fpr=$(gpg --list-keys --with-colons | awk -F: '$1=="fpr"{print $10; exit}')
echo "primary fingerprint: $fpr" | tee "$out/FINGERPRINT"

printf '%s' "$pass1" | gpg --batch --pinentry-mode loopback --passphrase-fd 0 \
    --quick-add-key "$fpr" "$subkey_algo" sign 2y

# gpg 2.1 and newer write a revocation certificate at key creation
cp "$GNUPGHOME/openpgp-revocs.d/$fpr.rev" "$out/revoke-primary.asc"

gpg --armor --export "$fpr" > "$out/keel-archive-keyring.asc"
printf '%s' "$pass1" | gpg --batch --pinentry-mode loopback --passphrase-fd 0 \
    --armor --export-secret-keys "$fpr" > "$out/primary-secret.asc"
printf '%s' "$pass1" | gpg --batch --pinentry-mode loopback --passphrase-fd 0 \
    --armor --export-secret-subkeys "$fpr" > "$out/signing-subkey-secret.asc"

echo test > "$out/t"
printf '%s' "$pass1" | gpg --batch --pinentry-mode loopback --passphrase-fd 0 \
    --detach-sign --armor "$out/t"
gpg --status-fd 1 --verify "$out/t.asc" "$out/t" 2>/dev/null | grep -q 'GOODSIG' && echo "gpg verification: OK"
if command -v sqv >/dev/null; then
    sqv --keyring "$out/keel-archive-keyring.asc" "$out/t.asc" "$out/t" && echo "sqv verification: OK"
fi
rm -f "$out/t" "$out/t.asc"
unset pass1 pass2
chmod 600 "$out"/*.asc "$out/FINGERPRINT"

gpg --list-keys --with-subkey-fingerprint "$fpr"
cat << REPORT

Files in $out/:
  keel-archive-keyring.asc     PUBLIC. Goes to common/keys/, the keyring package and the site.
  signing-subkey-secret.asc    SECRET. Only copy that goes to the build host (import as root there).
  primary-secret.asc           SECRET. Offline only: encrypted USB plus paper copy. Never on a server.
  revoke-primary.asc           Offline, with the primary. Publishing it revokes everything.
  FINGERPRINT                  Publish alongside the public key.
  gnupg/                       The keyring used to generate; delete after the copies are safe.
REPORT
