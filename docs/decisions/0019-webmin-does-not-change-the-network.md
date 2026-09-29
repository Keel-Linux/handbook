# 0019: Webmin does not change the network

Date: 2026-09-29
Status: **accepted**, decided by the maintainer on 2026-09-29.
Implemented in Keel-Linux/common#17.

## The decision

On a Keel appliance, Webmin's Network Configuration module shows the
interfaces, the routes and the resolvers, and changes none of them. It
ships read-only for root and for every Webmin user created later, with its
own configuration page closed. The network is changed in confconsole or at
the command line, never through Webmin, and this is kept deliberately, not
as a limit waiting for a fix.

An operator who needs to change what confconsole does not offer is expected
to do it at the command line: to edit `/etc/network/interfaces`, bring the
interface down and up with ifupdown-ng, and check `/etc/resolv.conf`. Being
able to do that is the bar for changing a machine's network at all.

## Why

1. **Attack surface.** Webmin is a web panel that runs as root on a machine
   reachable from the internet. Every page that can write the network
   configuration is a page that, through a stolen session, a weak password
   or a defect in Webmin, can take the machine off the network or send its
   traffic elsewhere. The fewer root actions the panel exposes, the less a
   compromise of it can do. Reading costs little; writing the network is
   among the most damaging things a panel can do.
2. **The module damages the configuration.** Measured on the core layer
   (common#17, turnkeylinux/tracker#2118): an unchanged save of eth0 drops
   its `inet6 dhcp` stanza, so dhcpcd turns IPv6 off on it, which on an
   IPv6-only network is the whole connection; it drops `dns-nameservers`
   and `hostname`; its Apply calls `/etc/init.d/networking`, which
   ifupdown-ng does not have, after the file is already written. The review
   of the fix also found that the module's own configuration page could
   point its hosts page at any root-writable file.
3. **One surface.** BRIEF section 6 makes confconsole the operator's single
   surface. A second writer of `/etc/network/interfaces` is a second set of
   rules for the same file, and the two already disagreed after one
   Webmin save.

## What would change it

Only a module that writes what ifupdown-ng and dhcpcd expect, proved by
tests against the real programs, shipped from Keel's own Webmin package
(tracker#17), and even then only if the attack surface argument above is
answered, not only the correctness one.
