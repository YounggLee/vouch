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

## 8. 운영 팁

- **Preview 모델**이므로 가격·동작이 변경될 수 있음. 코드에서 모델 ID는 상수 1곳에서만 관리하기.
- 단순 작업에서는 `thinkingBudget: 0`으로 비용/지연 절감.
- 1M 컨텍스트를 활용하는 반복 호출은 **컨텍스트 캐싱**(`createCachedContent`)으로 비용 1/10 수준 절감 가능.
- 비실시간 대량 처리는 **batchGenerateContent**로 가격 절반.
- JSON 파싱이 필요하면 `responseMimeType: "application/json"` + `responseSchema` 사용.

## 9. 참고 링크

- 공식 모델 문서: https://ai.google.dev/gemini-api/docs/models?hl=ko
- 가격: https://ai.google.dev/gemini-api/docs/pricing?hl=ko
- API 키 발급: https://aistudio.google.com/apikey
