# Writing: ASD-STE100 for every project text

The project writes in Simplified Technical English (ASD-STE100, issue 8).
This applies to documentation, decision notes, commit messages, PR and
issue text, console and CLI messages, log lines, alerts, and reports to
the maintainer. The specification is free from <https://www.asd-ste100.org>
(registration required). The dictionary is not copied here; the rules
below are the ones that change how we write most.

## Words

- Use a word in one meaning only, and use the same word for the same
  thing in every text. Do not use a synonym for variety.
- Use the technical name of a thing (`VIP`, `spec`, `overlay`, `pair`,
  `region`) as the project's glossary defines it. Do not invent a second
  name.
- Do not use slang, idioms or metaphors. Write "fails", not "blows up".
- Write "do not", "cannot", "is not". Do not use contractions.
- Write numbers as digits: 3 nodes, 250 ms, 10 s.

## Noun phrases

- Keep a noun cluster to 3 words. Write "the certificate of the etcd
  member", not "the etcd member leaf certificate chain".
- Use a hyphen when two words make one adjective: "read-only replica".

## Verbs

- Use the active voice. Write "keel writes the file", not "the file is
  written by keel".
- Use the simple present for facts, the imperative for instructions, the
  simple past for what happened.
- Do not use an -ing form as a verb. Write "the node joins", not "the
  node is joining".
- Do not use a verb as a noun. Write "the node starts", not "the start of
  the node occurs".

## Sentences

- A procedural sentence has at most 20 words. A descriptive sentence has
  at most 25 words.
- One topic per sentence. Keep the order subject, verb, object.
- Make "that" and "which" explicit. Do not omit them.
- Put a condition before the instruction: "If the lease expires, the
  primary releases the VIP."

## Procedures

- One instruction per sentence. Two only when the actions are at the same
  time.
- Use the imperative: "Run `keel vip promote`."
- Put a warning or a caution before the step it protects, as its own
  sentence, with the condition first and the action second.
- Use a numbered list for a sequence and a bulleted list for a set.

## Descriptive text

- A paragraph has at most 6 sentences and one topic.
- The first sentence of a paragraph states the topic.
- Use a table for data that has a structure.

## Punctuation and layout

- Use a colon to introduce a list. Do not use semicolons to join clauses.
- Do not use parentheses in instructions.
- Do not use em dashes (section 10 of the brief).

## Where the rule is softer

- Code identifiers, command output, quoted errors and quoted upstream
  text stay as they are.
- Decision notes keep the three-part justification of the brief; each
  part follows the rules above.
- Chat with the maintainer follows the sentence rules in Portuguese:
  short sentences, one topic each, the question at the end.

## Check before you send

1. Is every sentence under 20 or 25 words?
2. Is every verb active and in an approved form?
3. Does each term have one name, the one in the glossary?
4. Is every instruction one imperative sentence?
5. Is the condition before the action?
