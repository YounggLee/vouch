# vouch — AI-native Diff Reviewer (v3 brainstorm 결과)

- **날짜**: 2026-04-26
- **저자**: yj.l@navercorp.com
- **컨텍스트**: CMUX × AIM Intelligence Hackathon Seoul (one-day, terminal-only, 6pm ship)
- **트랙**: Developer Tooling
- **참가 형태**: 솔로
- **타깃 심사관**: Austin Wang (cmux/Manaflow), AIM Intelligence 엔지니어
- **수반 문서**: [2026-04-26-ardiff-analysis.md](./2026-04-26-ardiff-analysis.md) (경쟁 분석, 이전 코드네임 ardiff 시점에 작성됨)

## 0. 변경 이력

### v3.2 (현재 — pre-flight 환경 점검 후)
- **남은 시간 2h 46m** (15:14 → 18:00 ship)으로 확인. 시간 잔인하게 빡빡하지만 scope 유지
- **P1 PR 모드 인스코프** (github.com, gh CLI 인증 사용)
- **P2 두 단계 LLM 호출 유지** (semantic 후처리 + 분석 따로)
- **P3 claude-hook stop 자동 트리거 인스코프** (R3 risk 받아들임)
- **P4 Python 3.9.6 사용** (시스템 설치본). spec §10의 3.12+ 표기 수정
- **P5 데모 fixture**: 미리 만든 todo 앱 + 사전 캐시된 LLM 응답

### v3.1
- **이름 확정**: `ardiff` → **`vouch`** ("you vouch, AI helps" — 사람이 결정에 보증한다는 디자인 원칙을 이름이 직접 표현)
- **Semantic hunk 단일화**: git hunk를 사용자에게 노출하지 않음. **vouch는 semantic hunk만 보여준다.** Phase 1/2 분리 폐기. raw hunk는 내부 입력일 뿐
- 토글(g 키로 raw hunk 보기) 제거
- **cmux 강결합을 의식적으로 채택** (§6.1 참고). Host 추상화는 v2로 후퇴 — 지금은 cmux 전용 도구임을 정직하게 표명

### v2
- F3 Multi-Model Disagreement 컷 → §5 TODO
- Semantic hunk를 1급 시민으로 승격
- 입력 모드 3종 확정: 미커밋 / commit (또는 범위) / PR
- 언어/TUI: Python + Textual
- F1+F2+F4 단일 Gemini Flash batched call
- 데모는 사전 녹화/캐시된 LLM 응답
- 슬로건: "Closed-loop reject + Semantic hunk on cmux"

## 1. 문제

AI 코딩 에이전트가 코드를 만드는 속도가 사람이 검토하는 속도를 압도한다. 두 가지 우려가 동시에 존재:

1. **AI에게 PR 리뷰까지 전담시키면 안 된다** — 책임의 일부는 사람의 손에 남아야 한다
2. **그렇다고 매번 모든 변경을 사람이 통독할 수도 없다** — 생성 속도가 너무 빠르다

이 둘 사이에 도구가 필요하다.

## 2. 디자인 원칙

> **AI는 리뷰어가 아니라 "리뷰 보조 시니어 엔지니어"다.**
> AI는 결정하지 않는다. AI는 **분류**하고, **압축**하고, **의미적으로 묶고/쪼개고**, **자기 불확실성을 자백**한다. 결정 키(accept/reject)는 항상 사람의 손에 있다.

핵심 슬로건:
> **"You vouch. AI helps."**
> *Closed-loop reject + Semantic hunk on cmux — first cmux-native AI review CLI.*

부산물 슬로건:
> "AI는 사람의 30분짜리 리뷰를 5분짜리 리뷰로 줄인다 — 같은 의사결정 책임으로."

## 3. 사용자 텐션 → 디자인 응답 매핑

