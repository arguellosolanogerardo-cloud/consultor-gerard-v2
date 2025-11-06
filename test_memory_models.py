#!/usr/bin/env python3
"""
Script para probar diferentes modelos de Ollama y medir uso de memoria
"""
import psutil
import time
import requests
from datetime import datetime

def get_memory_usage():
    """Obtener uso de memoria del sistema"""
    mem = psutil.virtual_memory()
    return {
        'total_gb': round(mem.total / (1024**3), 1),
        'available_gb': round(mem.available / (1024**3), 1),
        'used_percent': mem.percent
    }

def test_model(model_name, prompt="Hola, ¿cómo estás?"):
    """Probar un modelo y medir memoria antes/durante/despues"""
    print(f"\n{'='*50}")
    print(f"Probando modelo: {model_name}")
    print(f"{'='*50}")

    # Memoria antes
    mem_before = get_memory_usage()
    print(f"Memoria antes: {mem_before['available_gb']}GB disponible")

    try:
        # Hacer la petición
        start_time = time.time()
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': model_name,
                'prompt': prompt,
                'stream': False
            },
            timeout=30
        )

        end_time = time.time()
        response_time = end_time - start_time

        if response.status_code == 200:
            result = response.json()
            mem_after = get_memory_usage()

            print(f"✅ Modelo {model_name} funciona correctamente")
            print(f"⏱️  Tiempo de respuesta: {response_time:.2f} segundos")
            print(f"📊 Memoria después: {mem_after['available_gb']}GB disponible")
            print(f"📉 Memoria usada: {mem_before['available_gb'] - mem_after['available_gb']:.1f}GB")
            print(f"📝 Respuesta: {result['response'][:100]}...")

            return True, response_time, mem_before['available_gb'] - mem_after['available_gb']
        else:
            print(f"❌ Error con modelo {model_name}: {response.status_code}")
            return False, None, None

    except Exception as e:
        print(f"❌ Error probando {model_name}: {str(e)}")
        return False, None, None

def main():
    print("🔍 Probador de Modelos Ollama - Uso de Memoria")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Verificar que Ollama esté corriendo
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code != 200:
            print("❌ Ollama no está disponible. Inicia el servidor primero.")
            return
    except:
        print("❌ No se puede conectar a Ollama. ¿Está corriendo?")
        return

    # Obtener lista de modelos disponibles
    try:
        response = requests.get('http://localhost:11434/api/tags')
        models = [model['name'] for model in response.json()['models']]
        print(f"🤖 Modelos disponibles: {', '.join(models)}")
    except:
        print("❌ Error obteniendo lista de modelos")
        return

    # Modelos a probar (priorizando los más pequeños primero)
    test_models = [
        'llama2:7b',      # 7B parámetros - más eficiente
        'mixtral:8x7b',   # 7B parámetros - versión más pequeña de Mixtral
        'mixtral:8x22b'   # 22B parámetros - el actual
    ]

    results = []

    for model in test_models:
        if model in models:
            success, response_time, mem_used = test_model(model)
            if success:
                results.append({
                    'model': model,
                    'time': response_time,
                    'mem_used': mem_used
                })
        else:
            print(f"⚠️  Modelo {model} no está disponible")

    # Resumen
    print(f"\n{'='*50}")
    print("📊 RESUMEN DE RESULTADOS")
    print(f"{'='*50}")

    if results:
        print("Modelo\t\tTiempo(s)\tMemoria(GB)")
        print("-" * 40)
        for result in results:
            print(f"{result['model']}\t\t{result['time']:.2f}\t\t{result['mem_used']:.1f}")
    else:
        print("❌ No se pudieron probar modelos exitosamente")

if __name__ == "__main__":
    main()