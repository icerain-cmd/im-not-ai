---
name: humanize-ylw
description: Preserve-first Korean humanities editing for academic papers, academic books, public humanities books, columns, official documents, and researcher social posts. Use when revising Korean prose in the author's YLW style, especially requests such as "내 문체로 윤문", "인문학 논문을 보수적으로 다듬어", or `$humanize-ylw`, while strictly preserving arguments, concepts, citations, numbers, and protected terminology. Do not use to evade AI detectors.
---

# Humanize YLW

Restore the sentence the author would likely have chosen. Do not optimize for detector evasion. Prefer no edit when uncertain.

## Inputs

Accept a file path or pasted Korean text and optional `profile` and `intensity`.

- Default `profile=auto`. Run `python3 scripts/profile_router.py INPUT`; if confidence is below 0.62, use `generic-conservative`.
- Default `intensity=conservative`; use `standard` for `humanities-book` and `column` unless the user specifies otherwise.
- Never infer `deep`; require an explicit request.

Read [ylw-style-constitution.md](references/ylw-style-constitution.md) for every run. Read [genre-profiles.md](references/genre-profiles.md) for the selected profile, [ylw-taxonomy.md](references/ylw-taxonomy.md) when diagnosing, and [protected-terms.yml](references/protected-terms.yml) before editing.

## Workflow

1. Create `_workspace/{run_id}/` and preserve the input as `original.md`.
2. Mark never-touch spans: direct quotations, citation source data, footnotes, references, DOI, URL, numbers, dates, titles, laws, English abbreviations, YAML frontmatter, code fences, inline code, tables, blockquotes, and HTML comments.
3. Detect candidates using the upstream taxonomy plus YLW-A through YLW-L. Treat pattern matches as candidates, not verdicts.
4. For each candidate, analyze sentence function, paragraph role, genre, and protected concepts. Reject edits that merely simplify academic register.
5. Edit only supported spans. Do not add claims, evidence, examples, scholars, metaphors, certainty, causality, or paragraph reordering unless explicitly allowed.
   - When the following sentence already demonstrates importance, delete an empty importance marker such as `여기서 주목해야 할 점은 매우 중요하다`; do not recast it as `여기서 주목할 점은` or another metadiscourse frame.
6. Write only the revised body to `_workspace/{run_id}/candidate.md`.
7. Run `python3 scripts/integrity_check.py --before original.md --after candidate.md --profile PROFILE --intensity INTENSITY --protected references/protected-terms.yml --final final.md --report report.md`.
8. If the result is `RISK`, keep the original in `final.md`. If `REVIEW`, identify exact review points in `report.md`; do not describe the result as final. Return `SAFE` only when all strict integrity checks pass.

## Editing limits

| Intensity | Expected lexical change | Structure |
|---|---:|---|
| conservative | 5–15% | Preserve paragraphs |
| standard | 10–25% | Merge redundant sentences if claims remain |
| deep | 15–35% | Reorder only inside paragraphs and only when authorized |

Protected terms override repetition rules. Preserve necessary transitions, qualifications, contrasts, and repeated concepts. Never turn possibility into certainty, some into all, correlation into causation, or a quoted view into the author's view.

## Output

Return paths to `final.md` and `report.md`, selected profile and confidence, intensity, and status (`SAFE`, `REVIEW`, or `RISK`). Keep analysis out of `final.md`. Do not append `HUMANIZE-SUMMARY` comments.
