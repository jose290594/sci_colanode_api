@echo off
REM Start sidecar then FastAPI (dev helper)
set ROOT=%~dp0..
set NODE_PATH=%ROOT%\sidecar\node_modules;%ROOT%\vendor\colanode\node_modules
start "colanode-sidecar" cmd /c "cd /d %ROOT%\sidecar && set NODE_PATH=%NODE_PATH% && npx tsx src/index.ts"
timeout /t 3 /nobreak >nul
cd /d %ROOT%
.\.venv\Scripts\python -m sci_colanode_api.main
