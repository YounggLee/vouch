from vouch.models import RawHunk, SemanticHunk, Analysis, ReviewItem


def test_raw_hunk_construction():
    h = RawHunk(
        id="r1",
        file="auth.py",
        old_start=10,
        old_lines=5,
        new_start=10,
        new_lines=7,
        header="@@ -10,5 +10,7 @@",
        body="-old\n+new\n",
    )
    assert h.id == "r1"
    assert h.file == "auth.py"


def test_semantic_hunk_groups_raw():
    s = SemanticHunk(
        id="s1",
        intent="Add ctx parameter to check_access",
        files=["auth.py", "views.py"],
        raw_hunk_ids=["r1", "r2", "r3"],
        merged_diff="...",
    )
    assert len(s.raw_hunk_ids) == 3


def test_review_item_combines_semantic_and_analysis():
    s = SemanticHunk(
        id="s1", intent="x", files=["a.py"], raw_hunk_ids=["r1"], merged_diff="d"
    )
    a = Analysis(
        id="s1",
        risk="high",
        risk_reason="touches auth",
        confidence="uncertain",
        summary_ko="권한 확장",
    )
    item = ReviewItem(semantic=s, analysis=a, decision=None, reject_reason=None)
    assert item.decision is None
    assert item.semantic.id == item.analysis.id
