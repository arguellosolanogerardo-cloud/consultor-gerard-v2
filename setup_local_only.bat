@echo off
echo ============================================
echo CONFIGURACION SISTEMA 100%% LOCAL - SIN COSTOS
echo ============================================
echo.
echo Este script configura el sistema para funcionar
echo EXCLUSIVAMENTE en local usando Ollama.
echo.
echo NO se requieren API keys ni costos externos.
echo.

REM Verificar si Ollama está instalado
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama no está instalado.
    echo.
    echo Para instalar Ollama:
    echo 1. Ve a: https://ollama.ai/download
    echo 2. Descarga e instala Ollama para Windows
    echo 3. Reinicia este script
    echo.
    pause
    exit /b 1
)

echo [OK] Ollama está instalado
echo.

REM Descargar modelo DeepSeek R1 8B (mejor calidad disponible para tu equipo)
echo Descargando modelo DeepSeek R1 8B (mejor calidad, ~5.2 GB)...
echo.
ollama pull deepseek-r1:8b

if %errorlevel% neq 0 (
    echo [WARNING] No se pudo descargar DeepSeek R1 8B, intentando Llama3.2 3B...
    ollama pull llama3.2:3b
    if %errorlevel% neq 0 (
        echo [WARNING] Tampoco Llama3.2, intentando Llama2 7B...
        ollama pull llama2:7b
        if %errorlevel% neq 0 (
            echo [ERROR] No se pudo descargar ningún modelo.
            echo Verifica tu conexión a internet.
            pause
            exit /b 1
        )
    )
)

echo.
echo [OK] Modelo descargado correctamente
echo.

REM Iniciar Ollama en segundo plano
echo Iniciando servicio Ollama...
start /B ollama serve

REM Esperar a que Ollama esté listo
timeout /t 5 /nobreak >nul

REM Verificar que Ollama esté funcionando
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama podría no estar completamente iniciado.
    echo Espera unos segundos más...
    timeout /t 10 /nobreak >nul
)

echo.
echo ============================================
echo CONFIGURACION COMPLETADA
echo ============================================
echo.
echo El sistema está listo para funcionar 100%% LOCAL:
echo.
echo - Sin costos externos
echo - Sin API keys requeridas
echo - Funcionamiento offline completo
echo.
echo Para iniciar la aplicación:
echo   streamlit run consultar_web.py
echo.
echo ¡Disfruta del sistema sin costos!
echo.
pause