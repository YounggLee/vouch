"""
plan Task 6의 `semantic_postprocess` 호출을 Gemini 3 Flash로 사전 검증.

검증 포인트:
1. Gemini API가 top-level ARRAY responseSchema를 받아들이는가
2. raw hunk들의 묶기(grouping)가 의도대로 동작하는가
3. raw_hunk_ids 모든 항목이 정확히 한 SemanticHunk에 속하는가
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from unidiff import PatchSet

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIFF = ROOT / "tests" / "fixtures" / "sample.diff"
MODEL = "gemini-3-flash-preview"
ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)


def load_api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GEMINI_API_KEY not found in .env")


def parse_hunks(diff_text: str) -> list[dict]:
    patch = PatchSet(diff_text)
    out: list[dict] = []
    for pf in patch:
        for h in pf:
            header = (
                f"@@ -{h.source_start},{h.source_length} "
                f"+{h.target_start},{h.target_length} @@"
            )
            body = "".join(str(line) for line in h)
            out.append(
                {
                    "id": f"r{len(out)}",
                    "file": pf.path,
                    "header": header,
                    "body": body,
                }
            )
    return out


SEMANTIC_PROMPT = """\
너는 git diff의 raw hunk들을 받아 SemanticHunk로 후처리하는 코드 리뷰 보조다.

규칙:
- 같은 변경 의도를 공유하는 hunk들은 하나의 SemanticHunk로 grouping해라
  (예: 함수 시그니처 변경 + 그 함수의 caller 업데이트 + 관련 테스트 수정)
- 한 raw_hunk_id는 정확히 하나의 SemanticHunk에만 속해야 한다
- 큰 hunk(>20 line)가 명백히 두 의도를 담고 있으면 splitting을 제안
  (현재 입력에선 raw 단위 분할은 불가하므로 intent에 메모만 남겨라)
- 의도가 불분명하면 보수적으로 단독 SemanticHunk로 둔다

출력 schema 그대로 JSON만:
- id: "s0", "s1", ...
- intent: 한국어 한 줄 (최대 60자)
- raw_hunk_ids: 이 SemanticHunk에 속하는 raw hunk id 목록

입력 raw hunks JSON:
"""

# Gemini는 top-level ARRAY를 직접 schema로 허용하지 않는 경우가 있어 OBJECT wrapping
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "semantic_hunks": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "intent": {"type": "STRING"},
                    "raw_hunk_ids": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                },
                "required": ["id", "intent", "raw_hunk_ids"],
                "propertyOrdering": ["id", "intent", "raw_hunk_ids"],
            },
        }
    },
    "required": ["semantic_hunks"],
}


def call_gemini(api_key: str, raw_hunks: list[dict]) -> dict:
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": SEMANTIC_PROMPT
                        + json.dumps(raw_hunks, ensure_ascii=False, indent=2)
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    req = urllib.request.Request(
        f"{ENDPOINT}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}:\n{e.read().decode('utf-8')}", file=sys.stderr)
        raise
    latency = time.time() - t0

    raw = json.loads(body)
    text = raw["candidates"][0]["content"]["parts"][0]["text"]
    return {
        "latency_s": round(latency, 2),
        "usage": raw.get("usageMetadata", {}),
        "model_version": raw.get("modelVersion"),
        "parsed": json.loads(text),
    }


def verify_partition(raw_ids: list[str], result: dict) -> list[str]:
    """raw_hunk_ids가 정확히 한 번씩만 등장하는지 검증."""
    issues = []
    seen: dict[str, str] = {}
    for sh in result["semantic_hunks"]:
        for rid in sh["raw_hunk_ids"]:
            if rid in seen:
                issues.append(f"  ❌ {rid} appears in both {seen[rid]} and {sh['id']}")
            seen[rid] = sh["id"]
    missing = [rid for rid in raw_ids if rid not in seen]
    extra = [rid for rid in seen if rid not in raw_ids]
    if missing:
        issues.append(f"  ❌ raw ids missing from any group: {missing}")
    if extra:
        issues.append(f"  ❌ unknown ids appearing in groups: {extra}")
    return issues


def main() -> int:
    api_key = load_api_key()
    diff_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIFF
    diff = diff_path.read_text()
    raw = parse_hunks(diff)
    print(f"input: {len(raw)} raw hunk(s) from {diff_path.name}")
    for h in raw:
        print(f"  {h['id']}  {h['file']}")

    result = call_gemini(api_key, raw)
    print(f"\nmodel: {result['model_version']}  ({result['latency_s']}s)")
    u = result["usage"]
    print(
        f"tokens: prompt={u.get('promptTokenCount')} "
        f"output={u.get('candidatesTokenCount')} "
        f"thinking={u.get('thoughtsTokenCount', 0)} "
        f"total={u.get('totalTokenCount')}"
    )

    print("\nresult:")
    for sh in result["parsed"]["semantic_hunks"]:
        rids = ", ".join(sh["raw_hunk_ids"])
        print(f"  [{sh['id']}]  {sh['intent']}")
        print(f"     ↳ groups: {rids}")

    issues = verify_partition([h["id"] for h in raw], result["parsed"])
    print("\npartition check:")
    if issues:
        for i in issues:
            print(i)
        return 1
    print("  ✅ each raw hunk assigned exactly once")

    print(
        f"\ncompression: {len(raw)} raw → "
        f"{len(result['parsed']['semantic_hunks'])} semantic"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