| 사용자의 우려 | vouch의 답 |
|---|---|
| "AI가 PR 리뷰를 전담하면 안 됨" | 결정 키는 항상 사람. AI는 분류·압축·이상 탐지만. accept/reject 입력은 사람의 키 입력. **이름 그대로 사람이 vouch한다.** |
| "근데 매번 다 못 봄" | Semantic hunk로 의미 단위 묶기 + Risk triage + Self-doubt로 진짜 봐야 할 10%만 사람이 본다. 나머지 90%는 빠르게 흘려보낸다. |
| "AI가 놓치는 게 있을 거임" | 사람이 항상 high-risk를 풀로 본다. AI는 사람의 "검토 우선순위"를 정할 뿐. False negative를 줄이는 보수적 분류 (의심스러우면 high). |
| "AI 분류를 어떻게 믿음?" | Self-doubt 자백을 함께 표시 — 큐에서 ⚠️/❓는 우선순위 자동 상승. 사람이 분류 자체를 한 키로 override 가능. |

## 4. 인스코프 기능 (해커톤 MVP)

### F1. Risk-Triaged Review Queue

모든 semantic hunk를 risk score로 분류해서 큐로 보여준다.

- **High** (🔴): 비즈니스 로직, 보안, 비-기계적 변경, 새 의존성 — 100% 사람 검토 강제
- **Medium** (🟡): public API 시그니처, 상태 변이, 검증 로직 — 풀 검토 권장
- **Low** (🟢): rename, import 정리, 포매팅, 주석 — batch accept 옵션 제공

분류 근거를 한 줄로 자백 (예: "SQL 파라미터를 직접 보간 — 보안 검토 필요").

### F2. Self-Doubt Signal

각 semantic hunk에 LLM이 confidence를 첨부:

- ✅ Confident — 테스트 있음, 변경 의도 명확, 기존 패턴과 일치
- ⚠️ Uncertain — 기존 컨벤션을 추정해서 작성, 또는 영향 범위 모호
- ❓ Guess — 의도 불분명, 한 가지 해석으로 진행

큐에서 ⚠️/❓는 우선순위를 한 단계 자동 상승.

### F4. Plain-English Semantic Diff

semantic hunk 옆에 LLM이 만든 한국어 한 줄 설명을 붙여 사람이 빠르게 훑게 한다:

```
- if user.role == "admin":
+ if user.role == "admin" or user.is_super:
    grant_access()
```
> "관리자 외에 super 사용자도 접근 허용. 권한 확장."

1000줄 변경을 30초에 훑을 수 있게 만드는 핵심 기능.

### F1+F2+F4 통합 구현 노트

세 기능 모두 같은 입력(semantic hunk)에 대한 LLM 분석. **단일 Gemini 2.5 Flash 호출**에 batch + structured output (JSON schema)로 묶는다:

```jsonc
// 입력: semantic hunk N개의 diff
// 출력 schema (단위당)
{
  "id": "...",
  "risk": "high|med|low",
  "risk_reason": "한 줄",
  "confidence": "confident|uncertain|guess",
  "summary_ko": "한 줄"
}
```

레이턴시·비용·구현 모두 절약. semantic 후처리 호출과 분석 호출은 두 단계로 나뉘지만, 둘 다 batched 단일 호출.

### F7. Closed-Loop Reject — Feedback to Source Surface

reject 시 사람이 한 줄 사유를 적으면:

1. 모든 reject 사유를 모음
2. "다음 항목들이 이런 이유로 거절됐어 — 다시 시도해" 형태의 프롬프트로 빌드
3. **원래 생성 에이전트가 돌고 있는 cmux surface로 send** (`cmux send` + `cmux send-key Enter`)
4. 에이전트가 다시 시도 → claude-hook stop → vouch 자동 재실행 → 새 큐

이 루프가 **"사람이 진짜 owner"** + **"리뷰 결과가 학습 신호로 즉시 재투입"** 을 동시에 충족. **Revdiff와의 핵심 차별점** (Revdiff는 quit 시 structured output까지만, vouch는 send + 재시도 자동).

Source surface 식별:
- **1순위**: `VOUCH_SOURCE_SURFACE` 환경변수 (사용자가 명시)
- **2순위**: `--source-surface <ref>` CLI 플래그
- **3순위 (자동)**: claude-hook stop으로 호출된 경우, 호출자의 `CMUX_SURFACE_ID`를 자동으로 source로 사용

## 5. 아웃오브스코프 (TODO, 해커톤 후)

