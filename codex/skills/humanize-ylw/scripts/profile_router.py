#!/usr/bin/env python3
"""Deterministic, conservative genre routing for Humanize YLW."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROFILES = ("academic", "academic-book", "humanities-book", "column", "official", "social")
SIGNALS = {
    "academic": (r"초록|주제어|본 연구|선행연구|연구 목적|연구 결과|참고문헌", r"\([^)]*\d{4}[^)]*\)"),
    "academic-book": (r"제\s*\d+\s*장|이 장에서는|앞 장에서|이하에서는", r"각주|미주"),
    "humanities-book": (r"독자|우리의 삶|일상|이야기|장면", r"왜\s|어떻게\s"),
    "column": (r"기고|칼럼|사설|지면|자 분량", r"해야 한다|필요하다"),
    "official": (r"사업|추진|계획|보고|회의|담당|예산|붙임|귀 기관", r"\d+\.\s|[가-힣]+:\s"),
    "social": (r"#\w+|링크드인|스레드|팔로우",),
}


def route(text: str) -> dict[str, object]:
    scores = {name: 0 for name in PROFILES}
    for name, patterns in SIGNALS.items():
        for pattern in patterns:
            scores[name] += min(len(re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)), 3)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], PROFILES.index(item[0])))
    top_name, top_score = ranked[0]
    second_score = ranked[1][1]
    evidence = sum(scores.values())
    confidence = 0.0 if top_score == 0 else min(0.95, 0.45 + 0.12 * top_score + 0.08 * (top_score - second_score))
    selected = top_name if confidence >= 0.62 else "generic-conservative"
    intensity = "standard" if selected in {"humanities-book", "column"} else "conservative"
    return {"profile": selected, "confidence": round(confidence, 2), "suggested_intensity": intensity,
            "scores": scores, "evidence_count": evidence}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    text = Path(args.input).read_text(encoding="utf-8")
    print(json.dumps(route(text), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
