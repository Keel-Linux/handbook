# Traps this project has already fallen into

Each of these cost hours, and each is recognisable by a signature. They are
written down so the next one costs minutes, and so a reviewer can ask "is this
that one again?" instead of rediscovering it. Dates are when we hit it.

## A container that nobody attached to blocks on its own console

**Signature.** A first boot hangs forever in one hook. Two or three unrelated
hooks are also reported as failed, typically `15regen-sslcert` and
`95secupdates`. There is no journal to read.

**Cause.** The appliance ships `inithooks.service` with `StandardOutput=tty`
and `TTYPath=/dev/tty1`. Nothing reads tty1 in a container, the terminal buffer
fills, and the next write blocks. A real container image never runs that unit
that way: buildtasks' headless patch carries a marker and the container conf
sets `REDIRECT_OUTPUT=true`.

**Fix.** A container build does three things, not one: the marker file,
`REDIRECT_OUTPUT=true`, and a drop-in giving the unit `StandardOutput=journal`.
Enforced in `bt_mark_container` of each appliance's boot test library.

**Hit** 2026-09-26 in the forum appliance, again 2026-09-27 in both database
appliances, because the library was copied rather than shared.

## The stock LXC apparmor profile refuses the namespaces systemd wants

**Signature.** `systemctl show <unit> -p ExecStartPre` reports `status=226`,
which is `NAMESPACE`. Several systemd units fail together:
`systemd-journald`, `systemd-logind`, `systemd-sysusers`, `systemd-sysctl`,
`tmp.mount`.

**Cause.** Units with `ProtectSystem=full` or `ProtectHome=true` need a mount
namespace the stock profile denies.

**Fix.** `lxc.apparmor.profile = generated` plus the matching allow in the
container config. Enforced in `bt_lxc_config` of the boot test libraries.

**Hit** 2026-09-26 with redis in the forum appliance, 2026-09-27 in both
database appliances.

## On Debian, `localhost` is not an IPv6 name

**Signature.** A service answers on 127.0.0.1 and refuses on `[::1]`, while
its configuration says `localhost` and looks right.

**Cause.** Debian's `/etc/hosts` maps `::1` to `ip6-localhost` and never to
`localhost`, so a resolver asked for `localhost` gets IPv4 only.
`listen_addresses = 'localhost'` in PostgreSQL and `bind localhost` in Redis
therefore bind one family.

**Fix.** Literal addresses in configuration, always: `::1,127.0.0.1`. The
instance description's `listen` field is a list of literals for the same
reason.

**Hit** 2026-09-27: the PostgreSQL appliance shipped listening on IPv4 only,
and its own verification hook caught it.

## Asserting the configuration is not asserting the behaviour

**Signature.** A build asserts a setting is present and passes, and the running
service does not do what the setting was supposed to make it do.

**Cause.** The assertion reads the file it just wrote.

**Fix.** Assert the behaviour: connect to the port, ask the server what it
thinks it is, read the role from the server rather than from the config.

**Hit** 2026-09-27, the PostgreSQL listen address: the recipe asserted the
default `localhost` believing it meant both families.

## A literal version in a recipe hides a stale package

**Signature.** A layer is built after new packages are published and comes out
with the old ones, and nothing complains.

**Cause.** The recipe asserted a literal, `grep -c '+keel1$'`, which the stale
versions satisfied.

**Fix.** Assert against the archive: the installed version must be the
candidate the build time archive offers, and the index the build read must be
the live one. `bin/keel-archive-check` and `conf.d/zz-project-packages` in the
appliance recipes.

**Hit** 2026-09-27, the forum chain.

## Code merged without a changelog entry never reaches a machine

**Signature.** The code is on the default branch, the gate is green, and the
image does not have it. Somebody concludes the code was never written.

**Cause.** No new `debian/changelog` entry, so the newest installable version
is the old one.

**Fix.** The `package / changelog` check: a pull request that changes a file the
package ships must add an entry with a greater version. Required on every
repository that produces a package.

**Hit** 2026-09-26, the confconsole Instance menu and console mark.

## gpg truncates its output file before asking for the passphrase

**Signature.** A signing step fails and the file it was signing is now empty.

**Fix.** Sign to a temporary file and move it into place. In `release_sign`.

**Hit** 2026-09-27.

## A reproducibility reference that cannot match is worse than none

**Signature.** A daily check reports drift every morning. Nobody reads it any
more.

**Cause.** The recorded digest describes a layer nobody serves, because a
deliberate rebuild changed it on purpose.

**Fix.** A release drops the reference of a layer it rebuilt, and the next
check seeds a new one and says so. Also: measure what the work can actually
make identical. Package lists can be made identical by pinning; tarballs
cannot, because install time state differs, so those are two separate claims
with two separate verdicts.

**Hit** 2026-09-26, and the criterion itself was wrong until 2026-09-27.

## A recipe without git history has no deterministic date

**Signature.** `ERROR [layer-lib]: SOURCE_DATE_EPOCH not set and no git history
in <product dir>`, and a release that dies on its second layer.

**Cause.** The product directory was a copy, not a checkout.

**Fix.** Every product directory on the build host is a checkout of its
repository, with `build/` excluded locally. A recipe that exists only as a
directory cannot be built reproducibly and cannot be rebuilt by anybody else.

**Hit** 2026-09-27, the nodejs-nginx stack layer, which existed nowhere else.

## A log line must never be able to kill the job

**Signature.** A hook dies with no output at the point where it should have
logged something, and on the one path where it logs a warning.

**Cause.** A level outside `err|warn|info|debug` raises, and the caller caught
only `OSError`.

**Fix.** The logger's refusal is handled like an unwritable log file, by
printing to stderr. And a test reads the script's own source, asserting every
level it passes is one the logger accepts.

**Hit** 2026-09-27, in code added the same day, and the appliance gate did not
catch it because the test pre-rendered what the hook was supposed to produce.

## Two builds on one host, and one lock

**Signature.** A release exits 4 immediately, `the build lock is held`, right
after somebody typed a passphrase that expires in ten minutes.

**Fix.** A bounded wait on the lock rather than an instant refusal, and signing
as a separate phase that takes no lock and runs in seconds.

**Hit** 2026-09-27, three passphrase moments lost.

## Things we did wrong and would do again unless written down

- **Discarding a local commit on a guess.** A checkout on the build host had a
  commit not on the remote; it was discarded because a commit with the same
  message existed on the branch. It was not the same change, and the broken
  cipher list it removed was published. Confirm by content, never by message.
- **`chown -R` under a product directory.** It walked into a mounted deck. The
  published layer survived only because an overlay sends writes to its upper
  directory. `git config --global --add safe.directory` is the remedy for an
  ownership complaint, and it touches no file.
- **Copying a test library instead of sharing it.** The same 130 lines in four
  repositories meant every fix above had to be ported by hand, twice.
