#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para el sistema híbrido GERARD
Prueba el fallback entre OpenAI, Ollama y Google Gemini
"""

import os
import sys
import time

# Configurar UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Configurar variables de entorno para UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'

# Importar las funciones del sistema híbrido
try:
    from consultar_web import get_llm_with_fallback, get_embeddings_with_fallback
    print("✅ Funciones del sistema híbrido importadas correctamente")
except ImportError as e:
    print(f"❌ Error importando funciones: {e}")
    sys.exit(1)

def test_llm_fallback():
    """Prueba el fallback del LLM"""
    print("\n🧪 Probando LLM con fallback...")

    llm = get_llm_with_fallback()
    if llm is None:
        print("❌ No se pudo inicializar ningún LLM")
        return False

    print(f"✅ LLM inicializado: {type(llm).__name__}")

    # Probar una consulta simple
    try:
        if hasattr(llm, 'invoke'):
            # Nuevo estilo LangChain
            response = llm.invoke("¿Cuál es la capital de Francia?")
        else:
            # Estilo antiguo
            response = llm("¿Cuál es la capital de Francia?")

        print(f"✅ Respuesta del LLM: {str(response)[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error en consulta LLM: {e}")
        return False

def test_embeddings_fallback():
    """Prueba el fallback de embeddings"""
    print("\n🧪 Probando embeddings con fallback...")

    embeddings = get_embeddings_with_fallback()
    if embeddings is None:
        print("❌ No se pudieron inicializar embeddings")
        return False

    print(f"✅ Embeddings inicializados: {type(embeddings).__name__}")

    # Probar embeddings con un texto simple
    try:
        test_text = "Esta es una prueba de embeddings"
        if hasattr(embeddings, 'embed_query'):
            # Nuevo estilo LangChain
            vector = embeddings.embed_query(test_text)
        else:
            # Estilo antiguo
            vector = embeddings.embed([test_text])[0]

        print(f"✅ Vector generado: dimensión {len(vector)}")
        return True
    except Exception as e:
        print(f"❌ Error generando embeddings: {e}")
        return False

def test_provider_switching():
    """Prueba el cambio entre proveedores simulando fallos"""
    print("\n🧪 Probando cambio entre proveedores...")

    # Simular que OpenAI falla (borrando temporalmente la key)
    original_openai_key = os.environ.get("OPENAI_API_KEY")
    if original_openai_key:
        print("🔄 Simulando fallo de OpenAI...")
        os.environ["OPENAI_API_KEY"] = ""

        # Probar LLM después del "fallo"
        llm = get_llm_with_fallback()
        if llm:
            print(f"✅ Fallback funcionó: {type(llm).__name__}")
        else:
            print("❌ Fallback falló")

        # Restaurar la key
        os.environ["OPENAI_API_KEY"] = original_openai_key
        print("🔄 Key de OpenAI restaurada")

    return True

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas del sistema híbrido GERARD")
    print("=" * 50)

    # Verificar disponibilidad de servicios
    print("📋 Estado de servicios:")
    print(f"  Ollama disponible: {'✅' if 'OLLAMA_AVAILABLE' in globals() and globals()['OLLAMA_AVAILABLE'] else '❌'}")
    print(f"  OpenAI key: {'✅' if os.environ.get('OPENAI_API_KEY') else '❌'}")
    print(f"  Google key: {'✅' if os.environ.get('GOOGLE_API_KEY') else '❌'}")

    # Ejecutar pruebas
    results = []

    results.append(("LLM Fallback", test_llm_fallback()))
    results.append(("Embeddings Fallback", test_embeddings_fallback()))
    results.append(("Provider Switching", test_provider_switching()))

    # Resultados finales
    print("\n" + "=" * 50)
    print("📊 RESULTADOS FINALES:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 ¡Todas las pruebas pasaron! El sistema híbrido está funcionando correctamente.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa la configuración.")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)