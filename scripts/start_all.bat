@echo off
echo =====================================================
echo   E-commerce Supabase  -  Iniciando tudo
echo =====================================================

:: Detecta o Anaconda automaticamente
set CONDA_ROOT=
for %%d in (
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\Anaconda3"
    "%LOCALAPPDATA%\anaconda3"
    "C:\ProgramData\anaconda3"
    "C:\anaconda3"
    "C:\ProgramData\Anaconda3"
) do (
    if exist "%%~d\python.exe" (
        if not defined CONDA_ROOT set CONDA_ROOT=%%~d
    )
)

if not defined CONDA_ROOT (
    echo [ERRO] Anaconda nao encontrado automaticamente.
    echo Execute este bat pelo Anaconda Prompt.
    pause
    exit /b 1
)

set PYTHON=%CONDA_ROOT%\python.exe
set UVICORN=%CONDA_ROOT%\Scripts\uvicorn.exe

echo [OK] Python encontrado: %PYTHON%

echo.
echo [1/3] Subindo LocalStack...
docker-compose up -d
timeout /t 15 /nobreak >nul

echo [2/3] Provisionando filas SQS via Terraform...
cd infra
terraform apply -auto-approve
cd ..

echo [3/3] Iniciando servicos...
start "API FastAPI"  cmd /k "%UVICORN% api.main:app --reload --port 8000"
start "Frontend"     cmd /k "%PYTHON% launcher_server.py"
timeout /t 3 /nobreak >nul
start "Pagamento"    cmd /k "%PYTHON% consumidores/pagamento.py"
start "Estoque"      cmd /k "%PYTHON% consumidores/estoque.py"
start "Fiscal"       cmd /k "%PYTHON% consumidores/fiscal.py"
start "Logistica"    cmd /k "%PYTHON% consumidores/logistica.py"
start "Notificacao"  cmd /k "%PYTHON% consumidores/notificacao.py"

echo.
echo =====================================================
echo  Tudo iniciado!
echo  API:           http://localhost:8000
echo  Docs:          http://localhost:8000/docs
echo  Frontend:      http://localhost:3000
echo  AWS Explorer:  http://localhost:3000/admin.html
echo =====================================================
pause