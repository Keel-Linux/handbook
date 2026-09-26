# Keel handbook

Working notes for the Keel Linux project: the standing brief, the running
status log, decision notes and the operational documentation for the build
host, the public services host and the release pipeline.

This repository is private because it records host addresses, sudo policy and
recovery procedures. Material that is safe in public is promoted to the site
repository instead of being published from here:

| Here | Published as |
|------|--------------|
| `docs/org-plan.md` | site: organization guidelines |
| `docs/ci-cd.md` | site: contributing and CI |
| `docs/decisions/` | site: decision log, once each note is cleared |
| `docs/brand/` | site: brand assets (the SVG master lives here) |

## Layout

| Path | What it holds |
|------|---------------|
| `BRIEF.md` | the standing brief; read it before touching code |
| `STATUS.md` | running log, newest section last |
| `docs/decisions/` | numbered decision notes, one per direction taken |
| `docs/infra*` | build host, releases host, recovery, VM provisioning |
| `docs/m0-gate*` | the equivalence and packing gate and its runs |
| `docs/brand/` | mark, lockups, icons, social card |
| `docs/keys/` | public keyring and fingerprint; no secret material |
| `repos/` | working clones, not tracked here |

Code lives in the organization repositories, not in this one.
