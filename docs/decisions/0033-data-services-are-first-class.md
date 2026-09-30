# 0033: Data services are first-class appliances

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-011).

## Decision

- **The data services are appliances of their own:** PostgreSQL,
  MariaDB, Redis, and Elasticsearch or OpenSearch (which of the two is not
  decided).
- **Embedded in a simple installation; discovered on the mesh in an
  advanced one** (0026).
- **A search index is derived data.** It is rebuilt when a node joins and
  is never replicated by file (0032).

## What this amends

- **0013, "The standard set"** (MariaDB, PostgreSQL, Redis): extended with
  a search engine. 0013's sovereignty rule applies to it: an engine that
  cannot be rebuilt from our own archive does not ship.
- **0013, phase 1** (an application using a database elsewhere): the
  default for an advanced installation.
- **0010**: the data services are the components it was written for; how
  they are packaged is 0036.

## Review notes (open points for the maintainer)

- [ ] **Elasticsearch or OpenSearch** is open and tracked in the roadmap.
  Neither is in Debian 13's main archive, so either one means a Keel
  package (0039), and the licence of each belongs in the comparison.
