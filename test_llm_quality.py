# -*- coding: utf-8 -*-
"""
Script de pruebas de calidad y coherencia de respuestas
Evalúa la calidad de las respuestas de diferentes LLMs
"""

import os
import sys
import re
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
from collections import defaultdict

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

class QualityEvaluator:
    """Clase para evaluar calidad de respuestas de LLMs"""

    def __init__(self):
        self.models = {}
        self._initialize_models()

    def _initialize_models(self):
        """Inicializa modelos para evaluación de calidad"""

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

    def evaluate_response_quality(self, response: str, criteria: Dict[str, Any]) -> Dict[str, float]:
        """Evalúa la calidad de una respuesta según criterios específicos"""

        scores = {}

        # 1. Verificar formato de citas SRT
        if 'require_srt_citation' in criteria and criteria['require_srt_citation']:
            citation_pattern = r'\(Fuente:\s*[^,]+,\s*Timestamp:\s*[^)]+\)'
            citations = re.findall(citation_pattern, response)
            scores['citation_format'] = min(len(citations) / max(1, criteria.get('expected_citations', 1)), 1.0)

        # 2. Verificar idioma español
        if 'require_spanish' in criteria and criteria['require_spanish']:
            spanish_words = len(re.findall(r'\b(el|la|los|las|un|una|es|son|está|están|ser|estar|hacer|ir|ver|dar|saber|querer|llegar|pasar|deber|poner|parecer|quedar|creer|haber|vivir|sentir|traer|caer|valer|dar|ver|saber|querer|venir|salir|poner|tener|venir|hacer|poder|decir|ir|ser|estar|tener|hacer|poder|decir|ir|ser|estar)\b', response.lower()))
            total_words = len(response.split())
            scores['spanish_language'] = spanish_words / max(1, total_words)

        # 3. Verificar ausencia de información inventada
        if 'check_no_hallucination' in criteria and criteria['check_no_hallucination']:
            hallucination_indicators = [
                'según mi conocimiento', 'creo que', 'pienso que', 'probablemente',
                'en mi opinión', 'generalmente', 'normalmente', 'típicamente',
                'usualmente', 'comúnmente', 'habitualmente'
            ]
            hallucination_score = 0
            for indicator in hallucination_indicators:
                if indicator.lower() in response.lower():
                    hallucination_score += 0.2
            scores['no_hallucination'] = max(0, 1.0 - hallucination_score)

        # 4. Verificar longitud apropiada
        if 'max_length' in criteria:
            word_count = len(response.split())
            if word_count <= criteria['max_length']:
                scores['appropriate_length'] = 1.0
            else:
                scores['appropriate_length'] = criteria['max_length'] / word_count

        # 5. Verificar coherencia temática
        if 'required_keywords' in criteria:
            found_keywords = 0
            for keyword in criteria['required_keywords']:
                if keyword.lower() in response.lower():
                    found_keywords += 1
            scores['thematic_coherence'] = found_keywords / len(criteria['required_keywords'])

        # 6. Verificar timestamps únicos (no rangos)
        if 'require_single_timestamps' in criteria and criteria['require_single_timestamps']:
            timestamp_pattern = r'Timestamp:\s*(\d+:\d+:\d+)'
            timestamps = re.findall(timestamp_pattern, response)
            # Verificar que no hay rangos (contienen guiones)
            single_timestamps = [t for t in timestamps if '-' not in t]
            scores['single_timestamps'] = len(single_timestamps) / max(1, len(timestamps))

        return scores

    def compare_responses(self, prompt: str, criteria: Dict[str, Any], num_runs: int = 3) -> Dict[str, Any]:
        """Compara respuestas de diferentes modelos"""

        results = {
            'prompt': prompt,
            'criteria': criteria,
            'runs': num_runs,
            'model_responses': {}
        }

        for model_name, model in self.models.items():
            print(f"🤖 Evaluando {model_name}...")
            model_results = []

            for run in range(num_runs):
                try:
                    response = model.invoke(prompt)
                    response_text = response.content if hasattr(response, 'content') else str(response)

                    quality_scores = self.evaluate_response_quality(response_text, criteria)

                    run_result = {
                        'run': run + 1,
                        'response': response_text,
                        'quality_scores': quality_scores,
                        'overall_score': sum(quality_scores.values()) / len(quality_scores) if quality_scores else 0
                    }

                    model_results.append(run_result)
                    print(f"  Run {run + 1}: Score {run_result['overall_score']:.3f}")

                except Exception as e:
                    run_result = {
                        'run': run + 1,
                        'response': None,
                        'error': str(e),
                        'quality_scores': {},
                        'overall_score': 0
                    }
                    model_results.append(run_result)
                    print(f"  Run {run + 1}: ERROR - {e}")

            # Calcular estadísticas del modelo
            successful_runs = [r for r in model_results if r['response'] is not None]
            if successful_runs:
                overall_scores = [r['overall_score'] for r in successful_runs]
                avg_score = sum(overall_scores) / len(overall_scores)
                consistency = 1.0 - (max(overall_scores) - min(overall_scores))  # Menor varianza = mayor consistencia

                results['model_responses'][model_name] = {
                    'runs': model_results,
                    'successful_runs': len(successful_runs),
                    'success_rate': len(successful_runs) / num_runs,
                    'avg_overall_score': avg_score,
                    'score_consistency': consistency,
                    'best_response': max(successful_runs, key=lambda x: x['overall_score'])['response'],
                    'worst_response': min(successful_runs, key=lambda x: x['overall_score'])['response']
                }
            else:
                results['model_responses'][model_name] = {
                    'runs': model_results,
                    'successful_runs': 0,
                    'success_rate': 0,
                    'avg_overall_score': 0,
                    'score_consistency': 0,
                    'best_response': None,
                    'worst_response': None
                }

        return results

    def run_quality_tests(self) -> Dict[str, Any]:
        """Ejecuta pruebas completas de calidad"""

        # Definir criterios de evaluación para Gerard
        gerard_criteria = {
            'require_srt_citation': True,
            'expected_citations': 2,
            'require_spanish': True,
            'check_no_hallucination': True,
            'max_length': 1000,
            'require_single_timestamps': True,
            'required_keywords': ['amor', 'sanación', 'espiritual']
        }

        # Prompts de prueba representativos
        test_prompts = [
            {
                'name': 'consulta_amor',
                'prompt': """Responde como Gerard, citando únicamente de fuentes SRT con formato exacto:
(Fuente: [título], Timestamp: [tiempo])
¿Que dice Gerard sobre el amor?""",
                'criteria': gerard_criteria
            },
            {
                'name': 'consulta_sanacion',
                'prompt': """Responde como Gerard, citando únicamente de fuentes SRT con formato exacto:
(Fuente: [título], Timestamp: [tiempo])
¿Que dice Gerard sobre la sanación espiritual?""",
                'criteria': gerard_criteria
            },
            {
                'name': 'consulta_timestamp',
                'prompt': """Responde como Gerard, citando únicamente de fuentes SRT con formato exacto:
(Fuente: [título], Timestamp: [tiempo])
Encuentra una cita específica sobre evacuación con timestamp único.""",
                'criteria': {**gerard_criteria, 'required_keywords': ['evacuación', 'espiritual']}
            }
        ]

        all_results = {
            'timestamp': datetime.now().isoformat(),
            'test_suite': 'gerard_response_quality',
            'tests': []
        }

        for test_case in test_prompts:
            print(f"\n🧪 Ejecutando prueba: {test_case['name']}")
            result = self.compare_responses(
                test_case['prompt'],
                test_case['criteria'],
                num_runs=2  # Reducido para pruebas más rápidas
            )
            result['test_name'] = test_case['name']
            all_results['tests'].append(result)

        return all_results

    def generate_quality_report(self, results: Dict[str, Any]) -> str:
        """Genera reporte de calidad"""

        report = []
        report.append("# REPORTE DE CALIDAD DE RESPUESTAS DE LLMs")
        report.append(f"**Fecha:** {results['timestamp']}")
        report.append(f"**Suite de pruebas:** {results['test_suite']}")
        report.append("")

        # Resumen general
        all_scores = []
        model_summary = defaultdict(list)

        for test in results['tests']:
            for model_name, model_data in test['model_responses'].items():
                if model_data['successful_runs'] > 0:
                    all_scores.append(model_data['avg_overall_score'])
                    model_summary[model_name].append(model_data['avg_overall_score'])

        if all_scores:
            report.append("## RESUMEN GENERAL")
            report.append(f"- **Total de pruebas:** {len(results['tests'])}")
            report.append(f"- **Puntuación promedio global:** {sum(all_scores)/len(all_scores):.3f}")
            report.append("")

        # Resultados por modelo
        report.append("## RESULTADOS POR MODELO")
        report.append("")

        for model_name in sorted(model_summary.keys()):
            scores = model_summary[model_name]
            avg_score = sum(scores) / len(scores)
            success_rate = len([s for s in scores if s > 0]) / len(scores)

            report.append(f"### {model_name}")
            report.append(f"- **Puntuación promedio:** {avg_score:.3f}")
            report.append(f"- **Tasa de éxito:** {success_rate:.1%}")
            report.append(f"- **Consistencia:** {1.0 - (max(scores) - min(scores)):.3f}")
            report.append("")

        # Detalles por prueba
        for test in results['tests']:
            report.append(f"## PRUEBA: {test['test_name']}")
            report.append(f"**Prompt:** {test['prompt'][:100]}...")
            report.append("")

            for model_name, model_data in test['model_responses'].items():
                report.append(f"### {model_name}")
                report.append(f"- **Ejecuciones exitosas:** {model_data['successful_runs']}/{len(model_data['runs'])}")
                report.append(f"- **Puntuación promedio:** {model_data['avg_overall_score']:.3f}")
                report.append(f"- **Consistencia:** {model_data['score_consistency']:.3f}")

                if model_data['best_response']:
                    report.append(f"- **Mejor respuesta:** {model_data['best_response'][:200]}...")
                report.append("")

        return "\n".join(report)

def main():
    """Función principal"""

    print("🚀 Iniciando pruebas de calidad y coherencia de LLMs")
    print("=" * 60)

    evaluator = QualityEvaluator()

    if not evaluator.models:
        print("❌ No se pudieron inicializar modelos. Verifica las dependencias y claves API.")
        return

    # Ejecutar pruebas de calidad
    print("Ejecutando pruebas de calidad...")
    results = evaluator.run_quality_tests()

    # Generar y guardar reporte
    report = evaluator.generate_quality_report(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"llm_quality_report_{timestamp}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📁 Reporte guardado en: {report_file}")

    # Mostrar resumen ejecutivo
    print("\n📊 RESUMEN EJECUTIVO DE CALIDAD")
    print("=" * 60)

    for test in results['tests']:
        print(f"\n{test['test_name'].upper()}:")
        for model_name, model_data in test['model_responses'].items():
            if model_data['successful_runs'] > 0:
                score = model_data['avg_overall_score']
                print(f"  {model_name}: {score:.3f} ({model_data['successful_runs']}/{len(model_data['runs'])} exitosas)")

if __name__ == "__main__":
    main()