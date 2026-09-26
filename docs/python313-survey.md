# Python 3.13 compatibility survey: fab, common, tklbam, turnkey-pylib

Date: 2026-09-24. Serves BRIEF.md section 8 ("Python 3.13 compatibility across
fab / common / tklbam / turnkey-pylib" as existing work to carry in and finish)
and STATUS.md "next steps" item 2. Survey only: no code was changed, nothing
was committed or pushed.

## Where the evidence comes from

All version-specific results come from the project TKLDev 19.0 build host over
SSH, since this workstation has Python 3.12 only.

```
$ ssh root@2804:710:d0:5:bb3f:380a:f07b:7951 'python3 -V; cat /etc/debian_version'
Python 3.13.5
13.6
```

Trees surveyed (copied to `/root/py313/src` on the VM, removed afterwards):

| Tree | Source | Branch / commit |
| --- | --- | --- |
| fab | TKL/forks/fab | `feat/source-date-epoch`, e828f03 |
| common | TKL/forks/common | `fix/postfix-local-fatal`, c8c0b10 |
| tklbam | TKL/upstream/tklbam | `master`, 31134d3 |
| turnkey-pylib | cloned read-only for this survey | `master`, aff7628 |

There is no `tklbam` and no `turnkey-pylib` under `forks/`, although STATUS.md
records both forks as created on GitHub. `turnkey-pylib` was therefore cloned
read-only from https://github.com/turnkeylinux/turnkey-pylib.git into
a scratch clone of turnkey-pylib, and `tklbam` was read from
`upstream/`. Local clones of the two forks are a prerequisite for the work.

## Summary

| Repository | State under Python 3.13 | Blocking issues | Size of fix |
| --- | --- | --- | --- |
| fab | Works. Already targeted at 3.13 by its own packaging | One unpackaged contrib script uses the removed `crypt` module | Small: one file, one function, and it is not shipped in the .deb |
| common | Works. All seven Python 3 scripts run under 3.13 | None. Three Python 2 files exist but are demo/third-party payload, not build code | Small: delete or port three dead files, no functional change |
| tklbam | Core is Python 2 by design and runs on PyPy2 7.3.23, which is packaged and installed on 19.0. Not broken under 3.13, because it never runs under 3.13 | None for 19.0. The real issue is strategic: the pypy2 dependency, not a syntax port | Large: a full Python 3 port of 68 files, of which 43 do not even parse. Not required for M0 or M1 |
| turnkey-pylib | Does not work. Pure Python 2 library: 22 of 36 modules fail to parse, only 6 import cleanly | Whole library | Medium as a port, but likely zero: nothing in the surveyed set depends on the package any more |

Biggest single blocker: none of the four repositories blocks Python 3.13 on the
19.0 platform today. The one that looks like a blocker, tklbam, is a deliberate
PyPy2 design still supported on Trixie. What BRIEF.md section 8 calls "Python
3.13 compatibility" has, for fab and common, already landed upstream.

## fab

### Byte compilation

```
$ python3 -m compileall -q -f fab
(no output, exit 0)
```

No SyntaxError, no SyntaxWarning, in 15 `.py` files plus the `fab` entry point.

### Imports

```
$ PYTHONPATH=/root/py313/src/fab python3 -c "import fablib.<module>"
fablib, fablib.annotate, fablib.common, fablib.cpp, fablib.help,
fablib.installer, fablib.plan, fablib.removelist, fablib.resolve   -> all ok
```

All nine modules import. Importing them with `-W always::DeprecationWarning`
produced no warnings.

Note for whoever reruns this: importing from inside the fab checkout fails with
`ImportError: cannot import name 'deb822' from 'debian'`, because `fab/debian/`
shadows `python3-debian` as an implicit namespace package. Testing artifact,
not a bug.

### Entry point

`fab --help` works, and all nine subcommands (query, cpp, chroot, install,
plan-annotate, plan-resolve, apply-overlay, apply-patch, apply-removelist)
answer `--help` successfully. `fab cpp` was run end to end on a scratch plan
and produced correct output. `fab plan-annotate` failed only with
`pool_lib.PoolError: no pool found`, which is environmental.

### Removed and changed APIs

`TKL/forks/fab/contrib/cryptpass.py:20` `import crypt`, and `:62`
`print(crypt.crypt(password, random_salt()))`.

```
$ python3 fab/contrib/cryptpass.py
  File "/root/py313/src/fab/contrib/cryptpass.py", line 20, in <module>
    import crypt
ModuleNotFoundError: No module named 'crypt'
```

`crypt` was removed in Python 3.13 (PEP 594). Mitigating facts:
`debian/fab.install` ships only `share/*` and `contrib/fab-*`, so
`cryptpass.py` is not in the package; and the code uses a two character DES
salt from `random.randint`, which was already the wrong thing to do. The fix is
to drop the script or reimplement it with `passlib`, `libxcrypt` via ctypes or
an `openssl passwd -6` subprocess.

No hits in fab for `imp`, `distutils`, `asyncore`, `asynchat`, `cgi`,
`telnetlib`, `pipes`, `nntplib`, `smtpd`, `locale.getdefaultlocale`,
`datetime.utcnow`, `ssl.wrap_socket`, `SafeConfigParser`, or the deprecated
`unittest` aliases. Same for common: zero hits on the whole list, and no
`python`/`python2` invocations in its shell and make fragments.

### Packaging

`fab/debian/control` already declares `python3-all (>= 3.13)` and
`X-Python3-Version: >= 3.13`, and `pyproject.toml` builds with setuptools and
ships `py.typed`. fab has been modernized for 3.13 upstream.

### Tests

No pytest or unittest suite. `fab/tests/` holds `regtest.sh` plus two fixture
scripts (`parseopts.py`, `ptyfork.py`) that the shell regtest drives.
`regtest.sh` hardcodes `FAB=/turnkey/projects/fab/fab` and performs real builds
against a package pool, so it was not run: this survey must not run builds or
touch `/turnkey`. **UNVERIFIED**: whether `fab/tests/regtest.sh` passes
under 3.13.

## common

### Byte compilation

```
$ python3 -m compileall -q -f common
*** Error compiling 'common/overlays/helloworld/usr/local/src/helloworld/helloworld.py'...
  File "...", line 4
    print "hello world"
SyntaxError: Missing parentheses in call to 'print'.

*** Error compiling 'common/overlays/ninjux/usr/local/bin/quicktile.py'...
  File "...", line 914
    print "Keybindings defined for use with --daemonize:\n"
SyntaxError: Missing parentheses in call to 'print'.
```

Both are Python 2 and both are inert:

- `common/overlays/helloworld/usr/local/src/helloworld/helloworld.py:4` is
  sample content for the revision control demo repositories built by
  `common/conf/create-repos` (referenced from
  `common/mk/turnkey/revisioncontrol.mk:1`). It is committed into a demo git
  and svn repository, never executed.
- `common/overlays/ninjux/usr/local/bin/quicktile.py:914` is a vendored
  third-party window tiler in the ninjux desktop overlay, shebang
  `#!/usr/bin/env python2`, not referenced from any plan in `common/plans/`.

A third Python 2 file has no `.py` extension and so is missed by `compileall`:
`common/overlays/desktop/usr/local/bin/gvim:1`, shebang `#!/usr/bin/python`.
Same desktop line, same status. No SyntaxWarning anywhere in the tree.

### The Python 3 scripts

Seven files carry a `python3` shebang or are imported as Python 3. All were run
with `--help` on the VM under 3.13. Paths are under `common/overlays/`:

| Script | Result |
| --- | --- |
| samba-fileserver/usr/lib/inithooks/bin/setpass.py | prints usage, ok |
| samba-fileserver/usr/lib/inithooks/bin/sambapass.py | prints usage, ok |
| pgsql/usr/lib/inithooks/bin/pgsqlconf.py | prints usage, ok |
| web2py/usr/lib/inithooks/bin/web2py.py | prints usage, ok |
| tomcat/usr/lib/inithooks/bin/tomcat.py | prints usage, ok |
| mysql/usr/lib/inithooks/bin/mysqlconf.py | needs `pymysql`; ok with a stub |
| mysql/usr/lib/confconsole/plugins.d/System_Settings/Mysql_perf_info.py | imports, exit 0 |

`mysqlconf.py:26-27` imports `pymysql` and `pymysql.cursors`, which are not
installed on the build host (`python3-pymysql` is a runtime dependency of the
MySQL appliances, not of TKLDev). With a minimal `pymysql` stub on
`PYTHONPATH`, the script parses its options and prints usage correctly, so the
import failure is environmental, not a 3.13 problem. **UNVERIFIED**: the
database code paths in `mysqlconf.py` against a real MariaDB under 3.13.

### Removed APIs and tests

No hits for any item on the 3.12/3.13 removal list (covered in the fab section
above). common has no pytest or unittest code.

## tklbam

### Which parts are Python 2 and which are Python 3

This has to be settled before any failure is reported. The packaging is
unambiguous.

- `debian/control` Build-Depends and Depends both list
  `turnkey-pypy2 | turnkey-pypy2-full`; Depends also lists
  `turnkey-python3-boto3 | python3-boto3`.
- `debian/rules` has `override_dh_shlibdeps:` with the comment "don't try to
  link libs - won't work because we build against pypy".
- 24 files carry the shebang `#!/usr/lib/tklbam-pypy2/bin/pypy`, plus one
  `#!/usr/bin/env python`. All of `lib/` including `lib/pylib/` is in that set.
- `debian/tklbam.install` installs `lib/*` into `/usr/lib/tklbam/`, and
  `debian/tklbam.links` links `/usr/bin/tklbam` to `/usr/lib/tklbam/cmd.py`,
  which starts with the pypy shebang.
- Exactly two files are Python 3: `aws_cred_file.py` and
  `contrib/fixclock-hook`, both `#!/usr/bin/python3`. There is no `setup.py`,
  and `SET_PYPY_TESTING_ENV` exists to put `/usr/lib/tklbam-pypy2/bin` on
  `PATH` "for testing py2 commands".

On the 19.0 build host this is a working, supported arrangement:

```
$ dpkg -l | grep -iE 'pypy|tklbam'
ii  tklbam          1.5.3+2+g31134d3   TurnKey Backup and Migration agent
ii  turnkey-pypy2   7.3.23+turnkey1    PyPy2 python runtime for use by TKLBAM

$ apt-cache policy turnkey-pypy2
  Candidate: 7.3.23+turnkey1
     999 http://archive.turnkeylinux.org/debian trixie/main amd64 Packages

$ tklbam-status
TKLBAM (Backup and Migration):  NOT INITIALIZED
```

The Python 2 core runs correctly on Trixie. Reporting it as a "Python 3.13
failure" would be wrong.

### The Python 3 parts

```
$ python3 -c 'import aws_cred_file'   -> ok
$ python3 aws_cred_file.py            -> AWS_ID (AWS account ID) must be set in env
$ python3 contrib/fixclock-hook       -> ValueError: not enough values to unpack
```

Both behave correctly under 3.13; the second only complains about missing
arguments. No 3.13 problem in the Python 3 surface of tklbam.

### Size of a hypothetical port

```
$ python3 -m compileall -q -f tklbam     (first failures)
tklbam/lib/backup.py:133      0777 literal
tklbam/lib/changes.py:132     except OSError, e
tklbam/lib/cmd_backup.py:209  except getopt.GetoptError, e
tklbam/lib/cmd_escrow.py:95   0600 literal
tklbam/lib/cmd_internals/cmd_create_profile.py:209   backtick repr
tklbam/lib/cmd_internals/cmd_merge_userdb.py:50      print statement
...
43 of 68 .py files fail to parse under Python 3.13.
```

25 files already parse as Python 3, among them `lib/cmd.py`, `lib/cliwrapper.py`,
`lib/pkgman.py`, `lib/userdb.py`, `lib/utils.py`, `lib/pathmap.py`,
`lib/passphrase.py`, `lib/version.py`, the two PostgreSQL internals, and 7 of
the 12 vendored `lib/pylib/` modules. Parsing is not running: they still target
pypy2.

### Removed and changed APIs

Dormant today, because the code runs on PyPy2, but the first things a port
would hit. Paths are relative to the tklbam repository.

- `lib/cliwrapper.py:14` `import imp`, `:33` `imp.find_module(modname, path)`,
  `:34` `imp.load_module(modname, *args)`. `imp` was removed in Python 3.12;
  the replacement is `importlib.util`.
- `lib/pkgman.py:39` `re.split(':\s*', line, 1)` raises
  `SyntaxWarning: invalid escape sequence '\s'`, the only one in all four
  trees. Two issues in one line: the unraw `'\s'`, and the positional
  `maxsplit`, deprecated since 3.13, which must become `maxsplit=1`.

No hits for `distutils`, `asyncore`, `asynchat`, `cgi`, `crypt`, `telnetlib`,
`pipes`, `nntplib`, `smtpd`, `locale.getdefaultlocale`, `datetime.utcnow`,
`ssl.wrap_socket`, `SafeConfigParser`, or the deprecated `unittest` aliases.

### Tests

No pytest or unittest suite. `tests/` holds standalone pypy2 scripts and shell
scripts; `regtest/regtest.sh` exercises a real backup. Neither can run under
3.13, and neither was run here: the regtest touches live system state on the
build host.

## turnkey-pylib

### Byte compilation

```
$ python3 -m compileall -q -f turnkey-pylib
22 of 36 modules in pylib/ fail to parse.
```

Failing: cliconf, command, conffile, debug, debversion, fixedmap, flock,
forked, git, hashstore, lazyclass, localmsg, metahook, multiprocessing_utils,
netinfo, paged, paths, pidlock, sighandle, stdtrap, threadloop, udevdb.
Representative first failures: `pylib/cliconf.py:232` backtick repr,
`pylib/command.py:109` `except IOError, e:`, `pylib/debug.py:67` backtick repr,
`pylib/debversion.py:220` print statement, `pylib/metahook.py:142`
`TabError: inconsistent use of tabs and spaces`.

### Imports

Of the 14 modules that parse, only 6 import (`ar`, `fifobuffer`, `fileevent`,
`parsedate`, `popen4`, `retry`). The other 8:

```
debian_pylib  ModuleNotFoundError: No module named 'distutils'
executil      ModuleNotFoundError: No module named 'commands'
sysversion    ModuleNotFoundError: No module named 'commands'
state         ModuleNotFoundError: No module named 'ConfigParser'
temp          NameError: name 'file' is not defined
tktimeout     ModuleNotFoundError: No module named 'Tkinter'
chroot        SyntaxError (raised by a Python 2 module it imports)
debinfo       SyntaxError (raised by a Python 2 module it imports)
```

6 of 36 modules usable: not a compatibility gap, an unported Python 2 library.

### Removed and changed APIs

Paths below are relative to the read-only clone at
the scratch clone of turnkey-pylib.

- `setup.py:5` `import commands`, `setup.py:7` `from distutils.core import setup`
- `pylib/debian_pylib.py:4` `from distutils.core import setup as _setup`
- `pylib/executil.py:16`, `pylib/git.py:16`, `pylib/paged.py:19`,
  `pylib/stdtrap.py:513` `import commands`
- `pylib/state.py:25` `from ConfigParser import ConfigParser`
- `pylib/tktimeout.py:10` `from Tkinter import *`

`distutils` was removed in Python 3.12; `commands`, `ConfigParser` and
`Tkinter` are Python 2 module names.

### Packaging, and does anything still need it?

`debian/control` declares `python-all (>= 2.6.6-3~)`, `dh-python2` and
`X-Python-Version: >= 2.6`; `setup.py` calls `file("debian/control")`. The
package has never been ported, and the branch list is master and 15.x only.

Grepping the whole `TKL/forks` and `TKL/upstream` set, nothing depends on the
`turnkey-pylib` package. tklbam actively rejects it:
`upstream/tklbam/debian/control:23` and `:30` list `turnkey-pylib` under both
Conflicts and Replaces, and tklbam vendors 12 of its modules under `lib/pylib/`
(command, conffile, executil, fifobuffer, fileevent, paths, pidlock, popen4,
retry, stdtrap, temp) as pypy2 code. fab imports none of it.

So the honest size of this fix is: porting turnkey-pylib is a medium job
(36 modules, 22 of them unparseable, no tests), and it may be work that nobody
needs. Confirming the package is dead is the prerequisite to deciding.

## Recommended order of work

1. **Clone the tklbam and turnkey-pylib forks** into `TKL/forks/` with the
   upstream remote attached, as STATUS.md assumes. Unblocks branch work on both.
2. **Decide whether turnkey-pylib is dead.** One grep across the tier-1
   appliance repositories settles it. Unblocks dropping a third of this work
   item from BRIEF section 8 outright.
3. **fab: remove or reimplement `contrib/cryptpass.py`.** One file, one PR,
   worth sending upstream too, since fab is 3.13-clean otherwise.
4. **common: delete or port the three Python 2 files** (`helloworld.py`,
   `quicktile.py`, `desktop/.../gvim`). All three are in overlays outside the
   tier-1 catalog, so deleting them is also a catalog-honesty decision
   (BRIEF section 3 item 5).
5. **Add a `compileall` gate to CI for fab and common** once 3 and 4 land.
   This is what actually prevents section 8 from reopening.
6. **tklbam: treat pypy2 as a design question, not a porting task.** Not
   blocking 19.0; should not start before M1. When it does, `lib/cliwrapper.py`
   (the `imp` based dispatcher) and `lib/pkgman.py:39` are the first files, and
   the 25 already-parsing files are the natural first slice. It interacts
   directly with BRIEF section 5.6 and `tklbam-python-boto`, so plan them
   together.

Items 3-5 are the whole of the near-term work and are small. Item 6 is the only
large piece, and it is deferrable.

## Open questions for the maintainer

1. **Is turnkey-pylib retired?** Nothing in the surveyed set depends on the
   package and tklbam Conflicts with it. If retired, it comes off the section 8
   list and the fork can be archived. If a tier-1 appliance still pulls it in,
   it needs a port and an owner.
2. **How long does Keel carry PyPy2 for tklbam?** `turnkey-pypy2 7.3.23` is in
   the TurnKey Trixie archive today. Keel must eventually rebuild that package
   itself, port tklbam to Python 3, or replace tklbam. A platform-lifetime
   decision that belongs with the section 5.6 Hub decoupling work.
3. **What replaces `crypt` in fab?** `passlib`, a `libxcrypt` ctypes binding, or
   `openssl passwd -6`. The two character DES salt cannot be carried forward
   either way, so this is a small security decision, not a mechanical port.
4. **Do the unmaintained desktop overlays stay in common?** `ninjux`, `desktop`
   and the `helloworld` demo are the only Python 2 left there. Deleting beats
   porting dead code, but it is a catalog scope decision.
5. **Does section 8 already consider fab and common done?** Both are 3.13-clean
   today and fab's packaging declares 3.13. If the carried-in work is an
   unpushed branch somewhere, find it before anyone redoes it.

## Cleanup

Created on the build host and then removed: `/root/py313/src/` (the four
trees), `/root/py313/venv/` (an empty venv; the host has no `pip` or
`ensurepip`, so nothing was installed and no pytest run was possible),
`/root/py313/stub/` (a two file `pymysql` stub used to test `mysqlconf.py`),
`/root/py313/` itself, and the scratch files `/tmp/t.plan`, `/tmp/t2.plan`,
`/tmp/e` from the fab smoke test.

Nothing under `/turnkey`, `/usr/lib/python3`, `/etc` or any installed package
was touched, no build was run, and nothing was installed with apt.
