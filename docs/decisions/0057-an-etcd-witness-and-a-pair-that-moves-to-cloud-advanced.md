# 0057: An etcd witness, and a pair that moves to cloud advanced

Date: 2026-10-15
Status: **decided 2026-10-15** under the maintainer's standing delegation
of design calls (least power). The maintainer approved the test that
needs it: a third site, BR3-THIN, holds a light etcd member for the
PostgreSQL pair of 0054 on BR1 and BR2.

## What was asked

The PostgreSQL pair on CTs 9054 (BR1) and 9062 (BR2) has no etcd. The
evidence of 2026-10-14 and 2026-10-15 shows what that costs: nothing
fences a live old primary, and failover is `keel database promote` by
the operator (keel#154). The maintainer asked for a third site with a
light etcd member, a witness, so that the pair runs with an etcd quorum
across 3 sites.

Two questions follow:

1. Is a witness, a node with no data and no role, a supported member?
2. The 2 pair nodes are `cloud_simple`. etcd runs only on
   `cloud_advanced` members. keel's `docs/spec.md` says: "Moving a
   machine between modes is out of scope". How does an existing pair get
   its 2 votes?

## Why (brief section 10)

1. **Why the current approach is not enough.** A witness alone gives 1
   voter. A quorum across 3 sites needs 3 voters, so the 2 pair nodes
   must be etcd members too. A pair installed as `cloud_simple` cannot
   get there without a reinstall, and a reinstall destroys the data and
   the mesh admission of a working pair.
2. **Whether it can be made to work.** keel reads `installation.mode` in
   3 places only: spec validation of `overlays.etcd` and `firewall`, the
   default state of an overlay that the spec does not declare, and the
   etcd member test (`keel.mesh.etcd`). Nothing on the machine records
   the mode (`keel diff`: "nothing on the machine records it"). On 9054,
   a copy of the spec with `cloud_advanced`, `overlays.etcd: enabled`
   and `overlays.vip: enabled` validates, and `keel diff` shows only the
   etcd and VIP overlays and Monit's derived file as changes.
3. **Why this is better.** The operator changes the spec, and keel's
   normal paths do the rest: `apply --system`, then `keel mesh etcd
   form` on the root's holder (keel `docs/mesh.md`). No new code path,
   no new command, and no reinstall.

## Decision

1. **A witness is a supported etcd member.** It is 0020's data-less
   voter and 0028's external arbiter. It is a Keel Core node with
   `installation.mode: cloud_advanced`, `overlays.etcd: enabled`, and no
   `database`, `appliance.vip` or other role in its spec. It joins the
   mesh with `keel mesh invite` and `keel mesh join` (0048), and etcd
   with the join or with `keel mesh etcd form`. It holds no data, so it
   does not need the resources of a data node.
2. **0020 names `keel-quorum`, which does not exist.** keel's VIP
   controller (`keel vip control`, `docs/vip.md`) is the election on
   etcd. The witness runs etcd and the overlays of Core (CrowdSec
   too). It runs no VIP controller, because it is not in a pair.
3. **An existing pair can move from `cloud_simple` to
   `cloud_advanced`, by the spec.** The operator does these steps:
   1. On each node of the pair, set `installation.mode:
      cloud_advanced`. Declare every overlay of the chain, with
      `etcd: enabled` and `vip: enabled`. Then run `keel spec apply
      --system-only`.
   2. On the root's holder, run `keel mesh etcd form --dry-run`, then
      `keel mesh etcd form`.
4. **Only this direction is in scope.** A move from `cloud_advanced` to
   a lower mode, or from `simple`, stays out of scope. keel does not
   change the mode by itself, as 0048 says.
5. **A test on real nodes proves it before keel's `docs/spec.md`
   changes.** The evidence file is
   `docs/evidence/2026-10-15-br3-thin-etcd-witness.md`. Each defect that
   the test finds is an issue in Keel-Linux/keel.

## Placement

0051 says: place the voters so that the loss of any one region keeps a
quorum. With 2 data nodes in 2 sites and the witness in a third site,
each single site cut leaves 2 of 3 voters. If the site of the standby
is cut, the primary keeps the VIP, but writes wait for the standby
(0054: synchronous commit with no timeout). That is 0054's design, not a
loss of quorum. The test found that this rule is not enough when the
cut site holds the etcd leader (keel#167): see "Result".

## What this amends

- **keel `docs/spec.md`, `installation.mode`**: "Moving a machine
  between modes is out of scope" gets one exception, `cloud_simple` to
  `cloud_advanced` by the steps above. The keel text changes after the
  evidence.
- **0020, "Decided, second round"**: the data-less voter runs etcd
  and no role. `keel-quorum` is keel's VIP controller.

## Result, 2026-10-15

The test of point 5 ran on BR1, BR2 and BR3-THIN
(`docs/evidence/2026-10-15-br3-thin-etcd-witness.md`). It proves the
procedure in part:

- The witness, the mode move and `keel mesh etcd form` work. etcd has
  3 voters in 3 sites. The form reports a member that took the cluster
  as "not reached" (keel#162).
- The procedure is not complete. After the form, the claim that the
  pair made before etcd has no lease (keel#161). Today only a planned
  `keel database promote` gives it one, and that leaves the old
  primary diverged, so a reseed follows (keel#163).
- A cut of 1 site does not always keep the pair working: see the
  evidence, and keel#164 to #169.

The keel text of `docs/spec.md` changes when keel#161 is fixed.
