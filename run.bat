@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ========================================
echo  Gichul Forge server launcher
echo ========================================
echo.

if not exist ".env.local" (
  if exist ".env.local.example" (
    copy ".env.local.example" ".env.local" >nul
    echo Created .env.local from .env.local.example
    echo Edit .env.local and set NVIDIA_NIM_API_KEY if AI processing is required.
    echo.
  ) else (
    echo WARNING: .env.local.example was not found.
    echo.
  )
)

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo ERROR: Python was not found. Install Python 3.11+ and run this file again.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: npm was not found. Install Node.js 20+ and run this file again.
  pause
  exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  %PYTHON_CMD% -m venv "backend\.venv"
  if errorlevel 1 (
    echo ERROR: Failed to create Python virtual environment.
    pause
    exit /b 1
  )
)

"%ROOT%backend\.venv\Scripts\python.exe" -c "import fastapi, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo Installing backend dependencies...
  "%ROOT%backend\.venv\Scripts\python.exe" -m pip install -r "%ROOT%backend\requirements.txt"
  if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies.
    pause
    exit /b 1
  )
)

if not exist "frontend\node_modules\next\package.json" (
  echo Installing frontend dependencies...
  pushd "%ROOT%frontend"
  if exist "pnpm-lock.yaml" (
    call corepack pnpm install
  ) else (
    call npm install
  )
  if errorlevel 1 (
    echo npm/pnpm install failed. Retrying with npm...
    call npm install
    if errorlevel 1 (
      popd
      echo ERROR: Failed to install frontend dependencies.
      pause
      exit /b 1
    )
  )
  popd
)

echo Starting backend on http://localhost:8000
start "Gichul Forge Backend" /D "%ROOT%backend" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting frontend on http://localhost:3000
start "Gichul Forge Frontend" /D "%ROOT%frontend" cmd /k "set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000&& call npm run dev"

echo.
echo Servers are starting in separate windows.
echo Frontend: http://localhost:3000
echo Backend docs: http://localhost:8000/docs
echo.

timeout /t 5 /nobreak >nul
start "" "http://localhost:3000"

endlocal
