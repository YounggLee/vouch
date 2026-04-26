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
pip install -e .
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

Verify all 4 input modes (uncommitted / commit / range / pr) against [vouch-fixtures](https://github.com/YounggLee/vouch-fixtures), a companion repo that seeds a baseline app, a feature branch with mixed-risk commits, and an open PR.

```
tests/setup_fixture.sh                       # clones to /tmp/vouch-fixtures
pytest tests/test_integration.py             # lite — diff fetch + raw hunk parse, no LLM
VOUCH_E2E=1 pytest tests/test_integration.py # full — adds semantic + analyze, hits Gemini
```

Lite skips automatically if the fixture isn't cloned, so it's safe to leave in CI.

## Roadmap (v2)

- Multi-model disagreement flag
- Anomaly detection vs. codebase patterns
- Per-hunk conversation
- Decision memory across sessions
