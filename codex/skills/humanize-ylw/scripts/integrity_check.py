#!/usr/bin/env python3
"""Deterministic integrity gate and report writer for Humanize YLW."""
from __future__ import annotations

import argparse
import difflib
import os
import re
import tempfile
from collections import Counter
from pathlib import Path

from adaptive_engine import analyze_document, author_lexicon_changes, detect_patterns, generated_patterns, load_yaml_list

NUMBER = re.compile(r"(?<![A-Za-z0-9])[-+]?\d[\d,]*(?:\.\d+)?%?")
DATE = re.compile(r"(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{4}년(?:\s*\d{1,2}월(?:\s*\d{1,2}일)?)?)")
URL_DOI = re.compile(r"(?:https?://\S+|doi:\s*\S+|10\.\d{4,9}/\S+)", re.I)
QUOTE = re.compile(r"[\"“](.*?)[\"”]|[‘](.*?)[’]|[「『](.*?)[」』]", re.S)
ABBR = re.compile(r"\b[A-Z][A-Z0-9-]{1,}\b")
MARKDOWN_REGION = re.compile(
    r"```[\s\S]*?```|`[^`\n]+`|<!--[\s\S]*?-->|^>[^\n]*$|^\[\^[^]]+\]:[^\n]*$|\[\^[^]]+\]|^\|[^\n]*\|\s*$",
    re.MULTILINE,
)
NEGATION = re.compile(r"않|아니|없|못하|불가능|금지")
CAUSAL = re.compile(r"때문|따라서|그러므로|초래|야기|인과|원인")
CONDITION = re.compile(r"경우|조건|한에서|라면|예외|다만")
QUALIFIER = re.compile(r"일부|대체로|가능성|가능하|수 있다|보인다|추정|제한적")
CERTAINTY = re.compile(r"반드시|모두|확실|단정")
SENTENCE = re.compile(r"(?<=[.!?다요])\s+|\n+")


