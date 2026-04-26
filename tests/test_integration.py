"""
Integration tests against the YounggLee/vouch-fixtures repo.

Two layers:
- lite (default): exercise diff input + raw hunk parsing for all 4 modes. No LLM.
- e2e (VOUCH_E2E=1): also run semantic_postprocess + analyze, asserting the
  expected risk distribution. First run hits live Gemini, subsequent runs cache.

Skips automatically if fixture is not cloned. Run `tests/setup_fixture.sh` first.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


# Isolate cache from the demo cache. Set BEFORE any vouch import.
os.environ.setdefault("VOUCH_CACHE_DIR", "/tmp/vouch-fixtures-cache")

FIXTURE = Path(os.environ.get("VOUCH_FIXTURE", "/tmp/vouch-fixtures"))
E2E = os.environ.get("VOUCH_E2E") == "1"

if not FIXTURE.exists():
    pytest.skip(
        f"fixture not cloned at {FIXTURE} — run tests/setup_fixture.sh",
        allow_module_level=True,
    )


def _git(*args, cwd=FIXTURE):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def clean_main():
    """Reset fixture to clean main before each test, restore after."""
    _git("checkout", "main")
    _git("reset", "--hard", "origin/main")
    _git("clean", "-fd")
    yield FIXTURE
    _git("checkout", "main")
    _git("reset", "--hard", "origin/main")
    _git("clean", "-fd")


def _pipeline(args, cwd):
    """Run vouch pipeline up to (not including) TUI."""
    from vouch.diff_input import get_unified_diff, resolve_mode
    from vouch.parser import parse_raw_hunks

    old = os.getcwd()
    os.chdir(cwd)
    try:
        spec = resolve_mode(args)
        diff = get_unified_diff(spec)
        raw = parse_raw_hunks(diff)
        if not E2E:
            return {"raw": len(raw), "sem": None, "high": None}
        from vouch.llm import analyze, semantic_postprocess

        sem = semantic_postprocess(raw)
        ana = analyze(sem)
        return {
            "raw": len(raw),
            "sem": len(sem),
            "high": sum(1 for a in ana if a.risk == "high"),
        }
    finally:
        os.chdir(old)


def test_uncommitted_mode(clean_main):
    _git("apply", "pending.diff")
    result = _pipeline([], clean_main)
    # pending.diff touches 3 files (cli.py, store.py + new debug.py)
    assert result["raw"] >= 3, result
    if E2E:
        assert result["sem"] >= 1
        # eval() and pickle.loads are unambiguously high-risk
        assert result["high"] >= 1


def test_commit_mode(clean_main):
    _git("checkout", "feature/auth")
    result = _pipeline(["HEAD"], clean_main)
    # last commit is the rename (LOW): should produce hunks but few
    assert result["raw"] >= 1, result


def test_range_mode(clean_main):
    result = _pipeline(["main..feature/auth"], clean_main)
    # feature/auth has 3 commits across 3 files
    assert result["raw"] >= 3, result
    if E2E:
        assert result["sem"] >= 1
        # SQL injection in auth.py is high
        assert result["high"] >= 1


def test_pr_mode(clean_main):
    result = _pipeline(["--pr", "1"], clean_main)
    assert result["raw"] >= 3, result
    if E2E:
        assert result["sem"] >= 1
        assert result["high"] >= 1
