from vouch.diff_input import resolve_mode, ModeSpec


def test_no_args_means_uncommitted():
    spec = resolve_mode([])
    assert spec.kind == "uncommitted"


def test_single_commit():
    spec = resolve_mode(["abc123"])
    assert spec.kind == "commit"
    assert spec.value == "abc123"


def test_range():
    spec = resolve_mode(["abc..def"])
    assert spec.kind == "range"
    assert spec.value == "abc..def"


def test_pr_flag():
    spec = resolve_mode(["--pr", "42"])
    assert spec.kind == "pr"
    assert spec.value == "42"


def test_pr_url():
    spec = resolve_mode(["https://github.com/x/y/pull/42"])
    assert spec.kind == "pr"
    assert spec.value == "42"
