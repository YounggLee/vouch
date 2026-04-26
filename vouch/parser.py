from typing import List

from unidiff import PatchSet

from vouch.models import RawHunk


def parse_raw_hunks(unified_diff: str) -> List[RawHunk]:
    if not unified_diff.strip():
        return []
    patch = PatchSet(unified_diff)
    out: List[RawHunk] = []
    for pf in patch:
        path = pf.path
        for h in pf:
            body_lines = []
            for line in h:
                body_lines.append(line.line_type + line.value.rstrip("\n"))
            body = "\n".join(body_lines)
            header = f"@@ -{h.source_start},{h.source_length} +{h.target_start},{h.target_length} @@"
            out.append(
                RawHunk(
                    id=f"r{len(out)}",
                    file=path,
                    old_start=h.source_start,
                    old_lines=h.source_length,
                    new_start=h.target_start,
                    new_lines=h.target_length,
                    header=header,
                    body=body,
                )
            )
    return out
