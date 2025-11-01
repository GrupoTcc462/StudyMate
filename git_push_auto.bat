@echo off
REM ==========================================================
REM  SCRIPT AUTOMÁTICO DE COMMIT E PUSH PARA GITHUB - UNIVERSAL
REM ==========================================================
title Git Auto Push - StudyMate

REM === CONFIGURAÇÕES PADRÃO ===
setlocal enabledelayedexpansion
set REPO_URL=https://github.com/GrupoTcc462/StudyMate.git
set BRANCH=main

echo.
echo ================================================
echo        AUTO COMMIT E PUSH - STUDYMATE
echo ================================================

REM === Verifica se está dentro de um repositório Git ===
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERRO] Este diretório não é um repositório Git.
    echo Inicializando repositório...
    git init
    git remote add origin %REPO_URL%
)

REM === Garante que o remoto 'origin' aponte para o repositório correto ===
git remote set-url origin %REPO_URL%

REM === Pergunta nome do projeto ou comentário opcional ===
echo.
set /p repo_name=Digite uma breve descricao (ex: Atualizacao notas): 

REM === Pega data/hora atual ===
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set dia=%%a
    set mes=%%b
    set ano=%%c
)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
    set hora=%%a
    set min=%%b
)

set commit_msg=Auto commit - %repo_name% - %dia%/%mes%/%ano% %hora%:%min%

echo.
echo ================================================
echo Adicionando arquivos alterados...
echo ================================================
git add -A

REM === Cria commit apenas se houver mudanças ===
git diff-index --quiet HEAD
if %errorlevel%==0 (
    echo.
    echo Nenhuma alteracao detectada. Nada a commitar.
    echo.
    pause
    exit /b
)

echo.
echo ================================================
echo Criando commit: "%commit_msg%"
echo ================================================
git commit -m "%commit_msg%"
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao criar commit.
    echo Verifique se há alterações pendentes ou conflitos.
    pause
    exit /b
)

echo.
echo ================================================
echo Enviando para o GitHub...
echo ================================================
git push -u origin %BRANCH%
if errorlevel 1 (
    echo.
    echo [ERRO] O push falhou!
    echo Verifique sua conexao, autenticacao GitHub ou conflitos de merge.
    echo.
    echo Dica: Tente rodar "git pull origin %BRANCH%" e depois executar este script novamente.
    pause
    exit /b
)

echo.
echo ================================================
echo  PUSH CONCLUIDO COM SUCESSO!
echo  Data/Hora: %date% %time%
echo ================================================
pause
exit /b
