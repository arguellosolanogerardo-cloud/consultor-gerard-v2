# -*- coding: utf-8 -*-
"""
Script de pruebas y validación para migración de LLM
Compara salidas entre diferentes proveedores: Gemini, Claude, OpenAI, Ollama
"""

import os
import sys
import time
import json
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd

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

# Importar LLMs disponibles
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from langchain_anthropic import ChatAnthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

class LLMComparator:
    """Clase para comparar diferentes LLMs"""

    def __init__(self):
        self.models = {}
        self._initialize_models()

    def _initialize_models(self):
        """Inicializa todos los modelos disponibles"""

        # Gemini Pro 2.5 (modelo actual)
        if GEMINI_AVAILABLE:
            try:
                self.models['gemini-pro-2.5'] = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-exp",
                    temperature=0.0,
                    max_tokens=4096,
                    google_api_key=os.getenv('GOOGLE_API_KEY')
                )
                print("✓ Gemini Pro 2.5 inicializado")
            except Exception as e:
                print(f"✗ Error inicializando Gemini: {e}")

        # Claude 3.5 Sonnet (reemplazo principal)
        if CLAUDE_AVAILABLE:
            try:
                self.models['claude-3.5-sonnet'] = ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    temperature=0.0,
                    max_tokens=4096,
                    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
                )
                print("✓ Claude 3.5 Sonnet inicializado")
            except Exception as e:
                print(f"✗ Error inicializando Claude: {e}")

        # GPT-4o Mini (reemplazo secundario)
        if OPENAI_AVAILABLE:
            try:
                self.models['gpt-4o-mini'] = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.0,
                    max_tokens=4096,
                    openai_api_key=os.getenv('OPENAI_API_KEY')
                )
                print("✓ GPT-4o Mini inicializado")
            except Exception as e:
                print(f"✗ Error inicializando OpenAI: {e}")

        # Ollama Llama2 (fallback local)
        if OLLAMA_AVAILABLE:
            try:
                self.models['ollama-llama2'] = ChatOllama(
                    model="llama2:7b",
                    temperature=0.0,
                    num_ctx=4096
                )
                print("✓ Ollama Llama2 inicializado")
            except Exception as e:
                print(f"✗ Error inicializando Ollama: {e}")

    def test_prompts(self, prompts: List[str]) -> Dict[str, Any]:
        """Ejecuta pruebas con diferentes prompts"""

        results = {
            'timestamp': datetime.now().isoformat(),
            'models_tested': list(self.models.keys()),
            'prompts': prompts,
            'results': {}
        }

        for prompt_name, prompt in prompts.items():
            print(f"\n🧪 Probando prompt: {prompt_name}")
            results['results'][prompt_name] = {}

            for model_name, model in self.models.items():
                print(f"  🤖 {model_name}...")
                start_time = time.time()

                try:
                    response = model.invoke(prompt)
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    latency = time.time() - start_time

                    results['results'][prompt_name][model_name] = {
                        'success': True,
                        'response': response_text,
                        'latency_seconds': round(latency, 3),
                        'tokens_estimated': len(response_text.split()) * 1.3,  # Estimación simple
                        'error': None
                    }

                    print(f"    ✓ {round(latency, 3)}s - {len(response_text)} chars")

                except Exception as e:
                    latency = time.time() - start_time
                    results['results'][prompt_name][model_name] = {
                        'success': False,
                        'response': None,
                        'latency_seconds': round(latency, 3),
                        'tokens_estimated': 0,
                        'error': str(e)
                    }

                    print(f"    ✗ {round(latency, 3)}s - Error: {e}")

        return results

    def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza los resultados de las pruebas"""

        analysis = {
            'summary': {},
            'performance_comparison': {},
            'reliability_stats': {},
            'recommendations': []
        }

        # Estadísticas por modelo
        for model_name in results['models_tested']:
            model_results = []

            for prompt_name, prompt_results in results['results'].items():
                if model_name in prompt_results:
                    model_results.append(prompt_results[model_name])

            if model_results:
                successful = [r for r in model_results if r['success']]
                failed = [r for r in model_results if not r['success']]

                analysis['summary'][model_name] = {
                    'total_tests': len(model_results),
                    'successful': len(successful),
                    'failed': len(failed),
                    'success_rate': len(successful) / len(model_results) if model_results else 0,
                    'avg_latency': sum(r['latency_seconds'] for r in successful) / len(successful) if successful else 0,
                    'total_tokens': sum(r['tokens_estimated'] for r in successful)
                }

        # Comparación de rendimiento
        if analysis['summary']:
            best_latency = min(analysis['summary'].items(), key=lambda x: x[1]['avg_latency'])
            best_reliability = max(analysis['summary'].items(), key=lambda x: x[1]['success_rate'])

            analysis['performance_comparison'] = {
                'fastest_model': best_latency[0],
                'fastest_latency': best_latency[1]['avg_latency'],
                'most_reliable_model': best_reliability[0],
                'highest_success_rate': best_reliability[1]['success_rate']
            }

        # Recomendaciones
        if 'gemini-pro-2.5' in analysis['summary']:
            gemini_stats = analysis['summary']['gemini-pro-2.5']
            if gemini_stats['success_rate'] < 0.95:
                analysis['recommendations'].append("Considerar migración - Gemini tiene baja tasa de éxito")

        # Recomendar mejor modelo alternativo
        alternatives = {k: v for k, v in analysis['summary'].items() if k != 'gemini-pro-2.5'}
        if alternatives:
            best_alt = max(alternatives.items(),
                          key=lambda x: (x[1]['success_rate'], -x[1]['avg_latency']))
            analysis['recommendations'].append(f"Recomendar {best_alt[0]} como reemplazo principal")

        return analysis

def main():
    """Función principal de pruebas"""

    print("🚀 Iniciando pruebas de comparación de LLMs")
    print("=" * 50)

    comparator = LLMComparator()

    if not comparator.models:
        print("❌ No se pudieron inicializar modelos. Verifica las dependencias y claves API.")
        return

    # Prompts de prueba basados en consultas típicas de Gerard
    test_prompts = {
        'consulta_simple': "¿Qué dice Gerard sobre el amor?",
        'consulta_cita': "Cita exactamente lo que dice Gerard sobre la sanación espiritual",
        'consulta_timestamp': "Encuentra una cita de Gerard con timestamp específico sobre evacuación",
        'consulta_larga': """Responde como Gerard, citando únicamente de fuentes SRT con formato exacto:
        (Fuente: [título], Timestamp: [tiempo])
        Tema: ¿Cómo se manifiesta el amor divino en la vida cotidiana?""",
        'consulta_tecnica': "Explica el concepto de vibración energética según Gerard"
    }

    # Ejecutar pruebas
    print(f"\n📋 Ejecutando {len(test_prompts)} pruebas con {len(comparator.models)} modelos...")
    results = comparator.test_prompts(test_prompts)

    # Analizar resultados
    analysis = comparator.analyze_results(results)

    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"llm_comparison_results_{timestamp}.json"
    analysis_file = f"llm_comparison_analysis_{timestamp}.json"

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # Mostrar resumen
    print("\n📊 RESUMEN DE RESULTADOS")
    print("=" * 50)

    for model, stats in analysis['summary'].items():
        print(f"\n{model.upper()}:")
        print(f"  ✅ Tasa de éxito: {stats['success_rate']:.1%}")
        print(f"  ⏱️  Latencia promedio: {stats['avg_latency']:.3f}s")
        print(f"  📝 Tokens estimados: {stats['total_tokens']:.0f}")

    if analysis['performance_comparison']:
        pc = analysis['performance_comparison']
        print("
🏆 COMPARACIÓN:"        print(f"  Más rápido: {pc['fastest_model']} ({pc['fastest_latency']:.3f}s)")
        print(f"  Más confiable: {pc['most_reliable_model']} ({pc['highest_success_rate']:.1%})")

    if analysis['recommendations']:
        print("
💡 RECOMENDACIONES:"        for rec in analysis['recommendations']:
            print(f"  • {rec}")

    print(f"\n📁 Resultados guardados en: {results_file}")
    print(f"📁 Análisis guardado en: {analysis_file}")

if __name__ == "__main__":
    main()