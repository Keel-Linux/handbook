# 0099: the QEMU guest agent of a Keel machine accepts only an allow-list of commands

Date: 2026-11-26
Status: **accepted, 2026-11-27.** The maintainer gave the direction on
2026-11-26: restrict the agent, strict before comfortable. The code is
merged (`common` pull request 87). A test machine built from the boot
layer passed on a real node (handbook evidence pull request 222): the
IP addresses show in Proxmox, `qm guest exec` and `qm guest passwd` are
refused, a backup with freeze and a shutdown from Proxmox work. The
maintainer accepted the note on 2026-11-27.

Sources, read on 2026-11-26: `common` branch `19.x` (`plans/keel-boot`),
`buildtasks` branch `19.x` (`products/boot/Makefile`), `keel`
`keel/layers/container.py`, the Debian 13 package
`qemu-guest-agent 1:10.0.13+ds-0+deb13u1`, and `qemu-server` of Proxmox
VE on `master` (`2f13e34`, Proxmox VE 9) and on `stable-bookworm`
(Proxmox VE 8).

## What the problem is

`qemu-guest-agent` is in the boot layer (decision 0052), so a virtual
machine or a real machine installed from the ISO runs it. A container
does not: `keel assemble` refuses a template with the package. The
Debian package ships no configuration file, so the agent accepts every
command. With it, a person with VM rights on the Proxmox host can run
a command as root in the guest (`qm guest exec`), read and write any
file, set a password, add an SSH key and set the clock. This goes
around the SSH keys, the firewall of 0097 and the declared state.

## What Keel does

The boot layer installs `/etc/qemu/qemu-ga.conf` (overlay
`overlays/keel-boot` of `common`) with `allow-rpcs`. qemu-ga 10.0 of
Debian 13 reads that file at start and refuses every command that is
not in the list.

Allowed: the commands that Proxmox VE 8 and 9 send by themselves, and
read-only information.

- Sent by Proxmox: `guest-sync-delimited` (before each command),
  `guest-ping` (agent check), `guest-network-get-interfaces` (IP
  addresses on the Summary page), `guest-fsfreeze-freeze`,
  `guest-fsfreeze-thaw` and `guest-fsfreeze-status` (backup in snapshot
  mode, snapshot, clone, replication), `guest-fstrim` (after a disk
  move or migration, when `fstrim_cloned_disks` is on), `guest-shutdown`
  (shutdown with the agent option on).
- Read-only, available through `qm agent`: `guest-sync`, `guest-info`,
  `guest-get-osinfo`, `guest-get-host-name`, `guest-get-time`,
  `guest-get-timezone`, `guest-get-fsinfo`, `guest-get-disks`,
  `guest-get-vcpus`, `guest-get-memory-blocks`,
  `guest-get-memory-block-info`, `guest-fsfreeze-freeze-list`.

Refused: every other command. That includes `guest-exec` and
`guest-exec-status`, all `guest-file-*`, `guest-set-user-password`,
`guest-set-time`, `guest-set-vcpus`, `guest-set-memory-blocks`, all
`guest-ssh-*`, all `guest-suspend-*`, `guest-get-users`, and the
statistics commands of qemu-ga 10 (`guest-get-load`,
`guest-get-cpustats`, `guest-get-diskstats`,
`guest-network-get-route`). A command that a later qemu-ga adds is
refused until this list names it.

## What changes for the operator

- `qm guest exec`, `qm guest passwd` and the file read and write of
  the Proxmox API fail with "the command is not allowed".
- Proxmox does not use `guest-suspend-*` by itself. `qm suspend
  --todisk` saves the VM state from the host and does not need it.
- Proxmox sends `guest-set-time` by itself only when the VM option
  `sync-time-on-resume` is on (default off). With the option on, that
  step fails after a resume, a rollback with RAM or a migration. Keep
  the option off. The NTP service of the guest sets the clock.
- An image built before this change keeps an agent that accepts every
  command. A machine in the field gets the list only from a new image
  or by hand.

## How it is tested

- `common` `tests/qemu-ga-conf.bats`: the exact list, no other overlay
  or conf has the file, and the container build applies no keel-boot
  overlay. Where qemu-ga is installed, it starts the agent on a unix
  socket with the file and checks the enabled commands and the refusals.
- On a real Proxmox VM from the ISO, before this note is accepted: the
  Summary page shows the IP addresses; `qm agent ID
  network-get-interfaces` answers; `qm guest exec ID -- id` is refused;
  a backup in snapshot mode logs the freeze and the thaw; a shutdown
  from Proxmox stops the VM. The results go into an evidence file.
