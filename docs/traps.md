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

## A protocol that ends its lines with CRLF, read with a `$` anchor

**Signature.** A check says a server did not answer, and the server is up,
listening and answering. The same command run by hand prints exactly what
the check was looking for.

**Cause.** Redis speaks CRLF. Every line of an `INFO` reply ends `\r\n` and
`redis-cli` prints the reply as it came, so `tcp_port:6379` is really
`tcp_port:6379\r`, and `grep -q "^tcp_port:6379$"` never matches it. `od -c`
is what settles it in one line:

    redis-cli INFO server | grep tcp_port | od -c
    t c p _ p o r t : 6 3 7 9 \r \n

**Fix.** `tr -d '\r'` before reading an `INFO` reply, in one function
everything calls, or match a prefix and never a whole line. And make the
test stub answer in CRLF: the stub of the day printed `\n`, so the suite was
green against a server that does not exist.

**Hit** 2026-09-28, in the first build of `unit-redis`, in the component's
own build time check.

## redis-cli exits 0 when the server answers with an error

**Signature.** A wrong password, a refused command and a successful one are
all a success to the script that ran them.

**Cause.** An error reply is a reply. `redis-cli` prints `AUTH failed:
WRONGPASS ...` or `NOPERM ...` and exits 0.

**Fix.** Read the answer, never the exit code, everywhere a Redis client is
run: the first boot hook, the build time check and the boot test all compare
the text. Each verdict has a test that drives it with the words a real
refusal produces.

**Found** 2026-09-27 while writing `unit-redis`, before it could be hit.

## A build time check that runs a service as root leaves it files it cannot write

**Signature.** A layer builds green, every check in it passes, and the
service will not start on any machine built from it. The journal says
`Can't open the log file: Permission denied`, or the same about a pid file
or a socket, and the file it names exists, is empty, and is owned by root
in a directory the service's own user owns.

**Cause.** The check started the service as root. Even when it redirects the
paths it knows about, a daemon may touch the packaged ones: Redis opens
**every** value its `logfile` setting is ever given, so the path in the
packaged configuration is created before a `--logfile` on the command line
replaces it. Root creates it, and the service's user can never write it.

**Fix.** A check that starts something owns what it left. Read the packaged
paths out of the configuration before starting, and take away afterwards
anything the check created and nothing was written to. The package ships no
such file, and the service makes its own at the first boot, as its own user.

**And the test stub has to be as impolite as the program.** The stub of the
day wrote only where it was told, so the suite was green against a daemon
that does not exist. It opens the packaged path now, and the test fails
without the cleanup.

**Hit** 2026-09-28, in the first `redis` layer that booted. Settled by
comparing with the `nodejs-nginx` layer, which installs the same package
and whose `/var/log/redis` is empty: nothing in the package or the common
tree did it, the check did.

## A Redis ACL user may be declared only once, in all the configuration there is

**Signature.** `redis-server` refuses to start, and the message names a line
that is correct on its own:

    Error in user declaration 'admin': Duplicate user found.
    A user can only be defined once in config files

**Cause.** Redis keeps the last value it reads for an ordinary directive,
which is what makes an `include` at the end of the file an override. `user`
is not an ordinary directive: a second declaration of the same account, in
any file the configuration includes, is fatal.

**Fix.** Declare an account in exactly one place. The pattern the SQL
engines use, publishing an account that cannot authenticate and giving it a
password at the first boot, does not port: on Redis the build time
configuration names no account at all, and the first boot declares it once.
An account that is not declared cannot authenticate either, which is the
property that pattern was for.

**Hit** 2026-09-28, in the same boot as the trap above.

## A check that deletes the log which explains its own failure

**Signature.** A build fails in a check that ran a service, and there is
nothing to read. The service's log was in the scratch directory the check
removes on the way out, so the failure has to be reproduced by hand in
whatever tree the build left behind.

**Fix.** The fatal path prints the last lines of the service's own log
before the cleanup runs. A check that starts something owns the evidence it
produced.

**Hit** 2026-09-28, in the same build as the CRLF trap above, which is why
that one cost a reproduction step it should not have.

## Every appliance built from `core` has the same machine-id

