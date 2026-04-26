from pathlib import Path
from vouch.parser import parse_raw_hunks

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_sample_diff():
    diff = (FIXTURES / "sample.diff").read_text()
    hunks = parse_raw_hunks(diff)
    assert len(hunks) == 2
    assert hunks[0].file == "auth.py"
    assert hunks[1].file == "views.py"
    assert hunks[0].id == "r0"
    assert hunks[1].id == "r1"
    assert "admin" in hunks[0].body or "admin" in hunks[0].header


def test_empty_diff():
    assert parse_raw_hunks("") == []
