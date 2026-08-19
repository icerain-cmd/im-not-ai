from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "codex" / "skills" / "humanize-ylw"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


router = load("ylw_router", SKILL / "scripts" / "profile_router.py")
gate = load("ylw_gate", SKILL / "scripts" / "integrity_check.py")


class ProfileRoutingTests(unittest.TestCase):
    def test_academic_route(self):
        result = router.route("본 연구의 목적은 선행연구를 검토하는 데 있다. 참고문헌과 주제어를 제시한다.")
        self.assertEqual(result["profile"], "academic")
        self.assertGreaterEqual(result["confidence"], 0.62)

    def test_low_confidence_falls_back(self):
        self.assertEqual(router.route("오늘 읽은 문장을 다시 생각했다.")["profile"], "generic-conservative")

    def test_book_and_column_defaults(self):
        self.assertEqual(router.route("독자와 우리의 삶에 관한 이야기다. 왜 우리는 기억하는가?")["suggested_intensity"], "standard")
        self.assertEqual(router.route("이 칼럼은 제도 개선이 필요하다고 주장한다. 해야 한다.")["suggested_intensity"], "standard")


class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terms = gate.protected_terms(SKILL / "references" / "protected-terms.yml")

    def test_safe_preserves_boundary_tokens(self):
        before = '2024년 연구는 “기계세는 조건부 개념이다”라고 밝혔다. WE는 일부 사례에서 가능성이 있다.'
        after = '2024년 연구는 “기계세는 조건부 개념이다”라고 밝혔다. 일부 사례에서 WE의 가능성이 있다.'
        result = gate.evaluate(before, after, self.terms, "standard")
        self.assertNotEqual(result["status"], "RISK")
        self.assertTrue(result["checks"]["protected_terms"])
        self.assertTrue(result["checks"]["numbers"])
        self.assertTrue(result["checks"]["quotes"])

    def test_risk_on_protected_term_loss(self):
        result = gate.evaluate("기계세는 개념이다.", "새 시대는 개념이다.", self.terms, "standard")
        self.assertEqual(result["status"], "RISK")
        self.assertIn("protected_terms", result["hard_failures"])

    def test_risk_on_number_or_negation_change(self):
        result = gate.evaluate("일부 12건은 인과가 없을 수 있다.", "모든 13건은 인과가 있다.", self.terms, "deep")
        self.assertEqual(result["status"], "RISK")

    def test_risk_on_markdown_region_change(self):
        before = "---\ntitle: 원문\n---\n\n`코드`\n\n> 직접 인용\n\n| 값 |\n|---|\n| 12 |"
        after = "---\ntitle: 수정\n---\n\n`다른 코드`\n\n> 직접 인용\n\n| 값 |\n|---|\n| 12 |"
        result = gate.evaluate(before, after, self.terms, "conservative")
        self.assertEqual(result["status"], "RISK")
        self.assertIn("markdown_regions", result["hard_failures"])
        self.assertIn("frontmatter", result["hard_failures"])

    def test_risk_rolls_back_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before, after = root / "a.md", root / "b.md"
            final, report = root / "final.md", root / "report.md"
            before.write_text("기계세는 가능성이 있다.", encoding="utf-8")
            after.write_text("새 시대는 확정적이다.", encoding="utf-8")
            result = gate.evaluate(before.read_text(encoding="utf-8"), after.read_text(encoding="utf-8"), self.terms, "standard")
            final.write_text(before.read_text(encoding="utf-8") if result["status"] == "RISK" else after.read_text(encoding="utf-8"), encoding="utf-8")
            report.write_text(gate.report(result, "academic", "standard"), encoding="utf-8")
            self.assertEqual(final.read_text(encoding="utf-8"), before.read_text(encoding="utf-8"))
            self.assertIn("Status: RISK", report.read_text(encoding="utf-8"))

    def test_paragraph_reorder_is_reported(self):
        before = "첫 문단은 그대로다.\n\n둘째 문단도 그대로다."
        after = "둘째 문단도 그대로다.\n\n첫 문단은 그대로다."
        result = gate.evaluate(before, after, self.terms, "deep")
        self.assertEqual(result["paragraph_reorder_count"], 1)
        self.assertEqual(result["status"], "REVIEW")


class PackagingTests(unittest.TestCase):
    def test_skill_resources_exist(self):
        for name in ("ylw-style-constitution.md", "genre-profiles.md", "protected-terms.yml", "ylw-taxonomy.md", "defaults.yml"):
            self.assertTrue((SKILL / "references" / name).is_file(), name)
        self.assertNotIn("TODO", (SKILL / "SKILL.md").read_text(encoding="utf-8"))

    def test_six_fixture_profiles_exist(self):
        base = ROOT / "tests" / "fixtures" / "ylw"
        for profile in ("academic", "academic-book", "humanities-book", "column", "official", "social"):
            self.assertTrue((base / profile / "cases.md").is_file(), profile)


if __name__ == "__main__":
    unittest.main()