**Signature.** Anything derived from `/etc/machine-id` is identical on two
machines that should differ. Measured 2026-09-27: both nodes of the two node
gate, and both live appliances on the build host, read
`f0e97605ab594989b4d78f4a126b5b37`, and so both nodes of a replicating pair
took the same MariaDB `server_id`, which is the one thing that stops
replication outright.

**Cause.** The published `core` layer's rootfs carries a populated
`/etc/machine-id`. Debian's own rule is the opposite: an image ships it empty
and systemd writes a fresh one at the first boot, which is what makes it an
identity. A layer that ships one hands its own identity to every machine built
from it.

**Fix.** Two, and both are wanted. The layer should ship `/etc/machine-id`
empty, which is `buildtasks`' container patch's job and is not done yet. And
nothing may depend on it being unique without saying so: `keel`'s `server_id`
derives from the machine-id **and** the addresses the server answers on, so a
pair on one /64 differs whatever the layer shipped.

**Hit** 2026-09-27, in the MariaDB replication work, on the first run that
booted two nodes from their descriptions.

## A bats suite cannot see a library that kills its caller

**Signature.** A unit suite is green, coverage is 100 percent, and the script
that uses the library exits in the middle with no message at all. The last
thing printed is the verdict before the one that failed.

**Cause.** `bats run` turns errexit off for the code it runs, so a function
that dies under `set -e` dies invisibly in the suite and fatally in the
caller. The usual shape is a helper that returns non-zero as an *answer*
rather than as an error, read with `cmd; rc=$?`, which is not one of the
constructs errexit exempts. `cmd || rc=$?` is.

**Fix.** `|| rc=$?`, never `; rc=$?`, for a helper whose non-zero return is
meaningful. And one test per library that runs it the way the caller does, in
a script with `set -euo pipefail`, because no amount of `run` coverage
substitutes for it.

**Hit** 2026-09-27, the first `lamp-client` boot test: `bt_has_local_database`
returns 1 for the artefact with no database server, which is the answer and
not a failure, and the landing page verdict died at that line. 66 tests and
100 percent line coverage on the same file.

## A path with a space in it breaks a whitespace comparison

**Signature.** An equivalence measurement reports one more differing file than
it should, in every pair including the control against itself, and the path
looks like it has nothing to do with the change.

**Cause.** `sha256sum` output is `<hash>  <path>`, and `join` and `awk` split
on whitespace. One path in a Debian rootfs has a space in its name,
`setuptools/_vendor/jaraco/text/Lorem ipsum.txt`, so it becomes two fields and
never matches itself.

**Fix.** Key the comparison on a tab-separated `path<TAB>hash`, and count the
paths with an internal space before trusting a count. There is exactly one
today, which is what makes this easy to miss and easy to dismiss.

**Hit** 2026-09-27, the LAMP composition measurement: 199 and 183 differing
files, which are 198 and 182.

**Hit again** 2026-09-28, in `apt/lib/mirror.sh`: `awk 'NF == 3'` over the
release MANIFEST's `size sha256 path` lines silently dropped any path with a
space in it, so the digest check never saw that file while `wget -r` still
fetched it and the install still published it: a hole in the gate exactly
where a crafted file name puts one. The fix refuses such a line rather than
skipping it (`mirror_manifest_odd_files`): the publication stops with exit 3
and names the path. The lesson the first entry did not draw: a field
**count** is the tell. If a format's last field can contain the separator,
counting fields is the bug.

## gpgv writes the plain text of a document whose signature it refused

**Signature.** A verification step "works": the program reads the body of a
signed file and goes on. It also goes on for a file signed by a key nobody
trusts, or altered after signing, because the body was there to read.

**Cause.** `gpgv --output FILE` writes the plain text **before** it decides,
and leaves it there on a refusal. Measured 2026-09-28, both cases produced
the full body beside a non zero exit:

    gpgv --status-fd 1 --keyring k.gpg --output plain stable
    rc=1
    [GNUPG:] BADSIG 37D007E12762D9B0 Keel Test Channel Key
    $ cat plain
    channel stable
    release 2026-09-28
    ...

