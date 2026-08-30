#!/bin/bash
LOG="/d/Hermes/hermes_update_$(date +%Y%m%d_%H%M%S).log"
echo "[$(date)] === update start ===" | tee -a "$LOG"
cd /d/Hermes/hermes-agent || { echo "cd failed" | tee -a "$LOG"; exit 1; }

# 清掉上次残留的死锁
rm -f .git/shallow.lock .git/index.lock 2>/dev/null

echo "[$(date)] git status (check local changes)" | tee -a "$LOG"
git status --porcelain 2>&1 | head -20 | tee -a "$LOG"

echo "[$(date)] git fetch" | tee -a "$LOG"
git fetch origin 2>&1 | tail -5 | tee -a "$LOG"

echo "[$(date)] git pull --ff-only" | tee -a "$LOG"
git pull --ff-only 2>&1 | tail -20 | tee -a "$LOG"

echo "[$(date)] HEAD after pull:" | tee -a "$LOG"
git describe --tags 2>/dev/null | tee -a "$LOG"
git log --oneline -1 2>/dev/null | tee -a "$LOG"

echo "[$(date)] pip install -e . (refresh deps)" | tee -a "$LOG"
./venv/Scripts/python.exe -m pip install -e . --upgrade 2>&1 | tail -25 | tee -a "$LOG"

echo "[$(date)] === final HEAD ===" | tee -a "$LOG"
git describe --tags 2>/dev/null | tee -a "$LOG"
echo "[$(date)] === update DONE ===" | tee -a "$LOG"
