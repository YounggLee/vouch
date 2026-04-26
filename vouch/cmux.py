import os
import shutil
import subprocess
import sys
from typing import Optional


def cmux_available() -> bool:
    if shutil.which("cmux") is None:
        return False
    try:
        r = subprocess.run(["cmux", "ping"], capture_output=True, text=True, timeout=2)
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def discover_source_surface(cli_flag: Optional[str]) -> Optional[str]:
    if cli_flag:
        return cli_flag
    v = os.environ.get("VOUCH_SOURCE_SURFACE")
    if v:
        return v
    v = os.environ.get("CMUX_SURFACE_ID")
    if v:
        return v
    return None


def workspace_id() -> Optional[str]:
    return os.environ.get("CMUX_WORKSPACE_ID")


def _run(args) -> bool:
    if shutil.which("cmux") is None:
        return False
    try:
        r = subprocess.run(args, capture_output=True)
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def set_status(key: str, message: str, icon: str = "shield-check") -> None:
    ws = workspace_id()
    args = ["cmux", "set-status", key, message, "--icon", icon]
    if ws:
        args += ["--workspace", ws]
    _run(args)


def clear_status(key: str) -> None:
    ws = workspace_id()
    args = ["cmux", "clear-status", key]
    if ws:
        args += ["--workspace", ws]
    _run(args)


def set_progress(value: float, label: str = "") -> None:
    ws = workspace_id()
    args = ["cmux", "set-progress", str(value)]
    if label:
        args += ["--label", label]
    if ws:
        args += ["--workspace", ws]
    _run(args)


def notify(title: str, body: str = "") -> None:
    args = ["cmux", "notify", "--title", title]
    if body:
        args += ["--body", body]
    _run(args)


def send_to_surface(surface: str, text: str) -> bool:
    if shutil.which("cmux") is None:
        return False
    ws = workspace_id()
    cmd1 = ["cmux", "send", "--surface", surface, text]
    cmd2 = ["cmux", "send-key", "--surface", surface, "Enter"]
    if ws:
        cmd1 += ["--workspace", ws]
        cmd2 += ["--workspace", ws]
    try:
        r1 = subprocess.run(cmd1, capture_output=True)
        r2 = subprocess.run(cmd2, capture_output=True)
        return r1.returncode == 0 and r2.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def post_pr_comment(pr: str, text: str) -> bool:
    if shutil.which("gh") is None:
        return False
    try:
        r = subprocess.run(
            ["gh", "pr", "comment", pr, "-F", "-"],
            input=text.encode("utf-8"),
            capture_output=True,
        )
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _try_clipboard(text: str) -> Optional[str]:
    candidates = [
        ("pbcopy", []),
        ("wl-copy", []),
        ("xclip", ["-selection", "clipboard"]),
        ("xsel", ["--clipboard", "--input"]),
    ]
    for cmd, extra in candidates:
        if shutil.which(cmd) is None:
            continue
        try:
            r = subprocess.run([cmd, *extra], input=text.encode("utf-8"), capture_output=True)
            if r.returncode == 0:
                return cmd
        except (subprocess.SubprocessError, OSError):
            continue
    return None


def deliver_reject(text: str, surface: Optional[str], pr_number: Optional[str] = None) -> str:
    """Deliver reject prompt via best available channel.

    Priority: gh PR comment (if pr_number) → cmux surface → clipboard → stdout.
    Returns the channel name: "gh", "cmux", "<clipboard-cmd>", or "stdout".
    """
    if pr_number and post_pr_comment(pr_number, text):
        sys.stderr.write(f"vouch: posted reject as PR #{pr_number} comment\n")
        return "gh"
    if surface and send_to_surface(surface, text):
        return "cmux"
    cb = _try_clipboard(text)
    if cb:
        sys.stderr.write(f"vouch: reject prompt copied to clipboard via {cb} — paste it into your agent\n")
        return cb
    print("\n--- vouch reject prompt ---")
    print(text)
    return "stdout"
