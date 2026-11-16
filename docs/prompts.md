# prompts.md — Operating the Agent

Letters are referenced from other documents: **K** kickoff · **P** per work package · **W** work-log template · **R** adversarial reviewer · **Q** Spec Query template · **C** context recovery · **I** incident template. Replace `<…>`.

## K — Kickoff (paste once, first)

```
You are the builder of `aethel`, the reference CLI and library for PIP-1 (Yellow Paper PIP-YP-1 v1.0.0-rc.3).
Read, in this order: AGENTS.md, docs/rules.md, docs/what-not-to-do.md, docs/decision-log.md, docs/intent.md.
Do not write code yet. Reply in at most 12 lines with:
1. the mission in your own words;
2. the source-of-truth order;
3. the twelve non-negotiables, rephrased;
4. the three runtime dependencies and why there are only three;
5. five things you will not build;
6. the first work package, its gate, and the commands that prove it.
Then wait for my go-ahead.
```

## P — Per work package (paste for each WP)

```
Work package: WP-<nn> <name>.
Read: AGENTS.md; docs/rules.md; docs/what-not-to-do.md; the WP card in docs/division-of-work.md;
and the sections listed for this WP in the table below.
Do, in order:
1. Restate scope and the tests that will prove it in at most five lines.
2. Write failing tests first for PT0/PT1 code.
3. Implement the smallest slice that passes. Respect the layering in docs/architecture.md.
4. Run `make check` and `make conformance`.
5. Fill work-log template W at docs/work-log/WP-<nn>.md with real command output.
6. Stop at the gate and wait for review.
Do not: edit tests/vectors or tests/fixtures; add a dependency; invent a flag, code, field or file;
start another WP; mark anything done without evidence.
Label every claim VERIFIED, DERIVED or ASSUMED. Probe every third-party call before relying on it.
```

| WP | Sections to read besides the card |
|---|---|
| 00 | `architecture.md` §2–3, §8 · `guidelines.md` §9 · `release-and-deployment.md` §1–3 · `testing-and-conformance.md` §1, §9 |
| 01 | `specs.md` §2, §14 · `architecture.md` §4, §7 |
| 02 | `specs.md` §3–4 · `what-not-to-do.md` §1 · `testing-and-conformance.md` §2, §4 · `skills.md` SKILL-01, 02 |
| 03 | `specs.md` §5 · `skills.md` SKILL-03 |
| 04 | `specs.md` §7 · `skills.md` SKILL-04 |
| 05 | `specs.md` §6 |
| 06 | `specs.md` §8 · `security.md` §3 · `decision-log.md` ADR-004 · `skills.md` SKILL-05 |
| 07 | `specs.md` §9–10, §12 · `testing-and-conformance.md` §3, §6 · `skills.md` SKILL-06 |
| 08 | `specs.md` §13 · `security.md` §4 · `skills.md` SKILL-07 |
| 09 | `specs.md` §7, §10 · `cli-spec.md` publish, revise |
| 10 | `cli-spec.md` (all) · `architecture.md` §6–7 · `guidelines.md` §5–6 · `skills.md` SKILL-08 |
| 11 | `cli-spec.md` selftest, explain, version · `specs.md` §14 |
| 12 | `specs.md` §5, §6, §8, §13 · `cli-spec.md` P1 commands |
| 13 | `specs.md` §9–10 · `testing-and-conformance.md` §5 |
| 14 | `testing-and-conformance.md` §7, §10–11 · `precision-scale-index.md` §2, §5 · `security.md` §5 |
| 15 | `release-and-deployment.md` · `security.md` §6, §8 |
| 16 | `guidelines.md` §6, §8 · `what-not-to-do.md` §4 · `user-requirements.md` §4 |
| 17 | `division-of-work.md` §6 · `release-and-deployment.md` §5 · `security.md` §8 |

## W — Work-log template (`docs/work-log/WP-<nn>.md`)

