# Finding crypto-analysis skills on GitHub

## Why this exists
Session 2026-08-27: user said "去github上找一下 有没有分析加密货币 相关的skill". `web_search` (Tavily backend) timed out; `curl -x socks5h://127.0.0.1:10808 https://api.github.com` returned HTTP:000 (proxy path to github dead, though Binance worked via the same proxy). **Authenticated `gh` CLI worked** — it carries its own token and egress, independent of the curl proxy.

## Working method (validated this session)
```bash
# repo search
gh search repos "crypto analysis" --limit 15 \
  --json fullName,description,url,stargazersCount
gh search repos "claude skill crypto trading" --limit 8
# browse a repo's tree for SKILL.md without cloning
gh api "repos/HKUDS/Vibe-Trading/git/trees/main?recursive=1" \
  --jq '.tree[].path' | grep -iE "crypto|SKILL.md"
# read a SKILL.md without cloning
gh api "repos/HKUDS/Vibe-Trading/contents/agent/src/skills/crypto-derivatives/SKILL.md" \
  --jq '.content' | base64 -d
# repo metadata (stars / last update)
gh api repos/HKUDS/Vibe-Trading \
  --jq '{stars:.stargazers_count,forks:.forks_count,updated:.updated_at}'
# discover skill definitions across repos
gh search code "crypto trading" --filename SKILL.md --limit 10
```
Prereq: `gh` must be authenticated (`gh auth status`). On this host it already is (token in `C:\Users\Administrator\AppData\Roaming\GitHub CLI\hosts.yml`). If `gh` is NOT authenticated in a future session, this path is unavailable — fall back to `web_search` or a browser tool.

## What was found (crypto-analysis skills on GitHub)
- **HKUDS/Vibe-Trading** (31.8k★, updated 2026-08-26) — full trading-agent suite with crypto skills under `agent/src/skills/`:
  - `crypto-derivatives` — perp funding-rate arbitrage, futures term-structure, option vol/Greeks (OKX/Deribit)
  - `defi-yield` — DeFi yield strategies
  - `ccxt` — exchange API connector
  - `onchain-analysis` — on-chain data
  - `token-unlock-treasury` — token unlocks / treasury flows
  - plus `candlestick` (patterns), `backtest/engines/crypto.py`
- **2025Emma/vibe-coding-cn** (i18n zh/en) — `hummingbot` (market-making/arb bot framework), `cryptofeed` (market data feed)
- `crypto-market-analysis` (this skill) — methodology + resource index, analysis-not-trading

## Note on local vs GitHub
The local `crypto-trend-analyzer` skill is a hands-on Binance K-line analyzer (real-time data + card). This `crypto-market-analysis` skill is the broader methodology + GitHub resource index. They are complementary: use `crypto-trend-analyzer` to *do* the analysis now; use this skill (and the GitHub list above) when the user wants *more/better* crypto-analysis sources or to find external skills.