**Fix.** Read the output only after every check below has passed, and
raise rather than return text on a refusal, so no caller can reach it.
`keel.layers.signature.verify_bytes` does this; on the publishing side the
function that was doing it is `release_signature_current` in
`apt/lib/release.sh`, which reads `--status-fd`. The first version of this
entry named `channel_verified` in `apt/lib/channel.sh` instead, which read
gpgv's exit status and nothing else, so it recorded as done a thing the
code it cited did not do. `channel_verified` reads the status fd now; it,
`release_signature_current` and the script that installs a pointer on the
public host all apply the rule below (`gpg_status_good` in
`apt/lib/common.sh`, and the same test inlined in the generated script).

**An exit status of 0 is not the check, and neither is `VALIDSIG`.** This
is the part that cost the most, because the first version of this entry
recorded "exit status and a VALIDSIG line" as sufficient and it is not.
Measured on gpgv 2.4.7:

| signature by | exit | status lines |
| --- | --- | --- |
| good key | 0 | `GOODSIG`, `VALIDSIG` |
| revoked primary | **0** | `REVKEYSIG`, `VALIDSIG` |
| revoked signing subkey, live primary | **0** | `REVKEYSIG`, `VALIDSIG` |
| expired key | **0** | `KEYEXPIRED`, `EXPKEYSIG`, `VALIDSIG` |

stderr says `Good signature from` in all four. `GOODSIG` is the only line
gpgv withholds. **So the rule is: require `GOODSIG`**, and refuse
`REVKEYSIG|EXPKEYSIG|KEYREVOKED|KEYEXPIRED` by name for a message that
says which it was.

It is worth knowing why this is not a detail. `VALIDSIG`'s last field is
the *primary* fingerprint, so pinning a primary as the accepted signer
also accepts a signature by a revoked subkey of it, and
`apt/keys/keel-archive-keyring.asc` already carries
`sub D276B62C2BD16F4E … r`, a signing subkey this project has had to
revoke once. Revocation is the whole answer to the theft of a signing key,
and a verifier that accepts `VALIDSIG` makes revocation do nothing.

**A second property:** `gpgv` reads a **binary** keyring only. An ASCII
armored one, which is the form this project publishes its keys in, gives
`NO_PUBKEY` and exit 2, which reads exactly like a wrong key. Dearmor
first. A `--keyring` given as a relative path is resolved against
`$GNUPGHOME` and not the working directory, and a keyring it cannot find
produces the same `NO_PUBKEY`: three different faults, one message.

**A third:** `gpgv` accepts SHA-1 unless told otherwise. Pass
`--weak-digest SHA1`.

**And a fourth, which is not about gpgv but about assuming it.** The first
draft of the client said gpgv is on every appliance because apt verifies
`InRelease` with it. On Debian 13 apt verifies with `sqv` and `gpgv` is a
package of its own, which `apt`'s own README already recorded for
`bin/verify-repo`. So the verifier could have been absent, and "I could
not check this" is the one refusal a client must never make quietly. A
program a check depends on is a package dependency, never an expectation.

**Found** 2026-09-28, writing the channel pointer verification of decision
0016, by testing the refusals before writing the code that reads the body.
**The revoked and expired rows were found in review, after this entry had
already been written with the wrong rule**, which is the trap this file is
for, sprung inside the file itself. An entry that records a fix is worth
less than no entry if the fix is not the one the code needs, because the
next reader stops looking. Both implementations now require `GOODSIG`, and
the shape to check for is: a verifier consulted for its exit status.

## In one `local`, bash expands every word before it assigns any of them

**Signature.** A function builds a path out of its own arguments and gets a
path with a hole in it: `/srv/keel-release/` where `/srv/keel-release/2026-09-28`
was meant. Under `set -u` in a generated script, the same shape is worse:
the script dies at the unbound name with no message, the caller reports a
generic failure, and the step looks like it did nothing.

**Cause.** This is not sequential:

    local date="$1" dir="$KEEL_RELEASE_ROOT/$date"

`local` is a builtin, so the shell expands all of its arguments first and
only then performs the assignments. `$date` in the second word is the value
`date` had *outside* the function, which is usually empty. Two statements
behave the way the one statement looks:

    local date="$1" dir
    dir="$KEEL_RELEASE_ROOT/$date"

