# ardiff — 해커톤 적합성 분석

- **날짜**: 2026-04-26
- **저자**: yj.l@navercorp.com
- **대상 문서**: [2026-04-26-vouch-design.md](./2026-04-26-vouch-design.md) (분석 작성 시점엔 코드네임 `ardiff`였음, 이후 `vouch`로 개명)
- **컨텍스트**: CMUX × AIM Intelligence Hackathon Seoul, 솔로, 6pm ship

## 0. 한 줄 결론

> **"AI 리뷰의 closed-loop을 cmux 위에서 처음으로 돌린 도구"** 한 문장으로 좁히고, F1/F2/F4는 그 슬로건의 부속품으로 깎아내야 한다. 그래야 Revdiff/Hunk/Greptile과 비교당해도 살아남고 6시간 안에 ship 가능하다.

핵심 우려:

1. F1·F2·F4는 이미 시장에 commodity. 핵심 차별성 약함.
2. F7 영역은 Revdiff가 거의 같은 포지셔닝. "Claude Code 후속 리뷰 TUI"는 이미 존재.
3. 솔로 6시간에 비해 스코프가 10–12시간짜리.
4. 진짜 차별점은 **cmux 깊은 통합**과 **reject 사유 → 자동 프롬프트 빌드 → 원 surface로 send → 재시도** 자동화 두 가지.

## 1. 기존 제품 매핑

| ardiff 기능 | 이미 하고 있는 제품 | 차별성 |
|---|---|---|
| F1 Risk Triage (high/med/low) | Greptile (catch rate 82%, confidence 1–5), OpenCode TUI `/fullreview` (working tree에서 risk assessment), CodeRabbit CLI, Cubic, Macroscope v3 (2026-02, precision 98%) | ❌ 표준 기능. 차별 포인트 거의 없음 |
| F2 Self-Doubt (✅/⚠️/❓) | Greptile의 5단 confidence score (저신뢰 PR은 사람이 먼저 보는 triage 워크플로 이미 운영됨) | ⚠️ 3단 라벨 + "자백체" UX는 신선하나 본질은 동일 |
| F3 Multi-Model Disagreement | Kosli (persona × model 2개 cross-check, finding agreement 28% 사례), theaiconsensus, 학술적으로 cross-model semantic disagreement = epistemic uncertainty 신호 (OpenReview 2026) | ✅ PR 리뷰 TUI 안에 시각적으로 녹인 사례는 거의 없음 — 차별성 있음 |
| F4 Plain-English Diff | SemanticDiff (tree-sitter AST 기반), GitHub Copilot diff summary, CodeRabbit, 거의 모든 PR 봇 | ❌ 완전 commodity |
| F7 Reject → Feedback Loop | **Revdiff** (revdiff.com — "Diff Review TUI for Claude Code & AI Agents", structured output on quit, Claude Code/Pi/OpenCode 연동). **Hunk** (modem-dev/hunk — `--agent-context`). **Critique** (remorses/critique — `critique review` 명령으로 Claude Code/OpenCode 백엔드 호출) | ⚠️ Revdiff가 가장 가까운 위협 — 같은 포지셔닝. 단, ardiff처럼 "reject 사유를 모아 자동 프롬프트 빌드 → cmux surface로 send" 자동화는 한 발 앞섬 |
| cmux 깊은 통합 | 없음 | ✅ 진짜 차별점. Austin Wang 심사관과 직결 |

### 가장 가까운 경쟁자 3종

- **Revdiff** (revdiff.com): "Diff Review TUI for Claude Code & AI Agents". Syntax highlight + inline annotation, quit 시 structured output을 AI 에이전트로 송신. **현재 ardiff와 가장 유사한 제품**. 데모 청자가 알고 있을 가능성 높음 — "Revdiff랑 뭐가 달라요?" 질문에 답을 미리 준비해야 함.
- **Hunk** (modem-dev/hunk): "review-first terminal diff viewer for agentic coders". `--agent-context`로 라이브 agent-assisted 리뷰. Risk triage·confidence·feedback loop은 명시되지 않음.
- **Critique** (remorses/critique): TUI git diff viewer. `critique review` 명령은 OpenCode/Claude Code 백엔드로 hunk 정렬 + 설명. 피드백을 agent로 *보내는* 구조는 아님.

## 2. 포지셔닝 재정립

문서의 4기능 매트릭스(F1–F4)는 이미 구식 메시지. 두 축으로 좁힐 것:

1. **cmux-native 리뷰 surface** — 다른 도구는 일반 터미널 위에서 도는데, ardiff는 cmux의 set-status / set-progress / set-hook / send를 1급 시민으로 사용. Austin Wang에게 90% 점수.
2. **Closed-loop Reject** — Revdiff는 quit 시 structured output까지만. ardiff는 한 발 더: reject 사유 → 프롬프트로 자동 빌드 → 원 에이전트 surface에 직접 send → 재시도 루프. 이게 슬로건이 되어야 함. ("리뷰가 학습 신호로 즉시 재투입")

