# 0071: Boot defaults: a hidden GRUB menu, lz4 initrd

Date: 2026-10-27
Status: **decided by the maintainer, 2026-10-28**. Evidence:
common/evidence/2026-10-27-boot-defaults.md.

## What was decided

- `common/conf/keel-boot/grub-timeout` sets `GRUB_TIMEOUT_STYLE=hidden`
  and `GRUB_TIMEOUT=1`. The menu is hidden, not removed. On the Proxmox
  noVNC console, a serial console or EFI, a held Shift at power on is not
  reliable; Esc opens the menu, and the cost is one second.
- `common/conf/keel-boot/initramfs-compress` sets `COMPRESS=lz4` and
  rebuilds the initrd. lz4 decompresses several times faster than zstd;
  the initrd is a little larger, which the boot pays back.
- `keel-core/conf.d/main` masks `systemd-binfmt.service` and
  `proc-sys-fs-binfmt_misc.automount`: the appliance uses no binfmt
  handler, and the service cost 828 ms in the boot's critical chain.
  An appliance that later installs qemu-user or wine can unmask them.
- `inithooks/bin/keel-host-keys` runs the three SSH host keys, the TLS
  pair and the snakeoil pair in parallel. They write different files;
  the service was 1066 ms with virtio-rng, against 1327 ms for the apt
  sequential build (the earlier 1719 ms run had no RNG and 2 vCPUs).
- Nothing else: `MODULES=dep` is not taken (the image boots hardware it
  was not built on), and `mitigations=off` is not taken (security).
- The changes are in the boot layer (`buildtasks/products/boot` applies
  `keel-boot`), so the Core layer test in `04`/`05` does not measure
  them; the boot-layer test is separate.

## Why

The Core image's boot has a three second GRUB wait and a zstd initrd
(`MODULES=most`). Both are Debian defaults, neither is a Keel choice.
A hidden menu with a one second wait keeps recovery reachable where a
held Shift does not work.

## Consequences

- The installed image boots without a visible menu; press Esc for
  recovery. The hidden menu costs one second.
- The initrd is larger and decompresses faster. `MODULES=most` stays, so
  the image still boots hardware the build host did not have.
- The binfmt mask is an image policy: a later qemu-user or wine
  installation must unmask the two units.
- `plans-boot.bats` (7 tests), `keel-core/tests/image-conf.bats` (13)
  and `inithooks/tests/test-host-keys.bats` (22) pass. The Core boot
  measured 5.336 s with `keel-host-keys` 1.152 s, networking 898 ms,
  systemd-binfmt 828 ms and postfix 405 ms. After the binfmt mask a boot
  was 4.866 s (2.877 s userspace), with networking 1.581 s,
  keel-host-keys 1.327 s, dev-vda 834 ms and postfix 364 ms; binfmt is
  gone from blame. A 2-vCPU test disk without virtio-rng then measured
  5.881 s and keel-host-keys 1.719 s, an entropy-bound outlier. With
  `-smp 4`, `-device virtio-rng-pci` and a 2G disk the Core boot was
  4.705 s (2.119 + 2.585 s): keel-host-keys 1.066 s, networking 930 ms,
  dev-vda 494 ms and postfix 377 ms. With the six masks and the built
  boot layer (kernel 6.12.113, 43M lz4 initrd) the Core boot is
  4.437 s (2.143 + 2.294 s): keel-host-keys 939 ms, networking 1.126 s,
  dev-vda 435 ms, postfix 374 ms, turnkey-init-fence 256 ms. The final
  Core with the Webmin/Python trims is **4.488 s** (2.095 + 2.393 s):
  keel-host-keys 935 ms, networking 783 ms, dev-vda 477 ms, postfix
  365 ms, turnkey-init-fence 226 ms; 0 failed. The parallel host keys are
  a distinct win over the apt build's 1.327 s. These figures use
  `GRUB_TIMEOUT=0`; the hidden menu adds one second.

## What this amends

Nothing. 0052 keeps the boot layer separate from the appliance layer.
