#!/usr/bin/env python3
"""
Script para probar el error de parsing JSON
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Simular la consulta problemática
query = "quienes son los guardianes del universo"

print("🔍 Probando consulta problemática...")
print(f"Query: {query}")
print("=" * 50)

# Importar las funciones necesarias
try:
    from consultar_web import literal_search_response, get_llm_with_fallback, OLLAMA_AVAILABLE
    print("✅ Funciones importadas correctamente")
    print(f"OLLAMA_AVAILABLE: {OLLAMA_AVAILABLE}")

    # Intentar obtener LLM
    if OLLAMA_AVAILABLE:
        llm = get_llm_with_fallback()
        print(f"LLM obtenido: {type(llm)}")
    else:
        print("❌ Ollama no disponible")

    # Simular documentos de prueba
    class MockDoc:
        def __init__(self, content, source="test.srt"):
            self.page_content = content
            self.metadata = {"source": source, "timestamp_start": "00:00:00"}

    test_docs = [
        MockDoc("Los guardianes del universo protegen la realidad de las fuerzas oscuras."),
        MockDoc("El gran evento cambió el curso de la historia humana."),
        MockDoc("El maestro Alaniso enseñó sobre el amor verdadero."),
    ]

    print("\n📄 Documentos de prueba:")
    for i, doc in enumerate(test_docs):
        print(f"  {i+1}. {doc.page_content}")

    print(f"\n🤖 Probando literal_search_response con query: '{query}'")
    response = literal_search_response(query, test_docs)
    print(f"Respuesta obtenida: {repr(response[:200])}")

    # Probar get_clean_text_from_json
    print("\n🧹 Probando get_clean_text_from_json...")
    from consultar_web import get_clean_text_from_json
    clean_response = get_clean_text_from_json(response)
    print(f"Respuesta limpia: {repr(clean_response[:200])}")

except Exception as e:
    print(f"❌ Error durante la prueba: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Prueba completada")