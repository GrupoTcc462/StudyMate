@echo off
title 🚀 GIT PUSH AUTOMATICO - STUDYMATE
color 0A

REM ================================================
REM  SCRIPT AUTOMÁTICO DE COMMIT E PUSH PARA GITHUB
REM ================================================

echo.
echo ========================================
echo 🔍 Verificando se este é um repositório Git...
echo ========================================
git rev-parse --is-inside-work-tree >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Este diretório não é um repositório Git.
    echo Inicializando o repositório local...
    git init
)

echo.
echo ========================================
echo 🔗 Configurando repositório remoto (origin)...
echo ========================================
git remote remove origin >nul 2>&1
git remote add origin https://github.com/GrupoTcc462/StudyMate.git

echo.
set /p repo_name=Digite o nome do repositorio (ex: StudyMate): 

REM Obtem data e hora atuais (compatível com diferentes formatos regionais)
for /f "tokens=1-4 delims=/.- " %%a in ('date /t') do (
    set data=%%a-%%b-%%c
)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
    set hora=%%a
    set min=%%b
)

REM Monta mensagem do commit
set commit_msg=Auto commit - %repo_name% - %data% %hora%h%min%m

echo.
echo ========================================
echo 🧱 Adicionando arquivos...
echo ========================================
git add -A

echo.
echo ========================================
echo 📝 Criando commit com mensagem:
echo "%commit_msg%"
echo ========================================
git commit -m "%commit_msg%" || echo ⚠️ Nenhuma alteração detectada para commit.

echo.
echo ========================================
echo 🌐 Verificando branch atual...
echo ========================================
for /f "tokens=*" %%b in ('git branch --show-current') do set branch_name=%%b
if "%branch_name%"=="" (
    echo ⚠️ Nenhum branch detectado. Criando 'main'...
    git branch -M main
    set branch_name=main
)
echo Branch atual: %branch_name%

echo.
echo ========================================
echo 🚀 Enviando para o GitHub...
echo ========================================
git push -u origin %branch_name%
IF ERRORLEVEL 1 (
    echo ❌ Erro ao enviar para o GitHub.
    echo Verifique:
    echo  - Se voce tem permissao para o repositorio.
    echo  - Se esta logado no GitHub.
    echo  - Se o token de acesso esta configurado corretamente.
    pause
    exit /b
)

echo.
echo ========================================
echo ✅ Push concluído com sucesso!
echo 📅 %date% ⏰ %time%
echo ========================================
pause
exit
