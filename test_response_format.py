#!/usr/bin/env python3
"""
Script de prueba para verificar el formato de respuesta de Gerard
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consultar_web import *
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import uuid

def test_gerard_response():
    print("=== PRUEBA DE FORMATO DE RESPUESTA DE GERARD ===\n")

    # Cargar recursos
    print("1. Cargando recursos...")
    try:
        llm, vs = load_resources()
        print("✓ Recursos cargados exitosamente\n")
    except Exception as e:
        print(f"✗ Error cargando recursos: {e}\n")
        return

    # Crear cadena de retrieval literal (sin LLM)
    print("2. Creando cadena de retrieval literal...")

    def hybrid_retriever_func(query: str):
        docs = hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)
        print(f"\n--- DOCUMENTOS RECUPERADOS PARA '{query}' ---")
        for i, doc in enumerate(docs[:5]):  # Solo mostrar primeros 5
            print(f"Doc {i+1}: {doc.page_content[:200]}...")
        print("--- FIN DOCUMENTOS ---\n")
        return docs

    def literal_response_func(data):
        query = data["input"]
        docs = hybrid_retriever_func(query)
        return literal_search_response(query, docs)

    retrieval_chain = RunnableLambda(literal_response_func)
    print("✓ Cadena creada")

    # Probar consulta
    print("3. Probando consulta...")
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session_hash = str(uuid.uuid4())
    payload = {
        'input': '¿Qué dice Gerard sobre el amor?',
        'date': ts,
        'session_hash': session_hash
    }

    try:
        answer_raw = retrieval_chain.invoke(payload)
        print("✓ Consulta ejecutada exitosamente\n")

        print("4. Analizando respuesta...")
        print("=" * 50)
        print("RESPUESTA COMPLETA:")
        print("=" * 50)
        print(answer_raw)
        print("=" * 50)

        # Verificar formato
        print("\n5. Verificación de formato:")

        # Buscar citas con el formato esperado
        import re
        citations = re.findall(r'\(Fuente: [^)]+, Timestamp: [^)]+\)', answer_raw)

        if citations:
            print(f"✓ Encontradas {len(citations)} citas con formato correcto:")
            for i, citation in enumerate(citations[:5], 1):  # Mostrar máximo 5
                print(f"  {i}. {citation}")
            if len(citations) > 5:
                print(f"  ... y {len(citations) - 5} más")
        else:
            print("✗ No se encontraron citas con el formato esperado (Fuente: ..., Timestamp: ...)")

        # Verificar que no hay JSON
        if '"respuesta"' in answer_raw or '["respuesta"' in answer_raw:
            print("✗ La respuesta aún contiene formato JSON")
        else:
            print("✓ La respuesta no contiene formato JSON")

        # Verificar idioma español
        spanish_words = ['el', 'la', 'los', 'las', 'de', 'en', 'con', 'por', 'para', 'como', 'que', 'es', 'son']
        has_spanish = any(word in answer_raw.lower() for word in spanish_words)
        if has_spanish:
            print("✓ La respuesta parece estar en español")
        else:
            print("? No se detecta claramente español (podría ser cita directa)")

        print("\n=== PRUEBA COMPLETADA ===")

    except Exception as e:
        print(f"✗ Error en consulta: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gerard_response()