def defaults(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith((" ", "#")) and ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


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


def token_sequence(pattern: re.Pattern[str], text: str) -> list[str]:
    result = []
    for match in pattern.finditer(text):
        result.append(next((g for g in match.groups() if g is not None), match.group(0)))
    return result


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def _word(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣]+", "", text)
    return re.sub(r"(?:으로는|에게는|에서는|부터는|까지는|은|는|이|가|을|를|의|에)$", "", text)


def protected_bindings(pattern: re.Pattern[str], text: str) -> list[tuple[str, str, str]]:
    """Bind protected values to neighboring content words to detect reassignment."""
    result = []
    for match in pattern.finditer(text):
        before_words = re.findall(r"[0-9A-Za-z가-힣]+", text[max(0, match.start() - 40):match.start()])
        after_words = re.findall(r"[0-9A-Za-z가-힣]+", text[match.end():match.end() + 40])
        left = next((_word(word) for word in reversed(before_words) if _word(word)), "")
        right = next((_word(word) for word in after_words if _word(word)), "")
        result.append((match.group(0), left, right))
    return result


def review_point(before: str, after: str, reason: str) -> dict[str, object]:
    left, right = paragraphs(before), paragraphs(after)
    for index in range(max(len(left), len(right))):
        a = left[index] if index < len(left) else ""
        b = right[index] if index < len(right) else ""
        if a != b:
            return {"paragraph": index + 1, "reason": reason, "before": a[:240], "after": b[:240]}
    return {"paragraph": 0, "reason": reason, "before": "", "after": ""}


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


def evaluate(before: str, after: str, terms: list[str], intensity: str,
             author_lexicon: list[str] | None = None, adaptive: bool = True) -> dict[str, object]:
    author_lexicon = author_lexicon or []
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}
    for name, pattern in (("numbers", NUMBER), ("dates", DATE), ("citations", URL_DOI),
                          ("quotes", QUOTE), ("abbreviations", ABBR), ("markdown_regions", MARKDOWN_REGION)):
        a, b = tokens(pattern, before), tokens(pattern, after)
        checks[name] = a == b and token_sequence(pattern, before) == token_sequence(pattern, after)
        details[name] = {"missing": list((a - b).elements()), "added": list((b - a).elements())}
    frontmatter = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.S)
    a_front, b_front = tokens(frontmatter, before), tokens(frontmatter, after)
    checks["frontmatter"] = a_front == b_front
    details["frontmatter"] = {"missing": list((a_front - b_front).elements()), "added": list((b_front - a_front).elements())}
    before_terms = Counter({term: before.count(term) for term in terms if term in before})
    after_terms = Counter({term: after.count(term) for term in before_terms})
    checks["protected_terms"] = before_terms == after_terms
    details["protected_terms"] = {"missing_or_changed": [t for t in before_terms if before_terms[t] != after_terms[t]]}
    protected_pattern = re.compile(
        "|".join([NUMBER.pattern, DATE.pattern, URL_DOI.pattern, QUOTE.pattern, ABBR.pattern]
                 + [re.escape(term) for term in terms]),
        re.I | re.S,
    )
    protected_context_before = Counter(
        sentence.strip() for sentence in SENTENCE.split(before) if protected_pattern.search(sentence)
    )
    protected_context_after = Counter(
        sentence.strip() for sentence in SENTENCE.split(after) if protected_pattern.search(sentence)
    )
    context_changed = protected_context_before != protected_context_after
    binding_pattern = re.compile("|".join((DATE.pattern, NUMBER.pattern)), re.I)
    binding_changed = protected_bindings(binding_pattern, before) != protected_bindings(binding_pattern, after)
    checks["protected_relations"] = not binding_changed
    details["protected_relations"] = {"changed": binding_changed}
    for name, pattern in (("negation", NEGATION), ("causality", CAUSAL),
                          ("conditions", CONDITION), ("qualifiers", QUALIFIER), ("certainty", CERTAINTY)):
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
    hard_fail = [k for k in ("numbers", "dates", "citations", "quotes", "abbreviations", "markdown_regions", "frontmatter", "protected_terms", "protected_relations",
                              "negation", "causality", "conditions", "qualifiers", "certainty") if not checks[k]]
    if before.strip() and not after.strip():
        hard_fail.append("empty_candidate")
    review_reasons = []
    context_wording_only = context_changed and not binding_changed and lexical <= 0.08 and restructure == 0 and not hard_fail
    if context_changed and not context_wording_only:
        review_reasons.append("protected-token context requires semantic review")
    if lexical > limits[intensity]:
        review_reasons.append(f"lexical change exceeds {intensity} limit")
    if para_delta != 0:
        review_reasons.append("paragraph count changed")
    if reorder_count != 0:
        review_reasons.append("preserved paragraphs reordered")
    if restructure > 0.34:
        review_reasons.append("sentence restructure rate exceeds 34%")
    generated = generated_patterns(before, after)
    if generated:
        review_reasons.append("generated pattern: " + ", ".join(generated))
    lexicon_changes = author_lexicon_changes(before, after, author_lexicon)
    if lexicon_changes:
        review_reasons.append("author lexicon changed: " + ", ".join(lexicon_changes))
    paragraph_analysis = analyze_document(before, intensity, terms, author_lexicon) if adaptive else []
    before_paragraphs, after_paragraphs = paragraphs(before), paragraphs(after)
    adaptive_limits = {"conservative": 0.15, "standard": 0.25, "deep": 0.35}
    if adaptive and len(before_paragraphs) == len(after_paragraphs):
        for index, (left, right, decision) in enumerate(zip(before_paragraphs, after_paragraphs, paragraph_analysis), 1):
            paragraph_lexical = 1.0 - difflib.SequenceMatcher(None, left, right).ratio()
            effective = decision["effective_intensity"]
            if paragraph_lexical > adaptive_limits[effective]:
                review_reasons.append(f"paragraph {index} exceeds effective {effective} limit")
    high_rhythm_change = any(
        decision["paragraph_function"] == "conclusion" and decision["rhetorical_risk"] == "HIGH"
        for decision in paragraph_analysis
    ) and bool(before_paragraphs and after_paragraphs and before != after and before_paragraphs[-1] != after_paragraphs[-1])
    if high_rhythm_change:
        review_reasons.append("conclusion rhythm changed")
    if hard_fail:
        status = "RISK"
    elif review_reasons:
        status = "REVIEW"
    else:
        status = "SAFE"
    strict_checks = ("numbers", "dates", "citations", "quotes", "abbreviations", "markdown_regions", "frontmatter", "protected_terms", "protected_relations",
                     "negation", "causality", "conditions", "qualifiers", "certainty")
    integrity_score = round(100 * sum(checks[k] for k in strict_checks) / len(strict_checks))
    if hard_fail:
        integrity_score = min(integrity_score, 99)
    author_reversal_risk = "HIGH" if lexicon_changes or high_rhythm_change else "MEDIUM" if generated or (context_changed and not context_wording_only) else "LOW"
    author_fidelity = "LOW" if hard_fail and any(k in hard_fail for k in ("protected_terms", "quotes", "negation", "causality", "qualifiers", "certainty")) else "MEDIUM" if author_reversal_risk != "LOW" else "HIGH"
    if hard_fail:
        status = "RISK"
    elif review_reasons or author_fidelity != "HIGH":
        status = "REVIEW"
    else:
        status = "SAFE"
    before_patterns = detect_patterns(before)
    after_patterns = detect_patterns(after)
    reduced_patterns = any(after_patterns[name] < count for name, count in before_patterns.items())
    if before == after:
        style_improvement = "NEUTRAL"
    elif generated:
        style_improvement = "UNCERTAIN"
    elif reduced_patterns:
        style_improvement = "CLEAR"
    elif lexical <= limits[intensity]:
        style_improvement = "MODEST"
    else:
        style_improvement = "UNCERTAIN"
    return {"status": status, "checks": checks, "details": details,
            "lexical_change_rate": round(lexical, 4), "sentence_restructure_rate": round(restructure, 4),
            "paragraph_count_delta": para_delta, "paragraph_reorder_count": reorder_count, "hard_failures": hard_fail,
            "protected_context_changed": context_changed,
            "protected_context_wording_only": context_wording_only,
            "review_reasons": review_reasons,
            "claims": "PASS" if not hard_fail else "RISK", "integrity_score": integrity_score,
            "style_improvement": style_improvement, "author_fidelity": author_fidelity,
            "author_reversal_risk": author_reversal_risk, "author_lexicon_changes": lexicon_changes,
            "generated_patterns": generated, "paragraph_analysis": paragraph_analysis,
            "review_points": [review_point(before, after, reason) for reason in dict.fromkeys(hard_fail + review_reasons)],
            "ylw_style_score": "deprecated"}


