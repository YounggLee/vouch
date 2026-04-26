import re
import subprocess
from dataclasses import dataclass
from typing import List, Literal, Optional


ModeKind = Literal["uncommitted", "commit", "range", "pr"]


@dataclass
class ModeSpec:
    kind: ModeKind
    value: Optional[str] = None


_PR_URL_RE = re.compile(r"https?://github\.com/[^/]+/[^/]+/pull/(\d+)")
_RANGE_RE = re.compile(r"^[^.\s]+\.\.[^.\s]+$")


def resolve_mode(args: List[str]) -> ModeSpec:
    if not args:
        return ModeSpec(kind="uncommitted")
    if args[0] == "--pr" and len(args) >= 2:
        return ModeSpec(kind="pr", value=args[1])
    m = _PR_URL_RE.match(args[0])
    if m:
        return ModeSpec(kind="pr", value=m.group(1))
    if _RANGE_RE.match(args[0]):
        return ModeSpec(kind="range", value=args[0])
    return ModeSpec(kind="commit", value=args[0])


def get_unified_diff(spec: ModeSpec) -> str:
    if spec.kind == "uncommitted":
        return _run(["git", "diff", "HEAD"])
    if spec.kind == "commit":
        return _run(["git", "show", "--format=", spec.value])
    if spec.kind == "range":
        return _run(["git", "diff", spec.value])
    if spec.kind == "pr":
        return _run(["gh", "pr", "diff", spec.value])
    raise ValueError(f"unknown mode {spec.kind}")


def _run(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {result.stderr}")
    return result.stdout
