# Evidence: file replication with Syncthing on a real pair across sites (0050, phase 4)

Date: 2026-10-24. Pair: WordPress first, then Odoo. The 0050 "done when"
list, on the images built by the image CI with syncthing in them.

## Release under test

| Piece | Version |
| --- | --- |
| keel | 0.23.52 (apt#66, head `071abd3`), trixie-testing |
| keel-web | 0.3.4 (apt#67) |
| syncthing | 2.1.6+keel1, keel-overlay-syncthing 0.1.0 |
| keel-wordpress image | `debian-13-keel-wordpress_19.0-10_amd64.tar.zst` (build 20261024T202430Z, gate run 4113) |
| keel-odoo image | `debian-13-keel-odoo_19.0-13_amd64.tar.zst` (same build) |

The archive mirror served all of them; `bin/keel-publish-mirror
--archive-only` verified "trixie-testing verifies" twice.

## Topology

3 CTs, `cloud_advanced`, mesh overlay `fd5f:c779:24d2::/64`, VIP
`fd5f:c779:24d2::ffff:9ba3` (decision 0051 range):

| CT | Site | Role in round 1 |
| --- | --- | --- |
| 9220 | BR1 | witness (WordPress) |
| 9221 | BR1 | replica B (WordPress) |
| 9222 | BR2 | primary C (WordPress) |

Netem is one egress qdisc on the BR2 CT's veth (`veth9222i0`), as the
2026-10-18 WordPress test did; the profile value is the full round trip.
CTs 9054, 9062, 9071, 9180-9219 were not touched.

## WordPress round

### The pair and the folders

`keel database follow` on both pair nodes: replica seed on B
(`Master_Host fd5f:c779:24d2::1fb1`, `Slave_IO/SQL Running: Yes`,
`read_only=1`), VIP on C. The syncthing folders flipped with the role:
B receive-only with simple versioning, C send-only, role files
`replicates=database,files`, peer devices exchanged over vipmsg,
`connected: true`.

Two defects surfaced at bring-up (both recorded below): the spec must
declare `overlays.syncthing: enabled` or the filesync half of the flip
never applies, and a manifest-declared replicate path missing from the
image (languages) leaves the folder in `error` until the directory is
created and syncthing restarts.

### 1. An upload on the primary, served by the replica

A 69-byte PNG uploaded on C through wp-cli (attachment 5,
`/wp-content/uploads/2026/10/test-upload.png`) replicated to B with the
identical sha256 `b1ff9c8ea3a780bad09b346c423d2d0e46815926879b18e841d928376a946640`
within seconds, and B served it over HTTP: `curl` from the witness to
`https://[fd5f:c779:24d2::8e9a]/wp-content/uploads/2026/10/test-upload.png`
answered `200 69` with the same sha256. Static uploads are not behind
the Anubis challenge, so no browser was needed.

### 2. `keel database promote` flips the folders with the database

`keel database promote` on B:

- B becomes the writable primary (`read_only=0`, a write probe in the
  wordpress database succeeds), C turns read-only (`read_only=1`, the
  same probe is refused) and rejoins as a replica.
- The syncthing folders flip with it: B's four folders become send-only,
  C's four become receive-only (`keel diff` folder rows: `same
  (sendonly)` / `same (receiveonly)`), role files follow.
- The VIP moves to B at epoch 2 and the flip applies on all three nodes.

**Defect: receive-side ownership.** On B the replicated
`uploads/2026/10/` tree had arrived `syncthing:syncthing` during the
initial replication batch (one `copyOwnershipFromParent` level worked,
the next did not; a fresh two-level tree created later replicated with
`www-data` at every level, so the failure is the ordering of a batch,
not the capability set — the unit has `CAP_CHOWN CAP_FOWNER
CAP_DAC_OVERRIDE`). After the promote, `www-data` could not write or
delete inside `2026/10` on the new primary: a wp-cli media import failed
with "The uploaded file could not be moved to wp-content/uploads/2026/10".
A recursive `chown -R www-data:www-data` of the four replicated trees
was needed before the promoted node could take application writes.
Recorded below as a defect; promote (or a filesync settle step) must
fix ownership itself.

After the chown, a wp-cli media import on B succeeded (attachment 6)
and replicated to C — the flipped direction — with `www-data` ownership
on arrival.

### 3. An edit on a replica is reported, kept, and alerted

With C the receive-only replica:

- A local edit on C raised `receiveOnlyChangedFiles` to 2 (the uploads
  folder) and `keel diff` reported the drift row
  `filesync./var/www/wordpress/wp-content/uploads.receiveOnlyChangedFiles: drift (declared 0, observed 2)`.
- The database watch raised the alert at its next run:
  `filesync-counts: a replicated folder holds local changes or is not in sync`
  (repeated each run while the condition holds; in this test CT no
  alert was *sent* because `/etc/keel/monitor.json` has no secret, an
  environment gap, not a keel defect).
- Kept, the two forms seen:
  - replica edit, then the primary replaces the same file: the
    replica's content survives as
    `test-upload.sync-conflict-20261024-222706-6I7CELO.png` next to the
    file — a **.sync-conflict**, not an entry in .stversions;
  - primary replaces, replica had no local edit: the previous version
    is archived in
    `.stversions/2026/10/promote-upload~20261024-222743.png` (simple
    versioning).

### 4./5. The five netem profiles, partition and heal

One egress qdisc on `veth9222i0`, profile value = full round trip (the
2026-10-18 precedent). For each profile a new file was written on the
primary B and the time until it landed on C with the right digest was
measured; overlay ping W to C in the last column.

| Profile | netem | converge | RTT min/avg/max (ms) |
| --- | --- | --- | --- |
| ideal | `delay 5ms` | 7 s | 9.3 / 10.0 / 11.0 |
| regional | `delay 100ms 10ms` | 7 s | 102.6 / 107.0 / 112.4 |
| design case | `delay 250ms 25ms` | 8 s | 260.7 / 268.8 / 278.2 |
| design case, lossy | `delay 250ms 25ms loss 2%` | 7 s | 248.9 / 253.4 / 256.4 |
| partition and heal | `drop 100%`, 60 s, then qdisc removed | 3 files on C 10 s after the heal | cut: 100% loss |

Under the lossy profile a replica edit followed by a primary replace
kept the replica's old content as a **.sync-conflict** file
(`netem-lossy.sync-conflict-20261024-223112-6I7CELO.txt`), the same form
as the ideal case — not an entry in .stversions. (.stversions is the
form when the replica had no local edit: the previous remote version is
archived there on replace.)

Every replicated file landed `www-data:www-data` with mode 644 in every
profile, including the partition heal (3 files written on B during the
60 s cut arrived together 10 s after the qdisc was removed).

End state after the heal: `keel diff` exit 0 on C and the witness, exit
13 on B (0 drift, 1 unknown: `database.server.replication.primary.host`
cannot be inferred on a node that is the primary — the designed meaning
of 13). The receive-only counters on C are 0 and 0. The checksums of
the four replicated trees (application files only: .stversions,
.stfolder and .stignore excluded, the file list sorted) are identical
on B and C:

| Tree | checksum (both nodes) |
| --- | --- |
| uploads | `dfc85b031c48c26d4e8ef0e967c5afedf74ba5b33c94113b5371728540c239a8` |
| themes | `9ca935842fc0eb7b7bd7aa48bd4ac1ddd1071ee6bb452c27d0320eb1b775b523` |
| plugins | `a1cef404c2ff7b712cd6065e2c488a676f7152e82465a42eb19adb9625d91608` |
| languages | empty tree on both (sha of the empty list) |

## Odoo round

Same done-when list, CTs 9223 (W, BR1), 9224 (B, BR1), 9225 (C, BR2),
image `debian-13-keel-odoo_19.0-13`, specs `r7-odoo5-*.yaml`, app domain
`odoo.keel.test`, own mesh `fddd:96f:29e0::/64`, VIP
`fddd:96f:29e0::ffff:9ba3`. The replica B was reseeded with
`--destroy-local-database` (it had taken install writes while
standalone), after which it streamed from C (`pg_stat_replication:
streaming`) with the two folders receive-only.

Two image facts shaped this round: the image ships no
`/var/lib/odoo/filestore` (defect 2 again, second image in a row), and
odoo's attachment storage defaults to the database — the standard
`ir_attachment.location = file` was set so attachments use the
replicated filestore. While the database is in recovery the appliance's
odoo holds no listener at all (decision 0059), so "served by the
replica" is proven at the VIP after the promote, and serving inside the
node was read at odoo directly on the loopback (the nginx and Anubis
layer is the same one the WordPress round passed end to end).

### 1./2. Upload, replication, promote, served by the (former) replica

An attachment created on C through odoo shell (id 16, 45 bytes, stored
at `filestore/odoo/2f/2ff9734a...`) replicated to B with the identical
sha256 `4c65af55c9785a797683580cc08b34b46b22f71305db65e16b0ca156bd1b25ec`.
`keel database promote` on B flipped the database (B writable, C read
only and rejoining), the two folders (B send-only, C receive-only), and
the VIP. After the promote:

- B's odoo bound 127.0.0.1:8069 (it holds no listener while read only,
  decision 0059) and, logged in with the replicated administrator, served
  `/web/content/16` with 200, 45 bytes, sha256 `4c65af55...` — the
  upload made on C, served by the former replica.
- The ownership defect reproduced: `filestore/odoo/2f/` and
  `filestore/odoo/checklist/` had arrived `syncthing:syncthing`; an
  `odoo` write probe in the tree was refused (`WRITE-FAILED`) until a
  recursive `chown -R odoo:odoo` of the two replicated trees (then
  `WRITE-OK`).
- The flipped direction works: a new attachment on B (id 47) replicated
  to C with the identical sha256 `bd12ff97...`.

### 3. An edit on a replica is reported, kept, and alerted

With C the receive-only replica, a local edit of a replicated file,
then a replace from the primary B: the replica's content survives as
`c0231ba2....sync-conflict-20261024-231653-6QRFCBX` (a .sync-conflict,
same form as WordPress), `keel diff` reports
`filesync./var/lib/odoo/filestore.receiveOnlyChangedFiles: drift
(declared 0, observed 1)`, and the database watch raised
`filesync-counts: a replicated folder holds local changes or is not in
sync` (again not sent: no monitor secret in the test CT).

### 4./5. The five netem profiles, partition and heal

One egress qdisc on `veth9225i0` (the BR2 CT), profile value = full
round trip.

| Profile | netem | converge | RTT min/avg/max (ms) |
| --- | --- | --- | --- |
| ideal | `delay 5ms` | 3 s | 8.6 / 9.1 / 9.6 |
| regional | `delay 100ms 10ms` | 7 s | 98.3 / 99.3 / 101.2 |
| design case | `delay 250ms 25ms` | 7 s | 249.9 / 264.5 / 277.9 |
| design case, lossy | `delay 250ms 25ms loss 2%` | 8 s | 234.2 / 247.1 / 259.1 |
| partition and heal | `drop 100%`, 60 s, then qdisc removed | 3 files on C in 10 s after the heal | cut: 100% loss |

Every replicated file landed `odoo:odoo` with mode 644 in every profile,
including the partition heal (3 files written on B during the 60 s cut
arrived together 10 s after the qdisc was removed).

Under the lossy profile a replica edit followed by a primary replace
kept the replica's old content as a **.sync-conflict** file
(`netem-lossy.sync-conflict-20261024-231910-6QRFCBX.txt`), the same form
as the ideal case — not an entry in .stversions. (.stversions is the
form when the replica had no local edit: the previous remote version is
archived there on replace.)

Final state: `keel diff` exit 0 on C and exit 13 on B (0 drift, 1
unknown: `database.server.replication.primary.host` cannot be inferred
on a node that is the primary — the designed meaning of 13, as in the
WordPress round). The receive-only counters on C are 0 and the folders
are `idle`. The checksums of the two replicated trees (application
files only: .stversions, .stfolder, .stignore and the kept
.sync-conflict files excluded, the file list sorted) are identical on B
and C:

| Tree | checksum (both nodes) |
| --- | --- |
| `/var/lib/odoo/filestore` | `a70875465c7b6ef87519eacf40db02bd01707ae65b7e51f923b0f08cdf4d607c` |
| `/opt/odoo/extra-addons` | `1ecf5c5709df3c311f17080e9bcef1a5dc620b48fbe01f0ef76498f38bcce9b6` |

(The first checksum pass differed only because the two .sync-conflict
files kept on C by design — item 3 and the lossy edit — were still in
the tree; after they were removed and the counters returned to 0, the
trees match.)


## Defects the test found

1. **The filesync flip needs the spec to declare it.** `filesync.applies`
   requires `overlays.syncthing: enabled` written in the spec; a
   manifest default is not enough (decisions 0027, 0041). With the key
   absent the pair forms with `replicates=database` only, syncthing
   stays send-receive on a node that must not take writes, and the only
   sign is an apply-time warning. The flip should refuse or warn loudly
   at `keel database follow` time, when the role is written.
2. **A replicate path missing from the image leaves the folder in
   error.** The WordPress manifest declares
   `wp-content/languages`, the image ships no such directory, and the
   folder sits in `error` (folder path missing) with a 500 from the
   rescan API until the directory is created and syncthing restarts.
   Either the image ships every declared path or apply creates it.
3. **Receive-side ownership breaks on the initial batch.** Nested
   directories replicated in one batch can arrive `syncthing-owned`
   (parent copied, child not), everything below inherits the wrong
   owner, and the application cannot write the tree after a promote
   until a manual recursive chown. `copyOwnershipFromParent` works level
   by level in steady state; promote (or a settle step at the flip)
   must restore the application owner over the replicated trees.

## Cleanup

Test CTs 9220-9225 destroyed after the evidence; the netem qdisc, the
test files under `/root`, and the test nft tables were removed; 9180,
9181 and the ksync0 bridge of the earlier phase were destroyed too.
9054, 9062, 9071 untouched.