| 기능 | 이유 |
|---|---|
| F3. Multi-Model Disagreement | (D2) 추가 모델 호출 비용 + 데모 가치 < closed-loop 시연. 컷. |
| F5. Anomaly Detection (코드베이스 패턴 비교) | 인덱싱 무거움. 시간 부족. |
| F6. Per-Hunk Conversation | nice-to-have. 핵심 루프엔 불필요. |
| F8. Decision Memory | 누적 데이터 필요. 데모에서 가치 표현 어려움. |
| Worktree 입력 모드 | (D3) Phase 1 입력 3종으로 충분. cmux 멀티 에이전트 시나리오는 v2. |
| AST 기반 함수 단위 분할 | tree-sitter 도입 무거움. semantic hunk 후처리로 충분. |
| Raw git hunk 토글 보기 | (v3) semantic만으로 충분하다는 확신. UI 단순화. |
| **Host abstraction (cmux 외 환경 지원)** | (v3, §6.1) 의식적으로 v2로 후퇴. v1은 cmux 전용. v2에서 `Host` 인터페이스로 CmuxHost / PlainHost 분리, 일반 터미널에서도 degraded 모드로 동작 |
| **Agent-synchronous mode (stdout / `--output` 파일 캡처)** | **v1.1** — 에이전트가 vouch를 subprocess로 spawn하고 결과를 stdout 또는 `--output <file>`로 회수하는 동작. Revdiff와 동일한 통합 경로. `cli.on_send`에 file 채널 한 줄 추가 + `cmux.deliver_reject`에 "file" tier 한 단 추가. 정체성 영향 없음 (보조 채널). |
| **Plugin 생태계 (Claude Code / Codex / OpenCode / Pi / Zed skill)** | **v2 — 정체성 확장 결정 필요**. 에이전트가 vouch의 1급 launcher가 되는 모델. Revdiff와 직접 경쟁 영역으로 진입. 결정 축: vouch는 (a) async 사람 도구, (b) sync 에이전트 도구 양립 가능한가, 아니면 v1의 async-only 정체성을 유지하고 sync use case는 명시적으로 cut인가. 이 결정이 안 된 채로 코드부터 늘리면 "cmux-native + agent-launcher + closed-loop" 3중 메시지가 흐려진다. 별도 design doc 필요 (`docs/superpowers/specs/<date>-vouch-agent-mode.md`). |

## 6. cmux 통합 전략

vouch는 cmux 위에서 사는 **CLI + TUI**다. cmux의 자산을 최대로 활용 — 이게 Austin Wang에게 "cmux를 제대로 쓴 도구"로 보일 핵심 포인트.

### 6.1 의식적 강결합 결정

vouch v1은 **cmux 전용**이다. cmux 없이 실행하면 실행을 거부하고 안내 메시지를 출력한다. 이는 의식적 디자인 결정:

**결합 부위**:
| 기능 | 의존도 | cmux 부재 시 |
|---|---|---|
| 핵심 리뷰 루프 (큐/accept/reject) | 0% | 동작 (Textual TUI 자체) |
| Diff 파싱·LLM 분석 | 0% | 동작 |
| claude-hook stop 자동 트리거 | 100% | 작동 불가 (수동 실행만) |
| Source surface 자동 식별 | 100% | 작동 불가 |
| reject 프롬프트 send | 100% | 작동 불가 |
| set-status / set-progress 사이드바 | 100% | 작동 불가 |
| notify | 100% | 작동 불가 |
| markdown viewer / multi-pane | 100% | 작동 불가 |

→ closed-loop 자동화 + 사이드바 시각화 = vouch의 데모 wow의 60%. 이게 cmux 전용으로 가는 이유.

**왜 의식적으로 강결합 채택**:
1. 해커톤 컨텍스트(CMUX × AIM 행사) — "cmux 전용"이 약점이 아니라 메시지
2. 6h 솔로엔 추상화 비용도 의미 있는 시간 손실
3. closed-loop의 진짜 자동화는 cmux의 claude-hook 없이 만들 수 없음 — 이 차별점을 약화시키지 않으려면 cmux를 가정해야 함
4. Austin Wang에 직격하는 포지셔닝 ("first cmux-native AI review CLI")

