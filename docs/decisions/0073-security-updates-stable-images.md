# 0073: Security updates for stable images

Date: 2026-10-30
Status: **decided by the coordinator under the maintainer's delegation,
2026-10-30**. Evidence: the stable-1 security audit of 2026-10-30 (below)
and the first boot measurement on CT 9323.

## What was found

The stable-1 pool (`conf/pools/stable-1/files` in `Keel-Linux/apt`, 622
members) was compared with Debian trixie, trixie-updates and
trixie-security on 2026-10-30:

- 26 packages from 8 Debian security advisories are older than Debian's:
  linux (DSA-6568), ca-certificates (DSA-6572), php8.4 (DSA-6574), nginx
  (DSA-6575), bind9 (DSA-6576), brotli (DSA-6582), libheif (DSA-6583) and
  imagemagick (DSA-6593). tzdata is older than trixie-updates.
- Seven of the eight advisories are older than the freeze (2026-10-26).
  The pool was behind on the day it froze.

A published core 19.0-11 image (CT 9322 on BR1) showed how an installed
appliance gets fixes:

- cron-apt runs every day. Its install action reads only
  `security.sources`: Debian trixie-security and Keel trixie-security. A
  simulated run installed bind9-host, bind9-libs, ca-certificates and
  libbrotli1. Debian fixes reach an installed appliance within a day.
- Keel trixie-security holds only keel-archive-keyring. keel 0.23.62 is in
  Keel trixie, which cron-apt does not read.
- cron-apt does not read trixie-updates, so tzdata stays old.
- With an IPv4 resolver on an IPv6-only CT, `apt-get update` fails and
  exits 0. cron-apt installed nothing, and with `MAILON=never` nobody was
  told.

The first boot (`95secupdates`) was measured on CT 9323 with netem
250 ms ±25 ms and 1.5 % loss: `apt-get update` on all sources fetched
8.6 MB in 132 s, over its 120 s limit, so the first boot installed no fix.
The security indices alone are 483 kB in 4 s, and the upgrade (4
packages, 1.8 MB) took 16 s.

## What was decided

1. **Daily runtime updates are the main path.** cron-apt installs from
   `security.sources` every day, as it does now. An installed appliance
   applies Debian security fixes within one day, whatever image it came
   from.
2. **The failure of that path is visible.** cron-apt's update runs with
   `--error-on=any`, so a failed fetch is an error that cron-apt logs, and
   the run stops. monit runs `keel-security-lists-age` every hour. It fails
   when Debian's security index is older than three days (the signed
   `Date` of the InRelease apt keeps), logs one line, and names an IPv4-only
   resolver on a host with no IPv4 route as the likely cause.
   (common#76; on Proxmox the fix is `pct set <id> --nameserver` with an
   IPv6 server.)
3. **tzdata comes from trixie-updates.** A second cron-apt action upgrades
   tzdata alone, from `debian.sources`, where it is installed.
4. **The first boot installs security fixes and never holds the boot.**
   An unattended first boot installs them as `SEC_UPDATES=force` does, as
   it already did; an operator at the console is asked. The update fetches
   only the security indices (inithooks#63), so it finishes on a 250 ms
   link. With no network, or at its limit, the boot goes on and cron-apt
   installs the fixes later (`offline` in `95secupdates`, unchanged).
5. **Keel trixie-security carries Keel fixes that a machine can take
   alone.** A Keel package with a security or data integrity fix goes to
   Keel trixie-security as well as trixie, so cron-apt installs it, when
   its maintainer scripts restart no paired service and no etcd member.
6. **keel, and every package that restarts a paired service or an etcd
   member, never goes to Keel trixie-security.** cron-apt runs at the same
   minute on every node, so it would restart both members of a pair, or
   every etcd member, at once. These packages go to Keel trixie only, with
   an advisory in `docs/advisories/`. The operator upgrades one node at a
   time, each after `keel mesh upgrade-check` passes on it, the VIP holder
   last. This is the least power: it adds nothing to the nodes, while a
   check run inside cron-apt would let two nodes pass at the same minute
   and restart together.
7. **The pool is refreshed, and the stable images rebuilt:**
   - within 7 days of a Debian advisory for a package that faces the
     network in a stable layer: nginx, bind9, php, openssl, openssh, curl,
     and the kernel for VM and ISO images;
   - and at least every 4 weeks for all other updates.
   Each refresh is a commit to `conf/pools/stable-1/` in `Keel-Linux/apt`
   (apt#75), and the rebuilt layers pass the release test (2 LXC on BR1
   and 1 on BR2, netem 250 ms) before they are published.

## Why

A frozen pool is what makes a stable image reproducible, so it cannot also
follow Debian by itself. The machines that run follow Debian every day,
which covers the installed base. What was missing was a signal when that
path breaks, and a rule for when new images must catch up. Keel's own
packages are different: some restart the services that a pair or an etcd
quorum shares, and an unattended upgrade on every node at the same minute
would turn a fix into an outage.

## Consequences

- The first refresh is due now: nginx (DSA-6575), bind9 (DSA-6576) and
  php8.4 (DSA-6574) are more than 7 days old.
- `Keel-Linux/apt` must refuse to publish keel and the paired-service
  packages to trixie-security (apt#82).
- A fresh image is behind Debian only until its first boot or its first
  cron-apt run.
- monit shows `security-lists` as failed on a machine that cannot fetch
  the index. Mail is still off, so the operator sees it in `monit summary`,
  and in the journal (tag `keel-security-lists`).

## What this does not do

- It does not turn on mail or any external alert.
- It does not add a resolver of its own: the CT's resolver is the
  Proxmox host's choice.
- It does not change the stable channel or the Proxmox index.
