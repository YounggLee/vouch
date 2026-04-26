from vouch.feedback import build_pr_review_body, build_reject_prompt
from vouch.models import Analysis, ReviewItem, SemanticHunk


def _item(sid, intent, files, reason):
    s = SemanticHunk(id=sid, intent=intent, files=files, raw_hunk_ids=[], merged_diff="")
    a = Analysis(id=sid, risk="high", risk_reason="", confidence="confident", summary_ko=intent)
    return ReviewItem(semantic=s, analysis=a, decision="reject", reject_reason=reason)


def test_build_reject_prompt_lists_items():
    rejects = [
        _item("s1", "intent A", ["a.py"], "use parameterized SQL"),
        _item("s2", "intent B", ["b.py", "c.py"], "missing null check"),
    ]
    out = build_reject_prompt(rejects)
    assert "다시 시도" in out
    assert "intent A" in out
    assert "use parameterized SQL" in out
    assert "intent B" in out
    assert "a.py" in out


def test_build_reject_prompt_empty():
    assert build_reject_prompt([]) == ""


def test_pr_review_body_strips_agent_framing():
    rejects = [
        _item("s1", "intent A", ["a.py"], "use parameterized SQL"),
        _item("s2", "intent B", ["b.py", "c.py"], "missing null check"),
    ]
    out = build_pr_review_body(rejects)
    # framing must be absent
    assert "[vouch]" not in out
    assert "다시 시도" not in out
    assert "거절된 항목 외에는" not in out
    # intent context optional but we keep it minimal — only files + reason
    assert "intent A" not in out  # intent is dropped per "사유만"
    # reasons + file paths must be present
    assert "use parameterized SQL" in out
    assert "missing null check" in out
    assert "`a.py`" in out
    assert "`b.py`" in out
    assert "`c.py`" in out


def test_pr_review_body_empty():
    assert build_pr_review_body([]) == ""
