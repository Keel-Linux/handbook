# 0011: unassigned

Status: **never written**, recorded 2026-09-28.

There is no decision 0011. The number was skipped when 0012 was written, not
lost, and nothing was ever removed.

## How that was established

Three checks, all empty:

- `git log --all --diff-filter=D -- 'docs/decisions/0011*'` returns nothing,
  so no such file was ever deleted.
- `git log --all -- 'docs/decisions/0011*'` returns nothing, so no such file
  was ever committed on any ref.
- Walking every tree of every commit on every ref finds no path containing
  `0011`, and no file in this repository references an 0011.

The directory's history shows 0010 added in `e49477c` on 2026-09-27 and the
next note added being 0012 in `1f9e3f3` the same day.

## Why the gap stays

A decision number is a stable identifier: notes cite each other, and commit
messages, code comments and issues cite notes. Renumbering to close a gap
would silently repoint every one of those references, which is a worse defect
than the gap.

Reusing 0011 for a future note was the alternative. It is rejected because it
would place a note dated later than 0012 and 0013 between 0010 and 0012, so a
reader scanning the directory in order would be reading them out of sequence
with no way to tell.

This file exists so that the next person who notices the gap finds the answer
instead of looking for a lost file.
