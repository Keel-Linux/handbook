# 0008: What kind of fork Keel is

Date: 2026-09-26
Status: proposed by the agent, for the maintainer to confirm or amend

## The question

Asked from outside the project: is Keel a full fork of the build system, or
only an appliance layer over a Debian base of its own? And, by the project's
own rule (brief section 10), where is the three-part justification for
forking instead of pushing upstream, given ten years of contribution there
and the intermediate path of a friendly downstream layer?

## What was built, as evidence

- Every repository of the build chain is forked with full history and the
  upstream remote kept: fab, common, buildtasks, tkldev, cdroots, bootstrap,
  inithooks, confconsole, webmin, turnkey-chroot, plus the appliances. The
  Debian base is Debian 13 unchanged; there is no Keel base of its own.
- The M0 gate proved on 2026-09-26 that unmodified 19.0 built from the
  organization is package-for-package identical to the upstream build.
- Every change made so far is additive and offerable upstream: seven bug
  fixes (issues drafted for the upstream tracker), SOURCE_DATE_EPOCH honoured
  only when set, IPv6 preseed keys with the IPv4 path byte-identical, a
  declarative reader that translates into the variables upstream hooks already
  read, a static IPv6 writer beside the IPv4 one. Interactive mode is intact.
- What is not offerable upstream as is: the naming (`keel-` prefix, own
  keyring and APT origin), the release cadence, the coverage gate, the
  honest catalog tiers, and the distribution model (layers, manifests, pull
  and assemble), which upstream has not asked for.

## Answer

Keel is a **full fork of the chain in custody, run as a downstream-first
project**: the code is kept upstream-compatible on purpose, so that every
improvement can be offered back, and the fork carries what upstream does not
carry today: cadence, tests as a gate, IPv6 by default, layered
distribution, and a maintained tier that is honest about what it maintains.
It is not a new base and it is not an appliance layer only, because the
properties the brief asks for (reproducible layers, declarative first boot,
sovereign network identity) live in fab, common, inithooks and confconsole,
not in the appliance recipes.

## Three parts

1. Why upstream as it is does not meet the need: one maintainer, releases
   months apart, 19.0 shipped without a trixie bootstrap and with a broken
   verify path in tkldev-setup, no test suite in the core repositories, IPv6
   treated as optional, no container-specific build path, and a Hub
   dependency the project cannot host. These are facts recorded in
   ../TKL/plan/00 and 02, not opinions.
2. Whether upstream could be made to meet it: partly, and that is being
   tried. The seven fixes are meant for upstream; the email to its maintainer
   went out on 2026-09-22 and the answer is pending. What cannot be obtained
   by pull request is the cadence and the standards (a 90 percent gate on a
   one-person project is not a patch), and the distribution model is a
   change of direction upstream has not requested.
3. Why the fork is better than only pushing upstream: it lets the
   improvements ship to the maintainer's own fleet on a known schedule while
   the upstream conversation happens, keeps every patch small and offerable
   because compatibility is a standing rule, and puts the cost of the fork
   where it is honest: the tier-1 list is the maintained set; everything else
   is labeled inherited.

## What would change the answer

If upstream accepts the fixes and the direction (declarative first boot,
IPv6 first, layered LXC builds), the right move is to shrink the fork toward
the downstream layer: keep the naming, the gate and the cadence, drop the
divergence. The structure chosen (upstream remote, additive changes) makes
that shrink cheap. That is the criterion to revisit this note after the
maintainer's reply.

## The name

The collision with keel.sh is recorded in 0001; the maintainer chose
KeelLinux, whose organization, domains and package names were free.
Nothing has been announced; changing the name before the announcement costs
a rename of repositories and packages that GitHub redirects.
