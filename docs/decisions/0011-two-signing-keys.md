# 0011: Two signing keys, and what each is allowed to say

Status: **in force since 2026-09-27, written down 2026-09-28.** The separation
was implemented and has been cited from code for a day before this note
existed; what follows records what is running, not a proposal. Extends 0005,
which settles the shape and custody of the release key. Relied on by 0016,
which gives the channel pointer to the online key.

## What is in force

Two distributions in the archive, signed by different keys, measured in
`conf/distributions` of `Keel-Linux/apt`:

| Distribution | `SignWith` | Where the secret lives |
|--------------|-----------|------------------------|
| `trixie` | `AD0964BE3F09DED469A3B6B2148E951314703180` | offline primary; a signing subkey is exported to the build host and is passphrase protected |
| `trixie-staging` | `33516A960EC47DC1DB403ECC9DA966DE8C77FDE9` | unprotected on the build host |

`keys/keel-archive-keyring.asc` and `keys/keel-staging-keyring.asc` are the
public halves, published separately, and an apt source names one of them in
`Signed-By` so that a machine configured for one distribution cannot verify
the other.

## Why two

`trixie` is what an installed appliance reads. Its signature has to mean that a
person decided these bits should reach a machine, so the key that makes it
requires a passphrase typed at a terminal, and the primary that certifies it
never touches the build host at all.

A nightly build cannot ask anyone for a passphrase. So `trixie-staging` is
signed by a key that lives unprotected beside the thing it signs.

That key adds no trust that does not already exist: the build host can already
build whatever it likes, so a key that only signs what that host produced tells
a verifier nothing it did not already have to assume. What matters is the
consequence in the other direction, and it is the whole point of the
separation: **the unprotected key can never sign what an installed appliance
reads.** Compromise of the build host costs the staging distribution and
nothing else.

## What each key is allowed to say

- The **release key** says: a person stood behind these bits.
- The **staging key** says: this build host produced these bits.

Anything that must carry the first meaning is signed with the release key, at a
terminal, by the maintainer. Anything a machine may assert unattended is signed
with the staging key, and must be something the build host could have claimed
anyway.

0016 applies that test to the channel pointer and concludes the online key may
sign it, because every revision it can name was already staged and signed with
the release key, and every manifest it names is pinned by digest inside the
signature. The pointer therefore only selects among things a person already
approved. That reasoning is only available because this note draws the line
where it does.

## The escape hatch, and its limit

`publish --unsigned-staging` writes the staging distribution with every
`SignWith` stripped, for a build host that has neither key. It exists so that a
machine can be brought up before it holds any secret. It is never a fallback
for `trixie`: `publish` exits 4 when no usable secret signing subkey for the
release `SignWith` is in the keyring, rather than publishing unsigned.

## Why this note was late, and what that cost

The separation was implemented first and cited from four places in
`Keel-Linux/apt` (`conf/distributions`, `lib/common.sh`, `lib/publish.sh`
twice) while the note did not exist. The number was skipped when 0012 was
written the same day.

That cost something concrete rather than being untidy. On 2026-09-28 the gap
was investigated, found to contain no deleted file, and recorded as a
deliberate gap in a placeholder note, on the reasoning that nothing referenced
an 0011. That reasoning was wrong: it checked this repository and not the one
doing the citing. The placeholder is replaced by this note.

The rule that follows: a decision cited from code exists, whether or not
anybody wrote it down, and a dangling citation is evidence that a note is
missing rather than that a number is free.
