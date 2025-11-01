@echo off
title  Configurando e Iniciando o Site STUDYMATE

REM ================================================
REM  SCRIPT DE INSTALACAO E EXECUCAO AUTOMATICA DO SITE DJANGO
REM ================================================

echo.
echo ========================================
echo  VERIFICANDO INSTALACAO DO PYTHON...
echo ========================================
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo  Python nao encontrado. 
    echo  Baixando e instalando Python 3.12...
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe -OutFile python_installer.exe"
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
) ELSE (
    for /f "tokens=2 delims= " %%v in ('python --version') do set pyver=%%v
    echo  Python %pyver% encontrado.
)

echo.
echo ========================================
echo  CRIANDO/VERIFICANDO AMBIENTE VIRTUAL...
echo ========================================
IF NOT EXIST venv (
    echo Criando ambiente virtual...
    python -m venv venv
) ELSE (
    echo Ambiente virtual ja existe.
)

echo.
echo ========================================
echo  ATIVANDO AMBIENTE VIRTUAL...
echo ========================================
call venv\Scripts\activate

echo.
echo ========================================
echo  ATUALIZANDO PIP E INSTALANDO DEPENDENCIAS...
echo ========================================
python -m pip install --upgrade pip >nul

IF EXIST requirements.txt (
    echo  Instalando dependencias de requirements.txt...
    pip install -r requirements.txt >nul
) ELSE (
    echo  Instalando Django e bibliotecas padrao...
    pip install django djangorestframework pillow >nul
)

echo.
echo ========================================
echo  EXECUTANDO MIGRATIONS...
echo ========================================
python manage.py migrate >nul

echo.
echo ========================================
echo  INICIANDO O SERVIDOR DJANGO...
echo ========================================
start "" http://127.0.0.1:8000/
start /min cmd /c "call venv\Scripts\activate && python manage.py runserver"

echo.
echo ========================================
echo  SITE INICIADO COM SUCESSO!
echo  O site foi aberto no navegador automaticamente.
echo ========================================

exit
