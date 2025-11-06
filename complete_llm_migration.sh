#!/bin/bash
# Script maestro de migración LLM completa
# Ejecuta todo el proceso de migración de una vez

echo "🤖 MIGRACIÓN COMPLETA DE LLM - SCRIPT MAESTRO"
echo "==============================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "consultar_web.py" ]; then
    echo "❌ Error: Ejecutar desde el directorio raíz del proyecto"
    exit 1
fi

echo "📋 PASO 1: Verificando estado del sistema..."
python llm_operations_center.py --status-only
if [ $? -ne 0 ]; then
    echo "❌ Verificación falló. Abortando."
    exit 1
fi

echo ""
echo "📦 PASO 2: Instalando dependencias..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Instalación de dependencias falló."
    exit 1
fi

echo ""
echo "🧪 PASO 3: Ejecutando pruebas completas..."
python test_llm_migration_suite.py
if [ $? -ne 0 ]; then
    echo "❌ Pruebas fallaron. Abortando."
    exit 1
fi

echo ""
echo "🚀 PASO 4: Ejecutando despliegue..."
python deploy_llm_migration.py
if [ $? -ne 0 ]; then
    echo "❌ Despliegue falló."
    exit 1
fi

echo ""
echo "🎯 PASO 5: Verificación final..."
python test_llm_integration.py
if [ $? -ne 0 ]; then
    echo "❌ Verificación final falló."
    exit 1
fi

echo ""
echo "==============================================="
echo "🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!"
echo "==============================================="
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo "1. Configura ANTHROPIC_API_KEY y OPENAI_API_KEY en .env"
echo "2. Ejecuta: streamlit run consultar_web.py"
echo "3. Monitorea métricas con: python llm_operations_center.py"
echo "4. Revisa reportes en MIGRATION_COMPLETED_REPORT.md"
echo ""
echo "📊 SISTEMA LISTO PARA PRODUCCIÓN"
echo "=================================="