def score(checks: dict[str, bool], lexical: float, limit: float) -> int:
    integrity = sum(checks[k] for k in ("numbers", "dates", "citations", "quotes", "abbreviations", "markdown_regions", "frontmatter")) / 7
    concepts = float(checks["protected_terms"])
    argument = sum(checks[k] for k in ("negation", "causality", "conditions", "qualifiers", "certainty")) / 5
    base = 25 * integrity + 20 * concepts + 15 * argument + 15 + 10 + 5 + 5
    return round(min(100, base + (5 if 0 < lexical <= limit else 0)))


def report(result: dict[str, object], profile: str, intensity: str, debug: bool = False,
           version: str = "YLW 0.2.0", reviewed_range: str = "full input") -> str:
    c = result["checks"]
    effective = sorted({item["effective_intensity"] for item in result["paragraph_analysis"]})
    trace = ""
    if debug and result["paragraph_analysis"]:
        trace = "\n## Adaptive Decision Trace\n" + "\n".join(
            f"- P{index}: function={item['paragraph_function']}; confidence={item['function_confidence']}; "
            f"concept={item['concept_risk']}; rhetorical={item['rhetorical_risk']}; "
            f"requested={item['requested_intensity']}; effective={item['effective_intensity']}; reason={item['reason']}"
            for index, item in enumerate(result["paragraph_analysis"], 1)
        ) + "\n"
    points = "\n".join(
        f"- Paragraph {item['paragraph']} — {item['reason']}\n  - Before: {item['before']}\n  - After: {item['after']}"
        for item in result["review_points"]
    ) or "- none"
    return f"""# Humanize YLW Report

Version: {version}

Profile: {profile}
Requested intensity: {intensity}
Effective intensity: {', '.join(effective) if effective else intensity}
Status: {result['status']}
Reviewed range: {reviewed_range}

## Integrity
- Score: {result['integrity_score']}
- Claims: {result['claims']}
- Numbers: {'PASS' if c['numbers'] else 'FAIL'}
- Citations: {'PASS' if c['citations'] and c['quotes'] else 'FAIL'}
- Protected terms: {'PASS' if c['protected_terms'] else 'FAIL'}
- Dates / abbreviations: {'PASS' if c['dates'] and c['abbreviations'] else 'FAIL'}
- Markdown never-touch regions: {'PASS' if c['markdown_regions'] and c['frontmatter'] else 'FAIL'}
- Negation / causality / conditions / qualifiers / certainty: {'PASS' if all(c[k] for k in ('negation','causality','conditions','qualifiers','certainty')) else 'FAIL'}

## Style
- Improvement: {result['style_improvement']}
- Generated patterns: {', '.join(result['generated_patterns']) if result['generated_patterns'] else 'none'}

## Author Fidelity
- Level: {result['author_fidelity']}
- Author reversal risk: {result['author_reversal_risk']}
- Author lexicon changes: {', '.join(result['author_lexicon_changes']) if result['author_lexicon_changes'] else 'none'}
- Conclusion rhythm risk: {'changed' if 'conclusion rhythm changed' in result['review_reasons'] else 'none'}

## Editing Metrics
- Lexical change rate: {result['lexical_change_rate']:.1%}
- Sentence restructure rate: {result['sentence_restructure_rate']:.1%}
- Paragraph count delta: {result['paragraph_count_delta']}
- Paragraph reorder count: {result['paragraph_reorder_count']}
- Protected-token context changed: {result['protected_context_changed']}

## Major edits
- See the candidate diff; this report does not invent edit rationales.

## Review Points
- Hard failures: {', '.join(result['hard_failures']) if result['hard_failures'] else 'none'}
- Review reasons: {', '.join(result['review_reasons']) if result['review_reasons'] else 'none'}
{points}

## Final
- Status: {result['status']}
- Reason: {'; '.join(result['hard_failures'] or result['review_reasons']) if result['hard_failures'] or result['review_reasons'] else 'integrity and author-fidelity gates passed'}
- YLW Style Score: deprecated
{trace}
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--profile", default="generic-conservative")
    p.add_argument("--intensity", choices=("conservative", "standard", "deep"), default="conservative")
    p.add_argument("--protected", required=True)
    p.add_argument("--author-lexicon")
    p.add_argument("--no-adaptive", action="store_true")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--reviewed-range", default="full input")
    p.add_argument("--final")
    p.add_argument("--report")
    args = p.parse_args()
    before = Path(args.before).read_text(encoding="utf-8")
    after = Path(args.after).read_text(encoding="utf-8")
    lexicon_path = Path(args.author_lexicon) if args.author_lexicon else Path(args.protected).with_name("author-lexicon.yml")
    lexicon = load_yaml_list(lexicon_path, "author_lexicon") if lexicon_path.is_file() else []
    result = evaluate(before, after, protected_terms(Path(args.protected)), args.intensity, lexicon, not args.no_adaptive)
    body = before if result["status"] == "RISK" else after
    config = defaults(Path(args.protected).with_name("defaults.yml"))
    rendered = report(result, args.profile, args.intensity, args.debug, config.get("version", "unknown"), args.reviewed_range)
    inputs = {Path(value).resolve() for value in (args.before, args.after, args.protected)}
    if args.author_lexicon:
        inputs.add(Path(args.author_lexicon).resolve())
    outputs = [Path(value) for value in (args.final, args.report) if value]
    try:
        resolved_outputs = [_validate_output(path, Path.cwd().resolve(), inputs) for path in outputs]
        if len(set(resolved_outputs)) != len(resolved_outputs):
            raise ValueError("final/report output paths must be distinct")
        if args.final:
            _atomic_write(Path(args.final), body)
        if args.report:
            _atomic_write(Path(args.report), rendered)
    except (OSError, ValueError) as exc:
        print(f"error: unsafe output path: {exc}")
        return 3
    print(result["status"])
    return {"SAFE": 0, "REVIEW": 1, "RISK": 2}[result["status"]]


def _validate_output(path: Path, workspace: Path, inputs: set[Path]) -> Path:
    if path.is_symlink():
        raise ValueError(f"symlink output rejected: {path}")
    resolved = path.resolve()
    if resolved.parent != workspace:
        raise ValueError(f"output must be directly inside workspace {workspace}: {path}")
    if resolved in inputs:
        raise ValueError(f"output aliases an input: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"output is not a regular file: {path}")
    return resolved


def _atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
