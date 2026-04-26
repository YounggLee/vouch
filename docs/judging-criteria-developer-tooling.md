# Developer Tooling 트랙 심사 기준

> 출처: CMUX x AIM Hackathon Guide — Developer Tooling 트랙 채점 루브릭
> 트랙 정의: CLI-first developer tools. Terminal workflows, agent orchestration, code generation, debugging.

## 채점 항목 및 가중치

| 항목 | 가중치 |
|---|---|
| Technical Depth | **30%** |
| Developer Experience | **25%** |
| Usefulness & Real-World Fit | **25%** |
| Demo & Presentation | **10%** |
| Judge's Personal Rating | **10%** |

각 항목은 1~5점으로 채점된다.

## 항목별 1~5점 정의

### Technical Depth (30%)

| 점수 | 정의 |
|---|---|
| 1 — Surface | Basic wrapper around existing tools, no novel engineering |
| 2 — Functional | Working integration with some custom logic |
| 3 — Solid | Non-trivial engineering, handles edge cases |
| 4 — Impressive | Complex architecture, custom protocols or parsers |
| 5 — Exceptional | Novel technical contribution, publication-worthy depth |

### Developer Experience (25%)

| 점수 | 정의 |
|---|---|
| 1 — Surface | Hard to install, confusing UX, poor feedback |
| 2 — Functional | Works but has friction; docs are incomplete |
| 3 — Solid | Smooth CLI/API, reasonable defaults, helpful errors |
| 4 — Impressive | Thoughtful ergonomics, great error messages, fast |
| 5 — Exceptional | "This is how it should work." Immediately intuitive |

### Usefulness & Real-World Fit (25%)

| 점수 | 정의 |
|---|---|
| 1 — Surface | Unclear who benefits or when you'd use it |
| 2 — Functional | Useful in narrow, specific scenarios only |
| 3 — Solid | Solves a real daily pain point for developers |
| 4 — Impressive | Many devs would reach for this immediately |
| 5 — Exceptional | Fills an obvious gap; hard to unsee it |

### Demo & Presentation (10%)

| 점수 | 정의 |
|---|---|
| 1 — Surface | Hard to follow what the tool does |
| 2 — Functional | Shows it works but misses the compelling use case |
| 3 — Solid | Concrete demo, explains the value well |
| 4 — Impressive | Live demo lands; judges want to try it themselves |
| 5 — Exceptional | Story + demo make the case unforgettably |

### Judge's Personal Rating (10%)

| 점수 | 정의 |
|---|---|
| 1 — Surface | Not interesting or compelling to me personally |
| 2 — Functional | Somewhat interesting but wouldn't think about it again |
| 3 — Solid | Solid idea; I can see the appeal |
| 4 — Impressive | I'd tell a colleague about this |
| 5 — Exceptional | This genuinely excites me; I want to see it succeed |

## 심사 진행 절차

1. **Submission** — Google Form 제출, 마감 6:00pm sharp
2. **Track Round** — 팀당 3분 발표 + 2분 채점 (비공개). 트랙별 1·2위 → Finalist 진출
3. **Finalist Round** — 6팀이 공개 발표 (3분)
4. **Final Judging & Awards** — Grand Prize + 트랙 우승 발표

## 제출 요건

- 팀당 1건 (중복 시 실격)
- 6:30pm 현장 심사에 최소 1명 참석 필수
- 배포된 데모 링크 + GitHub repo URL 필수 (`localhost`는 무효)

## 전략 메모

- **합산 가중치**: 기술 + DX + 유용성 = 80%, 발표 + 개인선호 = 20%
- **Technical Depth 3점 이상 확보**가 가장 중요. 단순 API 래퍼는 1점 직행
- **Live demo가 매끄럽게 작동**해야 Demo 4점. 설치 1줄(`pip install` / `npm i` / `curl | sh`) 동작 점검 필수
- **타겟 유저·시나리오를 30초 안에 납득**시켜야 Usefulness 3점 이상
