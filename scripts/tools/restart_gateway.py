#!/usr/bin/env python3
# 可靠重启 Hermes 网关 —— 不依赖 Windows 任务计划(InteractiveToken 在非交互环境拉不起)
# 直接 DETACHED 拉起网关进程，轮询日志确认成功才退出。
import subprocess, os, sys, time

VENV_PY = r"D:\Hermes\hermes-agent\venv\Scripts\python.exe"
LOG = r"D:\Hermes\logs\gateway.log"
CWD = r"D:\Hermes"
DETACHED = 0x00000008  # DETACHED_PROCESS

def find_pids():
    # wmic 精确匹配命令行含 hermes_cli.main gateway run 的 python
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'",
             "get", "processid,commandline", "/format:csv"],
            capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return []
    pids = []
    for line in out.splitlines():
        if "hermes_cli.main" in line and "gateway" in line and "run" in line:
            parts = [p for p in line.split(",") if p.strip().isdigit()]
            if parts:
                pids.append(int(parts[-1]))
    return pids

def kill_pids(pids):
    for p in pids:
        subprocess.run(["taskkill", "/PID", str(p), "/F"],
                        capture_output=True, timeout=10)

def start_detached():
    env = os.environ.copy()
    env["HERMES_HOME"] = r"D:\Hermes"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["HERMES_GATEWAY_DETACHED"] = "1"
    env["VIRTUAL_ENV"] = r"D:\Hermes\hermes-agent\venv"
    env["RESTART_SCRIPT_INVOKED"] = "1"  # 标记: 此进程由 restart_gateway.py 拉起
    # 在日志打专属标记, 事后可查是谁拉的
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\n=== RESTART_SCRIPT_INVOKED: restart_gateway.py 发起拉起 ===\n")
    except Exception:
        pass
    p = subprocess.Popen(
        [VENV_PY, "-m", "hermes_cli.main", "gateway", "run"],
        env=env, cwd=CWD, creationflags=DETACHED,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL)
    return p.pid

def wait_running(timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(LOG, encoding="utf-8", errors="ignore") as f:
                tail = f.readlines()[-60:]
            for l in tail:
                if "Gateway running with 3 platform" in l:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False

if __name__ == "__main__":
    print("[1] 找旧网关进程...", flush=True)
    pids = find_pids()
    print(f"    旧 PID: {pids}", flush=True)
    if pids:
        print("[2] 杀旧进程...", flush=True)
        kill_pids(pids)
        time.sleep(4)  # 等端口释放
    print("[3] DETACHED 起新网关...", flush=True)
    newpid = start_detached()
    print(f"    新 PID: {newpid}", flush=True)
    print("[4] 轮询日志等 'Gateway running'...", flush=True)
    ok = wait_running(45)
    print("RESULT: " + ("SUCCESS" if ok else "FAILED"), flush=True)
    sys.exit(0 if ok else 1)
