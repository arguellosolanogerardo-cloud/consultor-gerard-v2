# -*- coding: utf-8 -*-
"""
Script de validación de integración para la nueva función get_llm_with_fallback
Prueba la integración completa con Claude, OpenAI y Ollama
"""

import os
import sys
import time
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

from dotenv import load_dotenv
load_dotenv()

def test_fallback_function():
    """Prueba la función get_llm_with_fallback actualizada"""

    print("🔧 Probando función get_llm_with_fallback actualizada...")

    # Importar la función desde consultar_web.py
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from consultar_web import get_llm_with_runtime_fallback
        print("✅ Función importada correctamente")
    except ImportError as e:
        print(f"❌ Error importando función: {e}")
        return False

    # Obtener el LLM con fallback
    try:
        llm_fallback = get_llm_with_runtime_fallback()
        print("✅ LLM con fallback obtenido correctamente")
        print(f"   Tipo: {type(llm_fallback).__name__}")
    except Exception as e:
        print(f"❌ Error obteniendo LLM: {e}")
        return False

    # Probar una consulta simple
    test_prompt = "¿Qué dice Gerard sobre el amor?"
    print(f"\n🧪 Probando consulta: '{test_prompt}'")

    try:
        start_time = time.time()
        response = llm_fallback.invoke(test_prompt)
        latency = time.time() - start_time

        response_text = response.content if hasattr(response, 'content') else str(response)
        print("✅ Respuesta obtenida correctamente")
        print(".3f")
        print(f"   Longitud respuesta: {len(response_text)} caracteres")
        print(f"   Primeros 100 chars: {response_text[:100]}...")

        return True

    except Exception as e:
        print(f"❌ Error en consulta de prueba: {e}")
        return False

def test_individual_providers():
    """Prueba cada proveedor individualmente"""

    print("\n🔧 Probando proveedores individuales...")

    results = {}

    # Probar Claude
    try:
        from langchain_anthropic import ChatAnthropic
        claude = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0.0,
            max_tokens=100,
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        response = claude.invoke("Hola")
        results['claude'] = {'success': True, 'response': response.content[:50]}
        print("✅ Claude: OK")
    except Exception as e:
        results['claude'] = {'success': False, 'error': str(e)}
        print(f"❌ Claude: {e}")

    # Probar OpenAI
    try:
        from langchain_openai import ChatOpenAI
        openai = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=100,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        response = openai.invoke("Hola")
        results['openai'] = {'success': True, 'response': response.content[:50]}
        print("✅ OpenAI: OK")
    except Exception as e:
        results['openai'] = {'success': False, 'error': str(e)}
        print(f"❌ OpenAI: {e}")

    # Probar Ollama
    try:
        from langchain_ollama import ChatOllama
        ollama = ChatOllama(
            model="llama2:7b",
            temperature=0.0,
            num_ctx=100
        )
        response = ollama.invoke("Hola")
        response_text = response.content if hasattr(response, 'content') else str(response)
        results['ollama'] = {'success': True, 'response': response_text[:50]}
        print("✅ Ollama: OK")
    except Exception as e:
        results['ollama'] = {'success': False, 'error': str(e)}
        print(f"❌ Ollama: {e}")

    return results

def test_fallback_scenarios():
    """Prueba escenarios de fallback"""

    print("\n🔧 Probando escenarios de fallback...")

    # Simular fallo de API configurando claves inválidas temporalmente
    original_anthropic = os.environ.get('ANTHROPIC_API_KEY')
    original_openai = os.environ.get('OPENAI_API_KEY')

    try:
        # Forzar fallo de Claude configurando clave inválida
        os.environ['ANTHROPIC_API_KEY'] = 'invalid_key'
        print("🧪 Probando fallback desde Claude fallido...")

        from consultar_web import get_llm_with_runtime_fallback
        llm_fallback = get_llm_with_runtime_fallback()

        response = llm_fallback.invoke("Test fallback")
        response_text = response.content if hasattr(response, 'content') else str(response)
        print("✅ Fallback funcionó correctamente")
        print(f"   Respuesta: {response_text[:50]}...")

        return True

    except Exception as e:
        print(f"❌ Error en fallback: {e}")
        return False

    finally:
        # Restaurar claves originales
        if original_anthropic:
            os.environ['ANTHROPIC_API_KEY'] = original_anthropic
        if original_openai:
            os.environ['OPENAI_API_KEY'] = original_openai

