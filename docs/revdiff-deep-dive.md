# revdiff Deep Dive

**revdiff**의 디자인·아키텍처·UX·통합 방식을 자체 도구 개발 관점에서 정리한 문서. 공식 문서(<https://revdiff.com/docs>)와 Claude Code 플러그인 v0.8.6의 reference 파일을 통합 분석.

---

## 1. 한 줄 정의

> "AI 에이전트가 만든 변경분(diff)을 사람이 TUI에서 라인 단위로 코멘트하면, 그 코멘트를 stdout 구조화 텍스트로 뱉어 에이전트에게 다시 넘긴다."

즉 **사람 ↔ AI 사이의 코드 리뷰 핸드오프 채널**이다. Web 기반 PR 리뷰 UI(GitHub PR 등)를 터미널에 끼워 넣어, AI 에이전트의 작업 루프 안에 자연스럽게 들어가게 한 것.

---

## 2. 왜 만들어졌는가 (문제 의식)

기존 워크플로우의 문제:

| 상황 | 기존 방식 | revdiff 개선점 |
|------|----------|---------------|
| AI가 만든 코드 리뷰 | Claude/Codex 채팅창에서 자연어로 "여기 고쳐줘" | TUI에서 해당 라인에 직접 핀 꽂기 → 위치 명확 |
| 수정 사항 다중 전달 | 각 파일·라인을 채팅으로 일일이 설명 | 한 번에 여러 라인에 어노테이션 → 일괄 전달 |
| AI의 수정 검증 루프 | 다시 채팅으로 "확인했어, 이 부분 더" | revdiff 재실행 → 사용자가 quit할 때까지 반복 |
| 컨텍스트 손실 | 스크롤·발췌 과정에서 line number/diff 컨텍스트 깨짐 | 구조화된 출력 포맷이 line, hunk, type까지 보존 |

**핵심 인사이트**: 어노테이션을 stdin 입력이 아닌 **TUI 종료 시 stdout 출력**으로 캡처한다는 것. 비동기 사용자 입력을 동기 stdout 결과로 변환하는 트릭이 통합의 핵심.

---

## 3. 핵심 동작 모델 (시스템 시퀀스)

```
[Claude Agent] ──launch──▶ [revdiff TUI overlay]
                              │
                              ├─ 사용자가 diff 탐색
                              ├─ a/Enter로 라인 어노테이션
                              ├─ A로 파일 어노테이션
                              ├─ Ctrl+E로 $EDITOR 다중 줄
                              │
                              ▼ q (저장 종료) / Q (폐기)
                          stdout: 구조화된 텍스트
                              │
                          [Claude Agent]
                              ├─ 분류: 설명요청 vs 수정지시
                              ├─ 수정지시 → plan mode → edit
                              ├─ 설명요청 → markdown 생성 → revdiff --only로 다시 띄움
                              │
                              └─ 루프: 어노테이션 0개로 종료할 때까지
```

**중요한 설계 결정**:
- 어노테이션이 있는 채로 종료(`q`)하면 **자동으로 history 파일에 백업**한다 (`~/.config/revdiff/history/<repo>/<ts>.md`). stdout 캡처가 실패해도 복원 가능.
- `--output` 플래그로 stdout 대신 파일로 출력 가능 → 비동기 처리 친화적.

---

## 4. 입력 모드 5가지 (모드별 책임 분리)

revdiff의 진짜 강점은 **diff뿐만 아니라 임의 텍스트도 같은 UX로 어노테이션**할 수 있다는 점. 이는 모드의 직교성에서 나온다.

| 모드 | 활성 조건 | VCS 필요 | 사용 사례 |
|------|----------|---------|----------|
| **일반 diff** | `revdiff [base] [against]` | ✓ (git/hg/jj) | 커밋·브랜치·HEAD~N 비교 |
| **staged** | `--staged` | ✓ (git/jj) | index만 리뷰 |
| **all-files** | `--all-files` | ✓ (git/jj) | 트래킹된 모든 파일 브라우징 — **변경분 없이도** 코드 리뷰 |
| **only (단일 파일)** | `--only=path` | ✗ | 임의 파일을 컨텍스트-온리 모드로 — md/문서 리뷰에도 |
| **stdin (스크래치)** | `--stdin` | ✗ | 파이프 입력을 합성 파일처럼 — `terraform plan \| revdiff --stdin` |

**상호 배타성 매트릭스** (직교성 보장):
- `--stdin` ↔ refs / `--staged` / `--only` / `--all-files` / `--include` / `--exclude`
- `--all-files` ↔ refs / `--staged` / `--only`
- `--include`/`--exclude`는 일반 diff + all-files 양쪽에서 작동 (필터 prefix 매칭)

**컨텍스트-온리 모드의 의미**: VCS 변경이 없는 파일은 `+/-` 마커 없이 전체를 평면 텍스트로 보여주되, 어노테이션·구문 강조·검색 기능은 그대로. 이게 마크다운 plan 문서, AI 출력 검토 등에 결정적.

---

## 5. 출력 포맷 — 머신·사람 양립의 핵심

```
## handler.go (file-level)
consider splitting this file into smaller modules

## handler.go:43 (+)
use errors.Is() instead of direct comparison

## handler.go:43-67 (+)
refactor this hunk to reduce nesting

## store.go:18 (-)
don't remove this validation
```

### 포맷 규칙

| 요소 | 의미 | 비고 |
|------|------|------|
| `##` | 레코드 시작 마커 | 본문에 `## `가 있으면 한 칸 prefix(파서 보호) |
| `filename:line` | 위치 | 절대 라인 |
| `:line-end` | 범위 | 다중 라인 어노테이션 |
| `(+)` | 추가된 라인 | |
| `(-)` | 제거된 라인 | |
| `(file-level)` | 파일 단위 | A 키로 입력 |

### 포맷의 영리한 트릭

**"hunk" 키워드 자동 확장**: 어노테이션 본문에 단어 "hunk"(대소문자 무관)가 들어가면 출력 헤더가 자동으로 hunk 전체 범위로 확장됨. 사용자 입력은 단순한데 AI 소비자는 정확한 컨텍스트 범위를 받는다.

```
입력: handler.go:43 (+) "this hunk needs refactoring"
출력 헤더: ## handler.go:43-67 (+)   ← 자동 확장
```

이 한 가지 규칙이 사용자 부담을 0으로 만들면서 LLM 컨텍스트 정확도를 끌어올린다. **자체 도구 개발 시 참고할 만한 디자인 포인트**.

---

## 6. 어노테이션 분류 패턴 (Claude Code 플러그인 측 로직)

플러그인 스킬은 어노테이션 텍스트를 두 부류로 자동 분류:

### 설명 요청 (Explanation Request)
다음 중 하나를 만족 (case-insensitive):
- 본문에 `??`가 연속으로 2개 이상 등장
- 본문이 다음 단어로 시작: `explain`, `remind`, `describe`, `what is`, `what are`, `how does`, `how do`, `clarify`

→ AI가 코드를 읽고 markdown 답변 생성 → `/tmp/revdiff-explain-XXX.md` → `revdiff --only=...`로 다시 띄움 → 사용자가 markdown에 또 어노테이션 가능 (재귀적 Q&A 루프).

### 코드 수정 지시 (Code-Change Directive)
나머지 모든 어노테이션. plan mode 진입 → 사용자 승인 → 코드 수정.

**자체 도구 설계 함의**:
- 사용자에게 별도 UI 메타데이터(태그, 라벨)를 강요하지 않고 **본문 텍스트로 의도를 추론**한다.
- 마크 패턴(`??`)은 키보드 부담이 거의 없는 universal shortcut으로 잘 잡혔다.

---

## 7. 주요 키바인딩 (자체 도구의 UX 베이스라인 참고용)

### Navigation
| Key | Action |
|-----|--------|
| `j/k` `↑/↓` | 트리/diff 스크롤 |
| `h/l` `Tab` | 패인 전환 |
| `[` `]` | 이전/다음 hunk |
| `n` `p` | 이전/다음 변경 파일 (검색 활성 시 → 다음 매치) |
| `Ctrl+d` `Ctrl+u` | 반 페이지 |
| `Home` `End` | 처음/끝 |

### Annotation
| Key | Action |
|-----|--------|
| `a` / `Enter` | 라인 어노테이션 |
| `A` | 파일 어노테이션 |
| `@` | 어노테이션 목록 팝업 |
| `d` | 커서 아래 어노테이션 삭제 |
| `Ctrl+E` | `$EDITOR` 호출 (다중 줄) |

### View Toggles
| Key | Action |
|-----|--------|
| `v` | collapsed 모드 |
| `C` | compact 모드 |
| `w` | word wrap |
| `t` | 트리/TOC 패인 숨김 |
| `L` | 라인 번호 |
| `B` | blame gutter |
| `W` | intra-line word diff |
| `T` | 테마 선택기(라이브 미리보기) |
| `f` | 어노테이션된 파일만 필터 |
| `i` | 커밋 정보 팝업 |
| `R` | VCS에서 재로드 |

### Exit
| Key | Action |
|-----|--------|
| `q` | 저장 종료 → stdout으로 어노테이션 출력 |
| `Q` | 폐기 종료 (확인 프롬프트) |

### Vim Motion (`--vim-motion` opt-in)
숫자 prefix + `j/k/G`, `gg`, `G`, `zz/zt/zb`, `ZZ/ZQ`. **숫자/g/z/Z 키가 인터셉터로 잡혀 다른 단축키를 가린다는 사이드이펙트**까지 명시되어 있음. 모드 토글의 부작용을 문서화한 디테일이 인상적.

### 마우스
- 휠 스크롤 (3줄/노치), Shift+휠 (반 페이지)
- 트리 좌클릭 → 파일 로드
- diff 좌클릭 → 커서 이동
- TOC 좌클릭 → 섹션 점프
- 팝업 좌클릭 → 확인

마우스 활성 상태에서 터미널 native 텍스트 선택은 막힘. 우회: kitty `Ctrl+Shift+drag`, iTerm `Option+drag`, 기타 `Shift+drag`. **이 trade-off를 문서에 박아둠** — 자체 도구도 trade-off를 숨기지 말 것.

---

## 8. 설정 시스템 (CLI flag > env > config > default)

### 설정 파일 (`~/.config/revdiff/config`, INI)
주요 항목 (기본값과 함께):

```ini
staged = false
tree-width = 2          # 1-10
tab-width = 4
no-colors = false
no-status-bar = false
wrap = false
collapsed = false
compact = false
compact-context = 5
line-numbers = false
blame = false
word-diff = false
no-confirm-discard = false
no-mouse = false
vim-motion = false
chroma-style = catppuccin-macchiato
theme = dracula
history-dir = ~/.config/revdiff/history/
keys = ~/.config/revdiff/keybindings
include = src
exclude = vendor,mocks
```

`revdiff --dump-config > ~/.config/revdiff/config`로 템플릿 생성.

### 환경 변수 매핑
모든 옵션이 `REVDIFF_*` 환경 변수와 1:1 대응 (`REVDIFF_STAGED`, `REVDIFF_THEME`, `REVDIFF_NO_MOUSE` 등). 컨테이너·CI 친화적.

### 키바인딩 (`~/.config/revdiff/keybindings`, INI)
```
map x quit
unmap q
map ctrl+d half_page_down

# Chord (2단계, leader는 ctrl+*/alt+*만)
map ctrl+w>x mark_reviewed
map alt+t>n theme_select
```

**가용 액션 풀** (자체 도구의 액션 모델 참고용):
`down`, `up`, `page_down`, `page_up`, `half_page_down`, `half_page_up`, `home`, `end`, `scroll_left`, `scroll_right`, `scroll_center`, `scroll_top`, `scroll_bottom`, `next_item`, `prev_item`, `next_hunk`, `prev_hunk`, `toggle_pane`, `focus_tree`, `focus_diff`, `search`, `confirm`, `annotate_file`, `delete_annotation`, `annot_list`, `toggle_collapsed`, `toggle_compact`, `toggle_wrap`, `toggle_tree`, `toggle_line_numbers`, `toggle_blame`, `toggle_hunk`, `toggle_untracked`, `mark_reviewed`, `theme_select`, `filter`, `commit_info`, `quit`, `discard_quit`, `help`, `dismiss`

**modal key는 remap 불가** (annotation input, search input, confirm discard) — 안전성 디폴트.

**macOS Alt chord 함정**: 터미널이 Option을 Meta로 전달하도록 별도 설정 필요(iTerm: Esc+, Terminal.app: Use Option as Meta, Kitty: `macos_option_as_alt yes`). 이런 호환성 issue도 문서화함.

---

## 9. 테마 시스템 (이중 구조)

revdiff 테마 = **revdiff 자체 색상(23개 키)** + **chroma 구문 강조 스타일**.

### 내장 테마 (8개)
`basic`, `catppuccin-latte`, `catppuccin-mocha`, `dracula`, `gruvbox`, `nord`, `revdiff`, `solarized-dark`

### 테마 관리 명령
```bash
revdiff --list-themes               # 사용 가능 목록
revdiff --theme dracula             # 적용
revdiff --init-themes               # 번들 테마 재생성
revdiff --install-theme nord        # 갤러리에서 단일 설치
revdiff --init-all-themes           # 갤러리 전체 설치
revdiff --dump-theme > ~/.config/revdiff/themes/my-custom  # 현재 색상 → 파일
```

### 23개 색상 키 (모두 `#rrggbb`, `REVDIFF_COLOR_*` env 지원)
`accent`, `border`, `normal`, `muted`, `selected-fg/bg`, `annotation`, `cursor-fg/bg`, `add-fg/bg`, `remove-fg/bg`, `word-add-bg`, `word-remove-bg`, `modify-fg/bg`, `tree-bg`, `diff-bg`, `status-fg/bg`, `search-fg/bg`

### Chroma 스타일 (60+ 종)
- 어두운 테마: `catppuccin-macchiato`(기본), `dracula`, `tokyonight-*`, `gruvbox`, `nord`, `monokai`, `github-dark`, `solarized-dark` 등
- 밝은 테마: `github`, `solarized-light`, `catppuccin-latte`, `gruvbox-light` 등

### 우선순위
- `--theme` 사용 시 → 다른 `--color-*` 와 env를 **모두 무시하고 덮어씀** (전체 적용)
- `--theme` 없을 때 → built-in defaults < config < env < CLI flag
- `--theme` + `--no-colors` → 경고 출력 후 테마 적용

`T` 키로 라이브 미리보기 가능한 **인터랙티브 테마 선택기**가 있음. 자체 도구도 도입 가치.

---

## 10. VCS 통합

| VCS | 일반 diff | --staged | --all-files | 비고 |
|-----|----------|----------|-------------|------|
| git | ✓ | ✓ | ✓ | 완전 지원 |
| Mercurial (hg) | ✓ | ✗ | ✗ | diff만 |
| Jujutsu (jj) | ✓ | ✓ | ✓ | git+jj 공동 위치 시 jj 워킹카피 모델 사용 |

`i` 키로 커밋 subject + body 팝업 (git/hg/jj 모두). git에서만 history 파일에 short commit hash 기록.

`revdiff --only`나 `--stdin`은 **VCS 비요구**. 즉 VCS는 diff 생성 수단일 뿐 핵심 의존성이 아니다.

---

## 11. 통합 진입점 (Plugin 생태계)

### Claude Code 플러그인
```
/plugin marketplace add umputun/revdiff
/plugin install revdiff@umputun-revdiff
```
- `/revdiff` 슬래시 + 자연어 트리거 ("review diff", "annotate this file" 등)
- 자동 ref 감지: main/master + uncommitted → uncommitted, main + clean → HEAD~1, feature + clean → main 비교, feature + uncommitted → AskUserQuestion
- 부속 플러그인 `revdiff-planning`: Claude가 plan mode 종료 시 자동 launch

### 터미널 멀티플렉서 자동 감지 (오버레이 방식)
우선순위 순서:

| 터미널 | 환경변수 | 오버레이 명령 |
|--------|---------|--------------|
| tmux | `$TMUX` | `display-popup` |
| zellij | `$ZELLIJ` | `zellij run --floating` |
| kitty | `$KITTY_LISTEN_ON` | `kitty @ launch --type=overlay` |
| wezterm/Kaku | `$WEZTERM_PANE` | `wezterm cli split-pane` |
| cmux | `$CMUX_SURFACE_ID` | `cmux new-split` + `cmux send` |
| ghostty (macOS) | `$TERM_PROGRAM` | AppleScript split + zoom |
| iTerm2 (macOS) | `$ITERM_SESSION_ID` | AppleScript split pane |
| Emacs vterm | `$INSIDE_EMACS` | `emacsclient` 새 프레임 |

**Sandbox 주의**: ghostty/iTerm2의 `osascript` 사용은 Claude Code sandbox에서 차단됨 → `excludedCommands`에 `*/launch-revdiff.sh*` 추가 필요.

### Launcher 오버라이드 시스템 (2-layer chain)

| Layer | Path | Scope |
|-------|------|-------|
| User | `${CLAUDE_PLUGIN_DATA}/scripts/launch-revdiff.sh` | 사용자 전역 |
| Bundled | `${CLAUDE_SKILL_DIR}/scripts/launch-revdiff.sh` | 플러그인 기본 |

**프로젝트 레이어가 의도적으로 없음** — `revdiff-planning` 훅이 ExitPlanMode마다 자동 실행되는데, repo 제어 가능한 실행 파일을 두면 untrusted repo가 임의 코드 실행 가능. 보안적으로 일관된 결정.

오버라이드 파일은 **executable 비트 필수**, 아니면 fallthrough. `chmod -x`가 빠른 비활성화 방법이라는 디테일까지 문서화.

### Codex / OpenCode / Pi / Zed 통합도 1급 시민
- Codex: `~/.codex/skills/revdiff` 복사
- OpenCode: `cd plugins/opencode && bash setup.sh`
- Pi: `pi install https://github.com/umputun/revdiff` + 6개 슬래시 명령(`/revdiff`, `/revdiff-rerun`, `/revdiff-results`, `/revdiff-apply`, `/revdiff-clear`, `/revdiff-reminders`)
- Zed: `tasks.json` + 키바인딩으로 통합 (clipboard 연계 패턴: `revdiff --output=/tmp/x; pbcopy < /tmp/x`)

---

## 12. 검토 이력 (History) — 안전망 디자인

### 저장 위치
`~/.config/revdiff/history/<repo-name>/<timestamp>.md`

### 저장 규칙
- `q`로 어노테이션이 있는 채로 종료 → 자동 저장 (silent)
- `Q`로 폐기 → 저장 안 함
- 어노테이션 0개 → 저장 안 함
- `--stdin` 모드 → `stdin/` 하위
- `--only` + git 없음 → 부모 디렉토리명을 repo명 대신

### 파일 내용
1. 헤더: 경로, refs, (git만) short commit hash
2. stdout과 동일 포맷의 어노테이션 출력
3. 어노테이션된 파일에 한해 raw git diff (hg/jj는 비어있음)

### 활용 패턴 (Claude 플러그인)
"locate my latest revdiff review" 등의 자연어로 과거 어노테이션 호출 가능. `read-latest-history.sh` 도우미 스크립트가 `$REVDIFF_HISTORY_DIR` 또는 기본 경로에서 가장 최근 `.md` 검색.

**디자인 함의**: 항상 켜져 있지만 silent. stderr 로깅만, 프로세스 실패시키지 않음. 안전망(safety net) 패턴의 정석.

---

## 13. UX 디테일 모음 (자체 도구에 적용할 만한 것들)

### Status Bar Icon Row
오른쪽에 모드 상태 아이콘이 **고정 폭으로 항상 렌더**됨 (활성: status fg / 비활성: muted gray). 토글에 따라 row 너비가 변하지 않음. 좁은 터미널에선 좌측부터 drop.

| Icon | Toggle | 의미 |
|------|--------|------|
| ▼ | v | collapsed |
| ⊂ | C | compact |
| ◉ | f | filter (annotated only) |
| ↩ | w | wrap |
| ≋ | / | search |
| ⊟ | t | tree hidden |
| # | L | line numbers |
| b | B | blame |
| ± | W | word-diff |
| ✓ | Space | reviewed count |
| ∅ | u | untracked |

### Single-File Mode 자동 동작
diff에 파일이 1개일 때 트리 패인 자동 숨김 → 진단 패인이 전체 너비 사용. `Tab/h/l/n/p/f`는 no-op (단, 마크다운 TOC 활성 시 예외).

### Markdown TOC Pane
`.md`/`.markdown` 단일 파일 + context-only 모드 → 헤더 들여쓰기 TOC 자동. 펜스드 코드 블록 안의 헤더는 제외. 스크롤 시 현재 섹션 하이라이트.

### 다중 줄 어노테이션 (`Ctrl+E`)
`$EDITOR` → `$VISUAL` → `vi` 순으로 fallback. `EDITOR="code --wait"`처럼 인자 있는 값도 OK. 빈 파일로 종료 시 어노테이션 취소 + 기존 노트 보존. 출력에는 임베드된 newline으로 emit.

### Discard 확인 프롬프트
`Q`로 폐기 시 어노테이션 있으면 확인. `--no-confirm-discard`로 비활성 가능. `R`(reload)도 어노테이션 있으면 경고.

---

## 14. CLI 옵션 전수 (자체 도구 설계 시 비교 체크용)

### 위치 인자 (3가지 호출 형태)
```
revdiff                         # uncommitted
revdiff REF                     # REF vs working tree
revdiff REF1 REF2               # REF1..REF2 (or REF1...REF2)
```

### 옵션 (카테고리 분류)

**입력 모드:**
- `--staged`, `-A/--all-files`, `--stdin`, `-F/--only`, `--stdin-name`

**필터:**
- `-I/--include` (반복), `-X/--exclude` (반복)

**출력:**
- `-o/--output` (파일), `--history-dir`

**렌더링:**
- `--tree-width`, `--tab-width`, `--no-colors`, `--no-status-bar`, `--wrap`, `--collapsed`, `--compact`, `--compact-context`, `--cross-file-hunks`, `--line-numbers`, `--word-diff`, `--blame`

**상호작용:**
- `--no-confirm-discard`, `--no-mouse`, `--vim-motion`

**테마:**
- `--chroma-style`, `--theme`, `--dump-theme`, `--list-themes`, `--init-themes`, `--init-all-themes`, `--install-theme`

**색상 (23개):**
- `--color-{accent|border|normal|muted|selected-fg/bg|annotation|cursor-fg/bg|add-fg/bg|remove-fg/bg|word-add-bg|word-remove-bg|modify-fg/bg|tree-bg|diff-bg|status-fg/bg|search-fg/bg}`

**키바인딩/설정:**
- `--keys`, `--dump-keys`, `--config`, `--dump-config`

**메타:**
- `-V/--version`

---

## 15. 자체 도구 개발 시 참고할 핵심 디자인 결정

겹치는 부분이 많다고 하셨으니, 차별화 포인트를 잡을 때 **revdiff가 이미 잘 한 것**과 **revdiff가 다루지 않는 것**을 구분하는 게 유용:

### revdiff가 잘 잡은 것 (참고/계승할 가치)
1. **stdout 어노테이션 출력 = 비동기 입력의 동기화** — TUI 종료를 신호로 사용
2. **컨텍스트-온리 모드의 직교성** — diff 도구가 일반 텍스트 어노테이터까지 자연스레 확장
3. **"hunk" 키워드 자동 확장** — 사용자 입력 부담 0, AI 컨텍스트 정확도 ↑
4. **`??` 패턴 분류** — 메타데이터 없이 본문으로 의도 추론
5. **History 자동 백업** — silent + safety net
6. **2-layer launcher 오버라이드 + project layer 부재** — 보안과 확장성의 trade-off 설명
7. **status bar 고정폭 아이콘 row** — 시각적 안정성
8. **CLI > env > config > default 우선순위 + INI dump** — 초보자에게도 친화적
9. **VCS는 선택적 의존성** — only/stdin 모드의 존재
10. **터미널별 자동 감지 + osascript 보안 노트** — 통합 호환성을 끝까지 추적

### revdiff가 다루지 않는 것 (차별화 여지)
- **공동 리뷰**: 어노테이션은 단일 사용자 → 단일 AI 핸드오프. 다중 사용자 협업 X.
- **PR/이슈 트래커 연동**: GitHub/GitLab API로 코멘트 동기화 없음 (어노테이션은 stdout 끝).
- **AI 자동 응답**: 사람이 어노테이션, AI가 처리. AI가 어노테이션을 자동 생성하는 inverse 흐름은 플러그인 책임.
- **세션 재개**: history는 백업이지, "이어 작업하기" UI는 없음.
- **diff 외부 메타데이터**: CI 결과, lint, type 에러를 diff 위에 오버레이 X.
- **음성/리치 미디어 어노테이션**: 텍스트 only.
- **수정 사항 직접 적용**: revdiff는 출력만 하고 코드 수정은 외부 도구(Claude 등)에 위임. 통합되어 있지 않음.

### 통합 친화성을 위한 체크리스트
revdiff가 통합 도구로 자리 잡은 이유들 — 자체 도구 설계 시 검토:

- [ ] **stdout 또는 file output 양쪽 지원** (`-o` 플래그)
- [ ] **stdin/파이프 입력 지원** — 다른 도구와의 조합
- [ ] **종료 코드 명확화** — 정상/폐기/오류 구분
- [ ] **환경 변수 1:1 매핑** — 컨테이너·CI 친화
- [ ] **`--dump-*` 명령** — 설정 introspection
- [ ] **History/audit log** — silent safety net
- [ ] **Plugin/launcher 인터페이스 명세** — 외부 도구가 호출 가능하게
- [ ] **터미널별 동작 보장** — popup/split/floating 우선순위 자동 감지
- [ ] **Sandbox/permission 호환성** — Claude Code 등 환경의 제약 명시
- [ ] **인자 quoting 정확성** — `$@`/`$*` 함정 회피, 헬퍼 함수 제공

---

## 16. 참고 링크

- 공식 사이트: <https://revdiff.com>
- 공식 문서: <https://revdiff.com/docs>
- GitHub: <https://github.com/umputun/revdiff>
- Releases: <https://github.com/umputun/revdiff/releases>
- 테마 가이드: <https://github.com/umputun/revdiff/blob/master/themes/README.md>
- Pi 패키지: <https://github.com/badlogic/pi-mono>
- Codex CLI: <https://github.com/openai/codex>

---

## 부록 A. 모드 상호 배타성 매트릭스

|  | refs | --staged | --all-files | --only | --stdin | --include/--exclude |
|--|------|----------|-------------|--------|---------|---------------------|
| refs | — | OK | ✗ | OK (combine) | ✗ | OK |
| --staged | OK | — | ✗ | OK | ✗ | OK |
| --all-files | ✗ | ✗ | — | ✗ | ✗ | OK (필터) |
| --only | OK | OK | ✗ | — (반복 OK) | ✗ | ✗ |
| --stdin | ✗ | ✗ | ✗ | ✗ | — | ✗ |

## 부록 B. 우선순위 트리

```
설정값 결정:
  CLI 플래그
    ↓ override
  환경변수 (REVDIFF_*)
    ↓ override
  설정파일 (~/.config/revdiff/config)
    ↓ override
  built-in default

테마 적용:
  --theme 사용 시 → 모든 색상 덮어씀 (color flags/env 무시)
  --theme 미사용 시 → built-in < config < env < CLI flag
  --theme + --no-colors → 경고 + 테마 적용
```

## 부록 C. 디렉토리 레이아웃

```
~/.config/revdiff/
├── config                # INI, 주 설정
├── keybindings           # INI, 키 매핑
├── themes/
│   ├── basic
│   ├── catppuccin-{latte,mocha}
│   ├── dracula
│   ├── gruvbox
│   ├── nord
│   ├── revdiff
│   ├── solarized-dark
│   └── gallery/          # 커뮤니티 테마
└── history/
    └── <repo-name>/
        └── <timestamp>.md  # 백업된 어노테이션 + diff
```
