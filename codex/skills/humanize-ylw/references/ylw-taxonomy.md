# Personalized Taxonomy

Use these as contextual candidates layered over the upstream taxonomy.

| ID | Pattern | Decision rule |
|---|---|---|
| YLW-A | forced_contrast | Edit only if the contrast has no conceptual work |
| YLW-B | rhetorical_overclaim | Remove importance, novelty, or inevitability unsupported by the paragraph; never replace it with another “주목할 점” frame |
| YLW-C | redundant_conclusion | Merge a restated claim without deleting a qualification |
| YLW-D | abstract_noun_chain | Verbalize only non-technical nominal chains |
| YLW-E | mechanical_parallelism | Compress items included for rhythm rather than logic |
| YLW-F | fake_transition | Remove transitions with no discourse function |
| YLW-G | ornamental_adverb | Remove dispensable dramatic adverbs |
| YLW-H | excessive_explanation | Remove explanation already entailed by the preceding claim |
| YLW-I | choppy_emphasis | Reconnect theatrical short sentences when emphasis is unearned |
| YLW-J | academic_overhumanization | Do not edit: proposed revision would flatten academic register |
| YLW-K | concept_drift | Reject or roll back any substitution that shifts a concept |
| YLW-L | paragraph_moralization | Remove an unsupported abstract moral at paragraph end |
| YLW-M | conclusion_rhythm_risk | Prefer REVIEW over automatic deletion for functional repetition, short sentences, questions, or declarations in conclusions |
| YLW-N | semantic_flattening_risk | Flag a conceptual or author-lexicon expression replaced by more generic wording |
| YLW-O | generated_pattern | Recheck the candidate and flag a forced contrast, choppy emphasis, mechanical parallelism, redundant conclusion, fake transition, or rhetorical overclaim newly created by editing |

Pipeline: surface candidate → sentence function → paragraph role → genre profile → edit decision. A word match alone never authorizes an edit.

Run the same surface and functional detection after editing. Revise a generated pattern at most once; never enter a rewrite loop. Treat AI-like patterns as editing candidates, not evidence of AI authorship.
