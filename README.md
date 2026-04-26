# vouch

> You vouch. AI helps.

**Closed-loop AI diff reviewer for the agentic-coding era.**

- **For**: senior engineers whose review queue is bottlenecked by AI-agent PRs.
- **Does**: groups raw git hunks into *intent units*, tags each with risk/confidence, lets you accept or reject in a TUI — and **rejects flow back to the agent as a structured retry prompt**.
- **Different**: not a one-way reviewer. The reject loop closes automatically (cmux surface) or via clipboard (anywhere else).

![demo](docs/demo.gif)

## Architecture

```
        ┌──────────────────────────────────────────────────────────┐
        │  git diff (35 raw hunks)                                 │
        └────────────────────────┬─────────────────────────────────┘
                                 │ LLM semantic grouping
                                 ▼
                       ┌─────────────────┐
                       │ 5 intent units  │   risk · confidence · 한 줄 요약
                       └────────┬────────┘
                                │
                                ▼
                  ┌────────────────────────┐
                  │  TUI review queue      │   j/k · a/A · r (reason) · s · q
                  └────────┬───────────────┘
                           │ rejects bundled
                           ▼
              ┌──────────────────────────────┐
              │ delivery (best available)    │
              │  1. gh pr comment  (--pr)    │
              │  2. cmux surface   (auto)    │
              │  3. pbcopy / wl-copy / xclip │
              │  4. stdout                   │
              └──────────────┬───────────────┘
                             ▼
                       source agent / PR
```

## Install & run

### 5-second start (any terminal)

```
pip install git+https://github.com/YounggLee/vouch.git
vouch                    # review uncommitted changes
```

If `cmux` is not on PATH, sidebar/notify silently no-op and reject prompts fall through clipboard → stdout.

### Full experience (inside cmux)

```
vouch                                # uncommitted (default)
vouch HEAD~3                         # single commit
vouch main..HEAD                     # range
vouch --pr 42                        # GitHub PR
vouch --source-surface surface:5     # explicit reject target
vouch help                           # full guide (modes, keys, env, troubleshooting)
```

When run inside cmux, vouch publishes status/progress to the sidebar and pushes rejects directly to the source agent's surface.

Key bindings: `j`/`k` move, `a` accept, `A` accept-all-low, `r` reject (modal for reason), `s` send rejects → source, `q` quit.

## Environment

| Variable | Effect |
|---|---|
| `GEMINI_API_KEY` | Gemini API key. Falls back to repo `.env`. |
| `VOUCH_CACHE_DIR` | Response cache directory (default: `fixtures/responses`). |
| `VOUCH_CACHE_ONLY=1` | Use cache only — never call Gemini. Errors if cache misses. |
| `VOUCH_SOURCE_SURFACE` | Default reject-target surface. Falls back to `CMUX_SURFACE_ID`. |
| `VOUCH_MODEL` | Gemini model id (default: `gemini-3-flash-preview`). |

## Demo

```
./scripts/demo.sh
```

Uses pre-recorded LLM responses (`VOUCH_CACHE_ONLY=1`) so the demo is deterministic. Re-record the GIF with:

```
vhs scripts/demo.tape    # writes docs/demo.gif
```

## Integration tests

Verify all 4 input modes (uncommitted / commit / range / pr) against [YounggLee/vouch-fixtures](https://github.com/YounggLee/vouch-fixtures) — a companion repo that seeds a baseline app, a feature branch with mixed-risk commits, and an open PR.

| Layer | What it covers | LLM | Time |
|---|---|---|---|
| **lite** | `git diff` / `git show` / `gh pr diff` per mode → unidiff parsing | ❌ | ~1s |
| **e2e** | lite + `semantic_postprocess` + `analyze` → assert risk distribution | ✅ first run, cached after | ~30s cold, ~1s warm |

### Automated (pytest)

```bash
tests/setup_fixture.sh                          # clones to /tmp/vouch-fixtures, applies pending.diff
pytest tests/test_integration.py                # lite (CI-safe, skips if fixture missing)
VOUCH_E2E=1 pytest tests/test_integration.py    # e2e (needs GEMINI_API_KEY)
```

### Manual (TUI on each mode)

Try each mode interactively against the fixture:

```bash
# 1. From the vouch repo: set up fixture + load env + activate venv
./tests/setup_fixture.sh
set -a; . .env; set +a
source .venv/bin/activate          # so `vouch` is on PATH

# 2. cd into fixture
cd /tmp/vouch-fixtures

# 3. Try each mode
vouch                              # uncommitted (pending.diff applied to working tree)

git checkout feature/auth          # switch branch first
vouch HEAD                         # commit mode — last commit only
vouch HEAD~2..HEAD                 # range mode — last 2 commits

git checkout main                  # back to main
vouch main..feature/auth           # range mode — full feature branch
vouch --pr 1                       # pr mode — fixture PR #1
```

If you'd rather not activate the venv, call the binary directly:
`/Users/<you>/.../hackathon/.venv/bin/vouch ...`

Press `q` to exit the TUI. Each mode produces a different review queue — useful for sanity-checking the pipeline end-to-end without poking the demo fixture.

**Reset fixture between manual runs** (uncommitted mode dirties the tree):

```bash
cd /tmp/vouch-fixtures && git checkout main && git reset --hard origin/main && git clean -fd
```

Or just re-run `tests/setup_fixture.sh` (idempotent).

## Roadmap (v2)

- Multi-model disagreement flag
- Anomaly detection vs. codebase patterns
- Per-hunk conversation
- Decision memory across sessions
