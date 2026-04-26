import json
import os
from typing import List

from google import genai
from google.genai import types as gtypes

from vouch.cache import load as cache_load, save as cache_save
from vouch.models import Analysis, RawHunk, SemanticHunk


_MODEL = os.environ.get("VOUCH_MODEL", "gemini-2.5-flash")
_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")


def _use_cache_only() -> bool:
    return os.environ.get("VOUCH_CACHE_ONLY") == "1"


def _client() -> "genai.Client":
    if _PROJECT:
        return genai.Client(vertexai=True, project=_PROJECT, location=_LOCATION)
    return genai.Client()


_SEMANTIC_PROMPT = """\
You receive a list of raw git hunks from one change. Group hunks that share a single intent into a SemanticHunk; split a single oversized hunk (>20 lines) into multiple SemanticHunks if it covers multiple intents. Output JSON: a list where each item is {"id": "s<n>", "intent": "한국어 한 줄 의도", "raw_hunk_ids": ["r1", ...]}. Each raw_hunk_id must appear in exactly one SemanticHunk. Be conservative; prefer grouping only when intent is clearly shared.
Raw hunks JSON:
"""


_ANALYSIS_PROMPT = """\
You receive a list of SemanticHunks (each with merged diff). For each, output JSON object with fields: id, risk (high|med|low), risk_reason (한 줄), confidence (confident|uncertain|guess), summary_ko (한국어 한 줄). Be conservative on risk: business logic, security, new dependencies → high. Mechanical (rename/import/format) → low.
SemanticHunks JSON:
"""


def semantic_postprocess(raw_hunks: List[RawHunk]) -> List[SemanticHunk]:
    payload_obj = [
        {"id": h.id, "file": h.file, "header": h.header, "body": h.body}
        for h in raw_hunks
    ]
    payload = json.dumps(payload_obj, ensure_ascii=False)
    cached = cache_load("semantic_postprocess", payload)
    if cached is not None:
        return _build_semantic(raw_hunks, cached)
    if _use_cache_only():
        raise RuntimeError("VOUCH_CACHE_ONLY=1 but no cached response")
    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "intent": {"type": "STRING"},
                "raw_hunk_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["id", "intent", "raw_hunk_ids"],
        },
    }
    resp = _client().models.generate_content(
        model=_MODEL,
        contents=_SEMANTIC_PROMPT + payload,
        config=gtypes.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
        ),
    )
    parsed = json.loads(resp.text)
    cache_save("semantic_postprocess", payload, parsed)
    return _build_semantic(raw_hunks, parsed)


def _build_semantic(raw_hunks, parsed) -> List[SemanticHunk]:
    by_id = {h.id: h for h in raw_hunks}
    out = []
    for item in parsed:
        members = [by_id[rid] for rid in item["raw_hunk_ids"] if rid in by_id]
        files = sorted({m.file for m in members})
        merged = "\n\n".join(f"--- {m.file}\n{m.header}\n{m.body}" for m in members)
        out.append(
            SemanticHunk(
                id=item["id"],
                intent=item["intent"],
                files=files,
                raw_hunk_ids=[m.id for m in members],
                merged_diff=merged,
            )
        )
    return out


def analyze(semantic_hunks: List[SemanticHunk]) -> List[Analysis]:
    payload_obj = [
        {"id": s.id, "intent": s.intent, "files": s.files, "diff": s.merged_diff}
        for s in semantic_hunks
    ]
    payload = json.dumps(payload_obj, ensure_ascii=False)
    cached = cache_load("analyze", payload)
    if cached is not None:
        return [Analysis(**item) for item in cached]
    if _use_cache_only():
        raise RuntimeError("VOUCH_CACHE_ONLY=1 but no cached response")
    schema = {
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
        },
    }
    resp = _client().models.generate_content(
        model=_MODEL,
        contents=_ANALYSIS_PROMPT + payload,
        config=gtypes.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
        ),
    )
    parsed = json.loads(resp.text)
    cache_save("analyze", payload, parsed)
    return [Analysis(**item) for item in parsed]
