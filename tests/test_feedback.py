from vouch.feedback import build_reject_prompt
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
