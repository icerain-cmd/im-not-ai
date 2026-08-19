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

Pipeline: surface candidate → sentence function → paragraph role → genre profile → edit decision. A word match alone never authorizes an edit.
