# deepseek-v4.1-flash 涨价停用 — 2026-09-21

- 大哥令：涨价了不能用，先停用（glm-5.2 不动）。
- 消耗源（new-api 日志实查）：① 本地 Hermes 主力白天干活，单次 ~200k tokens，7 天 946M；② 本机 crontab 每 5 分钟 `quant/event_live.py` 事件合约模拟仓（173 in/200 out）。
- 动作：渠道 31（opencode go1 → opencode.ai/zen/go）models 下掉 `deepseek-v4.1-flash`（原备份 `~/ch31-models.bak-20260921`）；event_live 的 crontab 行注释（备份 `~/crontab.bak-20260921-0945`，脚本和 state 未动可恢复）。
- 影响：本地主力模型需切走 deepseek-v4.1-flash，否则本地聊天失败；云上主模型 muse-spark 不受影响。
- 顺带发现：token“韩”从 119.191.4.95 大量调 glm-5.2（单次 117k）；meme-monitor 三个进程（bsc_chain/flap_watch/bsc_signal）实际还在跑，与“已停用”记录不符，待核实。
