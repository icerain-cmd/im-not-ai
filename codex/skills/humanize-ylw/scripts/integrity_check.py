#!/usr/bin/env python3
"""Deterministic integrity gate and report writer for Humanize YLW."""
from __future__ import annotations

import argparse
import difflib
import re
from collections import Counter
from pathlib import Path

NUMBER = re.compile(r"(?<![A-Za-z가-힣])[-+]?\d[\d,]*(?:\.\d+)?%?(?![A-Za-z가-힣])")
DATE = re.compile(r"(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{4}년(?:\s*\d{1,2}월(?:\s*\d{1,2}일)?)?)")
URL_DOI = re.compile(r"(?:https?://\S+|doi:\s*\S+|10\.\d{4,9}/\S+)", re.I)
QUOTE = re.compile(r"[\"“](.*?)[\"”]|[「『](.*?)[」』]", re.S)
ABBR = re.compile(r"\b[A-Z][A-Z0-9-]{1,}\b")
MARKDOWN_REGION = re.compile(
    r"```[\s\S]*?```|`[^`\n]+`|<!--[\s\S]*?-->|^>[^\n]*$|^\[\^[^]]+\]:[^\n]*$|\[\^[^]]+\]|^\|[^\n]*\|\s*$",
    re.MULTILINE,
)
NEGATION = re.compile(r"않|아니|없|못하|불가능|금지")
CAUSAL = re.compile(r"때문|따라서|그러므로|초래|야기|인과")
CONDITION = re.compile(r"경우|조건|한에서|라면|예외|다만")
QUALIFIER = re.compile(r"일부|대체로|가능성|수 있다|보인다|추정|제한적")
SENTENCE = re.compile(r"(?<=[.!?다요])\s+|\n+")


def protected_terms(path: Path) -> list[str]:
    terms, in_exact = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "exact:":
            in_exact = True
        elif in_exact and stripped.startswith("-"):
            terms.append(stripped[1:].strip().strip("'\""))
        elif in_exact and stripped and not line.startswith((" ", "\t")):
            break
    return terms


def tokens(pattern: re.Pattern[str], text: str) -> Counter[str]:
    found = []
    for match in pattern.finditer(text):
        value = next((g for g in match.groups() if g is not None), match.group(0))
        found.append(value)
    return Counter(found)


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def paragraph_reorders(before: str, after: str) -> int:
    """Count inversions among paragraphs preserved verbatim in both texts."""
    left, right = paragraphs(before), paragraphs(after)
    positions: dict[str, list[int]] = {}
    for index, paragraph in enumerate(left):
        positions.setdefault(paragraph, []).append(index)
    used: Counter[str] = Counter()
    order = []
    for paragraph in right:
        indexes = positions.get(paragraph, [])
        occurrence = used[paragraph]
        if occurrence < len(indexes):
            order.append(indexes[occurrence])
            used[paragraph] += 1
    return sum(a > b for i, a in enumerate(order) for b in order[i + 1 :])


def evaluate(before: str, after: str, terms: list[str], intensity: str) -> dict[str, object]:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    for name, pattern in (("numbers", NUMBER), ("dates", DATE), ("citations", URL_DOI),
                          ("quotes", QUOTE), ("abbreviations", ABBR), ("markdown_regions", MARKDOWN_REGION)):
        a, b = tokens(pattern, before), tokens(pattern, after)
        checks[name] = a == b
        details[name] = {"missing": list((a - b).elements()), "added": list((b - a).elements())}
    frontmatter = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.S)
    a_front, b_front = tokens(frontmatter, before), tokens(frontmatter, after)
    checks["frontmatter"] = a_front == b_front
    details["frontmatter"] = {"missing": list((a_front - b_front).elements()), "added": list((b_front - a_front).elements())}
    before_terms = Counter({term: before.count(term) for term in terms if term in before})
    after_terms = Counter({term: after.count(term) for term in before_terms})
    checks["protected_terms"] = before_terms == after_terms
    details["protected_terms"] = {"missing_or_changed": [t for t in before_terms if before_terms[t] != after_terms[t]]}
    for name, pattern in (("negation", NEGATION), ("causality", CAUSAL),
                          ("conditions", CONDITION), ("qualifiers", QUALIFIER)):
        delta = len(pattern.findall(after)) - len(pattern.findall(before))
        checks[name] = delta == 0
        details[name] = {"count_delta": delta}

    ratio = difflib.SequenceMatcher(None, before, after).ratio()
    lexical = 1.0 - ratio
    before_s = [s for s in SENTENCE.split(before) if s.strip()]
    after_s = [s for s in SENTENCE.split(after) if s.strip()]
    restructure = abs(len(before_s) - len(after_s)) / max(len(before_s), 1)
    para_delta = len(paragraphs(after)) - len(paragraphs(before))
    reorder_count = paragraph_reorders(before, after)
    limits = {"conservative": 0.15, "standard": 0.25, "deep": 0.35}
    hard_fail = [k for k in ("numbers", "dates", "citations", "quotes", "abbreviations", "markdown_regions", "frontmatter", "protected_terms",
                              "negation", "causality", "conditions", "qualifiers") if not checks[k]]
    if hard_fail:
        status = "RISK"
    elif lexical > limits[intensity] or para_delta != 0 or reorder_count != 0 or restructure > 0.34:
        status = "REVIEW"
    else:
        status = "SAFE"
    return {"status": status, "checks": checks, "details": details,
            "lexical_change_rate": round(lexical, 4), "sentence_restructure_rate": round(restructure, 4),
            "paragraph_count_delta": para_delta, "paragraph_reorder_count": reorder_count, "hard_failures": hard_fail,
            "claims": "PASS" if not hard_fail else "RISK", "ylw_style_score": score(checks, lexical, limits[intensity])}


