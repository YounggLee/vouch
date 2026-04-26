import os
import shutil
import subprocess
from typing import Optional


def cmux_available() -> bool:
    if shutil.which("cmux") is None:
        return False
    r = subprocess.run(["cmux", "ping"], capture_output=True, text=True)
    return r.returncode == 0


def require_cmux() -> None:
    if not cmux_available():
        raise SystemExit(
            "vouch v1 requires cmux to be running.\n"
            "  - Install: https://cmux.com\n"
            "  - Plain-terminal mode is on the v2 roadmap."
        )


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


def set_status(key: str, message: str, icon: str = "shield-check") -> None:
    ws = workspace_id()
    args = ["cmux", "set-status", key, message, "--icon", icon]
    if ws:
        args += ["--workspace", ws]
    subprocess.run(args, capture_output=True)


def clear_status(key: str) -> None:
    ws = workspace_id()
    args = ["cmux", "clear-status", key]
    if ws:
        args += ["--workspace", ws]
    subprocess.run(args, capture_output=True)


def set_progress(value: float, label: str = "") -> None:
    ws = workspace_id()
    args = ["cmux", "set-progress", str(value)]
    if label:
        args += ["--label", label]
    if ws:
        args += ["--workspace", ws]
    subprocess.run(args, capture_output=True)


def notify(title: str, body: str = "") -> None:
    args = ["cmux", "notify", "--title", title]
    if body:
        args += ["--body", body]
    subprocess.run(args, capture_output=True)


def send_to_surface(surface: str, text: str) -> None:
    ws = workspace_id()
    cmd1 = ["cmux", "send", "--surface", surface, text]
    cmd2 = ["cmux", "send-key", "--surface", surface, "Enter"]
    if ws:
        cmd1 += ["--workspace", ws]
        cmd2 += ["--workspace", ws]
    subprocess.run(cmd1, capture_output=True, check=True)
    subprocess.run(cmd2, capture_output=True, check=True)
