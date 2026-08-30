import urllib.request, json

key = "sk-439...e957"  # DeepSeek API key from config
data = json.dumps({
    "model": "deepseek-chat",
    "messages": [
        {"role": "user", "content": "你好，请回复三个字"}
    ],
    "max_tokens": 10
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:8787/v1/chat/completions",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    },
    method="POST"
)

resp = urllib.request.urlopen(req, timeout=60)
result = json.loads(resp.read())
print("Status:", resp.status)
print("Full response:", json.dumps(result, ensure_ascii=False)[:500])
