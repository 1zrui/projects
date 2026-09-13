# GitHub 项目共享仓库

摘要：云上和本地 Hermes 通过 GitHub 仓库共享脚本、文档、skill 等项目文件。

## 仓库信息

- 地址：https://github.com/1zrui/projects
- 本地路径：`/home/ubuntu/workspace/projects`
- Token：存在 `~/.hermes/.env` 的 `GITHUB_TOKEN`

## 目录结构

```
projects/
├── quant-trading/          # 量化交易代码（backtest_engine/data_fetcher/strategies）
├── scripts/
│   ├── cron/               # 定时任务脚本（推广宝等）
│   └── tools/              # 工具脚本（table2img等）
├── docs/知识库/             # 知识库文档备份
├── skills/                 # Hermes skill 文件
├── .gitignore
└── README.md
```

## 同步方式

- 云上 push → 本地 pull
- 本地 push → 云上 pull
- 看 commit 记录知道谁改了啥

## 排除项（.gitignore）

- venv/、__pycache__/、*.pyc
- data/*.csv、data/*.json
- .env、*.log、.DS_Store

## 操作命令

```bash
# 推送
cd /home/ubuntu/workspace/projects
git add -A
git commit -m "描述"
git push origin main

# 拉取
git pull origin main
```
