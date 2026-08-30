import yaml

with open(r"D:\Hermes\config.yaml", "r", encoding="utf-8") as f:
    c = yaml.safe_load(f)

providers = c.get("providers", {})
deepseek = providers.get("deepseek", {})
key = deepseek.get("api_key", "")
print(f"DeepSeek key: {key[:12]}...{key[-6:]}")
print(f"Key length: {len(key)}")
print(f"Starts with sk-: {key.startswith('sk-')}")

aux = c.get("auxiliary", {})
we = aux.get("web_extract", {})
cp = aux.get("compression", {})
print(f"\nAux web_extract: provider={we.get('provider')}, model={we.get('model')}, base_url={we.get('base_url')}")
print(f"Aux compression: provider={cp.get('provider')}, model={cp.get('model')}, base_url={cp.get('base_url')}")
