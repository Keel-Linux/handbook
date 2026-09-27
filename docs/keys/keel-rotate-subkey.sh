#!/bin/bash
set -euo pipefail

usage() {
    cat >&2 << 'USAGE'
Syntax: keel-rotate-subkey.sh <primary fingerprint> <subkey fingerprint to revoke>

Replaces the signing subkey of the Keel Linux archive key on THIS machine,
which must be offline for the duration, and which must already hold the
secret of the primary key (import primary-secret.asc first, or run this with
GNUPGHOME pointing at the directory keel-keygen.sh produced).

What it does, in this order:

  1. revokes the named subkey, reason "key has been compromised";
  2. adds a new signing subkey, Ed25519, two year expiry;
  3. exports the public key, which now carries both the revocation and the
     new subkey, and the secret of the NEW subkey alone;
  4. proves the result: signs a file with the new subkey, verifies it against
     the exported public key, and refuses to finish if the old subkey is not
     marked revoked or the new one does not sign.

Writes to ./keel-rotation-<date>/ and prints what goes where. No secret is
printed. Run as a normal user, not root.
USAGE
    exit 1
}

[ $# -eq 2 ] || usage
primary="${1//[[:space:]]/}"
old="${2//[[:space:]]/}"

if [ -z "${KEEL_ALLOW_ONLINE:-}" ]; then
    for family in -4 -6; do
        if ip "$family" route show default 2>/dev/null | grep -q .; then
            echo "This machine has a default route. Disconnect it first, or set KEEL_ALLOW_ONLINE=1 if you accept the risk." >&2
            exit 1
        fi
    done
fi

command -v gpg >/dev/null || { echo "gpg not found" >&2; exit 1; }

gpg --list-secret-keys "$primary" >/dev/null 2>&1 || {
    echo "no secret key for $primary in ${GNUPGHOME:-$HOME/.gnupg}" >&2
    echo "import primary-secret.asc first, or set GNUPGHOME to the offline directory" >&2
    exit 1
}

# The index gpg --edit-key gives this subkey: the subkeys of the primary in
# listing order, counted from 1. Reading it rather than assuming it is what
# makes the revocation hit the intended key.
index=$(gpg --with-colons --list-keys "$primary" | awk -F: -v want="$old" '
    $1 == "sub" { n++ }
    $1 == "fpr" && n > 0 && $10 == want { print n; exit }')
[ -n "$index" ] || { echo "$old is not a subkey of $primary" >&2; exit 1; }

out="keel-rotation-$(date -u +%Y%m%d)"
mkdir -p "$out"
chmod 700 "$out"

read -r -s -p "Passphrase of the primary key: " pass; echo
ask() { printf '%s' "$pass" | gpg --batch --pinentry-mode loopback --passphrase-fd 0 "$@"; }

echo "revoking subkey $old (index $index)"
printf 'key %s\nrevkey\ny\n1\nSecret transmitted through a chat channel on 2026-09-24; never used to sign.\n\ny\nsave\n' \
    "$index" \
    | gpg --batch --pinentry-mode loopback --passphrase "$pass" \
        --command-fd 0 --status-fd 2 --edit-key "$primary" >/dev/null 2>"$out/revoke.log" || {
            echo "revocation failed, see $out/revoke.log" >&2; exit 1; }

echo "adding the new signing subkey"
ask --quick-add-key "$primary" ed25519 sign 2y

new=$(gpg --with-colons --list-keys "$primary" | awk -F: -v old="$old" '
    $1 == "sub" { revoked = ($2 == "r"); usable = ($12 ~ /s/) }
    $1 == "fpr" && usable && !revoked && $10 != old { fpr = $10 }
    END { print fpr }')
[ -n "$new" ] && [ "$new" != "$old" ] || { echo "cannot find the new subkey" >&2; exit 1; }
echo "new signing subkey: $new"

gpg --armor --export "$primary" > "$out/keel-archive-keyring.asc"
ask --armor --export-secret-subkeys "$new!" > "$out/signing-subkey-secret.asc"
printf '%s\n' "$primary" > "$out/FINGERPRINT"
printf '%s\n' "$new" > "$out/SUBKEY-FINGERPRINT"

# Proof, against the exported public key rather than the local keyring.
echo rotation-test > "$out/t"
ask --detach-sign --armor --local-user "$new!" "$out/t"
verify_home=$(mktemp -d)
gpg --homedir "$verify_home" --batch --quiet --import "$out/keel-archive-keyring.asc"
gpg --homedir "$verify_home" --batch --status-fd 1 --verify "$out/t.asc" "$out/t" 2>/dev/null \
    | grep -q "VALIDSIG $new" || { echo "the new subkey does not verify" >&2; exit 1; }
gpg --homedir "$verify_home" --with-colons --list-keys "$primary" \
    | awk -F: -v old="$old" '$1=="sub"{r=($2=="r")} $1=="fpr" && $10==old {exit r?0:1}' \
    || { echo "the old subkey is not revoked in the exported key" >&2; exit 1; }
rm -rf "$verify_home"
rm -f "$out/t" "$out/t.asc"
unset pass
chmod 600 "$out"/*.asc "$out/FINGERPRINT" "$out/SUBKEY-FINGERPRINT"

gpg --list-keys --with-subkey-fingerprint "$primary"
cat << REPORT

Verified: the new subkey signs and verifies against the exported public key,
and the old subkey is marked revoked in it.

Files in $out/:
  keel-archive-keyring.asc     PUBLIC. Replaces the published keyring: it now
                               carries the revocation and the new subkey. Copy
                               it to the build host as well, so the archive,
                               the keyring package and the site can be updated
                               from it without it passing through a chat:
                                 scp $out/keel-archive-keyring.asc root@<build host>:/root/
  signing-subkey-secret.asc    SECRET. The only copy that leaves this machine,
                               and only by scp to the build host:
                                 scp $out/signing-subkey-secret.asc root@<build host>:/root/
                               then, on the build host:
                                 gpg --import /root/signing-subkey-secret.asc
                                 shred -u /root/signing-subkey-secret.asc
  FINGERPRINT                  The primary, unchanged: it never left this machine.
  SUBKEY-FINGERPRINT           The new signing subkey, to record in the decision note.

Do not send either .asc through a chat channel. That is what is being undone
here.
REPORT
