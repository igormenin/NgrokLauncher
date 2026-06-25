@echo off
setlocal enabledelayedexpansion

echo ====================================================
echo NGROK Launcher - Criador de Executavel
echo ====================================================

echo [1/5] Verificando dependencias Python...
python -c "import customtkinter" 2>nul
if %errorlevel% neq 0 (
    echo CustomTkinter nao encontrado. Instalando...
    pip install customtkinter
) else (
    echo CustomTkinter ja instalado.
)

python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo PyInstaller nao encontrado. Instalando...
    pip install pyinstaller
) else (
    echo PyInstaller ja instalado.
)

echo.
echo [2/5] Localizando pasta do CustomTkinter...
for /f "delims=" %%i in ('python -c "import os, customtkinter; print(os.path.dirname(customtkinter.__file__))"') do set CUSTOMTKINTER_DIR=%%i
echo Pasta localizada: %CUSTOMTKINTER_DIR%

echo.
echo [3/5] Compilando executavel com PyInstaller...
pyinstaller --noconsole --onefile --clean --icon="launcher_icon.ico" --add-data "launcher_icon.ico;." --add-data "%CUSTOMTKINTER_DIR%;customtkinter" ngrok_launcher.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao compilar o executavel com PyInstaller.
    pause
    exit /b %errorlevel%
)

echo.
echo [4/5] Movendo executavel compilado para a raiz...
if exist "dist\ngrok_launcher.exe" (
    move /y "dist\ngrok_launcher.exe" ".\ngrok_launcher.exe"
) else (
    echo [ERRO] Arquivo executavel nao encontrado em dist\.
    pause
    exit /b 1
)

echo.
echo [5/5] Limpando arquivos temporarios de build...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "ngrok_launcher.spec" del /f /q "ngrok_launcher.spec"

echo.
echo ====================================================
echo Sucesso! Executavel gerado: ngrok_launcher.exe
echo ====================================================
pause
