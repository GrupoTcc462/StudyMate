@echo off
REM ================================================
REM  SCRIPT AUTOMÁTICO DE COMMIT E PUSH PARA GITHUB
REM ================================================

echo.
set /p repo_name=Digite o nome do repositorio (ex: Studymate_GitHub): 

REM Obtem data e hora atuais
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (
    set dia=%%a
    set mes=%%b
    set ano=%%c
)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
    set hora=%%a
    set min=%%b
)

REM Monta mensagem do commit
set commit_msg=Auto commit - %repo_name% - %dia%/%mes%/%ano% %hora%:%min%

echo.
echo ========================================
echo Adicionando todos os arquivos modificados
echo ========================================
git add .

echo.
echo ========================================
echo Criando commit com mensagem:
echo "%commit_msg%"
echo ========================================
git commit -m "%commit_msg%"

echo.
echo ========================================
echo Enviando para o GitHub...
echo ========================================
git push -u origin main

echo.
echo ========================================
echo  Push concluído! (%date% %time%)
echo ========================================
pause
