# Evidence: the application owner of a replicated tree after a first batch (keel#225)

Date: 2026-10-25. Fix: Keel-Linux/keel PR 226 (keel 0.23.53). Defect: keel#225,
found in the 0050 phase-4 test
(2026-10-24-syncthing-0050-wordpress-odoo-cross-site.md).

## What this test covers

This test uses 2 CTs and the real syncthing of the WordPress image. It
reproduces the defect in the first batch of a replication. It then runs
the code of the fix on the node that receives the files. It does not run
a full database pair and a `keel database promote`. The fix runs in the
flip to primary, after the folders are send-only. The unit tests cover
that call. The code that changes the owners is the same code in both
places.

## Setup

| Item | Value |
| --- | --- |
| CTs | 9226 (sender), 9227 (receiver), both on BR1, unprivileged, bridge vtnet88 |
| Image | `debian-13-keel-wordpress_19.0-10` (keel 0.23.52, syncthing 2.1.6+keel1) |
| Fix | keel 0.23.53, built from the head of the PR branch, installed with `dpkg -i` (not published) |
| Folder | `/var/www/wordpress/wp-content/uploads`, owner `www-data` on both nodes |
| Configuration | rendered by `keel.system.filesync.config_xml`: send-only on 9226, receive-only on 9227, `copyOwnershipFromParent` on, the unit of the image with its 3 capabilities |

The sender held a tree of 27 years, 12 months each, 6 files in each
month, all owned by `www-data`. The receiver started with an empty
folder. The two syncthing daemons then made the first batch.

## Result 1: the defect

After the first batch (2296 entries received, `needFiles` 0):

- 1316 entries on the receiver belonged to `syncthing:syncthing`. They
  included the directories `uploads/2000/05` and `uploads/2026/10`, and
  the files in them.
- A `www-data` write in `uploads/2000/05` failed with "Permission
  denied". A `www-data` `mkdir` in `uploads/2026/10` failed the same way.

This is the state that stopped the promoted application in keel#225.

## Result 2: the fix

On the receiver, `keel` 0.23.53 was installed and the restore step of
the flip ran (`filesync._restore_owner`, on the folder). Output:
`syncthing: the application owner restored on 1316 replicated entries`.

- Entries owned by `syncthing`: 1316 before, 0 after. Entries not owned
  by `www-data`: 0 after.
- `uploads/2000/05` and `uploads/2026/10` are `www-data:www-data`.
- The `www-data` file write and the `www-data` `mkdir` that failed
  before both succeeded.
- Syncthing reported the folder `idle` with `receiveOnlyChangedFiles` 0
  and `needFiles` 0 after the change of owners (the later test files
  were removed first). Syncthing does not sync owners, so the change of
  owners is not a local change.

## Clean-up

CTs 9226 and 9227 were stopped and destroyed with their disks. No other
CT was touched. The .deb and the scripts were removed from the host. Nothing was
published to the apt archive.

## Still open

- A full pair test of the flip (database and files) with the 0.23.53
  image is for the next image release. It needs keel 0.23.53 in
  trixie-testing.