```
# WP-<nn> <name> — work log
Date: <date>        Branch: <name>        Commit: <hash>

Goal (one line):
Files changed:
Tests added (name — requirement or rule ID):

Gate evidence (paste real output, last lines are enough):
  $ make check          -> <summary: lint, type, N passed, coverage per tier>
  $ make conformance    -> <N vectors, N fixtures, selftest result>
  $ <WP-specific command from the gate column> -> <output>

Claims
  VERIFIED: <what you ran and saw>
  DERIVED:  <what follows from cited text, with section numbers>
  ASSUMED:  <anything unconfirmed; each must become VERIFIED or a Spec Query>

Third-party calls probed (command and output):
Decisions or queries opened (ADR-…, Q-…):
Deviations from the WP card: none | <what and why>
Open risks:
Next:
```

## R — Adversarial reviewer (a different session from the builder if possible)

```
You are the adversarial reviewer for WP-<nn>. You write no production code.
Read AGENTS.md, docs/rules.md, docs/what-not-to-do.md and the WP card, then the diff.
1. Attack the diff against every row of what-not-to-do.md §1–§6.
2. Try to make `verify` report PASS for something wrong: flip bits in every file, reorder manifest lines,
   swap envelopes between bundles, rename directories, add symlinks, exceed limits.
3. Search outputs, logs and fixtures for secrets; search the diff for invented flags, codes, fields,
   placeholders, TODOs, unlabelled assumptions, banned claims.
4. Re-run `make check` and `make conformance` yourself and compare with the work log.
5. Confirm tests/vectors and tests/fixtures are unchanged: `sha256sum -c tests/vectors/SHA256SUMS`.
Write docs/reviews/WP-<nn>.md: findings, each with severity FC0–FC4 (docs/precision-scale-index.md §3),
an exact reproducer and a suggested test; then a verdict: CLOSE or BLOCK. Any FC3 or FC4 means BLOCK.
```

## Q — Spec Query (`docs/queries/Q-<n>.md`)

```
# Q-<n>: <one-line question>
Status: open | answered (<date>, <by>)
Yellow Paper clauses (quoted, with section numbers):
What I think they mean:
Other readings:
Options and consequences for each:
What I would choose, and why:
Tests and code that depend on the answer:
Work that can continue without it:
```

## C — Context recovery (when a session restarts or the context is lost)

```
Your context was reset. Do not continue from memory.
1. Read AGENTS.md, docs/rules.md and docs/what-not-to-do.md again.
2. Read the latest file in docs/work-log/, every open file in docs/queries/, and docs/decision-log.md.
3. Run `git status`, `git log --oneline -15`, `make check` and `make conformance`.
4. Reply in at most 10 lines: current WP, last green commit, what is half-done, open queries, and what you will do next.
Wait for my confirmation before changing anything.
```

## I — Incident note (`docs/incidents/I-<n>.md`, for FC4 only)

```
# I-<n>: <title>
Detected: <date, how>     Class: FC4     Release blocked: yes
What happened:
Scope (versions, commands, inputs affected):
Root cause:
Fix (commit):
Regression test (path):
How it escaped earlier checks, and what changes so it cannot again:
Owner informed: <date>
```

## Owner's acceptance checklist (use at every gate)

1. `git pull`, then run `make check` and `make conformance` yourself. Both green.
2. `sha256sum -c tests/vectors/SHA256SUMS` passes and `git diff --stat main -- tests/vectors tests/fixtures` is empty.
3. `grep -rniE "TODO|FIXME|NotImplementedError|lorem" src/` finds nothing.
4. Open the work log: every gate item has pasted output; ASSUMED lines are empty or turned into queries.
5. Read `docs/reviews/WP-<nn>.md`: verdict is CLOSE and no FC2+ remains open.
6. Spot-check by hand: publish a small text, verify it, flip one bit in `text.md`, verify again. It must fail.
7. Only then authorise the next work package.
