# 0085: A node tells the administrator through ntfy when an upgrade waits for a person

Date: 2026-11-10
Status: **the rule is decided by the maintainer, 2026-11-10.** The
maintainer said that it is good to tell the administrator, through ntfy,
when there is a new supervised upgrade, and that this applies to each
application of the operating system. The coordinator chose the method
below under the maintainer's delegation. Nothing in it is built. The
tests at the end must pass on a real machine before the method is
released.

## What was asked

Some upgrades do not install themselves. A person must start them. The
maintainer asked that the node tells the administrator when such an
upgrade is available. The message goes through ntfy (0063). The rule is
for each application, not only for OJS (0084), where the question came
from.

## What is true today

- cron-apt installs Debian security fixes and the packages of Keel
  trixie-security each day, with no person (0073 items 1 and 5).
- keel, and each package that restarts a paired service or an etcd
  member, goes to Keel trixie only. The operator upgrades one node at a
  time, the VIP holder last (0073 item 6).
- Runtimes and applications move through the Keel channel (0083). Note
  0084 says that no OJS upgrade is unattended, because each OJS build
  migrates the database.
- No node tells a person that such an upgrade is available. Note 0073
  says that it "does not turn on mail or any external alert". The
  operator learns it from an advisory, or from `apt list --upgradable` on
  each node.
- keel has `keel notify`. monit calls it. It sends one message to each
  channel in `/etc/keel/monitor.json`, and the ntfy channel takes a list
  of servers (0063 item 3). When no channel takes the message, it goes to
  syslog and to the mailbox of root. Its levels are `warn`, `critical`
  and `recovery`. Its checks are a closed list
  (`keel/monitor/constants.py`).

## Decision

### 1. What a supervised upgrade is

A supervised upgrade is a newer version of an installed package that the
daily unattended run does not install. The node keeps no list of package
names. After the daily run, each package that apt can still upgrade is a
supervised upgrade.

Thus the rule applies to each application and to each Keel package with
no work for each application. A new application cannot be forgotten.

### 2. The check

keel gets one read-only command (proposed name: `keel upgrade pending`).
It reads the state of apt and prints the packages that wait, each with
its installed version and its candidate version. It installs nothing and
it holds nothing.

monit runs the command as a `check program`, the same method as
`security-lists` (0073 item 2). The check runs after the daily cron-apt
run, so that it does not report a fix that cron-apt installs some hours
later.

### 3. The message

When a supervised upgrade waits, keel sends one message through the
channels that the node already has. The message is a new check,
`upgrade`, with a new level, `notice`. On ntfy, `notice` has the default
priority. It is not an alarm.

The message gives:
- the name of the node, and its mode;
- in a pair, the role of the node (standby, or VIP holder), because the
  order of the upgrade depends on it;
- each package with its installed version and its new version. After 10
  packages, the message gives the number of the others;
- the upgrade note of each package, if the package has one (item 5);
- the command to run. In `simple` mode it is `apt upgrade`. In a pair,
  the message says: the standby first, then the VIP holder, each after
  `keel mesh upgrade-check` passes.

The message contains no secret, no token and no address of the node.

### 4. How frequently

- One message when the set of packages and new versions changes.
- One reminder after 7 days, if the set did not change.
- One message with the level `recovery` when no upgrade waits anymore.

The node does not send the same message each day. People mute a topic
that repeats.

### 5. The upgrade note and the urgency of a package

A new version is not installed yet, so a file inside the new package
cannot give its note. The note comes from the package index. A Keel
package can have two optional fields in its control file:

- `Keel-Upgrade-Note`: one line, 200 characters at most. Example for
  OJS: "This upgrade migrates the database. The site is in maintenance
  during the migration."
- `Keel-Upgrade-Urgency: security`: the upgrade corrects a security
  defect or a data integrity defect, and it needs a person (0073 item
  6). For this value, the level of the message is `warn`, not `notice`.

`keel upgrade pending` reads the two fields of the candidate version
from apt. A package with no field gets the usual message.

### 6. What the notice does not do

- It does not install and it does not start an upgrade. The person
  decides when.
- It does not replace the advisory in `docs/advisories/` (0073 item 6).
- It does not add a topic or a server. It uses the channels in the
  instance description of the node.

### 7. A node with no channel

`keel notify` already writes to syslog and to the mailbox of root when
no channel takes a message. The check also shows in `monit summary`. A
node with no ntfy channel is not silent on the machine itself.

### 8. A pair

Each node of a pair sends its own message, because each node holds its
own packages. Each message names the role of its node. With 3 ntfy
servers and 2 nodes, a person can get 6 messages for one upgrade. This
is accepted, as in 0063: no message is lost.

## What this amends

- **0073.** The sentence "It does not turn on mail or any external
  alert" stays true for the security index check. This note adds one
  external notice, for a different event. Item 6 of 0073 gets this
  addition: the node tells the operator that the upgrade waits.
- **0084.** Section 8 of that note says that the operator
  runs `apt upgrade` for OJS. With this note, the operator gets a message
  first, and the OJS packages carry `Keel-Upgrade-Note`.
- **0063.** Not changed. Step 4 of 0063 (the production nodes send to
  the three servers) is a condition for the message to reach a phone.

## Rejected alternatives

- **Install first, then tell.** This is against 0073 item 6: two nodes
  of a pair can restart at the same minute. It is also against 0084: a
  database migration starts with no person present.
- **Mail.** Mail is off on a Keel node (`MAILON=never`, 0073). ntfy is
  the alert path that 0063 decided.
- **One central message from the build host for each release.** The
  build host does not know which node has which package. It also cannot
  reach the nodes of a different operator. It can be added later; it
  does not replace the notice of the node.
- **A list of package names for each application.** It is work for each
  application, and a new application can be forgotten.
- **A message each day.** See item 4.

## Tests before the release

All tests are on real machines, with evidence.

1. A node has a newer keel in Keel trixie, and the daily run is done.
   The check lists keel. One message arrives on a phone through ntfy.
   The second run of the check sends nothing.
2. With the clock 7 days later and the same set, one reminder arrives.
   After `apt upgrade`, one `recovery` message arrives.
3. A Debian security fix that cron-apt installs gives no message.
4. In a pair, each node sends a message, and each message names the
   correct role.
5. A node with no channel writes the syslog line, and `monit summary`
   shows the check.
6. The two fields go through the archive tool (reprepro) into the
   `Packages` file, and `apt-cache show` gives them on a node.
7. On a 250 ms link with loss, the check ends in its time limit. A
   fetch that fails does not give a false "no upgrade waits".

## Not verified

- If the daily cron-apt run refreshes the index of Keel trixie. If it
  does not, the check must refresh that index, or the node does not see
  a new package.
- If reprepro keeps the two fields with no change to its configuration.
- The hour of the check in relation to the hour of the cron-apt run.

## Sources

- The maintainer, 2026-11-10 (chat).
- 0021 (the monitor and `keel notify`), 0063, 0073, 0083, 0084
  (handbook#169).
- `keel/monitor/notify.py` and `keel/monitor/constants.py` of keel
  0.23.96.
- `overlays/turnkey.d/security-lists/` of `Keel-Linux/common`.
