# webtoon-harness

## 하네스: 웹툰 자동 제작

**목표:** 트렌드 조사부터 완성 세로 스크롤 뷰어까지, 웹툰 한 회차를 에이전트 팀으로 자동 제작한다.

**트리거:** 웹툰 제작·회차 제작·시나리오·패널 렌더·조립 등 웹툰 관련 작업 요청 시 `webtoon-orchestrator` 스킬을 사용하라. 후속 작업("다음 화", "다시/수정/보완", "콘티 다시", "패널 재렌더", "대사 수정")도 동일. 단순 웹툰 추천/감상은 직접 응답 가능.

**핵심 규약:**
- 렌더는 Gemini API (`.env`의 GEMINI_API_KEY). 이미지에 글자를 굽지 않는다(무텍스트 렌더).
  - **대량 렌더(회차 첫 전량·대량 REGEN)는 `scripts/gemini_batch.py` — 단가 절반.**
  - 소량 재렌더·레퍼런스 시트는 `scripts/gemini_render.py` (즉시 확인 필요).
- 말풍선·대사는 조립 단계 HTML 오버레이(`ep{NN}_lettering.json`). 대사 수정은 재렌더 없이 재조립로 끝난다.
- 렌더 전 콘티(`storyboard.html`) 사용자 승인 게이트 필수 — 컷 완급(display_height 차등)은 렌더 후 고칠 수 없다.
- 베이크 텍스트를 쓰던 시절의 산출물(EP01)은 한글 서식(잔액/채무자/기한) 기준 — 한자 금지.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-08-03 | 초기 구성 (27 에이전트, codex 베이크 렌더) | 전체 | - |
| 2026-08-07 | 베이크 텍스트 순한글 서식 확정 (잔액/채무자/기한) | EP01 산출물, style-bible | 사용자 "한자 이해 안 됨" 피드백 |
| 2026-08-08 | 렌더러 codex→Gemini API 전환, panel-artist-a/b/c→panel-renderer 통합 | webtoon-panel-render, agents | 렌더 23시간→수 분, 캐릭터 일관성(레퍼런스 이미지 첨부) 강화 |
| 2026-08-08 | 말풍선 in-image 베이크→HTML 오버레이 전환 (lettering.json) | webtoon-assembly, letterer/compositor/QA | "이미지랑 글자가 따로 논다" 피드백 + 한글 베이크 재렌더 루프 제거 |
| 2026-08-08 | 콘티(storyboard.html) 승인 게이트 신설, display_height 위계 복원 | webtoon-panel-breakdown, panel-director | "속도감·완급 없다"(이석진 실장) 피드백 — 컷 높이 평탄화가 원인 |
| 2026-08-08 | 시나리오 9 에이전트→3 통합 (story-architect/episode-designer/script-writer) | webtoon-scenario, agents | 제작 시간 단축(직렬 9단계 병목), 품질 게이트 G1~G16 승계 |
| 2026-08-08 | 오케스트레이터 재작성 (19 에이전트, 새 파이프라인) + CLAUDE.md 등록 | webtoon-orchestrator | 위 4개 개편 통합 |
| 2026-08-22 | 성경 웹툰 「꿈 꾸는 자」(창세기 요셉) 기획 전환. 「원한 정산부」는 `_workspace_wonhan_*/`에 보관 | 전체 | 사용자 "내용이 이해가 안 된다" → 교회용 성경 각색으로 전환 |
| 2026-08-22 | 성경 각색 특수 규약 신설 (본문 대조 게이트, `[본문]/[연결]/[해석]` 라벨, 창작분 표시, 교회 고지 문서) | 시나리오·비주얼·조립 전 단계 | 교회에서 쓰이므로 본문 정확성이 최우선 |
| 2026-08-24 | **배치 렌더 모드 추가** (`scripts/gemini_batch.py` — 단가 50%, Files API ref 업로드 캐시) | webtoon-panel-render, panel-renderer | 렌더 비용 절감. 회차당 약 $18 → $9 |
