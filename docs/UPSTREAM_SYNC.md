# Upstream Sync

공식 상태는 사용자 포크 `origin`이다. R:은 재생성 가능한 작업 clone이다.

```text
origin   https://github.com/icerain-cmd/im-not-ai.git
upstream https://github.com/epoko77-ai/im-not-ai.git
```

## 갱신 절차

```bash
git status
git fetch origin
git fetch upstream
git switch main
git pull --ff-only origin main
git merge --ff-only upstream/main  # 가능할 때
git push origin main
```

Fast-forward가 불가능하면 feature branch에서 `upstream/main`을 merge하고 충돌과 전체 회귀 테스트를 검토한다. 공유 작업트리를 다른 PC에서 동시에 편집하지 않는다.

## 예상 충돌 지점

- `install.sh`: Codex 설치 대상 목록
- `README.md`와 `INSTALL.md`: upstream 설치 설명(개인화 문서는 `README-YLW.md`에 격리)
- `codex/skills/humanize-korean/references`: R:의 symlink 비호환 표현
- plugin manifest와 version tests: upstream 버전은 YLW 0.2.x와 독립적으로 유지

## 업데이트 후 검증

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s tests -p 'test_ylw.py'
bash tests/test_install_flags.sh
```

실패를 skip하거나 숨기지 말고 upstream 변화와 YLW 레이어 사이의 계약을 고친다.
