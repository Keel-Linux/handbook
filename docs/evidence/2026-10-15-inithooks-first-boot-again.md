# Evidence: the first boot inithooks ran again on each reboot

Date: 2026-10-15, 20:55 to 21:40 UTC.
Issue: keel#155, item 6 (the image notes).
Fixes: Keel-Linux/common#55 (`35pgsqlpass`) and Keel-Linux/inithooks#47
(the `Dialog` of `libinithooks`).

Machines:

- Test host: hw12-br1 (`2804:710:d0:2::12`).
- Test CT: 9081, new, from
  `local:vztmpl/debian-13-keel-postgresql_19.0-6+step12_amd64.tar.zst`,
  unprivileged, `pct create --password` with a random password. The CT
  was removed after the test.
- CTs 9054 and 9062 belong to another test. This test did not touch them.

Output is trimmed.

## Summary

| Item | Result | Numbers |
| --- | --- | --- |
| 1. The cause | Found | `35pgsqlpass` draws its password screen on tty1. Nobody is attached. The first boot stops there, and `98finalize` does not run. |
| 2. Reproduction | PASS | After 300 s, `RUN_FIRSTBOOT=true`. A reboot ran the first boot again. The ED25519 host key changed. |
| 3. The fix on the CT | PASS | With the hook of common#55, the first boot ended in 20 s. `RUN_FIRSTBOOT=false`. |
| 4. Reboot after the fix | PASS | No first boot run. The host key and the root password state stayed the same. |
| 5. The hostname | Not inithooks | Proxmox writes `/etc/hostname` from the CT configuration at each start. |

## 1. The first boot of a new CT

```
$ pct create 9081 local:vztmpl/debian-13-keel-postgresql_19.0-6+step12_amd64.tar.zst \
    --hostname ihtest --unprivileged 1 ... --password <random>
$ grep RUN_FIRSTBOOT /etc/default/inithooks      # in the template
RUN_FIRSTBOOT=true
$ pct start 9081
# 60 checks, 5 s apart
60 active RUN_FIRSTBOOT=true
```

`/var/log/inithooks.log` at that time:

```
INFO: first boot notices not drawn: the console has no size, nobody is attached to it
INFO: the first boot questions are not asked, and the hooks print into /var/log/inithooks.log
...
INFO: [10regen-sshkeys] running
...
INFO [turnkey-sudoadmin]: user_state root unlock
passwd: password changed.
...
INFO: [30rootpass] not asked, nobody can answer (the console has no size, nobody is attached to it): ...
INFO: [31fqdn] not asked, nobody can answer ...
INFO: [35pgsqlpass] running
```

The process tree:

```
root  1482  /bin/bash /usr/lib/inithooks/run
root  3505   \_ /bin/bash -e /usr/lib/inithooks/firstboot.d/35pgsqlpass
root  3506       \_ /usr/bin/python3 /usr/lib/inithooks/bin/pgsqlconf.py --user=postgres --pass=
root  3508           \_ /usr/bin/dialog --file /tmp/pythondialog.tmp_oaty3e_
```

`35pgsqlpass` comes from `common/overlays/pgsql`. With no `DB_PASS`,
`pgsqlconf.py` asks the password in a `dialog` screen. `30rootpass` and
`31fqdn` ask `console_unattended` first, and `35pgsqlpass` did not. The
screen waits for an answer that nobody can give.

## 2. A reboot runs the first boot again

```
$ ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub     # before
256 SHA256:ANtKbNWgU21DgIrCVa3wmDqqqfkNVTt0m/2Bx3J9b6c root@ihtest (ED25519)
$ echo drift-test > /etc/hostname; hostname drift-test
$ pct reboot 9081
$ ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub     # after
256 SHA256:XqPK3+gdfqRul4+KLdBe3pkCgPR/tdHuUrOp5/NCjjY root@ihtest (ED25519)
$ hostname; cat /etc/hostname
ihtest
ihtest
$ grep -c "Running firstboot scripts" /var/log/inithooks.log
2
$ tail -1 /var/log/inithooks.log
INFO: [35pgsqlpass] running
```

The host key changed, and the first boot stopped at `35pgsqlpass` again.
This is the behavior of CTs 9062 and 9054 on 2026-10-14. On each run,
`29sudoadmin` writes the root password state again, which explains the
locked root on 9062.

The hostname came back to `ihtest`, the name in the CT configuration.
Proxmox writes `/etc/hostname` at each start. The `postgres` name of CT
9054 is its Proxmox name, so the change of hostname is not an effect of
inithooks.

## 3. The fix on the CT

The hook of common#55 replaced the one in the CT:

```
27f23bfccb197c2420e93097f230ca3468ce22823b43d0f0495a62f12b8da738  common: overlays/pgsql/.../35pgsqlpass
27f23bfccb197c2420e93097f230ca3468ce22823b43d0f0495a62f12b8da738  CT 9081: /usr/lib/inithooks/firstboot.d/35pgsqlpass
$ pct reboot 9081
done after 20 s
RUN_FIRSTBOOT=false
INFO: [35pgsqlpass] running
INFO: [35pgsqlpass] not asked, nobody can answer (the console has no size, nobody is attached to it): the postgres account keeps no password (local peer authentication only); keel-init asks it
INFO: [35pgsqlpass] successfully completed
INFO: [36pgsqlverify] running
ERR: [36pgsqlverify] failed - exit code 1
INFO: [98finalize] running
INFO: [98finalize] successfully completed
```

`RUN_FIRSTBOOT` was still `true` before this boot, so the first boot ran a
third time, and it ended. `36pgsqlverify` of keel-postgresql fails on
purpose when no database password was declared, and the first boot goes
on.

## 4. Reboot after the fix

```
$ pct reboot 9081
$ grep RUN_FIRSTBOOT /etc/default/inithooks
RUN_FIRSTBOOT=false
$ grep -c "Running firstboot scripts" /var/log/inithooks.log
3
$ ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
SHA256:KmiUob6uqwd089wmBkRKh+uhd4pMJvdZfdGLIWMXUTs      # same as after step 3
$ passwd -S root | cut -d" " -f2
P
```

No first boot run. The host key and the root password state did not
change.

## What the fixes do

- common#55: `35pgsqlpass` uses `console_unattended` of inithooks, as
  `30rootpass` does. With no `DB_PASS` and nobody at the console, it
  writes 1 line and exits 0. `DB_PASS` still sets the password with no
  screen.
- inithooks#47: the `Dialog` of `libinithooks/dialog_wrapper.py` raises an
  error before it draws a widget when `INITHOOKS_UNATTENDED` gives a
  reason. Another hook that asks anyway then fails, `run` logs it, and the
  first boot ends.

Both ship in the next image build. The step 12 templates on BR1 and BR2
still have the old hook.

## Cleanup

```
$ pct stop 9081; pct destroy 9081
```
