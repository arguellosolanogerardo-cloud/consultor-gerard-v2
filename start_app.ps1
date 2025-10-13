# Script de inicio para GERARD - Consultor Web
# Usa el entorno virtual limpio (.venv_clean) con protobuf 5.x compatible

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  GERARD - Consultor Web" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Iniciando aplicación Streamlit..." -ForegroundColor Yellow
Write-Host "Entorno: .venv_clean (protobuf 5.29.5)" -ForegroundColor Gray
Write-Host ""

# Cambiar al directorio del proyecto y activar entorno limpio
Set-Location E:\proyecto-gemini-limpio
& .\\.venv_clean\Scripts\python.exe -m streamlit run consultar_web.py

Write-Host ""
Write-Host "Aplicación detenida." -ForegroundColor Yellow
