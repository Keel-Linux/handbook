# 0040: Monitoring per machine with Monit, aggregated per site in etcd

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-017).

## Decision

- **Monit stays per machine**, and restarts what it can.
- **An agent in the etcd overlay** writes a compact summary of Monit's
  state to the node's registry key (0025).
- **The site view is a view over etcd.**
- **Prometheus is optional**; the same agent can expose it.
- **Machine alerting is Monit's; mesh alerting is etcd watches.**
- **Monit's checks are generated from the composition manifest** (0034).

## What this amends

- **0021, "What it does not do"**: "it never grows a disk, restarts a
  service or kills a process ... the configuration keel writes does not
  ask it to". Monit now restarts what it can. Growing a disk stays the
  operator's act.
- **0021, "In a replicated set"**: each node's Monit watched its peers
  over WireGuard through Monit's HTTP interface, and the elected primary
  reported. Peer watching becomes etcd watches over the summaries; a node
  that stops writing its summary is the node that cannot speak for
  itself.
- **0021, "The monitor: monit, configured from the spec"**: unchanged for
  a machine; for an application, the checks also come from its manifest.

## Resolved (maintainer, 2026-09-30)

- **Monit restarts what it can.** 0021's "never restarts a service" is
  superseded on that point. As an implementation detail, which services
  Monit restarts and how many times before it stops and alerts come from
  the manifest per service, so that a restart loop is reported rather
  than hidden.
