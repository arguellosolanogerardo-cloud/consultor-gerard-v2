#!/usr/bin/env python3
"""
Test script para verificar la función literal_search_response mejorada
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consultar_web import literal_search_response, extract_quotes_with_keyword

# Crear documentos de prueba simulados
class MockDoc:
    def __init__(self, content, source="test.srt"):
        self.page_content = content
        self.metadata = {"source": source}

# Documentos de prueba con contenido relevante
test_docs = [
    MockDoc("Los guardianes del universo protegen la realidad de las fuerzas oscuras."),
    MockDoc("El gran evento cambió el curso de la historia humana."),
    MockDoc("El maestro Alaniso enseñó sobre el amor verdadero."),
    MockDoc("La verdad es el camino hacia la iluminación espiritual."),
]

# Pruebas
test_queries = [
    "¿Qué sabes sobre los guardianes del universo?",
    "¿Qué es el gran evento?",
    "¿Quién es el maestro Alaniso?",
    "¿Cuál es la verdad según Gerard?",
]

print("🧪 Probando función literal_search_response mejorada...")
print("=" * 60)

for query in test_queries:
    print(f"\nPregunta: {query}")
    try:
        response = literal_search_response(query, test_docs)
        print(f"Respuesta: {response[:200]}..." if len(response) > 200 else f"Respuesta: {response}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 40)

print("\n✅ Test completado")