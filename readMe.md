

# test the Anthropic claude API
## Question
```
curl https://api.anthropic.com/v1/messages \
    --header "x-api-key: YOUR KEY" \
    --header "anthropic-version: 2023-06-01" \
    --header "content-type: application/json" \
    --data \
'{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, world"}
    ]
}'
```
## Réponse

# test the Google Gemini API
## Question
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent" \
  -H 'Content-Type: application/json' \
  -H 'X-goog-api-key: GEMINI_API_KEY' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Explain how AI works in a few words"
          }
        ]
      }
    ]
  }'

## Réponse :
  {
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "AI learns from data to make predictions or decisions.\n"       
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "avgLogprobs": -0.076992181214419281
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 8,
    "candidatesTokenCount": 11,
    "totalTokenCount": 19,
    "promptTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 8
      }
    ],
    "candidatesTokensDetails": [
      {
        "modality": "TEXT",
        "tokenCount": 11
      }
    ]
  },
  "modelVersion": "gemini-2.0-flash",
  "responseId": "ZZF3aI69MbW3mNAP3Pv2wA4"
}