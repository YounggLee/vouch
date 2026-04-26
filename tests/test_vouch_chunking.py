"""
plan §7 R4 (Chunking 임계) 사전 검증.

목적:
- N개의 raw hunk를 단일 분석 호출에 넣을 때 prompt 토큰이 어떻게 증가하는가
- 50 hunk 임계에서 실제로 timeout/오류가 나는가
- 단일 호출의 응답 품질이 유지되는가
- Chunking이 진짜 필요한 임계는 어디인가

전략: 변형된 합성 hunk를 N=10/30/60/100개로 늘려가며 호출하고
prompt/output/thinking 토큰과 latency를 표로 출력.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "gemini-3-flash-preview"
ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)


def load_api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GEMINI_API_KEY not found in .env")


def synth_hunks(n: int) -> list[dict]:
    """n개의 비슷한 모양의 raw hunk를 합성."""
    out = []
    for i in range(n):
        out.append(
            {
                "id": f"r{i}",
                "file": f"module/file_{i:03d}.py",
                "diff": (
                    f"@@ -10,3 +10,3 @@ def handler_{i}(req):\n"
                    f"     log.debug('handler_{i}')\n"
                    f"-    return process(req, mode='legacy')\n"
                    f"+    return process(req, mode='v{(i % 3) + 2}')\n"
                ),
            }
        )
    return out


SYSTEM_INSTRUCTION = """\
너는 코드 리뷰 보조 시니어 엔지니어다. 각 hunk를 다음 기준으로 분류해라.
- risk: high|med|low
- confidence: confident|uncertain|guess
- summary_ko: 한국어 한 줄 (<=60자)
- risk_reason: 한국어 한 줄
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "hunks": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "risk": {"type": "STRING", "enum": ["high", "med", "low"]},
                    "risk_reason": {"type": "STRING"},
                    "confidence": {
                        "type": "STRING",
                        "enum": ["confident", "uncertain", "guess"],
                    },
                    "summary_ko": {"type": "STRING"},
                },
                "required": [
                    "id",
                    "risk",
                    "risk_reason",
                    "confidence",
                    "summary_ko",
                ],
            },
        }
    },
    "required": ["hunks"],
}


def build_prompt(hunks: list[dict]) -> str:
    parts = ["다음 hunk들을 모두 분류해서 schema에 맞춰 JSON으로 답해.\n"]
    for h in hunks:
        parts.append(f"--- id={h['id']} (file={h['file']}) ---\n{h['diff']}")
    return "\n".join(parts)


def call(api_key: str, hunks: list[dict], timeout_s: int = 120) -> dict:
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": build_prompt(hunks)}]}],
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
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "error": f"HTTP {e.code}: {e.read().decode('utf-8')[:200]}",
            "latency_s": round(time.time() - t0, 2),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "latency_s": round(time.time() - t0, 2),
        }
    latency = round(time.time() - t0, 2)
    raw = json.loads(body)
    parsed = json.loads(raw["candidates"][0]["content"]["parts"][0]["text"])
    return {
        "ok": True,
        "latency_s": latency,
        "usage": raw.get("usageMetadata", {}),
        "returned": len(parsed.get("hunks", [])),
    }


def main() -> int:
    api_key = load_api_key()
    sizes = [10, 30, 60, 100]
    print(
        f"{'N':>4}  {'status':>7}  {'lat(s)':>7}  {'prompt':>7}  "
        f"{'out':>5}  {'total':>7}  {'returned':>9}"
    )
    print("-" * 60)
    for n in sizes:
        hunks = synth_hunks(n)
        r = call(api_key, hunks)
        if not r["ok"]:
            print(f"{n:>4}  {'FAIL':>7}  {r['latency_s']:>7}   {r['error'][:80]}")
            continue
        u = r["usage"]
        print(
            f"{n:>4}  {'ok':>7}  {r['latency_s']:>7}  "
            f"{u.get('promptTokenCount', 0):>7}  "
            f"{u.get('candidatesTokenCount', 0):>5}  "
            f"{u.get('totalTokenCount', 0):>7}  "
            f"{r['returned']:>9}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
