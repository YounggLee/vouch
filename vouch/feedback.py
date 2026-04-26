from typing import List

from vouch.models import ReviewItem


def build_reject_prompt(rejected: List[ReviewItem]) -> str:
    """Agent-retry framing. Sent to source surface for the agent to re-attempt."""
    if not rejected:
        return ""
    lines = [
        "[vouch] 다음 변경들이 사람의 리뷰에서 거절됐어. 사유를 반영해 다시 시도해줘:",
        "",
    ]
    for it in rejected:
        files = ", ".join(it.semantic.files)
        lines.append(f"- ({files}) {it.semantic.intent}")
        lines.append(f"    사유: {it.reject_reason or '(no reason)'}")
    lines.append("")
    lines.append("거절된 항목 외에는 그대로 유지하고, 위 사유를 직접 해소하는 변경만 적용해줘.")
    return "\n".join(lines)


def build_pr_review_body(rejected: List[ReviewItem]) -> str:
    """PR review body. Reasons only — no agent-retry framing."""
    if not rejected:
        return ""
    sections = []
    for it in rejected:
        files = ", ".join(f"`{f}`" for f in it.semantic.files)
        reason = it.reject_reason or "(no reason)"
        sections.append(f"### {files}\n{reason}")
    return "\n\n".join(sections)