def generate_integration_report(results: Dict[str, Any]) -> str:
    """Genera reporte de integración"""

    report = []
    report.append("# REPORTE DE VALIDACIÓN DE INTEGRACIÓN")
    report.append(f"**Fecha:** {results['timestamp']}")
    report.append("")

    # Función de fallback
    report.append("## FUNCIÓN GET_LLM_WITH_FALLBACK")
    status = "✅" if results['fallback_function_test'] else "❌"
    report.append(f"{status} **Estado:** {'Exitosa' if results['fallback_function_test'] else 'Fallida'}")
    report.append("")

    # Proveedores individuales
    report.append("## PROVEEDORES INDIVIDUALES")
    for provider, data in results['individual_providers'].items():
        status = "✅" if data['success'] else "❌"
        report.append(f"### {provider.upper()}")
        report.append(f"{status} **Estado:** {'OK' if data['success'] else 'Error'}")
        if data['success']:
            report.append(f"**Respuesta de prueba:** {data['response']}")
        else:
            report.append(f"**Error:** {data['error']}")
        report.append("")

    # Escenarios de fallback
    report.append("## ESCENARIOS DE FALLBACK")
    status = "✅" if results['fallback_scenarios_test'] else "❌"
    report.append(f"{status} **Estado:** {'Exitosa' if results['fallback_scenarios_test'] else 'Fallida'}")
    report.append("")

    # Recomendaciones
    report.append("## RECOMENDACIONES")
    if all(results['individual_providers'][p]['success'] for p in results['individual_providers']):
        report.append("✅ **Todos los proveedores funcionan correctamente.**")
        report.append("La migración puede proceder con confianza.")
    else:
        report.append("⚠️ **Algunos proveedores fallaron.**")
        failed_providers = [p for p, d in results['individual_providers'].items() if not d['success']]
        report.append(f"Proveedores con problemas: {', '.join(failed_providers)}")
        report.append("Verificar configuración de APIs y cuotas.")

    return "\n".join(report)

def main():
    """Función principal"""

    print("🚀 VALIDACIÓN DE INTEGRACIÓN DE LLM MIGRATION")
    print("=" * 60)

    results = {
        'timestamp': datetime.now().isoformat(),
        'fallback_function_test': False,
        'individual_providers': {},
        'fallback_scenarios_test': False
    }

    # Test 1: Función de fallback
    results['fallback_function_test'] = test_fallback_function()

    # Test 2: Proveedores individuales
    results['individual_providers'] = test_individual_providers()

    # Test 3: Escenarios de fallback
    results['fallback_scenarios_test'] = test_fallback_scenarios()

    # Generar reporte
    report = generate_integration_report(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"llm_integration_validation_{timestamp}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📁 Reporte guardado en: {report_file}")

    # Resumen final
    all_passed = (
        results['fallback_function_test'] and
        results['fallback_scenarios_test'] and
        all(results['individual_providers'][p]['success'] for p in results['individual_providers'])
    )

    print("\n" + "=" * 60)
    print("📊 RESULTADO DE INTEGRACIÓN")
    print("=" * 60)
    print(f"Función fallback: {'✅' if results['fallback_function_test'] else '❌'}")
    print(f"Proveedores individuales: {'✅' if all(results['individual_providers'][p]['success'] for p in results['individual_providers']) else '❌'}")
    print(f"Escenarios de fallback: {'✅' if results['fallback_scenarios_test'] else '❌'}")

    if all_passed:
        print("\n🎉 ¡INTEGRACIÓN EXITOSA! Listo para migración.")
    else:
        print("\n⚠️ Problemas de integración detectados. Revisar configuración.")

if __name__ == "__main__":
    main()