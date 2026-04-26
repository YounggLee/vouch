import subprocess

from vouch import cmux


class _FakeCompleted:
    def __init__(self, rc: int = 0) -> None:
        self.returncode = rc
        self.stdout = b""
        self.stderr = b""


def test_deliver_reject_prefers_gh_when_pr_number_given(monkeypatch):
    calls = []

    def fake_which(name):
        return f"/usr/bin/{name}" if name == "gh" else None

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompleted(0)

    monkeypatch.setattr(cmux.shutil, "which", fake_which)
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    channel = cmux.deliver_reject("hello", surface="surface:1", pr_number="42")

    assert channel == "gh"
    assert calls and calls[0][:4] == ["gh", "pr", "comment", "42"]


def test_deliver_reject_falls_through_when_gh_missing(monkeypatch, capsys):
    def fake_which(name):
        return None  # no gh, no clipboard, no cmux

    monkeypatch.setattr(cmux.shutil, "which", fake_which)
    monkeypatch.setattr(
        cmux.subprocess,
        "run",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    channel = cmux.deliver_reject("body", surface=None, pr_number="42")

    assert channel == "stdout"
    assert "body" in capsys.readouterr().out


def test_deliver_reject_no_pr_number_skips_gh(monkeypatch):
    calls = []

    def fake_which(name):
        return f"/usr/bin/{name}" if name == "gh" else None

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompleted(0)

    monkeypatch.setattr(cmux.shutil, "which", fake_which)
    monkeypatch.setattr(cmux.subprocess, "run", fake_run)

    channel = cmux.deliver_reject("text", surface=None, pr_number=None)

    assert channel == "stdout"
    assert calls == []
