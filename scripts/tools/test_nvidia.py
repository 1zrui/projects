import json, os, urllib.request

custom = json.loads(os.environ.get("CUSTOM_PROVIDERS", "[]"))
nv = {}
for p in custom:
    if p.get("name") == "nvidia":
        nv = p
        break

base = nv.get("base_url", "https://integrate.api.nvidia.com/v1")
key = nv.get("api_key", "")
url = f"{base}/chat/completions"
print(f"Target URL: {url}")
print(f"Using key: {key[:10]}...{key[-4:]}" if key else "No key found")

body = {
    "model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "messages": [{"role": "user", "content": "say hi"}],
    "max_tokens": 5
}

req = urllib.request.Request(
    url,
    data=json.dumps(body).encode(),
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    },
    method="POST"
)

try:
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    print(f"Success! Status: {resp.status}")
    print(json.dumps(data, indent=2)[:300])
except urllib.error.HTTPError as e:
    err_body = e.read().decode()
    print(f"HTTP {e.code}: {err_body[:200]}")
except Exception as e:
    print(f"Error: {e}")
