#!/usr/bin/env python3
"""
Script para diagnosticar configuración de GPU en Ollama
"""

import requests
import json
import time

def check_ollama_gpu():
    """Verifica configuración de GPU en Ollama"""
    print("🔍 DIAGNOSTICANDO CONFIGURACIÓN GPU DE OLLAMA")
    print("=" * 50)

    try:
        # Ver modelos disponibles
        print("\n📋 Modelos disponibles:")
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            for model in models:
                name = model.get('name', 'N/A')
                size = model.get('size', 'N/A')
                print(f"   • {name} (tamaño: {size})")
        else:
            print(f"   ❌ Error obteniendo modelos: {response.status_code}")
            return

        # Verificar GPU con una petición de embeddings
        print("\n🎮 Probando uso de GPU con embeddings...")
        start_time = time.time()

        # Hacer una petición de embeddings que debería usar GPU
        embed_response = requests.post('http://localhost:11434/api/embeddings',
                                     json={'model': 'llama2:7b', 'prompt': 'test gpu usage'},
                                     timeout=30)

        end_time = time.time()
        embed_time = end_time - start_time

        if embed_response.status_code == 200:
            result = embed_response.json()
            embedding = result.get('embedding', [])
            print(f"   ✅ Embedding generado en {embed_time:.2f} segundos")
            print(f"   📏 Dimensión del embedding: {len(embedding)}")
        else:
            print(f"   ❌ Error en embeddings: {embed_response.status_code}")
            print(f"   Respuesta: {embed_response.text}")

        # Verificar configuración del sistema
        print("\n💻 Información del sistema:")
        try:
            import psutil
            memory = psutil.virtual_memory()
            print(f"   RAM: {memory.available/(1024**3):.1f}GB disponible de {memory.total/(1024**3):.1f}GB")
            print(f"   CPU: {psutil.cpu_percent(interval=1):.1f}% uso")
        except ImportError:
            print("   psutil no disponible para monitoreo de sistema")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error conectando con Ollama: {e}")
        print("\n💡 Posibles soluciones:")
        print("   1. Asegúrate de que Ollama esté ejecutándose")
        print("   2. Verifica que el modelo llama2:7b esté descargado")
        print("   3. Revisa la configuración de GPU en Ollama")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    check_ollama_gpu()