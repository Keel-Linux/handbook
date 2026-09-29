# 0021: A resource monitor that tells the operator what to do

Date: 2026-09-29
Status: **decided 2026-09-29** (see "Decided" at the end). Asked for by
the maintainer on 2026-09-29: an
internal monitor that notifies the operator, by email, Telegram and
whatever else is worth it, when a disk fills, memory runs short, or CPU
or network are overused, so that they grow the disk or the memory in
time; and, in a replicated set (decision 0020), one node watching the
others, so that a node that cannot speak for itself, a full disk
included, is still reported.

## What exists today, and why it is not enough

`security.alerts` (the secalerts hook, converged by `apply` since
keel#36) sends one kind of mail: security updates. Nothing on an
appliance watches its own resources. The first sign of a full disk is
the application failing, and on a full disk the mail that could have
warned about it cannot be queued either, because postfix needs disk to
queue. Adding checks to the secalerts path would not fix that: the
channel itself fails in the case that matters most.

## The monitor: monit, configured from the spec

Measured with `apt-cache policy` on trixie, 2026-09-29:

| Package | Version | Verdict |
| --- | --- | --- |
| monit | 1:5.34.3-1 | proposed |
| prometheus-node-exporter | 1.9.0-1+b4 | not proposed: it exports metrics and alerts on nothing without a Prometheus and an Alertmanager elsewhere |
| collectd | 5.12.0-26 | not proposed: it collects, and its thresholds plugin is not a notifier with recovery and reminders |
| netdata | absent | out: not in the archive, which costs the sovereignty claim of 0013 |

monit is one small daemon that already checks what was asked for, on a
cycle, with the rules an alert needs: a condition must hold for N cycles
before it fires, a recovery is reported, and a reminder repeats while the
condition lasts. It checks a filesystem's space and inodes, memory, swap,
CPU and load, a network interface's link and throughput, processes, and a
remote host's ports. Writing a sampler of our own would redo that, less
well.

`keel spec apply --system` converges it like any other field: a new
`monitor` section of the spec is rendered into
`/etc/monit/conf.d/keel.conf`, and `keel diff` compares it. The operator
writes thresholds, not monit syntax.

```yaml
monitor:
  enabled: true
  checks:
    disk: {warn: 80, critical: 90}       # percent used, every mounted filesystem
    inodes: {critical: 90}
    memory: {warn: 85, for_minutes: 5}
    swap: {warn: 50, for_minutes: 5}
    cpu: {warn: 90, for_minutes: 10}
    load_per_core: {warn: 2.0, for_minutes: 10}
    network:
      eth0: {link: true, max_mbit: 800, for_minutes: 5}
  notify:
    email: true                          # security.alerts' address
    telegram:
      chat_id: "-1001234567890"
      token: {file: /etc/keel/secrets/telegram_token}
    ntfy:
      url: https://ntfy.example.org/keel-blog
      token: {file: /etc/keel/secrets/ntfy_token}
    webhook:
      url: https://hooks.example.org/keel
```

Defaults apply to every check the section leaves out, so `enabled: true`
alone gives a useful monitor. Network throughput has no default: what is
too much depends on the link, so it is watched only when declared.

## Where the notification goes, and why not only email

A monit alert runs `keel notify`, which sends to every declared channel:

| Channel | Why it is worth it |
| --- | --- |
| email | already configured on every appliance (`security.alerts`); best effort, since it needs disk to queue |
| Telegram | the Bot API is one HTTPS call, and reaches a phone |
| ntfy | push to a phone over plain HTTPS, and self-hostable, so no third party is required |
| webhook | one JSON POST; Matrix, Slack, Discord and Mattermost all accept one, without code for each here |

`keel notify` writes nothing to disk on its way: it reads the message
from monit's environment and the tokens from their secret files, and
posts over HTTPS. So on a full disk the HTTPS channels still work where
email does not. Tokens never reach an argument vector, a log line or the
monit configuration; they are secret references, as elsewhere in the
spec.

**Every message says what to do**, not only what happened:

```
blog (2001:db8:1::10): / is 92% full (critical at 90%).
Grow the disk: in Proxmox, pct resize 101 rootfs +10G (container) or
qm resize 101 scsi0 +10G then growpart and resize2fs (VM).
Largest directories: /var/lib/mysql 18G, /var/log 4.1G.
```

The hints name the hypervisor commands only when the machine can tell
what it runs on (the LXC marker, `systemd-detect-virt`), and never run
them: growing a disk is the host's operation.

## In a replicated set (decision 0020)

Each node's monit also watches its peers over WireGuard: that the peer
answers, and the peer's own monit status. monit's HTTP interface is
bound to the WireGuard address and localhost only, read-only, with
credentials. So a node that is down, or cannot send (a full disk, a
broken network), is reported by another one. Only one node sends the
report about a peer, the elected primary, or the lowest-addressed
healthy node while there is no election, so a failure is announced once,
not twice.

This part waits for the overlay (0020, step 2). A standalone appliance
gets everything else first.

## What it does not do

- Act on its own: it never grows a disk, restarts a service or kills a
  process. monit can; the configuration keel writes does not ask it to.
  An appliance that restarts things behind the operator's back is harder
  to reason about than one that says what is wrong.
- Depend on the TurnKey Hub or on Keel Cloud (brief problem 7): every
  channel is one the operator declares.
- Expose monit's web interface on a public address.

## How it is tested

The renderer and `keel notify` under `--root` and against a local HTTPS
server, like every other field. On the build host, a container whose
disk is filled on purpose (a loop-mounted filesystem, filled with
`fallocate`) must produce a message on a local ntfy endpoint with its
own disk at 100%, and a recovery message once the file is removed.

## Decided 2026-09-29

- **The channels are email, Telegram, ntfy and webhook**, all four.
- **The defaults are the ones above**: disk 80 percent to warn and 90
  critical, inodes 90, memory 85 for 5 minutes, swap 50 for 5 minutes,
  CPU 90 for 10 minutes, load 2 per core for 10 minutes; network only
  when declared.
- **Off unless the spec enables it.** Without a declared channel there is
  nobody to tell; a first boot question in the init fence can come later.
- **Built right after the network field of keel#35**, before M3's
  orchestrated upgrade: it is small, and it protects the appliances that
  already run.