**얻는 것**: 데모 임팩트 극대화, 시간 절약, 차별점 보존
**잃는 것**: cmux 미사용자 시장 (그러나 v1 타깃 아님)

### 6.2 사용한 cmux 기능 매핑

| cmux 기능 | vouch에서의 역할 |
|---|---|
| `read-screen / send / send-key` | F7 closed-loop의 핵심: 원 에이전트 surface와 통신 |
| `markdown` viewer 패널 | F4 plain-English diff + reject 사유 노트 렌더 |
| `set-status` | 검토 진행률을 사이드바에 시각화 ("12/47 reviewed · 3 high pending") |
| `set-progress` | 0–1 진행률 표시 |
| `notify` | 큐 빌 때, 새 변경 들어올 때 알림 |
| `set-hook` (tmux 호환) | 사용자가 "session-stopped" 등 이벤트에 vouch 자동 실행 binding 가능 |
| `claude-hook stop` (stdin JSON) | Claude Code stop hook → vouch 자동 트리거 |
| `new-pane / new-surface` | 큐 / diff / 대화 패널 자동 분할 |
| `CMUX_SURFACE_ID` 환경변수 | F7 source surface 자동 식별 |
| `tree --all` (이름→ref 해석) | 사용자가 source surface를 이름으로 지정해도 매핑 가능 |

## 7. 리뷰 단위 — Semantic Hunk (단일 단위)

**vouch가 사람에게 보여주는 단위는 오직 semantic hunk 하나다.** raw git hunk는 내부 입력일 뿐 UI에 노출되지 않는다.

### 단위 계층 (내부 처리)

```
파일
└── git hunk (raw, 내부 전용)
    ↓ semantic 후처리 LLM 호출
    └── semantic hunk  ← 사용자가 보는 유일한 단위
```

### Semantic hunk 정의

LLM이 raw git hunk들을 입력으로 받아 두 가지 후처리를 수행:

#### (1) **Splitting (쪼개기)** — 큰 hunk 분할

긴 git hunk는 의미 경계로 쪼개서 여러 semantic hunk로 나눈다.

예: 30줄짜리 git hunk 한 개 →
- semantic hunk #1 "검증 로직 추가"
- semantic hunk #2 "에러 처리 분기"
- semantic hunk #3 "로깅 추가"

#### (2) **Grouping (묶기)** — 의도적으로 함께 본 hunk 그룹화

서로 다른 파일/함수에 흩어진 hunk가 **같은 변경 의도**일 경우 한 카드로 묶는다.

예:
- file `auth.py`의 raw hunk #2 (함수 시그니처 변경)
- file `views.py`의 raw hunk #5 (caller 업데이트)
- file `views.py`의 raw hunk #11 (다른 caller 업데이트)
- file `tests/test_auth.py`의 raw hunk #1 (테스트 시그니처 업데이트)

→ semantic hunk: **"check_access에 ctx 파라미터 추가 + caller 3곳 + 테스트 1곳 동시 업데이트"**. 한 카드로 본다.

### 왜 semantic hunk가 vouch의 핵심인가

일반 코드 리뷰 도구는 git이 잘라준 hunk를 그대로 보여준다. AI가 만든 변경은 **맥락이 여러 파일·여러 hunk에 걸침**. 사람이 이걸 머리로 다시 묶는 것이 리뷰의 가장 큰 인지 부담이다. vouch는 이 작업을 AI가 대신 해서, 사람은 **"한 의도 = 한 결정"**의 깔끔한 단위로 본다. raw hunk를 사용자에게 노출하지 않는 것은 의식적 선택 — "AI가 정리한 결과를 사람이 vouch한다"는 워크플로우를 강제하기 위함.

### 처리 파이프라인

```
1. Diff 입력 (§8 모드)
2. unidiff로 raw git hunk 파싱
3. Semantic 후처리 LLM 호출 (1회, batched) — splitting/grouping 결정
4. Semantic hunk 목록 생성 (각 항목에 원래 raw hunk들 reference)
5. F1+F2+F4 분석 LLM 호출 (1회, batched) — risk/confidence/summary 첨부
6. TUI 큐에 렌더
```

### 실패 처리

