# 0083: The base follows Debian stable with security updates, and runtimes and applications move through the Keel channel

Date: 2026-11-10
Status: **decided by the maintainer, 2026-11-10** ("sim", the answer to
the three points of the decision below: the base, the channel and the
Node.js package). The maintainer's reason: "security is a daily
practice, a habit; the process is more important than the destination".
The coordinator decided two details under the maintainer's delegation:
the first line is 24, and the build pins the release keys by
fingerprint. The package name and the open points are not decided.

## What was asked

Debian stable and the TurnKey appliances carry a Node.js that is older
than the upstream LTS lines. Must Keel move its base to a rolling base,
for example Debian testing? Or must the newer software come to Keel in a
different way?

## What was found

Node.js is the first example. The facts were checked on 2026-11-10.

| Item | Fact | Source |
| --- | --- | --- |
| Debian 13 | nodejs 20.19.2 (`20.19.2+dfsg-1+deb13u3` in trixie-security). forky and sid have 24.22.2 | <https://qa.debian.org/madison.php?package=nodejs> |
| Node.js end of life | 20: 2026-04-30. 22: 2027-04-30. 24: 2028-04-30. 26: 2029-04-30 | <https://raw.githubusercontent.com/nodejs/Release/main/schedule.json> |
| Node.js LTS phases | 24 is in maintenance from 2026-10-20. 26 is LTS from 2026-10-28 | the same `schedule.json` |
| Upstream advice | "Production applications should only use Active LTS or Maintenance LTS releases." From Node.js 27, each major version moves to LTS | <https://nodejs.org/en/about/previous-releases> |
| Latest releases | v24.22.2 (2026-10-27), v26.13.0 (2026-10-28) | <https://nodejs.org/dist/index.json> |
| Upstream signature | each download directory has `SHASUMS256.txt.asc`, the SHA-256 sums with the releaser's PGP signature. The keyring is in `nodejs/release-keys`. The check is `gpgv` on the file, then `shasum --check` | <https://github.com/nodejs/node#verifying-binaries> |
| Applications | NodeBB 4.16.7 needs `node >=22` | <https://raw.githubusercontent.com/NodeBB/NodeBB/v4.16.7/install/package.json> |
| Applications | Ghost 6.72.0 accepts `^22.23.1 \|\| ^24.20.0` | <https://raw.githubusercontent.com/TryGhost/Ghost/v6.72.0/ghost/package.json> |
| Applications | Mastodon 4.7.3 needs `node >=22` in `package.json` and `streaming/package.json`. Its `.nvmrc` is `24.19` | <https://raw.githubusercontent.com/mastodon/mastodon/v4.7.3/package.json>, <https://raw.githubusercontent.com/mastodon/mastodon/v4.7.3/streaming/package.json>, <https://raw.githubusercontent.com/mastodon/mastodon/v4.7.3/.nvmrc> |
| TurnKey | common's `conf/nodejs` clones `tj/n` at its head and runs `n lts`. So the Node.js version is the LTS of the day of the build, with no pin | <https://raw.githubusercontent.com/turnkeylinux/common/master/conf/nodejs> |

Debian describes the security of testing as follows:

