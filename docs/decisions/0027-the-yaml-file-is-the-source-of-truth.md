# 0027: The YAML file is the source of truth

Date: 2026-09-30
Status: **decided by the maintainer, 2026-09-30** (ADR-005).

## Decision

Every installation, simple or advanced, by hand or automated, emits a
complete YAML file: everything that was discovered and chosen, the
defaults included and written out explicitly. It is the installation's
documentation and the advanced interface. One answer file replays many
installations.

The file is re-emitted after every upgrade (0039).

## What this amends

- **Brief section 5.2** (the instance spec, `/etc/keel/instance.yaml`):
  extended. The spec was what an operator could declare; it is now also
  what every installation writes back, complete.
- **0009**: its rule stands, a field is reported the way the machine
  really is. Emitting explicit defaults means an absent section no longer
  has to be read as "default"; keel#46 (an absent monitor section turns
  the monitor off) is the kind of ambiguity this closes.
- **0020**: the role in the spec is the one chosen at installation, and
  the elected role is runtime state. The emitted file records the former.
