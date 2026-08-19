# Humanize YLW — Korean Humanities Writing Engine

Personalization layer: **YLW 0.1.0**
Upstream: **im-not-ai 2.x**

AI detector 우회가 아니라 한국어 인문학 연구자의 논지·개념·인용·문체를 보존하는 최종 윤문 시스템이다. upstream `humanize-korean`은 그대로 유지하며 YLW 기능은 별도 Codex skill로 제공한다.

## 설치

```bash
./install.sh --codex-only
```

R:처럼 symlink를 지원하지 않는 파일시스템에서는 `./install.sh --codex-only --copy`를 사용한다.

## 사용법

```text
$humanize-ylw paper.md
$humanize-ylw book.md profile=humanities-book
이 원고를 내 문체 기준으로 최종 윤문해. 프로필 academic. 강도 conservative.
```

프로필은 `academic`, `academic-book`, `humanities-book`, `column`, `official`, `social`이다. 자동 판별 신뢰도가 낮으면 `generic-conservative`로 처리한다.

강도는 `conservative`(5~15%, 학술 기본), `standard`(10~25%, 대중 인문서·칼럼 기본), `deep`(15~35%, 명시 요청만)이다.

## 결과

```text
_workspace/{run_id}/final.md
_workspace/{run_id}/report.md
```

`final.md`는 수정 본문만 담는다. `report.md`는 profile, intensity, 무결성, 변화율, 위험과 `SAFE`/`REVIEW`/`RISK`를 기록한다. `RISK`면 후보를 확정하지 않고 원문을 유지한다.

## Upstream 동기화

[docs/UPSTREAM_SYNC.md](docs/UPSTREAM_SYNC.md)를 따른다. `origin` 사용자 포크가 유일한 Source of Truth이며 R: clone은 작업 복사본이다.

## 알려진 한계

- 주장 동등성의 결정적 검사는 부정·인과·조건·한정 표지 변화와 보존 token을 중심으로 한다. 미묘한 철학적 의미 변화는 사람 검토가 필요하다.
- 자동 장르 판별은 보수적으로 설계됐으며 혼합 장르는 `generic-conservative`로 후퇴할 수 있다.
- 실제 윤문은 언어모델의 문맥 판단을 사용하므로 deterministic gate를 통과해도 `REVIEW` 항목을 저자가 확인해야 한다.
