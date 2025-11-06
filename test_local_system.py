#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE PRUEBA - SISTEMA 100% LOCAL
Verifica que todo funciona correctamente sin APIs externas
"""

import os
import sys
import requests
import time

def test_ollama_service():
    """Verificar que Ollama está ejecutándose"""
    print("🔍 Verificando servicio Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama está ejecutándose correctamente")
            return True
        else:
            print(f"❌ Ollama respondió con código: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ No se puede conectar con Ollama: {e}")
        return False

def test_llm_initialization():
    """Verificar que el LLM se inicializa correctamente"""
    print("\n🔍 Probando inicialización del LLM...")
    try:
        # Importar la función desde el módulo principal
        sys.path.append(os.path.dirname(__file__))
        from consultar_web import get_llm_with_fallback

        llm = get_llm_with_fallback()
        if llm is not None:
            print("✅ LLM inicializado correctamente")
            print(f"   Tipo: {type(llm).__name__}")

            # Probar una consulta simple
            print("🔍 Probando consulta de prueba...")
            test_response = llm.invoke("¿Qué es el amor según Gerard?")
            if test_response and len(test_response) > 10:
                print("✅ Consulta procesada correctamente")
                print(f"   Respuesta (primeros 100 chars): {test_response[:100]}...")
                return True
            else:
                print("❌ La consulta no produjo una respuesta válida")
                return False
        else:
            print("❌ No se pudo inicializar el LLM")
            return False
    except Exception as e:
        print(f"❌ Error al probar LLM: {e}")
        return False

def test_faiss_loading():
    """Verificar que FAISS se carga correctamente"""
    print("\n🔍 Probando carga de base de datos FAISS...")
    try:
        from consultar_web import load_resources
        llm, vs = load_resources()
        if vs is not None:
            print("✅ Base de datos FAISS cargada correctamente")
            return True
        else:
            print("❌ No se pudo cargar la base de datos FAISS")
            return False
    except Exception as e:
        print(f"❌ Error al cargar FAISS: {e}")
        return False

def main():
    print("=" * 50)
    print("TEST SISTEMA 100% LOCAL - SIN COSTOS")
    print("=" * 50)
    print()

    all_tests_passed = True

    # Test 1: Ollama service
    if not test_ollama_service():
        all_tests_passed = False

    # Test 2: LLM initialization
    if not test_llm_initialization():
        all_tests_passed = False

    # Test 3: FAISS loading
    if not test_faiss_loading():
        all_tests_passed = False

    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 TODOS LOS TESTS PASARON - SISTEMA LISTO")
        print("🚀 Puedes ejecutar: streamlit run consultar_web.py")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("🔧 Revisa los errores arriba y solucionalos")
    print("=" * 50)

    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())