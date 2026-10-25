# keel#228: file replication resumes after a node restart

Date: 2026-10-25
keel: 0.23.55 (fix in keel/system/filesync.py, line 125-129)
Image: debian-13-keel-wordpress 19.0-11
Platform: BR1 (hw12-br1, 2804:710:d0:2::12), LXC on Proxmox VE
CTs: 9230 (wp228-a, primary), 9231 (wp228-b, replica)
Mode: cloud_simple, single-site pair
Overlay prefix: fd7f:95c4:1538::/64

## Bug

Before 0.23.55, `keel spec apply` used an unscoped sed to set
START_PAUSED on Syncthing folders. The sed also matched `<device>`
entries inside `<folder>` blocks, pausing the peer device. After a
reboot, Syncthing loaded the config with the peer device paused and
never reconnected. File replication stopped until an operator
unpaused the device by hand.

## Fix (keel 0.23.55)

The sed in filesync.py (line 127) now scopes to `/<folder /,/<\/folder>/`,
so only `<folder>` elements get `paused="true"`. Device entries keep
`paused="false"`.

## Test setup

1. Two fresh LXC containers from WordPress 19.0-11 on BR1.
2. Upgraded to keel 0.23.55 via `dpkg -i`.
3. ULA addresses fd00:228::a and fd00:228::b on eth0 (no SLAAC on
   this bridge).
4. `keel mesh create` on A, `keel mesh invite` + `keel mesh join` on B.
5. `keel vip pair`, `keel spec apply --system-only` on both, `keel vip
   promote` on A.

Syncthing configured 4 WordPress folders (uploads, plugins, themes,
languages): sendonly on primary, receiveonly on replica. The peer device
connected and was not paused.

## Evidence: primary reboot

### Before reboot

| Check                         | Result           |
|-------------------------------|------------------|
| Devices paused                | False (both)     |
| Folders paused                | False (all 4)    |
| Connection to peer            | True             |
| test228.txt replicated        | yes              |

### After reboot (before vip check)

| Check                         | Result           |
|-------------------------------|------------------|
| Devices paused                | **False (both)** |
| Folders paused                | True (all 4)     |
| Connection to peer            | False            |

Devices are NOT paused. This is the fix: before 0.23.55, devices would
also be paused=true here, and no amount of unpausing folders would
restore the connection.

### After `keel vip check` re-acquires VIP

| Check                         | Result           |
|-------------------------------|------------------|
| VIP carried                   | yes              |
| Devices paused                | False (both)     |
| Folders paused                | **False (all 4)**|
| Connection to peer            | True             |
| test228-post.txt replicated   | yes              |
| DB Seconds_Behind_Master      | 0                |

## Evidence: replica reboot

### After reboot

| Check                         | Result           |
|-------------------------------|------------------|
| Devices paused                | **False (both)** |
| Folders paused                | False (all 4)    |
| Connection to peer            | reconnected      |
| test228-b-reboot.txt replicated| yes             |
| DB Seconds_Behind_Master      | 0                |

The replica's folders were not paused after reboot because the replica
does not acquire VIP; `keel database follow` runs at boot and sets the
role and folder direction without the START_PAUSED cycle.

## Conclusion

keel 0.23.55 fixes #228. After a primary reboot:

1. Syncthing devices stay `paused=false` (the fix).
2. Folders start paused (the intended START_PAUSED behavior).
3. `keel vip check` re-acquires the VIP and unpauses folders.
4. The peer reconnects and file replication resumes.
5. Database replication also resumes (0 seconds behind).

After a replica reboot, devices and folders are both unpaused and
replication resumes immediately.
