@echo off
rem 一键启动后端（自动创建虚拟环境、安装依赖、迁移、灌演示数据）
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 创建虚拟环境 .venv
  python -m venv .venv
  if errorlevel 1 goto error
)

echo [2/3] 安装依赖
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 goto error

echo [3/3] 启动服务
".venv\Scripts\python.exe" -m backend.dev %*
goto end

:error
echo.
echo [启动失败] 请确认已安装 Python 3.11+ 并加入 PATH，然后重试。
echo 也可以手动执行：python -m backend.dev
exit /b 1

:end
endlocal
