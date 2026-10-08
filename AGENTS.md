# Agents: how to work on Keel

This file is for every agent that works on a Keel-Linux repository. The
brief is `BRIEF.md`. The decisions are `docs/decisions/`. Read both
before the first change.

## Communication: ASD-STE100

Write every project text in Simplified Technical English (ASD-STE100).
The rules are in `docs/writing.md`. They apply to:

- documentation and decision notes;
- commit messages, PR and issue text, review comments;
- console, CLI, log and alert messages;
- reports to the maintainer.

The short form of the rules:

1. One word, one meaning. Use the glossary's name for each thing.
2. Active voice. Simple present for facts, imperative for instructions.
3. A sentence has at most 20 words in a procedure, 25 in a description.
4. One instruction per sentence. The condition comes before the action.
5. A paragraph has at most 6 sentences and one topic.
6. No contractions, no slang, no metaphors, no -ing verbs, no em dashes.

## Rules that are not negotiable

- No attribution of an AI tool anywhere: no `Co-Authored-By`, no session
  link, no "generated with" line, in commits, PR text or files.
- No merge with a red check. Fix the check first (decision 0053).
- Every test on the real platform ships an evidence file (decision 0053).
- Commit author is the maintainer's identity, one logical change per
  commit, format `<type>: <description>`.
- Section 10 of the brief: English, IPv6-first, no Docker or Kubernetes,
  no history rewrite, process over result.

## Before you report

1. Verify the result on the platform, not in the tool's claim.
2. Write the evidence file.
3. Write the report in STE: what changed, what was measured, what is
   open. Put the question for the maintainer last, as one yes/no.