- "security updates for testing are not managed by the security team"
  (<https://www.debian.org/devel/testing>).
- Testing gets fixes from unstable. "there is a minimum two-day
  migration delay, and sometimes security fixes can be held up by
  transitions." In the months after a release, "security fixes for
  testing may lag behind" (<https://www.debian.org/security/faq>).
- Testing "does not have permanent security support". A package in
  testing can be "(temporarily) removed due to bugs or unmet
  dependencies", and testing can be broken for months. When testing is
  frozen, only release-critical fixes migrate
  (<https://www.debian.org/doc/manuals/debian-faq/choosing.en.html>).

## Why (brief section 10)

1. **Why the current approach is not enough.** Keel takes Node.js in
   three ways now. 0064 puts a Node.js 22 tarball under `/opt/node` in
   the Ghost image. 0065 builds Node.js 24 from the forky source.
   TurnKey's `conf/nodejs` takes the LTS of the day, with no pin. A
   tarball in an image gets no apt update. Three ways give three
   versions and three update paths.
2. **Whether it can be made to work.** It can. The Keel archive already
   carries packages that Debian does not have (0074). The images get
   Debian security fixes every day (0073). The commissioning gate (0075)
   tests each image before a release.
3. **Why this is better.** The base stays on the Debian line that has
   full security support. Only the parts that must move fast move, and
   each move goes through the same gate. A machine that is installed
   gets the new Node.js from apt. It does not need a new image.

## Decision

1. **The base is Debian stable with its security updates.** Keel does
   not use Debian testing or any other rolling base. The reasons are the
   facts above: testing has no full support from the security team, its
   fixes come with a delay, a package can leave it, and a freeze stops
   new versions. A major version in testing can also change on any day.
   Then a commissioning result (0075) of one day does not prove the
   image of the next day.
2. **Runtimes and applications move through the Keel channel.** The
   Keel channel is the path of a Keel package or layer: the Keel pool,
   then `trixie-testing`, then commissioning (0075), then the stable
   suite and the stable channel (0016). A runtime whose upstream moves
   faster than Debian stable comes as a Keel package on this path.
   Node.js is the first. The applications come on the same path. The
   channel can move every day, and each move passes the gate. This is
   how Keel makes security a daily habit.
3. **Node.js is one Keel package of the official LTS binary.** The
   proposed name is `keel-nodejs`.
   - The package carries the official Linux binary of one LTS line from
     nodejs.org.
   - When the package is built, the build checks `SHASUMS256.txt.asc`
     with `gpgv` against the Node.js release keys. Then it checks the
     sha256 of the tarball.
   - The source of the package pins the sha256 of the tarball (0012).
     It also pins the release keys by fingerprint, as 0074 pins the key
     of the web vault. The upstream example takes the keyring from the
     head of `nodejs/release-keys`, and Keel does not trust a head.
   - Updates come by apt on the Keel channel: `trixie-testing` first,
     then stable.
   - All Keel applications use the same Node.js line. The first line is
     24, because NodeBB, Ghost and Mastodon all accept it (see "What
     was found"). Ghost does not accept 26 at 6.72.0.
   - A change of LTS line is planned. It is done before the end of life
     of the line in use, 2028-04-30 for 24. Each application that uses
     Node.js passes commissioning on the new line before the change.
   - An application installs its npm dependencies from a committed lock
     file with `npm ci`.

## What it means for work

1. A new source repository for the Node.js package, in the pattern of
   `Keel-Linux/vaultwarden-deb` (0074). The build downloads the tarball,
   checks the signature and the sha256, and makes the `.deb`.
2. The package goes to `trixie-testing`. The application layers that
   need Node.js install it from their `plan`. No layer downloads
   Node.js itself.
3. NodeBB (0082) is the first user. Ghost (0064) and Mastodon (0065)
   use the same package when they are built.
4. Keel layers do not use common's `conf/nodejs`. Keel's copy runs `n`
   with `NODE_VER`, or with the latest LTS when `NODE_VER` is not set.

## Rejected alternatives

| Alternative | Why rejected |
| --- | --- |
| Debian testing as the base | no full support from the security team, a delay for fixes, packages can leave it, freezes. A commissioning result does not stay valid |
| Debian's own nodejs | 20.19.2 in Debian 13. Upstream ended Node.js 20 on 2026-04-30. NodeBB 4.16.7, Ghost 6.72.0 and Mastodon 4.7 need 22 or newer |
| The NodeSource apt repository | a third-party apt source and key in every image. Its versions reach a machine when NodeSource publishes them, not after the Keel gate |
| `n` or nvm with no pin | the version is the one of the day of the build. No pin, no gate, and no apt update on an installed machine |
| A tarball in each image (option A of 0082, and 0064) | each image carries its own copy. apt can update an installed machine, but it cannot update a file in an image. A Node.js security release then needs a new image and a new installation |
| A Keel package of forky's Node.js built from source (0065, option C of 0082) | a V8 build and new build dependencies on trixie, for each release. The official binary gives the same version with less work |

## Later work, not decided

A CI track that builds the images against Debian forky can show problems
of the next Debian release early. This is an idea only. It needs its own
note.

## Open points

1. **The package name.** `keel-nodejs` is a proposal. The name can also
   be `nodejs`, with a Keel version, so that it replaces Debian's
   package.
2. **Where the binary goes.** `/usr` with the Debian file names, or
   `/opt/node` with links in `/usr/bin`.
3. **How an LTS change is announced.** For example a note per change,
   a date in the release notes, and an alert on each machine some
   months before the end of life.
4. **Who watches the upstream security releases.** Somebody must see
   each Node.js security release and start the package build, with a
   time limit like the 7 days of 0073.
5. **How a security release reaches an installed machine.** cron-apt
   reads only `security.sources` (0073). So a Node.js fix must go to
   Keel trixie-security, or the operator must run the upgrade. 0073 keeps
   packages that restart a paired service out of trixie-security. So the
   package design must say if an update restarts the application.

## What this amends

- **0064**: Ghost uses the Keel Node.js package and its line, not a
  Node.js 22 tarball under `/opt/node`.
- **0065**: Mastodon uses the Keel Node.js package of the official
  binary, not a build of the forky source.
- **0082**: option D, the Keel Node.js package, replaces option A as the
  recommendation (amended in handbook#164).

It applies 0012, 0016, 0073, 0074 and 0075.
