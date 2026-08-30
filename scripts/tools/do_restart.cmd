@echo off
cd /d D:\Hermes
echo === DOUZI_ASYNC_RESTART begin @ %time% === >> D:\Hermes\logs\gateway-restart.log
for /f "skip=1 tokens=1" %%p in ('wmic process where "name='python.exe' and commandline like '%%hermes_cli%%'" get processid ^| findstr /r "[0-9]"') do (
  echo killing %%p >> D:\Hermes\logs\gateway-restart.log
  taskkill /pid %%p /f
)
timeout /t 4 /nobreak >nul
echo === DOUZI_ASYNC_RESTART starting new @ %time% === >> D:\Hermes\logs\gateway-restart.log
set HERMES_HOME=D:\Hermes
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set HERMES_GATEWAY_DETACHED=1
set VIRTUAL_ENV=D:\Hermes\hermes-agent\venv
set RESTART_SCRIPT_INVOKED=1
D:\Hermes\hermes-agent\venv\Scripts\python.exe -m hermes_cli.main gateway run >> D:\Hermes\logs\gateway-restart.log 2>&1