**Fix.** A `local` line declares names and assigns only from the positional
parameters; anything derived from another local goes on its own line. Both
halves of the channel work had this bug, and one of them was invisible: a
published script referenced `$release` where the generator should have
expanded it, so under `set -eu` it exited 1 before printing the refusal it
existed to print, and the publication reported a generic exit 6.

**Hit** 2026-09-28, twice, in the publishing side of decision 0016. The
adversarial test ("a second publication of one revision with other content
is refused") is what found the second one; the happy path passed.

## One control pair is not a noise floor

**Signature.** An equivalence measurement reports a small residue of files
that look like nothing to do with the change, typically a package's own
`changelog`, `md5sums` and `/var/lib/dpkg/status`. Or, worse, it reports zero
and a second control pair would not have.

**Cause.** Two builds of the same recipe do not differ by a fixed set. The
mariadb captures of 2026-09-27 differ by 179 files in one control pair and 182
in another, so a difference attributed to the change against the first pair may
be ordinary noise the first pair happened not to show. Subtracting one pair
answers "is this difference in that pair", not "is this difference noise".

**Fix.** Capture at least three controls and give every one of them to
`bt-layer-measure attribute` in `buildtasks`: `--control-again` is repeatable
and the floor it subtracts is the union over every pair, so no single pair
decides the verdict. The block also prints what each pair on its own would
have said, which is where the swing shows. Name the residue in the pull
request rather than leaving it out: the postgresql extraction's residue was
one line, the trailing comment on `listen_addresses` in `postgresql.conf`,
which the component's conf script writes and `conf.d/main` used to.

A union floor is more permissive, not more rigorous: it subtracts strictly
more than either pair, so zero against the union proves less than zero
against one pair would have. It is the right test because it is the one whose
answer does not depend on which two builds were named first, not because it
is the harder one.

**Hit** 2026-09-28, recounting the mariadb and postgresql extractions: 3 and 1
files that the merged pull requests reported as zero.

## A differing path inside the noise floor is not a noise difference

**Signature.** An equivalence measurement passes, and the change it was
measuring was one whose whole effect lands in a directory the measurement
subtracted by name.

**Cause.** A path is put inside the noise floor by where it is. Whether its
difference is really noise is a question about its bytes. For mariadb 173 of
the 179 noise-floor files are `/var/lib/mysql/**`, which holds
`mysql/global_priv` and `mysql/user.*`, and the component's build-time job
includes deleting accounts.

**Fix.** Keep the bytes of anything that can hold accounts, credentials, keys
or database content (`share/layer-state-paths` in `buildtasks`) and judge each
differing state path by its bytes, which is what `bt-layer-measure attribute`
does. Do not cancel a difference against the controls by position alone: two
unrelated changes at one line number or one byte offset look alike, and an
account added on the line a clock moves on would pass. A text line is noise
only if the controls pin what varies there, the same short length and only
digits and date punctuation, as a timestamp is; a binary difference is never
shown to be noise and has to be read and cleared in writing. A file the
measurement could not read is not a file that did not change, so an unsampled
state path fails the run.

**Hit** 2026-09-27, both component extractions: `global_priv.MAD`,
`global_priv.MAI`, `global_priv.frm` and `user.frm` all differ in the
control-unit pair and all were subtracted unexamined.

## Two machines answer to `tkldev`, and they run different fab

**Signature.** A claim about the build order, or about anything else in
`product.mk`, that is internally coherent, cites a real file at a real path,
survives a review, and does not describe what the build does. Nothing in the
change depends on the wrong part, which is why it survives: the facts the work
rests on are checked and correct, and the sentence around them is not.

**Cause.** The LXC container on a workstation and the build host both answer to
`tkldev`, and they run different fab. Reading `/usr/share/fab/product.mk` on
the nearer one answers a question about the other. Measured 2026-09-28:

| Machine | fab | `product.mk` md5 | Unit phases in `root.patched/body` |
| --- | --- | --- | --- |
| local `tkldev` container | `1.1.1`, stock | `0657df1a` | one, after the common removelists |
| fab `1.1.1+keel1` (b07a733) | `1.1.1+keel1` | `c04cb601` | one, after the common removelists, as in stock (the file differs from stock only in `SOURCE_DATE_EPOCH`) |
| build host | `1.1.1+keel2` | `a06bfe03` | three (overlays, conf scripts, removelists), before the common removelists |

**Fix.** Take the reading from the machine that builds, and name the fab
version beside it so the next reader can tell which file was read. A version
string alone is not enough: the first correction named `1.1.1+keel1`, the one
release that does not carry the order it was describing, and was wrong again in
the same way. Quote the md5 of the file the reading came from; `md5sum
/usr/share/fab/product.mk` on the build host settles it in one line, and
`dpkg-query -W fab` says which version that is.

**Hit** 2026-09-28 in the core login change (keel-core#9). The order written
into `conf.d/main`, `COVERAGE.md` and the commit message put the common
removelists before the units, read faithfully from the container's file. The
two facts the change rested on were true in both versions, so the first review
passed it; the second caught it, and then caught the version string in the
correction.

## A bats negation that is not last asserts nothing

**Signature.** A negative test passes whatever the code does. Deleting the
function it refutes, or making it return 0, leaves the suite green. The test
reads as a list of refusals and the last line is the only one that decides
anything.

**Cause.** Bash does not apply errexit to a negated command: `! cmd` is
exempt, by the shell's own rules, precisely so that a script can test a
command without dying. A bats test body has no assertions of its own; its
verdict is the exit status of the last command it ran. So `! cmd` decides the
test when it is the final command and is inert everywhere else, and moving a
line, or adding one after it, silently changes whether it asserts.

shellcheck grades the two cases apart, which is what makes a sweep possible:

    shellcheck -f gcc --shell=bash tests/*.bats | grep SC2314

`error:` is an inert one. `note:` is one in final position, which does assert
today and would stop asserting if a line were added after it.

**Fix.** `run ! cmd`, with `bats_require_minimum_version 1.5.0` at the top of
the file. It asserts wherever it stands. Write every negation that way, not
only the inert ones: a line whose meaning depends on its position is the trap,
and a file that mixes the two forms leaves a reader to work out which half is
real.

Three things to watch when converting. `run` replaces `$output`, `$status`
and `$lines`, so a body that refutes something and then reads the output of
the command it was refuting has to keep that output in a local first;
otherwise the second refutation greps an empty string and passes for a new
reason. `run` takes a command, not a pipeline: `! a | grep -q b` has to be
rewritten, not prefixed. And `run !` accepts any non-zero status, so a
misspelt function (127) or a `grep` of a file that is not there (2) passes
it; after a conversion, check that each refutation fails with the status
that means "no", not with one that means "could not ask".

**Enforced** in the `Negations that assert` step of `test-shell.yml` in the
`.github` repository, which every repository with a bats suite calls at
`@main`. shellcheck reports the negations at the top level of a test body
(SC2314 for `! cmd`, SC2315 for `! [[ ... ]]`, severity error only, so the
final-position ones are not failures). shellcheck does not see a negation
one level down, `a && ! b`, or `! cmd` inside a loop, a branch, a group or a
substitution, and bats passes every one of them; a short awk program in the
same step reports those, on any line of the body but its last. The step runs
before the coverage work and without a coverage script, because a suite that
is not asserting is not worth measuring. `keel` runs its bats suite from
pytest through `test-python.yml`, so the step does not reach it yet.

**Hit** 2026-09-28, everywhere at once: 57 inert negations on the default
branches of eight repositories, out of the 102 bare negations in the
organization's bats suites. The worst was `inithooks`
`tests/test-ipconfig.bats`, where twelve of the thirteen rejection cases of
"ip6_syntax rejects what is not an IPv6 address" were inert and only the
last one decided anything: an IPv6 validator's rejection set, in an
IPv6-first distribution. Closely followed by `keel-wordpress`, where five of
the six cases of "is_global_ipv6 refuses link local, loopback, multicast and
IPv4" never ran, and `unit-redis`, where the refutation that the bind
fragment never says `localhost` (put there by the entry above about Debian
and `localhost`) was itself inert.

Every predicate turned out to be right, so nothing shipped broken. That is
luck, not evidence: the one assertion that did fail when it was turned on,
`keel-nodebb`'s `! grep -q set_real_ip_from` against a file whose own comment
names the directive, could never have passed for any input, and it sat there
because nothing ever ran it.

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
