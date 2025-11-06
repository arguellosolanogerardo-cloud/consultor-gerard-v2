# -*- coding: utf-8 -*-
"""
Script de pruebas de carga y estrés para LLMs
Mide rendimiento bajo diferentes condiciones de carga
"""

import os
import sys
import time
import asyncio
import threading
import concurrent.futures
from typing import Dict, List, Any
from datetime import datetime
import statistics
import matplotlib.pyplot as plt
import seaborn as sns

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

class LoadTester:
    """Clase para pruebas de carga de LLMs"""

    def __init__(self):
        self.models = {}
        self._initialize_models()

    def _initialize_models(self):
        """Inicializa modelos para pruebas de carga"""

        # Claude 3.5 Sonnet (reemplazo principal)
        if CLAUDE_AVAILABLE:
            try:
                self.models['claude-3.5-sonnet'] = ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    temperature=0.0,
                    max_tokens=2048,  # Reducido para pruebas de carga
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
                    max_tokens=2048,
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
                    num_ctx=2048
                )
                print("✓ Ollama Llama2 inicializado")
            except Exception as e:
                print(f"✗ Error inicializando Ollama: {e}")

    def single_request_test(self, model_name: str, prompt: str, num_requests: int = 10) -> Dict[str, Any]:
        """Prueba de múltiples solicitudes secuenciales"""

        if model_name not in self.models:
            return {'error': f'Modelo {model_name} no disponible'}

        model = self.models[model_name]
        latencies = []
        errors = []

        print(f"🔄 Probando {num_requests} solicitudes secuenciales con {model_name}...")

        for i in range(num_requests):
            start_time = time.time()
            try:
                response = model.invoke(prompt)
                latency = time.time() - start_time
                latencies.append(latency)
                print(f"  {i+1}/{num_requests}: {latency:.3f}s")
            except Exception as e:
                latency = time.time() - start_time
                latencies.append(latency)
                errors.append(str(e))
                print(f"  {i+1}/{num_requests}: ERROR - {latency:.3f}s - {e}")

        return {
            'model': model_name,
            'test_type': 'sequential',
            'num_requests': num_requests,
            'latencies': latencies,
            'errors': errors,
            'success_rate': (num_requests - len(errors)) / num_requests,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'p95_latency': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        }

    def concurrent_request_test(self, model_name: str, prompt: str, num_concurrent: int = 5, num_requests: int = 20) -> Dict[str, Any]:
        """Prueba de solicitudes concurrentes"""

        if model_name not in self.models:
            return {'error': f'Modelo {model_name} no disponible'}

        model = self.models[model_name]
        latencies = []
        errors = []

        print(f"🔄 Probando {num_requests} solicitudes concurrentes ({num_concurrent} simultáneas) con {model_name}...")

        def single_request(request_id: int):
            start_time = time.time()
            try:
                response = model.invoke(prompt)
                latency = time.time() - start_time
                return {'latency': latency, 'error': None, 'id': request_id}
            except Exception as e:
                latency = time.time() - start_time
                return {'latency': latency, 'error': str(e), 'id': request_id}

        # Ejecutar solicitudes concurrentes
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(single_request, i) for i in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Procesar resultados
        for result in sorted(results, key=lambda x: x['id']):
            latencies.append(result['latency'])
            if result['error']:
                errors.append(result['error'])
            print(f"  {result['id']+1}/{num_requests}: {result['latency']:.3f}s {'ERROR' if result['error'] else ''}")

        return {
            'model': model_name,
            'test_type': 'concurrent',
            'num_concurrent': num_concurrent,
            'num_requests': num_requests,
            'latencies': latencies,
            'errors': errors,
            'success_rate': (num_requests - len(errors)) / num_requests,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'p95_latency': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        }

    def stress_test(self, model_name: str, prompts: List[str], duration_seconds: int = 60) -> Dict[str, Any]:
        """Prueba de estrés durante un período de tiempo"""

        if model_name not in self.models:
            return {'error': f'Modelo {model_name} no disponible'}

        model = self.models[model_name]
        latencies = []
        errors = []
        requests_completed = 0

        print(f"🔄 Prueba de estrés con {model_name} durante {duration_seconds}s...")

        start_time = time.time()
        end_time = start_time + duration_seconds

        while time.time() < end_time:
            prompt = prompts[requests_completed % len(prompts)]
            request_start = time.time()

            try:
                response = model.invoke(prompt)
                latency = time.time() - request_start
                latencies.append(latency)
                requests_completed += 1
                print(f"  ✅ {requests_completed}: {latency:.3f}s")
            except Exception as e:
                latency = time.time() - request_start
                latencies.append(latency)
                errors.append(str(e))
                requests_completed += 1
                print(f"  ❌ {requests_completed}: {latency:.3f}s - {e}")

        actual_duration = time.time() - start_time

        return {
            'model': model_name,
            'test_type': 'stress',
            'duration_target': duration_seconds,
            'duration_actual': actual_duration,
            'requests_completed': requests_completed,
            'requests_per_second': requests_completed / actual_duration,
            'latencies': latencies,
            'errors': errors,
            'success_rate': (requests_completed - len(errors)) / requests_completed if requests_completed > 0 else 0,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'min_latency': min(latencies) if latencies else 0,
            'max_latency': max(latencies) if latencies else 0,
            'std_latency': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'p95_latency': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        }

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Ejecuta pruebas completas de carga"""

        # Prompts de prueba variados
        test_prompts = [
            "¿Qué dice Gerard sobre el amor?",
            "Cita exactamente lo que dice Gerard sobre la sanación espiritual",
            "Explica el concepto de vibración energética según Gerard",
            "¿Cómo se manifiesta el amor divino en la vida cotidiana?",
            "Describe la importancia de la evacuación espiritual"
        ]

        results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }

        # Prueba secuencial
        print("\n📊 PRUEBA SECUENCIAL")
        results['tests']['sequential'] = {}
        for model_name in self.models.keys():
            results['tests']['sequential'][model_name] = self.single_request_test(
                model_name, test_prompts[0], num_requests=5
            )

        # Prueba concurrente
        print("\n📊 PRUEBA CONCURRENTE")
        results['tests']['concurrent'] = {}
        for model_name in self.models.keys():
            results['tests']['concurrent'][model_name] = self.concurrent_request_test(
                model_name, test_prompts[0], num_concurrent=3, num_requests=9
            )

        # Prueba de estrés (solo modelos cloud para no sobrecargar Ollama)
        print("\n📊 PRUEBA DE ESTRÉS")
        results['tests']['stress'] = {}
        cloud_models = [m for m in self.models.keys() if 'ollama' not in m]
        for model_name in cloud_models:
            results['tests']['stress'][model_name] = self.stress_test(
                model_name, test_prompts, duration_seconds=30
            )

        return results

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Genera un reporte detallado de las pruebas"""

        report = []
        report.append("# REPORTE DE PRUEBAS DE CARGA Y ESTRÉS DE LLMs")
        report.append(f"**Fecha:** {results['timestamp']}")
        report.append("")

        for test_type, test_results in results['tests'].items():
            report.append(f"## {test_type.upper()}")
            report.append("")

            for model_name, model_results in test_results.items():
                if 'error' in model_results:
                    report.append(f"### {model_name}")
                    report.append(f"❌ Error: {model_results['error']}")
                    report.append("")
                    continue

                report.append(f"### {model_name}")
                report.append(f"- **Tasa de éxito:** {model_results['success_rate']:.1%}")
                report.append(f"- **Latencia promedio:** {model_results['avg_latency']:.3f}s")
                report.append(f"- **Latencia mínima:** {model_results['min_latency']:.3f}s")
                report.append(f"- **Latencia máxima:** {model_results['max_latency']:.3f}s")
                report.append(f"- **Latencia P95:** {model_results['p95_latency']:.3f}s")
                report.append(f"- **Desviación estándar:** {model_results['std_latency']:.3f}s")

                if 'requests_per_second' in model_results:
                    report.append(f"- **Solicitudes/segundo:** {model_results['requests_per_second']:.2f}")

                if model_results['errors']:
                    report.append(f"- **Errores:** {len(model_results['errors'])}")
                    report.append("  - " + "\n  - ".join(model_results['errors'][:3]))  # Primeros 3 errores

                report.append("")

        return "\n".join(report)

def main():
    """Función principal"""

    print("🚀 Iniciando pruebas de carga y estrés de LLMs")
    print("=" * 60)

    tester = LoadTester()

    if not tester.models:
        print("❌ No se pudieron inicializar modelos. Verifica las dependencias y claves API.")
        return

    # Ejecutar pruebas completas
    print("Ejecutando pruebas completas...")
    results = tester.run_comprehensive_test()

    # Generar y guardar reporte
    report = tester.generate_report(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"llm_load_test_report_{timestamp}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📁 Reporte guardado en: {report_file}")

    # Mostrar resumen ejecutivo
    print("\n📊 RESUMEN EJECUTIVO")
    print("=" * 60)

    for test_type, test_results in results['tests'].items():
        print(f"\n{test_type.upper()}:")
        for model_name, model_results in test_results.items():
            if 'error' not in model_results:
                success_rate = model_results['success_rate']
                avg_latency = model_results['avg_latency']
                print(f"  {model_name}: {success_rate:.1%} éxito, {avg_latency:.3f}s promedio")

if __name__ == "__main__":
    main()