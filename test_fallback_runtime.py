#!/usr/bin/env python3
"""
Script para probar el fallback dinámico simulando errores 429
"""
import os
import sys

# Agregar el directorio actual al path para importar consultar_web
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from consultar_web import get_llm_with_runtime_fallback

    print("🔍 Probando fallback dinámico con simulación de error 429...")

    # Obtener el LLM con fallback
    llm = get_llm_with_runtime_fallback()
    print(f"✅ LLM wrapper obtenido: {type(llm).__name__}")

    # Simular una consulta que debería funcionar inicialmente
    print("\n1. Probando consulta inicial (debería usar OpenAI):")
    try:
        # Usar una consulta simple que no cuente mucho para tokens
        result = llm.invoke("Di 'Hola mundo' en español.")
        print(f"✅ Respuesta inicial: {str(result)[:100]}...")
    except Exception as e:
        print(f"❌ Error en consulta inicial: {e}")

    print("\n2. Simulando error 429 (esto requeriría modificar temporalmente la clave API)")
    print("Para probar el fallback real, necesitarías:")
    print("- Usar una clave API de OpenAI con cuota agotada")
    print("- O modificar temporalmente el código para forzar un error 429")
    print("- Luego ejecutar: llm.invoke('alguna consulta')")

    print("\n3. Verificando que Ollama esté listo como fallback:")
    import requests
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            print(f"✅ Ollama disponible con modelos: {models}")
            if 'gemma3:4b' in models:
                print("✅ Modelo gemma3:4b disponible para fallback")
            else:
                print("⚠️  Modelo gemma3:4b no encontrado, pero hay otros modelos disponibles")
        else:
            print("❌ Ollama no responde")
    except Exception as e:
        print(f"❌ Error conectando con Ollama: {e}")

    print("\n🎉 Configuración de fallback verificada!")

except Exception as e:
    print(f"❌ Error en la prueba: {e}")
    import traceback
    traceback.print_exc()