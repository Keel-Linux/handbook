# 0002: tklbam is the last component to be ported

Date: 2026-09-24
Status: decided by the maintainer

## Decision

tklbam and its Hub-specific bookkeeping (credentials, sub-key exchange, backup
records, profile download) are deferred to the end of the port. The other
components named in the brief (tkldev, fab, common, buildtasks, inithooks,
confconsole, the core appliance) come first, and the approach is a port of
the existing code, not a rewrite.

## Justification (brief section 10, three parts)

1. Why the previous ordering does not hold: brief section 5.6 starts Hub
   decoupling from `tklbam-python-boto`. The inventory in docs/hub-inventory.md
   shows that package is no longer on the storage path at all (tklbam declares
   Conflicts and Replaces on it and depends on Debian's duplicity with boto3),
   and that the Hub base URL is already overridable through `TKLBAM_APIURL`.
2. Whether it could be made to work: yes, nothing in tklbam blocks the other
   components. Backup upload and download, the encryption key and the restore
   path all work against any duplicity URL today, so an operator can back up a
   Keel appliance without the Hub before tklbam is touched, using
   `--address` and `--force-profile`.
3. Why deferring is better: the pieces that shape the product (build layers,
   instance spec, IPv6 identity, transition packages) do not depend on
   tklbam, while tklbam's remaining Hub coupling needs a service design
   (credentials, records catalogue) that belongs with the hosting decisions of
   brief section 11. Doing it last means designing that service once, with the
   spec and identity model already fixed.

## Consequences

- docs/hub-inventory.md stays the reference; its "needs a Keel service" rows
  for tklbam are parked, not lost.
- The smallest tklbam change it recommends (`s3-endpoint-url` conf option
  passed to duplicity) is small enough to do whenever an S3 target is chosen,
  without waiting for the full port.
- Brief section 5.6's first sentence ("tklbam-python-boto is the first piece
  to study") is superseded by this note.
