# YLW 0.2 Validation

## Scope

YLW 0.2 was evaluated against the same local, private evidence used for 0.1: one complete humanities paper, twelve public-humanities-book paragraphs, and one newspaper column. No unpublished manuscript text is committed here. Deterministic tests use synthetic equivalents and behavioral constraints.

## 0.1 → 0.2 behavior

| Evidence | 0.1 behavior | 0.2 behavior | Judgment |
|---|---|---|---|
| Academic | SAFE; minimal edit; no concept or argument drift | SAFE; Integrity 100; Author Fidelity HIGH; no generated pattern | EQUIVALENT |
| Humanities book | SAFE 8 / REVIEW 4 / RISK 0 | SAFE 8 / REVIEW 4 / RISK 0; H08 author-lexicon change and H11 conclusion rhythm now receive explicit reasons | 0.2 BETTER |
| Column | REVIEW; integrity passed, but editing created a split contrast | REVIEW; Integrity 100; generated `forced_contrast` and `choppy_emphasis` are explicitly detected | 0.2 BETTER |

## Improvements

- Requested intensity is now a maximum envelope; high-risk paragraphs receive a lower effective intensity.
- Paragraph function, concept risk, rhetorical risk, and author reversal risk are deterministic report inputs.
- `투영` is the sole initial author-lexicon item; changing it produces REVIEW instead of silent approval.
- Candidate output is checked for newly generated YLW patterns.
- Integrity, style improvement, and author fidelity are reported separately.
- Protected-context wording-only edits can be SAFE when strict tokens and argumentative markers remain unchanged.

## Regressions and risks

- No academic regression, concept drift, argument drift, RISK rollback failure, or protected-token corruption was observed.
- Pattern detection is deliberately conservative and heuristic. A generated-pattern warning still requires contextual author review.
- Chunk-local checks do not establish full-manuscript semantic verification.
- Live-LLM expression choices remain separate from deterministic CI behavior.

## Evidence metrics

- False positives: 0 confirmed in the evaluated academic and book negative controls.
- False negatives: 0 confirmed in the bounded evidence set; semantic review remains necessary.
- Author-reversal candidates: H08 author lexicon and H11 conclusion rhythm are now surfaced directly.
- Generated patterns: the known column split-contrast regression is detected.

## Release gates

The release is READY only after the complete repository suite, YLW suite, install tests, copied-install runtime smoke tests, repository/install identity check, and RISK rollback test all pass. Tagging occurs only on the verified `origin/main` merge commit.
