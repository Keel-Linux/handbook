# 0093: Keel ships one even Odoo version for each Debian stable base

Date: 2026-11-20
Status: **accepted 2026-11-20.** The maintainer decided the rule. On
2026-11-20 the maintainer answered "Odoo em versão par sim!" to the
question below. Nothing in the image changes now. The image already
follows the rule.

## What was asked

On 2026-11-16 the maintainer asked: "o ideal são versões pares do Odoo
nos Debian LTS não?" (the best choice is the even Odoo versions on the
Debian stable releases, true?).

The coordinator answered with the facts below. Then the coordinator
asked if the project records this rule in a decision note: "Odoo par por
base Debian, troca para a próxima versão par quando o Odoo encerrar o
suporte" (an even Odoo for each Debian base, and a change to the next
even version when Odoo ends the support). The maintainer said yes on
2026-11-20.

## What was found

- Odoo has no LTS versions. Odoo makes one major version each year, in
  September or October. Odoo supports the 3 most recent major versions,
  for approximately 3 years each.
- Debian freezes a new stable release at the start of an odd year. Thus
  the last Odoo version before the freeze is the version of the even
  year before.

| Debian stable | Odoo version ready before the freeze | In Debian |
| --- | --- | --- |
| bullseye (2021) | 14 (2020) | yes, 14.0 |
| bookworm (2023) | 16 (2022) | no |
| trixie (2025) | 18 (2024) | no |
| forky (approximately 2027) | 20 (approximately 2026) | not known |

- trixie has no `odoo` package. sid has Odoo 19.0.
- On 2026-11-20 the upstream repository `odoo/odoo` has the branches
  `19.0` and `20.0`.
- `keel-odoo` installs Odoo 18.0 from git, not from a package. The
  source is the snapshot `snapshot-18.0-1f2b50ade7a1` of
  `Keel-Linux/odoo`, at a pinned commit, in `/opt/odoo/18.0`
  (`conf.d/main`). Thus the image already follows the rule: Odoo 18 on
  trixie.
- The "19.0" in the image name `keel-odoo-19.0` is the version of the
  Keel platform. It is not the Odoo version.
- Odoo 18 loses the support of Odoo when Odoo 21 comes, approximately in
  October 2027. trixie has security support until 2028 and Debian LTS
  until 2030. Thus Odoo 18 ends before trixie ends.

The dates of Odoo 21 and of forky are estimates. They come from the
pattern of the earlier years.

## Why (brief section 10)

1. **Why a rule is necessary.** Odoo makes a new major version each
   year, but the Debian stable base stays for years. Without a rule,
   each image round can choose a different Odoo version.
2. **Whether it can be made to work.** It can. The image already ships
   Odoo 18 on trixie. The Odoo version is one pin in `conf.d/main` of
   `keel-odoo`.
3. **Why this is better.** The even version is the last Odoo version
   before the Debian freeze. Thus each Debian stable base gets one Odoo
   version, and the image keeps it until Odoo ends its support.

## Decision

1. **One even Odoo version for each Debian stable base.** The Odoo
   version of trixie is 18. The Odoo version of forky is 20.
2. **The change goes to the next even version when Odoo ends the
   support.** If Odoo ends the support of the even version before the
   Debian stable base ends, Keel changes to the next even version on the
   same base. On trixie, Keel changes from Odoo 18 to Odoo 20 when Odoo
   ends the support of Odoo 18, approximately in October 2027.
3. **Keel does not ship an odd Odoo version.** Odoo 19 and Odoo 21 are
   not Odoo versions of a Keel image.
4. The Odoo version moves through the Keel channel, as every
   application does (0083). Each change passes commissioning (0075).

## What it means for work

Nothing changes now. `keel-odoo` keeps Odoo 18.0. The change to Odoo 20
on trixie is work for a later image round.

## Open points

1. **The date of the change from Odoo 18 to Odoo 20 on trixie.** It
   depends on the real date of Odoo 21.
2. **How an installed node moves its database from Odoo 18 to Odoo 20.**
   This is a migration of data across two major versions. It was not
   discussed.
3. **The real dates of Odoo 21 and of forky.** The dates in this note
   are estimates.

## Related notes

It applies 0075 and 0083.
