# 0070: The keel CLI builds its parser without loading the library

Date: 2026-10-27
Status: **decided by the maintainer, 2026-10-28; confirmed by the
maintainer in chat, 2026-10-30**. Evidence:
keel/evidence/2026-10-27-cli-lazy-imports.md.

## Measured

The Core image's keel 0.23.56 measured `keel --help` 230 ms cold / 182 ms
warm with `import keel.cli` 153949 us in the first run, and 255 / 753 ms
with 170471 us in the second (the 753 ms warm call is an outlier). The
same image with 0.23.56+perf1 measured 42 / 29 ms and 8230 us, then
45 / 31 ms and 8688 us; both are upgrades with no failed units. The
import is 19.6x faster in the second run.

## What was decided

- `keel/cli.py` stores a handler as a dotted name and imports the one
  module it names after `parse_args`; `keel --help` does not import
  `keel.commands` or any command implementation.
- The values the parser needs live in `keel/constants.py` (and
  `keel.monitor.constants` and `keel.layers.layout` for their names), so
  the parser does not load a package for a constant.
- `keel/commands.py` imports `diff`, `inspect`, `layers`, `network` and
  `system` inside the handlers that use them, not at module import.
- `keel.mesh.parser` and `keel.mesh.vipcli` import their heavy modules on
  use; `Options` is a plain class, not a dataclass, so the parser does
  not import `dataclasses`.
- `keel.network.live` imports `Probes` on call. The old eager
  `keel.commands` import had ordered `keel.inspect` first and hidden the
  `confirm`/`switch`/`inspect` cycle; the on-call import makes the order
  irrelevant.
- Package `__init__` files stay eager. A lazy `__getattr__` cannot serve
  a public function whose name is also a submodule (`assemble`, `load`,
  `validate`, `plan`), because importing the submodule first binds the
  module and the `from package import name` then returns it.

## Why

`keel --help` took 191 ms with bytecode, of which about 170 ms was
imports. The CLI loaded the whole library (`commands`, `diff`, `inspect`,
`layers`, `manifest`, `system`) to print help; the host import profile
was 557 ms before and 38 ms after. The Core image measurements are above.

## Consequences

- `keel --help` and the parser-only paths do not read the library. A
  command still imports what it uses, on demand.
- No behavior changes and no new dependency. The 0.23.56 relevant subset
  is 201 passed, 28 subtests, in the image build. The full suite includes
  the multi-node netns tests and exceeds a 10-minute local run; the 0.20.0
  full suite was 3129 passed, 21 skipped.
- A future command that adds a handler as a callable instead of a dotted
  name would defeat the CLI half; the regression test
  `tests/test_lazy_imports.py` catches it.

## What this amends

Nothing. 0069 is the image-wide bytecode decision and still holds.
