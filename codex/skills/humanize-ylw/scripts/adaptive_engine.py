#!/usr/bin/env python3
"""Deterministic context-risk helpers for Humanize YLW 0.2."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

INTENSITIES = ("conservative", "standard", "deep")
HIGH_FUNCTIONS = {"concept-definition", "theoretical-argument", "qualification", "counterargument", "conclusion"}
MEDIUM_FUNCTIONS = {"literature-review", "introduction", "policy-proposal", "rhetorical-emphasis"}


class ParagraphDecision(NamedTuple):
    paragraph_function: str
    function_confidence: str
    concept_risk: str
    rhetorical_risk: str
    requested_intensity: str
    effective_intensity: str
    reason: str


FUNCTION_RULES = (
    ("concept-definition", re.compile(r"(?:이란|란 |는 .{0,30}(?:뜻한다|의미한다|개념이다|정의한다))")),
    ("literature-review", re.compile(r"(?:선행연구|연구사|기존 연구|[A-Za-z가-힣]+\(\d{4}\))")),
    ("qualification", re.compile(r"(?:다만|일부|대체로|한편|가능성|제한적|예외)")),
    ("counterargument", re.compile(r"(?:반론|반대로|그럼에도|그러나 .{0,30}(?:주장|견해))")),
    ("policy-proposal", re.compile(r"(?:정책|제도|마련해야|개선해야|지원해야)")),
    ("conclusion", re.compile(r"(?:결론적으로|결국|요컨대|마지막으로|출발점이 될 것이다)")),
    ("example", re.compile(r"(?:예를 들어|가령|사례로|이를테면)")),
    ("transition", re.compile(r"^(?:따라서|그러므로|한편|이제|다음으로)")),
    ("introduction", re.compile(r"(?:이 글은|본고는|살펴보고자|논의하고자|문제를 제기)")),
    ("rhetorical-emphasis", re.compile(r"(?:[?？]|^[^.!?]{1,30}[.!]\s*[^.!?]{1,30}[.!])")),
    ("theoretical-argument", re.compile(r"(?:때문이다|따라서|그러므로|전제|논증|인과|구조적으로)")),
    ("description", re.compile(r"(?:보인다|나타난다|놓여 있다|이루어진다)")),
)


STYLE_PATTERNS = {
    "forced_contrast": re.compile(r"아니다[.!]\s*[^\n.!?]{1,80}(?:있다|이다)[.!]"),
    "choppy_emphasis": re.compile(r"(?:^|\s)([^.!?\n]{1,22}[.!])\s+([^.!?\n]{1,22}[.!])"),
    "mechanical_parallelism": re.compile(r"(?:아닌 [^,.;]{1,40}[,;]\s*){2,}|(?:첫째|둘째|셋째).{0,100}(?:첫째|둘째|셋째)"),
    "redundant_conclusion": re.compile(r"(?:결국|요컨대|결론적으로).{0,100}(?:결국|요컨대|결론적으로)"),
    "fake_transition": re.compile(r"(?:^|\n)(?:이러한 맥락에서|이 지점에서|한편으로는)[, ]"),
    "rhetorical_overclaim": re.compile(r"(?:답은 자명하다|이 점은 매우 중요하다|주목해야 할 점이다)"),
}


def load_yaml_list(path: Path, root_key: str) -> list[str]:
    """Read leaf list items below a small, bundled YAML root without PyYAML."""
    values: list[str] = []
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == f"{root_key}:":
            active = True
            continue
        if active and line and not line.startswith((" ", "\t")):
            break
        if active and stripped.startswith("-"):
            values.append(stripped[1:].strip().strip("'\""))
    return values


def classify_paragraph(text: str, *, position: str = "middle") -> tuple[str, str]:
    for name, pattern in FUNCTION_RULES:
        if pattern.search(text.strip()):
            return name, "HIGH" if name in HIGH_FUNCTIONS else "MEDIUM"
    if len(text) < 100:
        return "transition", "LOW"
    return "explanation", "LOW"


def risk_levels(text: str, function: str, protected: list[str], author_lexicon: list[str], *, position: str = "middle") -> tuple[str, str]:
    concept_signals = sum(term in text for term in protected + author_lexicon)
    concept_signals += int(bool(re.search(r"(?:이란|란 |뜻한다|의미한다|즉|다시 말해)", text)))
    concept = "HIGH" if function in HIGH_FUNCTIONS or concept_signals >= 2 else "MEDIUM" if concept_signals else "LOW"
    rhetorical_signals = sum(bool(p.search(text)) for p in (
        re.compile(r"[?？]"), re.compile(r"^[^.!?]{1,30}[.!]"), re.compile(r"(?:결국|마지막|새로운)"),
    ))
    rhetorical = "HIGH" if position in {"first", "last"} or function in {"conclusion", "rhetorical-emphasis"} else "MEDIUM" if rhetorical_signals else "LOW"
    return concept, rhetorical


def adaptive_intensity(requested: str, function: str, concept_risk: str, rhetorical_risk: str, confidence: str = "HIGH") -> tuple[str, str]:
    if requested not in INTENSITIES:
        raise ValueError(f"unsupported intensity: {requested}")
    risk = "HIGH" if "HIGH" in (concept_risk, rhetorical_risk) or confidence == "LOW" else "MEDIUM" if "MEDIUM" in (concept_risk, rhetorical_risk) else "LOW"
    index = INTENSITIES.index(requested)
    if risk == "HIGH":
        index = min(index, 0 if requested != "deep" else 1)
    elif risk == "MEDIUM" and requested == "deep":
        index = 1
    return INTENSITIES[index], f"{risk.lower()} contextual risk; requested intensity is a maximum envelope"


def analyze_paragraph(text: str, requested: str, protected: list[str], author_lexicon: list[str], *, position: str = "middle") -> ParagraphDecision:
    function, confidence = classify_paragraph(text, position=position)
    concept, rhetorical = risk_levels(text, function, protected, author_lexicon, position=position)
    effective, reason = adaptive_intensity(requested, function, concept, rhetorical, confidence)
    return ParagraphDecision(function, confidence, concept, rhetorical, requested, effective, reason)


def detect_patterns(text: str) -> Counter[str]:
    return Counter({name: len(pattern.findall(text)) for name, pattern in STYLE_PATTERNS.items() if pattern.search(text)})


def generated_patterns(before: str, after: str) -> list[str]:
    old, new = detect_patterns(before), detect_patterns(after)
    return sorted(name for name, count in new.items() if count > old[name])


def author_lexicon_changes(before: str, after: str, lexicon: list[str]) -> list[str]:
    return [term for term in lexicon if before.count(term) != after.count(term)]


def analyze_document(text: str, requested: str, protected: list[str], author_lexicon: list[str]) -> list[dict[str, str]]:
    blocks = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    decisions = []
    for index, paragraph in enumerate(blocks):
        position = "first" if index == 0 else "last" if index == len(blocks) - 1 else "middle"
        decisions.append(analyze_paragraph(paragraph, requested, protected, author_lexicon, position=position)._asdict())
    return decisions