- semantic 후처리 LLM 호출 실패/timeout → 에러 표시 + 재시도 키 제공. **raw hunk로 fallback하지 않음** (디자인 결정: semantic만 보여준다는 약속을 지킴)
- 50 hunk 초과 등 prompt 폭발 임계 → 자동 chunking (raw hunk를 N개 단위로 잘라 여러 후처리 호출 → 결과 병합)

## 8. 입력 모드 (D3 결정)

vouch는 세 가지 입력 모드를 지원:

| 호출 형태 | 의미 |
|---|---|
| `vouch` | **미커밋 변경**: working tree의 unstaged + staged 통합 diff |
| `vouch <commit>` | **단일 commit**: `<commit>^..<commit>` |
| `vouch <ref>..<ref>` | **commit 범위** |
| `vouch --pr <number>` 또는 `vouch <pr-url>` | **PR 모드**: `gh pr diff` 사용 |

worktree path 모드는 TODO.

기본값: 인자 없으면 "미커밋 변경" 모드. 데모도 이 모드.

## 9. 데모 시나리오 (6pm 발표용, 90초)

**사전 준비**:
- 고정된 todo 앱 fixture
- Claude Code가 만들어낸 14파일 변경 snapshot (사전 녹화)
- semantic 후처리 + F1+F2+F4 LLM 응답 캐시 (라이브 호출 0–1회)

**라이브 흐름**:

1. cmux workspace에서 `vouch` 실행 (미커밋 변경 모드)
2. Semantic 후처리 진행률이 cmux progress bar로 표시 (3초)
3. 큐 등장: 47 raw hunk가 **18 semantic hunk**로 압축됨. 분류: 🔴 3 / 🟡 7 / 🟢 8
   - 예: "auth 도입: 4파일 8 hunk가 1 단위" 카드
4. 🟢 8개를 `A` 키로 batch accept (5초)
5. 🟡 7개를 `j/k`로 훑음, plain-English 한 줄로 1초씩 (10초)
6. 🔴 3개 풀 검토 — 그중 하나에 `r` reject + "이 SQL은 파라미터 바인딩 사용해야 함" 사유 작성 (15초)
7. vouch가 reject 사유를 모아 source surface로 send → cmux 다른 pane에서 Claude Code가 받아서 작업 시작 (live)
8. claude-hook stop 발생 → vouch 자동 재실행, 새 큐 표시 → 깨끗 → `A` accept (10초)
9. cmux 사이드바: "review complete · 18/18" status

심사관 인지 포인트:
- cmux 사이드바·notification·multi-pane이 1급 시민으로 쓰임 → Austin
- "AI가 결정 안 함, 사람이 키로 vouch함" → AIM Intelligence
- 47 raw hunk → 18 semantic hunk 압축이 시각화 → 차별점
- closed-loop이 같은 cmux 화면 안에서 순환 → "first cmux-native AI review"

## 10. 기술 스택 (확정)

