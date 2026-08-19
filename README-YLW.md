# Humanize YLW — Korean Humanities Writing Engine

Personalization layer: **YLW 0.2.0**
Upstream: **im-not-ai 2.x**

AI detector 우회가 아니라 한국어 인문학 연구자의 논지·개념·인용·문체를 보존하는 최종 윤문 시스템이다. upstream `humanize-korean`은 그대로 유지하며 YLW 기능은 별도 Codex skill로 제공한다.

## 설치

```bash
./install.sh --codex-only
```

R:처럼 symlink를 지원하지 않는 파일시스템에서는 최초 설치에 `./install.sh --codex-only --copy`를 사용한다. 기존 copy 설치본을 main 기준으로 갱신할 때는 설치기가 `.bak.<timestamp>`로 백업하도록 `./install.sh --codex-only --copy --force`를 사용한다.

## 사용법

```text
$humanize-ylw paper.md
$humanize-ylw book.md profile=humanities-book
이 원고를 내 문체 기준으로 최종 윤문해. 프로필 academic. 강도 conservative.
```

프로필은 `academic`, `academic-book`, `humanities-book`, `column`, `official`, `social`이다. 자동 판별 신뢰도가 낮으면 `generic-conservative`로 처리한다.

기본 실행은 adaptive mode다. 논문은 `academic + conservative`, 대중인문서와 칼럼은 `standard`를 요청 강도로 사용하되, 문단 기능·개념 위험·수사 위험이 높으면 내부 강도를 낮춘다. 요청 강도보다 높이지 않으며 변경률을 목표로 삼지 않는다.

```text
$humanize-ylw column.md profile=column
```

## 결과

```text
_workspace/{run_id}/final.md
_workspace/{run_id}/report.md
```

`final.md`는 수정 본문만 담는다. `report.md`는 requested/effective intensity, Integrity Score, Style Improvement, Author Fidelity와 `SAFE`/`REVIEW`/`RISK`를 기록한다. `RISK`면 후보를 확정하지 않고 원문을 유지한다.

`REVIEW`는 실패가 아니다. 문체·저자 어휘·결론 리듬처럼 사람의 선택이 필요한 상태다. `SAFE`도 문장이 반드시 더 좋다는 뜻이 아니라 무결성과 저자 충실성 위험이 낮다는 뜻이다.

## YLW 0.1 → 0.2

- 장르 기반 강도에 문단 기능별 adaptive downgrade를 추가했다.
- 단일 style score를 무결성·문체 개선·저자 충실성으로 분리했다.
- 편집 전 탐지뿐 아니라 편집 후 generated-pattern 검사를 수행한다.
- 절대 보존어와 별도로 저자 어휘 경고 계층을 추가했다.
- AI-like pattern은 통계적·문체적 후보일 뿐 AI 작성의 증거가 아니다.

## Upstream 동기화

[docs/UPSTREAM_SYNC.md](docs/UPSTREAM_SYNC.md)를 따른다. `origin` 사용자 포크가 유일한 Source of Truth이며 R: clone은 작업 복사본이다.

설치된 `humanize-ylw` 파일을 직접 수정하지 않는다. 모든 수정은 GitHub source repository의 feature branch에서 수행하고 main 병합 후 `./install.sh --codex-only --copy --force`로 다시 설치한다.

YLW 버전의 Source of Truth는 `codex/skills/humanize-ylw/references/defaults.yml`의 `version` 값이다. upstream `im-not-ai` 버전과 독립적으로 관리한다.

## 알려진 한계

- 주장 동등성의 결정적 검사는 부정·인과·조건·한정 표지 변화와 보존 token을 중심으로 한다. 미묘한 철학적 의미 변화는 사람 검토가 필요하다.
- 자동 장르 판별은 보수적으로 설계됐으며 혼합 장르는 `generic-conservative`로 후퇴할 수 있다.
- 실제 윤문은 언어모델의 문맥 판단을 사용하므로 deterministic gate를 통과해도 `REVIEW` 항목을 저자가 확인해야 한다.
- 대형 문서의 chunk 검사는 전체 원고의 의미가 전수 검증됐다는 뜻이 아니다. 보고서에 실제 검토 범위를 명시해야 한다.
