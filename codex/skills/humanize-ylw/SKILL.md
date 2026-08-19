---
name: humanize-ylw
description: Preserve-first Korean humanities editing for academic papers, academic books, public humanities books, columns, official documents, and researcher social posts. Use when revising Korean prose in the author's YLW style, especially requests such as "내 문체로 윤문", "인문학 논문을 보수적으로 다듬어", or `$humanize-ylw`, while strictly preserving arguments, concepts, citations, numbers, and protected terminology. Do not use to evade AI detectors.
---

# Humanize YLW

Restore the sentence the author would likely have chosen. Do not optimize for detector evasion. Prefer no edit when uncertain.

## Inputs

Accept a file path or pasted Korean text and optional `profile` and `intensity`.

- Resolve `SKILL_DIR` to the absolute directory containing this `SKILL.md`. Run bundled scripts and read references through `SKILL_DIR`; never assume the user's working directory is the skill directory.
- Default `profile=auto`. Run `python3 "$SKILL_DIR/scripts/profile_router.py" INPUT`; if confidence is below 0.62, use `generic-conservative`.
- Default `intensity=conservative`; use `standard` for `humanities-book` and `column` unless the user specifies otherwise.
- Never infer `deep`; require an explicit request.

Read [ylw-style-constitution.md](references/ylw-style-constitution.md) for every run. Read [genre-profiles.md](references/genre-profiles.md) for the selected profile, [ylw-taxonomy.md](references/ylw-taxonomy.md) when diagnosing, and both [protected-terms.yml](references/protected-terms.yml) and [author-lexicon.yml](references/author-lexicon.yml) before editing. Resolve every link relative to this `SKILL.md`.

## Workflow

1. Create `_workspace/{run_id}/` and preserve the input as `original.md`.
2. Mark never-touch spans: direct quotations, citation source data, footnotes, references, DOI, URL, numbers, dates, titles, laws, English abbreviations, YAML frontmatter, code fences, inline code, tables, blockquotes, and HTML comments.
3. Treat the requested intensity as a maximum envelope. Classify each target paragraph's function and confidence, then assess concept and rhetorical risk. Downgrade the effective intensity for high-risk definitions, arguments, qualifications, counterarguments, conclusions, openings, and final sentences; never upgrade it silently. Use the section heading and previous/current/next paragraphs as context while editing only the target paragraph.
4. Detect candidates using YLW-A through YLW-O. If the sibling `humanize-korean` skill is installed and its taxonomy resolves, also consult it as an optional upstream compatibility layer; YLW must still operate when that sibling reference is unavailable. Treat pattern matches as candidates, not evidence of AI authorship.
5. For each candidate, analyze sentence function, paragraph role, neighboring context, author lexicon, genre, and rhetorical role. Reject edits that merely simplify academic register. Do not automatically flatten an author-lexicon expression; record a semantic-flattening candidate as `REVIEW`.
6. Edit only supported spans. Do not add claims, evidence, examples, scholars, metaphors, certainty, causality, or paragraph reordering unless explicitly allowed.
   - When the following sentence already demonstrates importance, delete an empty importance marker such as `여기서 주목해야 할 점은 매우 중요하다`; do not recast it as `여기서 주목할 점은` or another metadiscourse frame.
7. Write only the revised body to `_workspace/{run_id}/candidate.md`.
8. Recheck the candidate against YLW-A through YLW-O. If editing created a forced contrast, choppy emphasis, mechanical parallelism, redundant conclusion, fake transition, or rhetorical overclaim, revise once at most and recheck. Never loop.
9. Run `python3 "$SKILL_DIR/scripts/integrity_check.py" --before original.md --after candidate.md --profile PROFILE --intensity INTENSITY --protected "$SKILL_DIR/references/protected-terms.yml" --author-lexicon "$SKILL_DIR/references/author-lexicon.yml" --final final.md --report report.md` from `_workspace/{run_id}/`.
10. If the result is `RISK`, keep the original in `final.md`. If `REVIEW`, identify exact before/after review points in `report.md`; do not describe the result as final. Return `SAFE` only when integrity is perfect, author fidelity is high, and no generated pattern or high reversal risk remains.

## Editing limits

| Intensity | Expected lexical change | Structure |
|---|---:|---|
| conservative | 5–15% | Preserve paragraphs |
| standard | 10–25% | Merge redundant sentences if claims remain |
| deep | 15–35% | Reorder only inside paragraphs and only when authorized |

Protected terms override repetition rules. Preserve necessary transitions, qualifications, contrasts, and repeated concepts. Never turn possibility into certainty, some into all, correlation into causation, or a quoted view into the author's view.

Protect conclusion rhythm, core slogans, conceptual metaphors, strong substantive claims, and intentional short sentences. A generally smoother sentence is not necessarily a better sentence by this author. For large documents, report the actually reviewed range and never claim full semantic verification from chunk-local checks.

## Output

Return paths to `final.md` and `report.md`, selected profile and confidence, requested/effective intensity, integrity score, style improvement, author fidelity, and status (`SAFE`, `REVIEW`, or `RISK`). `REVIEW` is a normal request for author judgment, not a failure. Keep analysis out of `final.md`. Do not append `HUMANIZE-SUMMARY` comments.
