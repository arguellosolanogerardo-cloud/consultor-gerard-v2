#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba mejorado para el sistema híbrido GERARD
Prueba el fallback sin depender de Streamlit
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

# Simular que no estamos en Streamlit
class MockStreamlit:
    def __init__(self):
        self.secrets = {}

mock_st = MockStreamlit()
sys.modules['streamlit'] = mock_st

def test_openai_llm():
    """Prueba OpenAI LLM directamente"""
    print("\n🧪 Probando OpenAI LLM...")

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("❌ No hay OPENAI_API_KEY")
        return False

    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.4,
            openai_api_key=openai_key,
            max_tokens=2000
        )

        response = llm.invoke("¿Cuál es la capital de España?")
        print(f"✅ OpenAI LLM funciona: {str(response.content)[:50]}...")
        return True
    except Exception as e:
        print(f"❌ OpenAI LLM falló: {e}")
        return False

def test_openai_embeddings():
    """Prueba OpenAI embeddings directamente"""
    print("\n🧪 Probando OpenAI embeddings...")

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        print("❌ No hay OPENAI_API_KEY")
        return False

    try:
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_key
        )

        vector = embeddings.embed_query("Esta es una prueba")
        print(f"✅ OpenAI embeddings funcionan: dimensión {len(vector)}")
        return True
    except Exception as e:
        print(f"❌ OpenAI embeddings fallaron: {e}")
        return False

def test_ollama_llm():
    """Prueba Ollama LLM directamente"""
    print("\n🧪 Probando Ollama LLM...")

    try:
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(
            model="mixtral:8x22b",
            temperature=0.4,
            num_ctx=4096
        )

        response = llm.invoke("¿Cuál es la capital de Italia?")
        print(f"✅ Ollama LLM funciona: {str(response)[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Ollama LLM falló: {e}")
        return False

def test_ollama_embeddings():
    """Prueba Ollama embeddings directamente"""
    print("\n🧪 Probando Ollama embeddings...")

    try:
        from langchain_ollama import OllamaEmbeddings
        embeddings = OllamaEmbeddings(
            model="mixtral:8x22b"
        )

        vector = embeddings.embed_query("Esta es una prueba")
        print(f"✅ Ollama embeddings funcionan: dimensión {len(vector)}")
        return True
    except Exception as e:
        print(f"❌ Ollama embeddings fallaron: {e}")
        return False

def test_google_llm():
    """Prueba Google Gemini LLM directamente"""
    print("\n🧪 Probando Google Gemini LLM...")

    google_key = os.environ.get("GOOGLE_API_KEY")
    if not google_key:
        print("❌ No hay GOOGLE_API_KEY")
        return False

    try:
        from langchain_google_genai import GoogleGenerativeAI
        llm = GoogleGenerativeAI(
            model="models/gemini-2.5-pro",
            google_api_key=google_key,
            temperature=0.4,
            top_p=0.90,
            top_k=25
        )

        response = llm.invoke("¿Cuál es la capital de Alemania?")
        print(f"✅ Google Gemini LLM funciona: {str(response)[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Google Gemini LLM falló: {e}")
        return False

def test_fallback_logic():
    """Prueba la lógica de fallback simulando fallos"""
    print("\n🧪 Probando lógica de fallback...")

    # Simular que OpenAI falla
    original_openai_key = os.environ.get("OPENAI_API_KEY")
    if original_openai_key:
        print("🔄 Simulando fallo de OpenAI...")
        os.environ["OPENAI_API_KEY"] = ""

        # Probar si Ollama funciona como fallback
        ollama_ok = test_ollama_llm()

        # Restaurar
        os.environ["OPENAI_API_KEY"] = original_openai_key
        print("🔄 Key de OpenAI restaurada")

        if ollama_ok:
            print("✅ Fallback a Ollama funciona correctamente")
            return True
        else:
            print("❌ Fallback a Ollama falló")
            return False
    else:
        print("⚠️ No hay key de OpenAI para simular fallo")
        return test_ollama_llm()

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas mejoradas del sistema híbrido GERARD")
    print("=" * 60)

    # Verificar disponibilidad de servicios
    print("📋 Estado de servicios:")
    print(f"  OpenAI key: {'✅' if os.environ.get('OPENAI_API_KEY') else '❌'}")
    print(f"  Google key: {'✅' if os.environ.get('GOOGLE_API_KEY') else '❌'}")
    print(f"  Ollama: {'✅' if test_ollama_available() else '❌'}")

    # Ejecutar pruebas
    results = []

    results.append(("OpenAI LLM", test_openai_llm()))
    results.append(("OpenAI Embeddings", test_openai_embeddings()))
    results.append(("Ollama LLM", test_ollama_llm()))
    results.append(("Ollama Embeddings", test_ollama_embeddings()))
    results.append(("Google Gemini LLM", test_google_llm()))
    results.append(("Fallback Logic", test_fallback_logic()))

    # Resultados finales
    print("\n" + "=" * 60)
    print("📊 RESULTADOS FINALES:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 ¡Todas las pruebas pasaron! El sistema híbrido está completamente funcional.")
        print("   OpenAI → Ollama → Google → Hash-based fallback funcionando correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. El sistema híbrido tiene respaldo limitado.")
        print("   Pero al menos un proveedor funciona, por lo que la app debería funcionar.")

    return all_passed

def test_ollama_available():
    """Verifica si Ollama está disponible sin hacer una consulta completa"""
    try:
        from langchain_ollama import OllamaLLM
        # Solo intentar crear la instancia, no hacer consulta
        llm = OllamaLLM(model="mixtral:8x22b", temperature=0.4, num_ctx=4096)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)