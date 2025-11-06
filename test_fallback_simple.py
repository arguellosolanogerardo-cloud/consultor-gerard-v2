#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento del sistema de fallback
"""
import os
import sys

# Agregar el directorio actual al path para importar consultar_web
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from consultar_web import get_llm_with_runtime_fallback, get_embeddings_with_fallback

    print("🔍 Probando sistema de fallback...")

    print("\n1. Probando LLM fallback:")
    llm = get_llm_with_runtime_fallback()
    if llm:
        print(f"✅ LLM obtenido: {type(llm).__name__}")
        print(f"   Modelo: {getattr(llm, '_current_llm', getattr(llm, 'model_name', getattr(llm, 'model', 'desconocido')))}")
    else:
        print("❌ No se pudo obtener LLM")

    print("\n2. Probando embeddings fallback:")
    embeddings = get_embeddings_with_fallback()
    if embeddings:
        print(f"✅ Embeddings obtenidos: {type(embeddings).__name__}")
        print(f"   Modelo: {getattr(embeddings, 'model', 'desconocido')}")
    else:
        print("❌ No se pudieron obtener embeddings")

    print("\n🎉 Prueba completada!")

except Exception as e:
    print(f"❌ Error en la prueba: {e}")
    import traceback
    traceback.print_exc()