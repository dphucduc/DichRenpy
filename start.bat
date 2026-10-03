@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Hay cai Python 3.10+ tu python.org truoc khi chay.
  pause
  exit /b 1
)
where git >nul 2>nul
if errorlevel 1 (
  echo Hay cai Git tu git-scm.com truoc khi chay.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failure
if not exist .tools mkdir .tools
if not exist .tools\unrpyc\.git git clone https://github.com/CensoredUsername/unrpyc.git .tools\unrpyc
if errorlevel 1 goto failure
git -C .tools\unrpyc checkout --detach 3ae8334ed71a05535927dcc559663d3aca51215b
if errorlevel 1 goto failure
echo Mo trinh duyet va truy cap dia chi duoc hien ben duoi.
.venv\Scripts\python.exe app.py
pause
exit /b 0
:failure
echo Khong the khoi dong. Xem thong bao loi ben tren.
pause
exit /b 1
