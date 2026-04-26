"""
vouch F1+F2+F4 분석 호출 PoC.

목적: Gemini 3 Flash가 structured output(JSON schema)로
risk / confidence / summary_ko 를 안정적으로 채우는지 검증.

이번 PoC에서는 단순화를 위해 raw git hunk를 그대로 LLM에 넘긴다.
실제 vouch에서는 semantic 후처리를 거친 hunk가 들어가지만,
분석 호출 자체의 동작 검증이라는 목적에는 무관.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from unidiff import PatchSet  # pip install unidiff

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIFF = ROOT / "tests" / "fixtures" / "sample.diff"
MODEL = "gemini-3-flash-preview"
ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)


def load_api_key() -> str:
    env = ROOT / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GEMINI_API_KEY not found in .env")


def parse_hunks(diff_text: str) -> list[dict]:
    patch = PatchSet(diff_text)
    out: list[dict] = []
    for pf in patch:
        for i, hunk in enumerate(pf):
            out.append(
                {
                    "id": f"{pf.path}#{i}",
                    "file": pf.path,
                    "diff": str(hunk),
                }
            )
    return out


SYSTEM_INSTRUCTION = """\
너는 코드 리뷰 보조 시니어 엔지니어다. 결정은 사람이 한다.
너의 역할은 각 hunk를 분류·압축·자기 불확실성 자백하는 것이다.

분류 기준:
- risk:
  - high: 비즈니스 로직 변경, 보안, 새 의존성, 비-기계적 변경
  - med:  public API 시그니처, 상태 변이, 검증 로직
  - low:  rename, import 정리, 포매팅, 주석
  False negative를 줄이기 위해 의심스러우면 한 단계 위.

- confidence:
  - confident: 의도 명확, 패턴 일치
  - uncertain: 컨벤션 추정, 영향 범위 모호
  - guess:     의도 불분명, 한 가지 해석으로 진행

summary_ko: 한국어 한 줄(최대 60자), '왜 바뀌었는지'를 담을 것.
risk_reason: 한국어 한 줄, 분류 근거.
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
                "required": ["id", "risk", "risk_reason", "confidence", "summary_ko"],
                "propertyOrdering": [
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


def build_user_prompt(hunks: list[dict]) -> str:
    parts = ["다음 hunk들을 각각 분류해줘. 응답은 schema대로 JSON만.\n"]
    for h in hunks:
        parts.append(f"--- id={h['id']} (file={h['file']}) ---\n{h['diff']}")
    return "\n".join(parts)


def call_gemini(api_key: str, hunks: list[dict]) -> dict:
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": build_user_prompt(hunks)}]}],
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
        err_body = e.read().decode("utf-8")
        print(f"HTTP {e.code} body:\n{err_body}", file=sys.stderr)
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


RISK_ICON = {"high": "🔴", "med": "🟡", "low": "🟢"}
CONF_ICON = {"confident": "✅", "uncertain": "⚠️", "guess": "❓"}


def render(result: dict) -> None:
    print(f"\nmodel: {result['model_version']}  ({result['latency_s']}s)")
    u = result["usage"]
    print(
        f"tokens: prompt={u.get('promptTokenCount')} "
        f"output={u.get('candidatesTokenCount')} "
        f"thinking={u.get('thoughtsTokenCount', 0)} "
        f"total={u.get('totalTokenCount')}"
    )
    print()
    for h in result["parsed"]["hunks"]:
        risk = RISK_ICON.get(h["risk"], "?")
        conf = CONF_ICON.get(h["confidence"], "?")
        print(f"{risk} {conf}  [{h['id']}]  {h['summary_ko']}")
        print(f"     ↳ {h['risk_reason']}")


def main() -> int:
    api_key = load_api_key()
    diff_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIFF
    diff = diff_path.read_text()
    hunks = parse_hunks(diff)
    print(f"parsed {len(hunks)} raw hunk(s) from {diff_path.name}")

    result = call_gemini(api_key, hunks)
    render(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
