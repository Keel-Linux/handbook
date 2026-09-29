# 0021: A resource monitor that tells the operator what to do

Date: 2026-09-29
Status: **decided 2026-09-29** (see "Decided" at the end). Asked for by
the maintainer on 2026-09-29: an internal monitor that notifies the
operator, by email, Telegram and whatever else is worth it, when a disk
fills, memory runs short, or CPU or network are overused, so that they
grow the disk or the memory in time; and, in a replicated set (decision
0020), one node watching the others, so that a node that cannot speak for
itself, a full disk included, is still reported.

## What exists today, and why it is not enough

`security.alerts` (the secalerts hook, converged by `apply` since
keel#36) sends one kind of mail: security updates. Nothing on an
appliance watches its own resources. The first sign of a full disk is
the application failing, and on a full disk the mail that could have
warned about it cannot be queued either, because postfix needs disk to
queue. Adding checks to the secalerts path would not fix that: the
channel itself fails in the case that matters most.

## The monitor: monit, configured from the spec

Measured with `apt-cache policy` on trixie, 2026-09-29; monit's features
checked against the manual page of that package:

| Package | Version | Verdict |
| --- | --- | --- |
| monit | 1:5.34.3-1 | chosen |
| prometheus-node-exporter | 1.9.0-1+b4 | not used: it exports metrics and alerts on nothing without a Prometheus and an Alertmanager elsewhere |
| collectd | 5.12.0-26 | not used: it collects, and its thresholds plugin is not a notifier with recovery and reminders |
| netdata | absent | out: not in the archive, which costs the sovereignty claim of 0013 |

monit is one small daemon that already checks what was asked for, on a
cycle: a filesystem's space and inodes (`check filesystem`), memory,
swap, CPU and load (`check system`), a network interface's link and
throughput per second or over a period (`check network`), processes, and
a remote host's ports. It holds a condition for N cycles before acting
(`for N cycles`). Its `exec` action runs a program with the event in the
environment (`MONIT_EVENT`, `MONIT_SERVICE`, `MONIT_DESCRIPTION`), but
only once when a test fails, so the configuration keel writes asks for
the rest explicitly: `repeat every N cycles` for a reminder while the
condition lasts, and `else if succeeded then exec` for the recovery.
Writing a sampler of our own would redo the rest, less well.

`keel spec apply --system` converges it like any other field: a new
`monitor` section of the spec is rendered into
`/etc/monit/conf.d/keel.conf`, and `keel diff` compares it. The operator
writes thresholds, not monit syntax.

```yaml
monitor:
  enabled: true
  checks:
    disk: {warn: 80, critical: 90}       # percent used
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
    details: true                        # directory sizes in the message
```

The rendering follows what monit can express:

- **Filesystems are listed at apply time.** monit has no wildcard, so
  apply writes one check per real mounted filesystem, leaving out pseudo
  filesystems and the mounts an LXC host provides; a filesystem mounted
  later is watched from the next apply.
- **Warn and critical are two services.** Two thresholds on one check
  share monit's one resource event, so going from critical back to warn
  could report a false recovery. Each level is its own named check, and
  the tests walk warn, critical, warn, ok.
- Defaults apply to every check the section leaves out, so
  `enabled: true` with a channel is a useful monitor. Network throughput
  has no default: what is too much depends on the link, so it is watched
  only when declared.
- **`enabled: true` without a working channel is a validation error**,
  and so is `email: true` while `security.alerts` is `skip`: a monitor
  with nobody to tell is worse than none, because it looks like one.

## Where the notification goes, and why not only email

A monit alert runs `keel notify`, which sends to every declared channel:

| Channel | What is sent, and why it is worth it |
| --- | --- |
| email | to `security.alerts`' address, already configured on every appliance; best effort, since postfix needs disk to queue |
| Telegram | the Bot API's `sendMessage`, one HTTPS call, reaches a phone |
| ntfy | one HTTPS POST, push to a phone, self-hostable so no third party is required |
| webhook | one HTTPS POST whose body is Slack compatible (`{"text": ...}`) plus the structured fields (host, check, value, threshold, level); Slack and Mattermost incoming webhooks take it as it is, and Discord takes it at its webhook URL with `/slack` appended. Matrix has no incoming webhook of its own: it needs a bridge such as hookshot, which then takes this POST |

The HTTPS channels work on a full disk, which email does not:

- `keel notify` reads the event from monit's environment and the tokens
  from their secret files, posts, and writes nothing on its way; it runs
  as `python3 -B`, so not even bytecode is written.
- monit keeps checking and running `exec` when its own state file and
  log cannot be written; it loses its log lines, not its alerts.
- Tokens never reach an argument vector or a log line. The Telegram
  token is part of the request path (`/bot<token>/`), so `keel notify`
  never prints a request URL, not even in an error.

**Every message says what to do**, not only what happened:

```
blog (2001:db8:1::10): / is 92% full (critical at 90%).
Grow the disk on the host, then the filesystem here:
  host (Proxmox, container): pct resize <vmid> rootfs +10G
  here: nothing more, the container sees the new size
Largest directories: /var/lib/mysql 18G, /var/log 4.1G.
```

The machine cannot know its VMID, its disk's name on the host, or even
that the host is Proxmox (`systemd-detect-virt` says `kvm` or `lxc`), so
the host command carries placeholders and names the hypervisor only as an
example. The steps inside the machine are chosen from what it can see:
`findmnt` for the filesystem type and device, and the LVM layout. So
ext4 on a partition gets `growpart` then `resize2fs`, XFS gets
`xfs_growfs`, LVM gets `pvresize` then `lvextend -r`, and a container's
mount point is named by the mount it is, not assumed to be `rootfs`.
Nothing is run: growing a disk is the operator's act on the host.

**Privacy.** A message carries the host name, its address and, with
`details: true`, the names and sizes of its largest directories, to
whichever service the operator declared, Telegram's servers included.
The docs say so where the channels are configured, and `details: false`
leaves the directory list out.

## In a replicated set (decision 0020)

Each node's monit also watches its peers over WireGuard: that the peer
answers, and the peer's own monit status. monit's HTTP interface listens
on the node's WireGuard address only (`use address` takes one), with
local use through `set httpd unixsocket`; it is read-only, and its
credentials live in the monit configuration, mode 0600, the one place a
secret of this feature is written into a configuration file. monit is
ordered after the WireGuard interface, so the address exists when it
binds. A node that is down, or cannot send (a full disk, a broken
network), is then reported by another one.

Who reports: the elected primary, which keel-quorum's majority makes
unique; while there is no election, the lowest-addressed node that sees
itself healthy. A partition between two nodes without an election can
make each report the other, so a failure is normally announced once, and
the note does not promise more.

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
server, like every other field, including warn, critical, warn, ok on one
filesystem and the recovery message. On the build host, a VM (a
container's root is the host's to size) whose root filesystem, the one
holding keel, monit and `/etc/keel/secrets`, is filled as root, reserved
blocks included, must produce a message on a local ntfy endpoint, and a
recovery message once the file is removed.

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
