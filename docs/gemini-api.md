# Gemini 3 Flash API 사용 가이드

본 프로젝트에서 사용하는 LLM은 **Gemini 3 Flash Preview** (`gemini-3-flash-preview`) 입니다.

## 1. 기본 정보

| 항목 | 값 |
|---|---|
| 모델 ID | `gemini-3-flash-preview` |
| 빌드 버전 | `3-flash-preview-12-2025` |
| 입력 토큰 한도 | 1,048,576 (1M) |
| 출력 토큰 한도 | 65,536 |
| 입력 모달리티 | 텍스트 / 이미지 / 비디오 / 오디오 |
| Thinking | 지원 (기본 ON) |
| 지원 메서드 | `generateContent`, `countTokens`, `createCachedContent`, `batchGenerateContent` |
| 상태 | Preview (GA 전 변경 가능) |

### 가격 (USD / 1M 토큰)
- 입력: $0.50 (텍스트/이미지/비디오), $1.00 (오디오)
- 출력: $3.00
- 캐시 입력: $0.05 (텍스트/이미지/비디오), $0.10 (오디오)
- 배치 입력/출력: $0.25 / $1.50

## 2. 환경 설정

API 키는 프로젝트 루트의 `.env`에 보관합니다.

```bash
# .env
GEMINI_API_KEY=AIza...
```

키 발급: https://aistudio.google.com/apikey

`.env`는 절대 Git에 커밋하지 마십시오.

> ⚠️ **키 노출 시 자동 폐기**: Google은 공개된 곳(GitHub, 로그, 캐시, 채팅 기록 등)에서 발견된 키를 자동으로 비활성화합니다 (`API key was reported as leaked`). 키를 셸 출력·로그·LLM 응답에 그대로 echo하지 말 것. `source .env`로 환경변수에 로드한 뒤 변수만 참조하세요.

## 3. 엔드포인트

```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=${GEMINI_API_KEY}
```

## 4. 빠른 호출 예시 (curl)

```bash
source .env

curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [
      {"parts": [{"text": "안녕! 한 문장으로 자기소개 해줘."}]}
    ]
  }'
```

### Thinking 끄기 (지연시간/비용 절감)

기본적으로 Gemini 3 Flash는 thinking이 켜져 있어 응답 전에 추가 토큰을 소비합니다. 단순 분류/추출/요약 등 추론이 불필요한 작업에서는 끄세요.

```json
{
  "contents": [{"parts": [{"text": "..."}]}],
  "generationConfig": {
    "thinkingConfig": {"thinkingBudget": 0}
  }
}
```

### 시스템 지시문 + 생성 옵션

```json
{
  "systemInstruction": {
    "parts": [{"text": "너는 한국어로만 답하는 친절한 비서다."}]
  },
  "contents": [
    {"role": "user", "parts": [{"text": "프로젝트 README를 한 줄로 요약해줘."}]}
  ],
  "generationConfig": {
    "temperature": 0.2,
    "topP": 0.95,
    "maxOutputTokens": 1024,
    "responseMimeType": "application/json"
  }
}
```

## 5. Python (공식 SDK) 예시

```bash
pip install google-genai python-dotenv
```

```python
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

resp = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="한 문장으로 자기소개 해줘.",
    config=types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_budget=0),  # 필요 시
    ),
)
print(resp.text)
```

## 6. Node.js (공식 SDK) 예시

```bash
npm install @google/genai dotenv
```

```js
import "dotenv/config";
import { GoogleGenAI } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const resp = await ai.models.generateContent({
  model: "gemini-3-flash-preview",
  contents: "한 문장으로 자기소개 해줘.",
  config: {
    temperature: 0.2,
    thinkingConfig: { thinkingBudget: 0 },
  },
});

console.log(resp.text);
```

## 7. 응답 구조 (요약)

```jsonc
{
  "candidates": [
    {
      "content": { "parts": [{"text": "..."}], "role": "model" },
      "finishReason": "STOP"
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 13,
    "candidatesTokenCount": 29,
    "thoughtsTokenCount": 987,   // thinking ON일 때만
    "totalTokenCount": 1029
  },
  "modelVersion": "gemini-3-flash-preview"
}
```