- **언어**: Python 3.9.6 (시스템 설치본 사용 — 환경 셋업 시간 절약)
- **TUI**: [Textual](https://textual.textualize.io/) (rich-based, async, 빠른 개발)
- **LLM**: Gemini 2.5 Flash (해커톤 크레딧, structured output 지원, 저레이턴시)
- **Diff 파싱**: `unidiff` 라이브러리
- **Git 호출**: subprocess via Python (`git diff`, `git show`)
- **PR fetch**: `gh pr diff <num>` shell out
- **cmux 연동**: subprocess via Python (`cmux send` / `read-screen` / `set-status` 등)

## 11. 성공 기준

- ≥10 raw git hunk가 있는 변경에 대해 semantic 후처리가 동작하여 단위 수가 줄어들거나(grouping) 큰 hunk가 쪼개짐(splitting)
- 사용자가 "AI에 결정을 넘기지 않은 상태"로 작업이 끝났다고 느낀다
- cmux 사이드바에 진행률이 시각화된다
- reject feedback이 실제로 source surface에 전달되고, claude-hook stop 트리거로 재실행이 일어난다
- 데모를 90초 안에 끝낼 수 있다
- semantic 후처리가 실패해도 명확한 에러 + 재시도로 우아하게 처리됨 (raw hunk로 회귀하지 않음)

## 12. Risks (명시)

### R1. **Semantic hunk 단일화 결정의 risk** ⚠️

분석 문서는 semantic hunk 자체를 "시도 금지" 권고했다. 사용자가 D1에서 "이게 cli의 핵심"으로 못박았고, v3에서 raw fallback도 제거. **명시적으로 받아들인 risk**:

- **시간 risk**: semantic 후처리 LLM 호출 + 결과 검증 로직이 추가 시간 요구. 6h엔 빡빡
- **데모 risk**: semantic 후처리가 비결정적 (LLM 응답에 따라 묶기 결과 달라짐) → 데모 fixture는 사전 녹화 LLM 응답으로 결정성 보장
- **fallback 없음 risk**: 후처리 실패 시 사용자에게 에러만 표시. raw로 안 떨어뜨림. → 데모 환경에선 캐시된 응답으로 우회 가능. 실사용에선 retry 키 제공

### R2. Revdiff와의 직접 비교

심사관이 Revdiff를 알 가능성. "Revdiff랑 뭐가 다름?" 답변 카드:
1. **cmux-native** (set-status / set-progress / claude-hook 1급 활용)
2. **Closed-loop send + 재시도 자동화** (Revdiff는 structured output까지, vouch는 send + claude-hook 트리거 + vouch 재실행)
3. **Semantic hunk** (Revdiff는 git hunk 그대로) — vouch만의 단일화된 의미 단위

### R3. claude-hook stop 자동 트리거의 환경 의존성

사용자가 cmux + Claude Code 통합 hook을 미리 설치해야 함. 데모 환경엔 사전 셋업 필요.

### R3.1. cmux 강결합 → 시장 좁음

§6.1의 의식적 결정에 따른 risk. v1은 macOS + cmux 사용자만 대상. 심사관이 "cmux 없으면?" 물을 경우 답변 카드:

- "v1은 의도적으로 cmux 전용. closed-loop 자동화는 cmux의 claude-hook 없이는 불가능"
- "Host 추상화는 v2 로드맵 (§5 TODO). PlainHost로 일반 터미널에서 degraded 동작 가능"
- "이번 해커톤은 CMUX × AIM 행사 — cmux 사용자가 1차 타깃이 자연스러움"

### R4. 큰 입력에서 Semantic 후처리 prompt 폭발

50 hunk 초과 시 LLM 호출 prompt가 길어 timeout/비용 위험. 임계치에서 자동 chunking으로 분할 처리 (§7 실패 처리 참고).

## 13. 액션 아이템

- [x] 이름 확정 → vouch (D5)
- [x] 슬로건 재작성 → "You vouch. AI helps."
- [x] F3 multi-model: 컷 (D2)
- [x] §7 리뷰 단위 확정: semantic hunk 단일화 (D1+v3)
- [x] F1+F2+F4 batch single-call 구조 spec 반영
- [x] cmux `set-hook` / `claude-hook` 능력 확인
- [x] 언어/TUI: Python + Textual 확정
- [x] 입력 모드 3종 확정 (D3)
- [ ] 데모용 todo 앱 fixture와 14파일 diff snapshot 사전 준비 (구현 단계)
- [ ] LLM 응답 캐시 (semantic 후처리 + 분석 두 단계 모두) 구현
- [ ] "Revdiff와의 차이" 답변 카드 1장 작성 (R2)
- [ ] cmux Claude Code stop hook 설치 절차 데모 환경에 사전 적용 (R3)
- [ ] semantic 후처리 chunking 로직 (50 hunk 임계, R4) 설계
- [ ] cmux 부재 감지 + 안내 메시지 (§6.1) 구현 — `cmux ping` 실패 시 "vouch v1 requires cmux. See v2 roadmap for plain-terminal mode." 출력 후 exit
- [ ] "cmux 없으면?" 질문 답변 카드 (R3.1)

## 14. 다음 단계

1. spec self-review (placeholder/모순/스코프 검사) — 인라인 fix
2. 사용자 spec 리뷰 게이트
3. 승인 후 `superpowers:writing-plans` skill로 구현 계획 생성
