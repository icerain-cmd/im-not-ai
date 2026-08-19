from __future__ import annotations

import importlib.util
import sys
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "codex" / "skills" / "humanize-ylw"
sys.path.insert(0, str(SKILL / "scripts"))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


router = load("ylw_router", SKILL / "scripts" / "profile_router.py")
gate = load("ylw_gate", SKILL / "scripts" / "integrity_check.py")
adaptive = load("ylw_adaptive", SKILL / "scripts" / "adaptive_engine.py")


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

    def test_risk_on_number_reassignment(self):
        before = "A 집단은 12건이고 B 집단은 13건이다."
        after = "A 집단은 13건이고 B 집단은 12건이다."
        self.assertEqual(gate.evaluate(before, after, self.terms, "deep")["status"], "RISK")

    def test_changed_protected_context_requires_review(self):
        before = "A 집단은 12건이다. 설명은 길다."
        after = "A 집단은 모두 12건이다. 설명은 길다."
        result = gate.evaluate(before, after, self.terms, "deep")
        self.assertNotEqual(result["status"], "SAFE")

    def test_risk_on_claim_strength_or_causality_change(self):
        cases = (
            ("가능하다.", "반드시 그렇다."),
            ("일부에 해당한다.", "모두에 해당한다."),
            ("연관될 수 있다.", "원인이 된다."),
        )
        for before, after in cases:
            with self.subTest(before=before, after=after):
                self.assertEqual(gate.evaluate(before, after, self.terms, "deep")["status"], "RISK")

    def test_risk_on_markdown_region_change(self):
        before = "---\ntitle: 원문\n---\n\n`코드`\n\n> 직접 인용\n\n| 값 |\n|---|\n| 12 |"
        after = "---\ntitle: 수정\n---\n\n`다른 코드`\n\n> 직접 인용\n\n| 값 |\n|---|\n| 12 |"
        result = gate.evaluate(before, after, self.terms, "conservative")
        self.assertEqual(result["status"], "RISK")
        self.assertIn("markdown_regions", result["hard_failures"])
        self.assertIn("frontmatter", result["hard_failures"])

    def test_risk_on_korean_single_quote_change(self):
        result = gate.evaluate("그는 ‘원래의 직접 인용문’이라고 썼다.", "그는 ‘바뀐 직접 인용문’이라고 썼다.", self.terms, "deep")
        self.assertEqual(result["status"], "RISK")
        self.assertIn("quotes", result["hard_failures"])

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

    def test_cli_rolls_back_and_rejects_symlink_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before, after = root / "original.md", root / "candidate.md"
            before.write_text("기계세는 2023년 개념이다.", encoding="utf-8")
            after.write_text("새 시대는 2024년 개념이다.", encoding="utf-8")
            command = [
                "python3", str(SKILL / "scripts" / "integrity_check.py"),
                "--before", str(before), "--after", str(after), "--protected", str(SKILL / "references" / "protected-terms.yml"),
                "--final", "final.md", "--report", "report.md",
            ]
            run = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            self.assertEqual((root / "final.md").read_text(encoding="utf-8"), before.read_text(encoding="utf-8"))
            target = root / "do-not-touch.md"
            target.write_text("sentinel", encoding="utf-8")
            (root / "final.md").unlink()
            (root / "final.md").symlink_to(target)
            unsafe = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(unsafe.returncode, 3)
            self.assertEqual(target.read_text(encoding="utf-8"), "sentinel")

    def test_paragraph_reorder_is_reported(self):
        before = "첫 문단은 그대로다.\n\n둘째 문단도 그대로다."
        after = "둘째 문단도 그대로다.\n\n첫 문단은 그대로다."
        result = gate.evaluate(before, after, self.terms, "deep")
        self.assertEqual(result["paragraph_reorder_count"], 1)
        self.assertEqual(result["status"], "REVIEW")

    def test_integrity_style_score_separation(self):
        result = gate.evaluate("답은 자명하다. 근거가 있다.", "근거가 있다.", self.terms, "standard")
        self.assertEqual(result["integrity_score"], 100)
        self.assertIn(result["style_improvement"], {"MODEST", "CLEAR"})
        self.assertEqual(result["ylw_style_score"], "deprecated")

    def test_risk_rollback_cli_report_uses_new_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "original.md").write_text("일부 12건은 가능성이 있다.", encoding="utf-8")
            (root / "candidate.md").write_text("모든 13건은 확실하다.", encoding="utf-8")
            run = subprocess.run([
                "python3", str(SKILL / "scripts" / "integrity_check.py"),
                "--before", "original.md", "--after", "candidate.md", "--profile", "academic",
                "--intensity", "conservative", "--protected", str(SKILL / "references" / "protected-terms.yml"),
                "--final", "final.md", "--report", "report.md",
            ], cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertEqual((root / "final.md").read_text(encoding="utf-8"), (root / "original.md").read_text(encoding="utf-8"))
            report = (root / "report.md").read_text(encoding="utf-8")
            self.assertIn("## Author Fidelity", report)
            self.assertIn("Status: RISK", report)
            self.assertNotIn("YLW Style Score: 100/100", report)

    def test_risk_on_protected_value_reassignment_with_same_sequence(self):
        before = "갑은 12건, 을은 13건, 병은 14건으로 집계되었다."
        after = "을은 12건, 갑은 13건, 병은 14건으로 집계되었다."
        result = gate.evaluate(before, after, self.terms, "deep")
        self.assertEqual(result["status"], "RISK")
        self.assertIn("protected_relations", result["hard_failures"])

    def test_empty_candidate_cli_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before, after = root / "original.md", root / "candidate.md"
            before.write_text("첫 문단이다.\n\n둘째 문단이다.", encoding="utf-8")
            after.write_text("", encoding="utf-8")
            run = subprocess.run([
                "python3", str(SKILL / "scripts" / "integrity_check.py"), "--before", "original.md", "--after", "candidate.md",
                "--protected", str(SKILL / "references" / "protected-terms.yml"), "--final", "final.md", "--report", "report.md",
            ], cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
            self.assertEqual((root / "final.md").read_text(encoding="utf-8"), before.read_text(encoding="utf-8"))
            self.assertIn("empty_candidate", (root / "report.md").read_text(encoding="utf-8"))


class AdaptiveEditingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terms = gate.protected_terms(SKILL / "references" / "protected-terms.yml")
        cls.lexicon = adaptive.load_yaml_list(SKILL / "references" / "author-lexicon.yml", "author_lexicon")

    def test_paragraph_function_classification(self):
        self.assertEqual(adaptive.classify_paragraph("기계세란 기술과 자연의 관계를 묻는 개념이다.")[0], "concept-definition")
        self.assertEqual(adaptive.classify_paragraph("예를 들어 지역의 사례를 살펴보자.")[0], "example")

    def test_adaptive_intensity(self):
        decision = adaptive.analyze_paragraph("기계세란 기술과 자연의 관계를 묻는 개념이다.", "standard", self.terms, self.lexicon)
        self.assertEqual(decision.effective_intensity, "conservative")
        ordinary = adaptive.analyze_paragraph("예를 들어 일상의 사용 장면을 살펴보자.", "standard", self.terms, self.lexicon)
        self.assertEqual(ordinary.effective_intensity, "standard")

    def test_adaptive_intensity_is_enforced(self):
        before = "기계세란 기술과 자연의 관계를 묻는 개념이며 인간의 삶을 설명한다."
        after = "기계세란 기술과 자연의 관계를 새롭게 해석하고 복잡한 인간의 일상과 삶을 폭넓게 설명하는 핵심 개념이다."
        result = gate.evaluate(before, after, self.terms, "standard", self.lexicon)
        self.assertEqual(result["paragraph_analysis"][0]["effective_intensity"], "conservative")
        self.assertEqual(result["status"], "REVIEW")
        self.assertTrue(any("effective conservative limit" in reason for reason in result["review_reasons"]))

    def test_conclusion_rhythm_protection(self):
        decision = adaptive.analyze_paragraph("결국 이것이 새로운 출발점이다. 우리는 어디로 갈 것인가?", "standard", self.terms, self.lexicon, position="last")
        self.assertEqual(decision.paragraph_function, "conclusion")
        self.assertEqual(decision.effective_intensity, "conservative")

    def test_author_lexicon_detection(self):
        self.assertIn("투영", self.lexicon)
        self.assertEqual(adaptive.author_lexicon_changes("철학을 투영한다.", "철학을 드러낸다.", self.lexicon), ["투영"])

    def test_semantic_flattening_review(self):
        result = gate.evaluate("구조는 철학을 투영한다.", "구조는 철학을 드러낸다.", self.terms, "standard", self.lexicon)
        self.assertEqual(result["status"], "REVIEW")
        self.assertEqual(result["author_fidelity"], "MEDIUM")

    def test_generated_pattern_detection(self):
        before = "문제는 떠나는 청년이 아니라 관계가 끊기는 지역에 있다."
        after = "문제는 떠나는 청년이 아니다. 관계가 끊기는 지역에 있다."
        self.assertIn("forced_contrast", adaptive.generated_patterns(before, after))

    def test_generated_pattern_second_pass(self):
        original = "문제는 떠나는 청년이 아니라 관계가 끊기는 지역에 있다."
        candidate_v1 = "문제는 떠나는 청년이 아니다. 관계가 끊기는 지역에 있다."
        candidate_v2 = "문제는 청년의 이탈보다 지역과의 관계 단절에 있다."
        self.assertTrue(adaptive.generated_patterns(original, candidate_v1))
        self.assertFalse(adaptive.generated_patterns(original, candidate_v2))

    def test_author_reversal_risk(self):
        result = gate.evaluate("구조는 철학을 투영한다.", "구조는 철학을 드러낸다.", self.terms, "standard", self.lexicon)
        self.assertEqual(result["author_reversal_risk"], "HIGH")

    def test_academic_regression(self):
        text = "그러나 이러한 구별은 두 범주가 경험적으로 언제나 분리된다는 뜻이 아니다."
        result = gate.evaluate(text, text, self.terms, "conservative", self.lexicon)
        self.assertEqual(result["status"], "SAFE")
        self.assertEqual(result["style_improvement"], "NEUTRAL")

    def test_humanities_book_regression(self):
        controls = (
            "창조주와 피조물 사이의 경계를 확인한다.",
            "디지털 봉건주의의 시대를 피할 수 없을 것이다.",
            "기술의 영역이 아니라 인간의 철학적 선택이다.",
        )
        for text in controls:
            with self.subTest(text=text):
                self.assertEqual(gate.evaluate(text, text, self.terms, "standard", self.lexicon)["status"], "SAFE")

    def test_column_regression(self):
        self.assertFalse(adaptive.generated_patterns("지역소멸을 논의하는 자리에 빠지지 않는 말이 있다.", "지역소멸을 논의할 때 빠지지 않는 말이 있다."))
        self.assertFalse(adaptive.generated_patterns("더 넓은 세상으로의 도전은 권리다.", "더 넓은 세상에 도전하는 것은 권리다."))
        self.assertIn("forced_contrast", adaptive.generated_patterns("문제는 A가 아니라 B에 있다.", "문제는 A가 아니다. B에 있다."))

    def test_review_precision(self):
        safe = gate.evaluate("2024년 연구가 시작됐다.", "2024년 연구는 시작됐다.", self.terms, "standard", self.lexicon)
        ambiguous = gate.evaluate("철학을 투영한다.", "철학을 드러낸다.", self.terms, "standard", self.lexicon)
        risk = gate.evaluate("일부 12건이다.", "모든 13건이다.", self.terms, "standard", self.lexicon)
        self.assertEqual((safe["status"], ambiguous["status"], risk["status"]), ("SAFE", "REVIEW", "RISK"))

    def test_integrity_score_cannot_be_perfect_on_risk(self):
        result = gate.evaluate("---\ntitle: 원문\n---\n본문", "---\ntitle: 변경\n---\n본문", self.terms, "standard", self.lexicon)
        self.assertEqual(result["status"], "RISK")
        self.assertLess(result["integrity_score"], 100)

    def test_review_points_include_before_after(self):
        result = gate.evaluate("철학을 투영한다.", "철학을 드러낸다.", self.terms, "standard", self.lexicon)
        self.assertTrue(result["review_points"])
        self.assertEqual(result["review_points"][0]["paragraph"], 1)
        self.assertTrue(result["review_points"][0]["before"])
        self.assertTrue(result["review_points"][0]["after"])


class PackagingTests(unittest.TestCase):
    def test_skill_resources_exist(self):
        for name in ("ylw-style-constitution.md", "genre-profiles.md", "protected-terms.yml", "author-lexicon.yml", "ylw-taxonomy.md", "defaults.yml"):
            self.assertTrue((SKILL / "references" / name).is_file(), name)
        self.assertNotIn("TODO", (SKILL / "SKILL.md").read_text(encoding="utf-8"))

    def test_six_fixture_profiles_exist(self):
        base = ROOT / "tests" / "fixtures" / "ylw"
        for profile in ("academic", "academic-book", "humanities-book", "column", "official", "social"):
            self.assertTrue((base / profile / "cases.md").is_file(), profile)

    def test_router_runs_outside_skill_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "paper.md"
            source.write_text("본 연구는 선행연구와 참고문헌을 검토한다. 주제어를 제시한다.", encoding="utf-8")
            result = subprocess.run(
                ["python3", str(SKILL / "scripts" / "profile_router.py"), str(source)],
                cwd=tmp,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"profile": "academic"', result.stdout)

    def test_copied_skill_runs_end_to_end_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installed = root / "installed" / "humanize-ylw"
            shutil.copytree(SKILL, installed)
            work = root / "manuscript"
            work.mkdir()
            original, candidate = work / "original.md", work / "candidate.md"
            original.write_text("기계세는 2023년 개념이다.", encoding="utf-8")
            candidate.write_text("기계세는 2023년의 개념이다.", encoding="utf-8")
            run = subprocess.run(
                ["python3", str(installed / "scripts" / "integrity_check.py"),
                 "--before", str(original), "--after", str(candidate),
                 "--protected", str(installed / "references" / "protected-terms.yml"),
                 "--final", "final.md", "--report", "report.md"],
                cwd=work, capture_output=True, text=True, check=False,
            )
            self.assertIn(run.returncode, (0, 1), run.stdout + run.stderr)
            self.assertEqual((work / "final.md").read_text(encoding="utf-8"), candidate.read_text(encoding="utf-8"))
            self.assertIn("# Humanize YLW Report", (work / "report.md").read_text(encoding="utf-8"))

    def test_ylw_version_is_consistent(self):
        defaults = (SKILL / "references" / "defaults.yml").read_text(encoding="utf-8")
        readme = (ROOT / "README-YLW.md").read_text(encoding="utf-8")
        version = next(line.split(":", 1)[1].strip() for line in defaults.splitlines() if line.startswith("version:"))
        self.assertIn(f"Personalization layer: **{version}**", readme)
        self.assertIn(f"# {version} Real-text Validation", (ROOT / "docs" / "REAL_TEXT_VALIDATION.md").read_text(encoding="utf-8"))
        self.assertIn("Upstream: **im-not-ai 2.x**", readme)


if __name__ == "__main__":
    unittest.main()