def score(checks: dict[str, bool], lexical: float, limit: float) -> int:
    integrity = sum(checks[k] for k in ("numbers", "dates", "citations", "quotes", "abbreviations", "markdown_regions", "frontmatter")) / 7
    concepts = float(checks["protected_terms"])
    argument = sum(checks[k] for k in ("negation", "causality", "conditions", "qualifiers")) / 4
    base = 25 * integrity + 20 * concepts + 15 * argument + 15 + 10 + 5 + 5
    return round(min(100, base + (5 if 0 < lexical <= limit else 0)))


def report(result: dict[str, object], profile: str, intensity: str) -> str:
    c = result["checks"]
    return f"""# Humanize Report

Profile: {profile}
Intensity: {intensity}
Status: {result['status']}

## Integrity
- Claims: {result['claims']}
- Numbers: {'PASS' if c['numbers'] else 'FAIL'}
- Citations: {'PASS' if c['citations'] and c['quotes'] else 'FAIL'}
- Protected terms: {'PASS' if c['protected_terms'] else 'FAIL'}
- Dates / abbreviations: {'PASS' if c['dates'] and c['abbreviations'] else 'FAIL'}
- Markdown never-touch regions: {'PASS' if c['markdown_regions'] and c['frontmatter'] else 'FAIL'}
- Negation / causality / conditions / qualifiers: {'PASS' if all(c[k] for k in ('negation','causality','conditions','qualifiers')) else 'FAIL'}

## Changes
- Lexical change rate: {result['lexical_change_rate']:.1%}
- Sentence restructure rate: {result['sentence_restructure_rate']:.1%}
- Paragraph count delta: {result['paragraph_count_delta']}
- Paragraph reorder count: {result['paragraph_reorder_count']}

## Detected patterns
- Deterministic integrity gate only; contextual YLW patterns are recorded by the editing agent.

## Major edits
- See the candidate diff; this report does not invent edit rationales.

## Possible over-edit risks
- Hard failures: {', '.join(result['hard_failures']) if result['hard_failures'] else 'none'}

## Final grade
- Status: {result['status']}
- YLW Style Score: {result['ylw_style_score']}/100
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--profile", default="generic-conservative")
    p.add_argument("--intensity", choices=("conservative", "standard", "deep"), default="conservative")
    p.add_argument("--protected", required=True)
    p.add_argument("--final")
    p.add_argument("--report")
    args = p.parse_args()
    before = Path(args.before).read_text(encoding="utf-8")
    after = Path(args.after).read_text(encoding="utf-8")
    result = evaluate(before, after, protected_terms(Path(args.protected)), args.intensity)
    body = before if result["status"] == "RISK" else after
    if args.final:
        Path(args.final).write_text(body, encoding="utf-8")
    rendered = report(result, args.profile, args.intensity)
    if args.report:
        Path(args.report).write_text(rendered, encoding="utf-8")
    print(result["status"])
    return {"SAFE": 0, "REVIEW": 1, "RISK": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
