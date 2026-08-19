# Personalization Audit

## Scope

Upstream `im-not-ai` 2.3.2의 README, 설치 스크립트, Claude/Codex/Gemini 진입점, skills, agents, taxonomy, rewriting playbook, metrics, gates, fixtures와 tests를 조사했다. YLW 레이어는 upstream 핵심을 대규모 수정하지 않고 `codex/skills/humanize-ylw/`에 격리한다.

## 유지할 기능

- 의미 불변, 근거 기반 span 수정, 장르와 register 보존
- 고유명사·수치·직접 인용 보호, prompt injection 방어
- taxonomy 후보 탐지 → 윤문 → 자체검증 흐름
- 정량 metric과 CI-safe Python 테스트
- `humanize-korean` 기존 스킬과 upstream 업데이트 경로

## 수정할 기능

- 단순 장르 추정은 6개 프로필과 저신뢰 `generic-conservative` 라우팅으로 확장한다.
- 문자 변경률 단일 게이트를 어휘 변화, 문장 재구성, 문단 변화, 주장 표지, 보호어·인용·수치 무결성으로 확장한다.
- 본문 말미 HTML 요약은 YLW에서 사용하지 않고 `report.md`로 분리한다.
- AI 패턴 점수는 후보 탐지로만 쓰고 문장 기능과 문단 역할 판정을 필수화한다.

## 삭제 또는 비활성화할 기능

- upstream 기능은 삭제하지 않는다.
- YLW 실행에서는 detector 우회 표현, 자동 극화, 새 사례·비유·주장 생성, 기본 문단 재배열을 비활성화한다.

## 새로 추가할 기능

- YLW Style Constitution과 보호 용어 사용자 확장 파일
- `academic`, `academic-book`, `humanities-book`, `column`, `official`, `social` 프로필
- YLW-A~L taxonomy와 `academic_overhumanization`, `concept_drift`
- `SAFE`/`REVIEW`/`RISK`, RISK 원문 롤백, 분리 보고서
- 보수적 자동 프로필 라우터와 YLW Style Score

## 과윤문 위험

- 기존 30/50% 문자 게이트는 5~15%가 기본인 학술문에 너무 느슨하다.
- 문장 길이, 접속사, 명사화의 표면 빈도만으로 수정하면 논증 단계와 개념어 반복이 손상될 수 있다.
- “자연스러운 한국어”를 구어체·단문으로 오해하면 저자 register가 평준화된다.

## 학술문체 오탐 위험

- `따라서`, `그러나`, `즉`, `이러한`은 논증 기능이 있으면 보존해야 한다.
- 긴 문장, 한정 표현, 개념 반복, 실제 이항 대립은 그 자체로 AI 패턴이 아니다.
- 인용자의 판단, 연구자의 판단, 연구사 서술을 한 목소리로 합치면 개념 drift가 발생한다.

## 장르별 충돌 가능성

- academic의 필요한 반복은 column의 압축 규칙보다 우선한다.
- humanities-book의 리듬 변화는 official의 행정적 명료성에 적용하지 않는다.
- social의 짧은 문단은 academic-book의 논증 단위를 쪼개는 근거가 아니다.
- 자동 판별이 불확실하면 academic을 추정하지 않고 `generic-conservative`로 후퇴한다.

## 플랫폼 관찰

R: 네트워크 drvfs는 symlink와 chmod를 지원하지 않는다. 기존 `codex/skills/humanize-korean/references` symlink는 일반 참조 파일로 보이며 Git에 type-change로 나타난다. YLW는 symlink 없이 실제 reference 파일을 두어 Windows 공유 드라이브에서도 동작하게 했다.