F1/F2/F4는 "이걸 가능하게 하는 분석 레이어" 정도로 톤 다운. 데모 시간의 60%는 cmux 사이드바 시각화 + reject 루프 시연.

AIM Intelligence(AI safety) 어필 포인트: "AI에게 결정 안 넘김 + Self-doubt 강제 자백" 메시지는 그대로 좋음.

## 3. 일정 리스크

솔로 6시간 추정:

| 작업 | 시간 |
|---|---|
| F1 risk triage (LLM 호출 + 큐 UI) | 1.5h |
| F2 self-doubt (F1 호출에 통합) | +0.3h |
| F3 multi-model (병렬 호출 + 의견차 비교) | 1h |
| F4 plain-English (F1 호출에 통합) | +0.2h |
| F7 reject feedback loop + cmux send | 1.5h |
| cmux 통합 (status/progress/hook/new-pane) | 1.5h |
| TUI 자체 (큐 / diff / 키바인딩) | 3–4h |
| 데모용 fixture 셋업 (todo 앱 + 인증 변경) | 1h |
| **합계** | **10–12h** |

→ **6시간으로 절대 못 끝낸다.**

### 스코프 컷 권고

- **F3 multi-model**: cut 또는 사전 녹화 fixture로 fake. 두 모델 병렬 호출 + 의견 차 요약은 시간 먹는데 데모 가치는 F7보다 낮음.
- **§7 Semantic hunk**: AST로 묶기 절대 시도 금지 → **git hunk 그대로**. 차별성은 cmux/F7에 두는 거지 hunk 단위가 아님.
- **F1+F2+F4**: 단일 Gemini Flash 호출 1번에 batch + structured output으로 묶기 (hunk 10–50개 → JSON 한 번). §11에 적힌 비용 폭발 우려 + 레이턴시 동시 해결.

## 4. §11 미해결 항목 결정 권고

- **입력**: worktree path 단일 인자 (`ardiff <path>`). cmux가 워크스페이스 = worktree 단위라 자연스러움.
- **Source surface 식별**: `CMUX_SOURCE_SURFACE` 환경변수 우선, fallback은 `--source-surface` 플래그. cmux의 `set-hook`이 stop 이벤트와 함께 surface ID를 노출하는지 먼저 확인 필요 (cmux 현재 버전 기능 확정 필요).
- **언어**: Python + Textual을 즉시 결정. 솔로 1일에 결정 미루기는 사치. cmux CLI는 shell out이라 언어 무관.

## 5. 데모 리스크

§8 시나리오 9번 "이번엔 깨끗 → accept all"은 라이브 LLM 답이 다를 위험이 큼. **녹화본 + 고정 fixture diff** 권고. 90초 데모면 라이브 LLM 호출은 한 번만 진짜로, 나머지는 캐시/녹화.

## 6. 액션 아이템

- [ ] 슬로건 재작성: "Closed-loop reject on cmux"로 좁힘
- [ ] F3 multi-model disagreement: 컷 또는 fake fixture 결정
- [ ] §7 리뷰 단위: git hunk로 확정 (semantic hunk 시도 금지)
- [ ] F1+F2+F4 batch single-call 구조로 통합 설계
- [ ] cmux `set-hook` stop 이벤트의 surface ID 노출 여부 확인
- [ ] 언어/TUI: Python + Textual로 확정
- [ ] 데모용 todo 앱 fixture와 14파일 diff snapshot 사전 준비
- [ ] "Revdiff와의 차이" 질문 대응 답변 준비 (closed-loop + cmux native 두 축)

## 부록 A. 참고 자료

- [revdiff — Diff Review TUI for Claude Code & AI Agents](https://revdiff.com/)
- [modem-dev/hunk — Review-first terminal diff viewer for agentic coders](https://github.com/modem-dev/hunk)
- [remorses/critique — TUI for reviewing git changes](https://github.com/remorses/critique)
- [Greptile benchmarks — confidence scoring & catch rate](https://www.greptile.com/benchmarks)
- [Bugbot vs CodeRabbit vs Greptile vs Graphite (2026)](https://getoden.com/blog/coderabbit-vs-cursor-bugbot-vs-greptile-vs-graphite-agent)
- [Kosli — multi-model cross-check for AI code review](https://www.kosli.com/blog/ai-code-review-with-specialized-llm-personas/)
- [Cross-Model Disagreement for Uncertainty Quantification (OpenReview)](https://openreview.net/forum?id=lOoRJo8xWy)
- [SemanticDiff — language-aware diff](https://semanticdiff.com/)
- [10 Open Source AI Code Review Tools (Augment, 2026)](https://www.augmentcode.com/tools/open-source-ai-code-review-tools-worth-trying)
- [manaflow-ai/cmux GitHub](https://github.com/manaflow-ai/cmux)
- [State of AI Code Review Tools 2025 (devtoolsacademy)](https://www.devtoolsacademy.com/blog/state-of-ai-code-review-tools-2025/)
