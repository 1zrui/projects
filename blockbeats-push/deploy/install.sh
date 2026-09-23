#!/usr/bin/env bash
# ============================================================================
# 律动(BlockBeats)快讯推送 · Linux 一键部署（Ubuntu / Debian 适用）
#
# 用法：  sudo bash install.sh [/opt/blockbeats-push]
#        在「解压后的项目目录里」执行即可；也可指定别的安装目录。
#
# 会做的事：装系统依赖(python3-venv + 中文字体) → 拷代码 → 建 venv 装 Pillow
#           → 生成 .env → 注册 systemd 服务 → 跑一次 --check 自检（不发群）
# ============================================================================
set -euo pipefail

APP_DIR="${1:-/opt/blockbeats-push}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="blockbeats-push"

echo "==> 源码目录: $SRC_DIR"
echo "==> 安装目录: $APP_DIR"

if [ "$(id -u)" != "0" ]; then
  echo "!! 请用 root 运行： sudo bash $0 $APP_DIR"; exit 1
fi

# ---------- 1. 系统依赖 ----------
echo "==> [1/6] 安装系统依赖（python3-venv + 中文字体）"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3-venv python3-pip fonts-noto-cjk >/dev/null
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y python3-pip google-noto-sans-cjk-fonts >/dev/null
elif command -v yum >/dev/null 2>&1; then
  yum install -y python3-pip && echo "    ⚠️ yum 源可能没有 Noto CJK 字体，若卡片中文变方块请手动装字体"
else
  echo "    ⚠️ 未知包管理器：请自行确保 python3-venv 与中文字体已安装"
fi

# ---------- 2. 拷代码 ----------
echo "==> [2/6] 拷贝代码到 $APP_DIR"
mkdir -p "$APP_DIR"
if [ "$SRC_DIR" != "$(cd "$APP_DIR" && pwd -P)" ]; then
  cp -f "$SRC_DIR/blockbeats_listener.py" "$SRC_DIR/requirements.txt" \
        "$SRC_DIR/config.example.env" "$SRC_DIR/README.md" "$APP_DIR/"
  mkdir -p "$APP_DIR/deploy"
  cp -f "$SRC_DIR/deploy/"* "$APP_DIR/deploy/" 2>/dev/null || true
fi

# ---------- 3. venv + 依赖 ----------
echo "==> [3/6] 创建 venv 并安装依赖（Pillow）"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# ---------- 4. 配置 ----------
echo "==> [4/6] 准备配置文件"
mkdir -p "$APP_DIR/state" "$APP_DIR/logs" "$APP_DIR/cache"
if [ -f "$APP_DIR/.env" ]; then
  echo "    .env 已存在 → 保留不动"
else
  cp "$APP_DIR/config.example.env" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo "    !! 已生成 $APP_DIR/.env —— 记得填 QQ_CLIENT_SECRET 后再启动"
fi

# ---------- 5. systemd ----------
echo "==> [5/6] 注册 systemd 服务"
sed "s#/opt/blockbeats-push#$APP_DIR#g" "$APP_DIR/deploy/$SERVICE_NAME.service" \
  > "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null
echo "    已注册并设为开机自启（暂未启动）"

# ---------- 6. 自检 ----------
echo "==> [6/6] 自检（只抓一次解析，不发群）"
"$APP_DIR/.venv/bin/python" "$APP_DIR/blockbeats_listener.py" --check || echo "    ⚠️ 自检未通过，先看上面的报错"

cat <<EOF

============================================================
✅ 安装完成。接下来：
  1) 编辑 $APP_DIR/.env 填好 QQ_CLIENT_SECRET
  2) 启动服务：      systemctl start blockbeats-push
  3) 看实时日志：    journalctl -u blockbeats-push -f
                     （脚本自己也会写 $APP_DIR/logs/listener.log）
  4) 通道实测：      $APP_DIR/.venv/bin/python $APP_DIR/blockbeats_listener.py --test-send
     → 群里收到一张测试卡 = 整条链路通
  5) 常用运维：      systemctl status|stop|restart blockbeats-push
============================================================
EOF
