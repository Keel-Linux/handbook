# Core login welcome, keel-core issue #7 (2026-10-29)

Issue: Keel-Linux/keel-core#7, "An appliance still announces itself as
TurnKey at login". The issue closes when the operator is welcomed once, as
Keel, with every system fact of the old banner (load, memory, processes,
swap, usage of /, addresses), and with no text about a service that Keel
does not use (TKLBAM).

## Image

- Template: `debian-13-keel-core_19.0-11_amd64.tar.zst` (stable-1 Core).
- sha512 on hw12-br1 is the same as the public mirror file
  `https://mirror.keellinux.org/images/debian-13-keel-core_19.0-11_amd64.tar.zst.sha512`:
  `fad1592a647147a4936a657b211bdef1197fc2298ee0adc3d2a0417c3630094dcb6c58f425e787972ed3dbdceb4623914cd32d8b89de29fbc07718e62e6f3288`

## Test CT

Host hw12-br1 (BR1). CT 9295, hostname `issue7-core`. The CT used the
pattern from `evidence/2026-10-13-step12-boot-checks.md`:

    pct create 9295 local:vztmpl/debian-13-keel-core_19.0-11_amd64.tar.zst \
      --hostname issue7-core --unprivileged 1 --features nesting=1 \
      --rootfs local-lvm:8 --memory 1024 --cores 1 \
      --net0 name=eth0,bridge=vtnet88,firewall=1,ip=dhcp,ip6=dhcp,tag=5,type=veth

Preseed `/etc/inithooks.conf` was written on the mounted rootfs (ROOT_PASS
random, HUB_APIKEY/SEC_ALERTS/SEC_UPDATES/REBOOT=SKIP). The CT was
destroyed after the test (`pct destroy 9295 --purge`).

First boot, journal:

    Oct 29 18:08:39 issue7-core inithooks[1894]: Inithooks run completed
    Oct 29 18:08:41 issue7-core inithooks[1904]: Confconsole started, Inithooks exiting

Versions (`dpkg-query -W`):

    confconsole      2.2.3+keel15
    inithooks        2.3.6+keel27
    keel-core        0.1.3
    turnkey-sysinfo  1.1.0+keel2

## Login output

Two interactive SSH logins as root
(`ssh -tt root@2804:710:d0:5:6db1:1270:df59:26e`, 18:09:10 and 18:09:18 UTC).
Both logins show the same output, with escape codes removed:

    Keel Linux core 19.0-trixie-amd64

    IPv6 SSH:  root@2804:710:d0:5:6db1:1270:df59:26e
    IPv4 SSH:  root@10.88.5.242

    Welcome to issue7-core, Keel Linux 19.0 (Debian 13/Trixie)

      System information for Thu Oct 29 18:09:10 2026 (UTC+0000)

        System load:  14.51            Memory usage:  20.3%
        Processes:    34               Swap usage:    0.0%
        Usage of /:   9.6% of 7.78GB   IP address for eth0: 10.88.5.242

        This system is not initialized yet: run keel-init to set it up.

        WARNING: Firstboot hooks will rerun on reboot!

        For Advanced commandline config run:    confconsole

      For more info see: https://github.com/Keel-Linux/confconsole

`grep -ciE 'turnkey|tklbam|hub'` on each capture: 1 match. The match is
the `github.com` link, not TurnKey or TKLBAM text.

The console title of confconsole is "Keel Linux Configuration Console".

## Result against issue #7

| Item | Result |
|------|--------|
| One welcome line | PASS: one `Welcome to ...` line |
| Welcome names Keel | PASS: `Keel Linux 19.0 (Debian 13/Trixie)` |
| No TurnKey name | PASS: 0 matches |
| No TKLBAM text | PASS: 0 matches |
| Load, memory, processes, swap, usage of /, address | PASS: all six present |

Verdict: PASS. Issue #7 is met on the stable-1 Core image.

## Notes outside issue #7

- The firstboot warning is from the test harness, not from the image. The
  preseed file was written from the host into an unprivileged CT, so its
  owner was `nobody`. `firstboot.d/98finalize` could not blank it, failed
  with exit code 1, and did not set `RUN_FIRSTBOOT=false`. The stable-1 CTs
  9231 and 9232 show `RUN_FIRSTBOOT=false`. For the next test, change the
  owner of the preseed file to the CT root (`chown 100000:100000`).
- The "more info" link points to GitHub. The source of the project is now
  git.pop.coop, and GitHub is a push mirror.
