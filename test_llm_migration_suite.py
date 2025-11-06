# -*- coding: utf-8 -*-
"""
Suite completa de pruebas para migración de LLM
Ejecuta comparación, carga, calidad y genera reporte consolidado
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, Any

# Configurar UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'

def run_test_script(script_name: str) -> Dict[str, Any]:
    """Ejecuta un script de prueba y captura resultados"""

    print(f"\n🚀 Ejecutando {script_name}...")
    try:
        result = subprocess.run([
            sys.executable, script_name
        ], capture_output=True, text=True, encoding='utf-8', cwd=os.getcwd())

        return {
            'script': script_name,
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {
            'script': script_name,
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def generate_consolidated_report(results: Dict[str, Any]) -> str:
    """Genera reporte consolidado de todas las pruebas"""

    report = []
    report.append("# REPORTE CONSOLIDADO DE MIGRACIÓN DE LLM")
    report.append(f"**Fecha de ejecución:** {results['timestamp']}")
    report.append(f"**Directorio de trabajo:** {os.getcwd()}")
    report.append("")

    # Resumen ejecutivo
    report.append("## RESUMEN EJECUTIVO")
    report.append("")

    successful_tests = sum(1 for r in results['test_results'] if r['success'])
    total_tests = len(results['test_results'])

    report.append(f"- **Tests ejecutados:** {total_tests}")
    report.append(f"- **Tests exitosos:** {successful_tests}")
    report.append(f"- **Tasa de éxito:** {successful_tests/total_tests:.1%}")
    report.append("")

    # Resultados detallados
    report.append("## RESULTADOS DETALLADOS")
    report.append("")

    for test_result in results['test_results']:
        status = "✅" if test_result['success'] else "❌"
        report.append(f"### {status} {test_result['script']}")
        report.append(f"- **Estado:** {'Exitoso' if test_result['success'] else 'Fallido'}")
        report.append(f"- **Código de salida:** {test_result['returncode']}")
        report.append("")

        if test_result['stdout']:
            report.append("**Salida estándar:**")
            report.append("```")
            # Limitar salida a últimas 20 líneas para no hacer el reporte demasiado largo
            lines = test_result['stdout'].split('\n')[-20:]
            report.append('\n'.join(lines))
            report.append("```")
            report.append("")

        if test_result['stderr']:
            report.append("**Errores:**")
            report.append("```")
            report.append(test_result['stderr'])
            report.append("```")
            report.append("")

    # Recomendaciones
    report.append("## RECOMENDACIONES PARA MIGRACIÓN")
    report.append("")

    if successful_tests == total_tests:
        report.append("✅ **Todas las pruebas pasaron exitosamente.**")
        report.append("")
        report.append("**Próximos pasos recomendados:**")
        report.append("1. Revisar los reportes detallados de cada test")
        report.append("2. Comparar métricas de rendimiento entre modelos")
        report.append("3. Evaluar costos y límites de cuota")
        report.append("4. Implementar cambios en producción con monitoreo")
    else:
        report.append("⚠️ **Algunas pruebas fallaron.**")
        report.append("")
        report.append("**Acciones recomendadas:**")
        report.append("1. Revisar errores en tests fallidos")
        report.append("2. Verificar configuración de APIs (claves, cuotas)")
        report.append("3. Instalar dependencias faltantes")
        report.append("4. Re-ejecutar tests después de correcciones")

    report.append("")
    report.append("---")
    report.append("*Reporte generado automáticamente por test_llm_migration_suite.py*")

    return "\n".join(report)

def main():
    """Función principal de la suite de pruebas"""

    print("🚀 SUITE COMPLETA DE PRUEBAS DE MIGRACIÓN DE LLM")
    print("=" * 70)
    print("Esta suite ejecutará múltiples tests para validar la migración de Gemini a Claude/OpenAI")
    print("")

    # Lista de scripts de prueba a ejecutar
    test_scripts = [
        'test_llm_comparison.py',      # Comparación básica de respuestas
        'test_llm_load_stress.py',     # Pruebas de carga y estrés
        'test_llm_quality.py'          # Evaluación de calidad de respuestas
    ]

    # Verificar que los scripts existen
    missing_scripts = []
    for script in test_scripts:
        if not os.path.exists(script):
            missing_scripts.append(script)

    if missing_scripts:
        print(f"❌ Scripts faltantes: {', '.join(missing_scripts)}")
        return

    # Ejecutar todos los tests
    results = {
        'timestamp': datetime.now().isoformat(),
        'test_results': []
    }

    for script in test_scripts:
        result = run_test_script(script)
        results['test_results'].append(result)

        if result['success']:
            print(f"✅ {script} completado exitosamente")
        else:
            print(f"❌ {script} falló (código: {result['returncode']})")

    # Generar reporte consolidado
    print("\n📊 Generando reporte consolidado...")
    report = generate_consolidated_report(results)

    # Guardar reporte
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"llm_migration_test_report_{timestamp}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"📁 Reporte consolidado guardado en: {report_file}")

    # Mostrar resumen final
    successful_tests = sum(1 for r in results['test_results'] if r['success'])
    total_tests = len(results['test_results'])

    print("\n" + "=" * 70)
    print("📊 RESULTADO FINAL")
    print("=" * 70)
    print(f"Tests ejecutados: {total_tests}")
    print(f"Tests exitosos: {successful_tests}")
    print(f"Tasa de éxito: {successful_tests/total_tests:.1%}")
    print(f"Reporte completo: {report_file}")

    if successful_tests == total_tests:
        print("\n🎉 ¡Todas las pruebas pasaron! Listo para migración.")
    else:
        print("\n⚠️ Algunas pruebas fallaron. Revisa el reporte para detalles.")

if __name__ == "__main__":
    main()