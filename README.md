# vouch

> You vouch. AI helps.

cmux-native AI diff reviewer — semantic hunks, risk triage, confidence self-doubt, closed-loop reject.

## What it does

- Reads a diff (uncommitted / commit / range / GitHub PR).
- LLM-groups raw git hunks into **semantic hunks** (one intent = one card).
- LLM-tags each card with **risk** (🔴 high / 🟡 med / 🟢 low), **confidence** (✅ / ⚠️ / ❓), and a 한국어 한 줄 요약.
- TUI queue lets a human accept/reject. Rejects with reasons are bundled into a prompt and **sent to the source agent's cmux surface** to retry.
- Status, progress, and notifications surface in the cmux sidebar.

## Run

```
vouch                        # uncommitted (default)
vouch HEAD~3                 # single commit
vouch main..HEAD             # range
vouch --pr 42                # GitHub PR
vouch hook stop              # called from Claude Code SessionStop hook
```

Key bindings: `j`/`k` move, `a` accept, `A` accept-all-low, `r` reject (modal for reason), `s` send rejects → source surface, `q` quit.

## Demo

```
./scripts/demo.sh
```

Uses pre-recorded LLM responses (`VOUCH_CACHE_ONLY=1`) so the demo is deterministic.

## Roadmap (v2)

- Host abstraction (CmuxHost / PlainHost) — works outside cmux
- Multi-model disagreement flag
- Anomaly detection vs. codebase patterns
- Per-hunk conversation
- Decision memory across sessions