비용 정산 시 `thoughtsTokenCount`도 출력 토큰처럼 과금됨에 주의하세요.

## 8. Structured Output (JSON Schema) — vouch에서 검증된 패턴

vouch의 F1+F2+F4 분석 호출처럼 **N개 항목을 한 번에 분류**해야 할 때 사용하는 패턴. 2026-04-26 PoC에서 동작 확인 (`tests/test_vouch_analysis.py`).

### 핵심 규칙

- `responseMimeType: "application/json"` + `responseSchema` 동시 지정 → 모델이 schema에 강제 부합하는 JSON만 생성
- schema의 `type`은 **대문자**: `OBJECT`, `ARRAY`, `STRING`, `NUMBER`, `BOOLEAN` (소문자 `object`/`string`은 거부됨)
- enum 필드도 그대로 강제됨 — vouch에서 `risk: high|med|low`, `confidence: confident|uncertain|guess` 모두 정확히 따랐음
- `propertyOrdering`로 필드 순서 고정 가능 (출력 안정성 ↑)
- 분류·추출형 작업은 `thinkingBudget: 0`으로 thinking 끄기 — vouch 4 hunk 분석 기준 **3.1초 / 860 tokens** (thinking on 대비 비용·지연 절반 이하)

### 예시 (vouch 분석 호출 발췌)

```python
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "hunks": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id":          {"type": "STRING"},
                    "risk":        {"type": "STRING", "enum": ["high", "med", "low"]},
                    "risk_reason": {"type": "STRING"},
                    "confidence":  {"type": "STRING",
                                    "enum": ["confident", "uncertain", "guess"]},
                    "summary_ko":  {"type": "STRING"},
                },
                "required": ["id", "risk", "risk_reason", "confidence", "summary_ko"],
                "propertyOrdering": ["id", "risk", "risk_reason", "confidence", "summary_ko"],
            },
        }
    },
    "required": ["hunks"],
}

payload = {
    "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
    "contents": [{"parts": [{"text": user_prompt}]}],
    "generationConfig": {
        "temperature": 0.1,                 # 분류는 낮게
        "responseMimeType": "application/json",
        "responseSchema": RESPONSE_SCHEMA,
        "thinkingConfig": {"thinkingBudget": 0},
    },
}
```

응답의 `candidates[0].content.parts[0].text`는 **이미 schema에 맞는 JSON 문자열** — `json.loads()`로 바로 파싱 가능.

### 시스템 지시문 작성 팁 (PoC에서 효과 확인)

- 모델의 역할을 한 문장으로: 예) "코드 리뷰 보조 시니어 엔지니어. 결정은 사람이 한다."
- 각 enum 값의 분류 기준을 글머리표로 명시
- **False negative를 싫어하면 "의심스러우면 한 단계 위" 같은 보수적 가이드를 넣을 것** — vouch 분석에서 SQL 변경의 인젝션 취약점을 정확히 잡아낸 것이 이 가이드 덕분

## 9. 운영 팁

- **Preview 모델**이므로 가격·동작이 변경될 수 있음. 코드에서 모델 ID는 상수 1곳에서만 관리하기.
- 단순 작업에서는 `thinkingBudget: 0`으로 비용/지연 절감.
- 1M 컨텍스트를 활용하는 반복 호출은 **컨텍스트 캐싱**(`createCachedContent`)으로 비용 1/10 수준 절감 가능.
- 비실시간 대량 처리는 **batchGenerateContent**로 가격 절반.
- JSON 파싱이 필요하면 `responseMimeType: "application/json"` + `responseSchema` 사용 (§8).

## 10. 참고 링크

- 공식 모델 문서: https://ai.google.dev/gemini-api/docs/models?hl=ko
- 가격: https://ai.google.dev/gemini-api/docs/pricing?hl=ko
- API 키 발급: https://aistudio.google.com/apikey
