# 0009: Four corrections to the spec vocabulary

Date: 2026-09-26
Status: implemented in keel-linux/keel (PRs 13, 14, 15, 16), proved on the
`forum2` bench

## Why this note exists

The first boot of a real appliance from a declarative description
(docs/forum-build-2026-09-26.md) ended with `keel diff --spec
/etc/keel/instance.yaml` reporting 5 same, 4 drift, 1 unknown, 6 not
declared, 3 not compared, exit 14. Every one of the five findings was
correct about the file and wrong about the machine: the appliance was doing
what the description asked, and the vocabulary could not say so. A drift
report that cries wolf is worse than no drift report, because an operator
learns to ignore it, so these are defects in the contract the project rests
on (brief section 4, principle 1) and not cosmetic.

Each one is written with the three part justification of brief section 10.

## 1. `network.ipv6.method`: inspect learns SLAAC from DHCPv6

The spec declared `auto`, inspect reported `dhcp`, because ifupdown has one
method for both and `01ipconfig` writes `iface eth0 inet6 dhcp` either way.

1. Why the previous approach does not work: inspect read the stanza method
   straight back as the spec method, so every SLAAC appliance drifted on the
   field that IPv6 first (brief section 4, principle 5) makes load bearing.
2. Whether it can be made to work: not from the file, which is genuinely
   ambiguous. From the machine, yes: a DHCPv6 client writes its lease down
   (`/var/lib/dhcpcd/<name>.lease6`, `/var/lib/dhcp/dhclient6*.leases`), and
   the kernel marks an address whose prefix came from a router
   advertisement `mngtmpaddr` in `ip -6 addr`.
3. Why the new approach is better than dropping one term: `auto` and `dhcp`
   are different deployments and an operator declares one of them on
   purpose. Collapsing them would make a stateful DHCPv6 network
   undeclarable. Reading them off the machine keeps both terms and costs one
   command and one glob. Where there is no evidence at all, the field is
   reported as not inferred, naming what was checked, because a guess is
   what produced the drift.

## 2. `tls.acme`: diff does not compare what the spec turns off

The spec declared `enabled: false` with `challenge` and `domains` below it,
and diff called both drift.

1. Why the previous approach does not work: the settings of a disabled
   feature describe nothing the machine is supposed to carry, so comparing
   them reports drift on a correct spec.
2. Whether it can be made to work: the alternative is a schema that refuses
   `domains` while ACME is disabled. It cannot be made to work without
   making the spec dishonest in the other direction: the operator could not
   prepare a certificate configuration before turning it on, and turning it
   off would mean deleting the domains.
3. Why the new approach is better: preparing the configuration and enabling
   it are two changes that should be reviewable apart. The settings stay in
   the file, diff compares the switch and nothing else it governs, so the
   day the name gets a DNS record the change is one word. The switch itself
   is still compared, so ACME running behind the spec's back is still drift.
   The rule is a table (`DISABLED_FEATURES`), not a special case for ACME.

## 3. `security.updates` becomes `security.updates_at_first_boot`

The spec said `skip`, inspect reported `force`, and the field name was the
defect.

1. Why the previous approach does not work: `SEC_UPDATES` is read once, by
   `95secupdates`, during the first boot. `force` installs the pending
   security updates then and there, `skip` installs nothing, unset makes the
   hook ask. It never had anything to say about whether the appliance keeps
   its updates current, which is cron-apt, shipped configured by the image
   either way. Read as a policy, the name made inspect read the cron-apt
   install action that every appliance carries and answer `force`.
2. Whether it can be made to work: no. No wording of the inference can fix a
   name that promises to control something the field does not control.
3. Why the new approach is better: the name now says what the value does;
   the semantics are documented in docs/spec.md; and `keel diff` does not
   compare the field at all, because the machine keeps no record of which
   value was used, which is the same reason `app` and `preseed` are not
   compared. inspect still writes a value, from the conf while it is there
   and otherwise from the appliance's update posture, because a spec without
   the field cannot boot headless, and the report says which of the two it
   is. The old name still loads with a warning naming the new one
   (`keel.spec.compat`), so specs already on disk keep working.

## 4. `instance.fqdn`: the apply phase writes the `/etc/hosts` entry

Reported unknown, because `/etc/hosts` carried no fully qualified name.

1. Why the previous approach does not work: nothing wrote the entry.
   `09hostname` writes `/etc/hostname` and seds the old name through a list
   of files, leaving `127.0.1.1 <short name>`; `hostname -f` then answers
   the short name. The declaration was real and the machine did not carry
   it, so the gap is in apply, not in inspect.
2. Whether it can be made to work in the hook: it could, but the hook is a
   shell script in the inithooks fork, and brief section 6 puts the logic in
   the library that both confconsole and the CLI call. `apply --system`
   already converges `users` and `locale` the same way.
3. Why the new approach is better: one code path, unit tested against
   scratch trees, idempotent, and it asks the very reader inspect uses
   (`fqdn_in_hosts`) whether the entry is there, so what apply writes is
   what inspect reads back. The address is the declared static IPv6 address
   when there is one (the Debian convention for a permanent address) and
   `127.0.1.1` otherwise, because a SLAAC or DHCPv6 address is a lease and
   must never be frozen into a file.

## Proved on the machine

`forum2` (2804:710:d0:5:deea:cbca:f115:6172), the container that produced
the findings, with the library of the four merged pull requests installed:

| | same | drift | unknown | not declared | not compared | exit |
| --- | --- | --- | --- | --- | --- | --- |
| before | 5 | 4 | 1 | 6 | 3 | 14 |
| after the library, before apply | 6 | 0 | 1 | 5 | 6 | 13 |
| after `keel spec apply --system` | 7 | 0 | 0 | 5 | 6 | 0 |

The interface count falls by one because `eth1`, which has no address and no
lease, is now reported as not inferred instead of as `dhcp`; that is the
third case of finding 1 working as designed.

## What this leaves for other repositories

- The first boot chain does not call `keel spec apply --system`, so the
  `/etc/hosts` entry is not written at first boot yet. The hook that calls
  it must run after `09hostname`, which rewrites `/etc/hosts` with a sed
  over the old name. That is an inithooks change.
- `inithooks/libinithooks/declarative.py` is a second implementation of the
  spec vocabulary. It does not know about the renamed field, the disabled
  feature rule or the IPv6 evidence. Two implementations of one contract
  will drift; the hook should call the library (brief section 6, one code
  path).
