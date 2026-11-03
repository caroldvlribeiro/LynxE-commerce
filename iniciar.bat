@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 (
    set "ERROR_MESSAGE=Nao foi possivel acessar a pasta do projeto."
    goto :fail
)

echo.
echo ============================================
echo   Inicializacao da loja Linx
echo ============================================
echo [1/4] Verificando o ambiente Python...

set "PYTHON=python"
if exist ".venv\Scripts\activate.bat" (
    echo Encontrado ambiente virtual .venv. Ativando...
    call ".venv\Scripts\activate.bat"
    if errorlevel 1 (
        set "ERROR_MESSAGE=Falha ao ativar o ambiente virtual .venv."
        goto :fail
    )
) else if exist "venv\Scripts\activate.bat" (
    echo Encontrado ambiente virtual venv. Ativando...
    call "venv\Scripts\activate.bat"
    if errorlevel 1 (
        set "ERROR_MESSAGE=Falha ao ativar o ambiente virtual venv."
        goto :fail
    )
) else (
    echo Ambiente virtual nao encontrado; sera usado o Python disponivel no sistema.
)

python --version >nul 2>&1
if errorlevel 1 (
    py -3 --version >nul 2>&1
    if errorlevel 1 (
        set "ERROR_MESSAGE=Python nao encontrado. Instale Python 3.11 ou superior."
        goto :fail
    )
    set "PYTHON=py -3"
)

%PYTHON% -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 (
    set "ERROR_MESSAGE=O projeto requer Python 3.11 ou superior."
    goto :fail
)

echo [2/4] Verificando dependencias do projeto...
%PYTHON% -c "import fastapi, uvicorn, redis, pydantic_settings, dotenv, argon2, email_validator" >nul 2>&1
if errorlevel 1 (
    echo Dependencias ausentes. Instalando conforme requirements.txt...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        set "ERROR_MESSAGE=Falha ao instalar as dependencias. Confira a conexao e requirements.txt."
        goto :fail
    )
    %PYTHON% -c "import fastapi, uvicorn, redis, pydantic_settings, dotenv, argon2, email_validator" >nul 2>&1
    if errorlevel 1 (
        set "ERROR_MESSAGE=Uma ou mais dependencias continuam indisponiveis apos a instalacao."
        goto :fail
    )
)
echo Dependencias verificadas.

echo [3/4] Verificando configuracao do Redis Cloud...
if not exist ".env" (
    set "ERROR_MESSAGE=Arquivo .env nao encontrado. Copie .env.example para .env e configure o Redis Cloud."
    goto :fail
)
echo Arquivo .env encontrado. A conexao Redis sera validada durante a inicializacao da API.

echo [4/4] Iniciando backend e frontend...
echo A loja sera disponibilizada em http://127.0.0.1:8000
echo Pressione Ctrl+C para encerrar o servidor.
echo.
%PYTHON% -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
if errorlevel 1 (
    set "ERROR_MESSAGE=O servidor nao iniciou ou foi encerrado com erro. Confira as mensagens acima e a configuracao do Redis."
    goto :fail
)

echo.
echo Servidor encerrado.
exit /b 0

:fail
echo.
echo [ERRO] %ERROR_MESSAGE%
echo Corrija o problema indicado e execute iniciar.bat novamente.
echo.
pause
exit /b 1
