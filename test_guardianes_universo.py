#!/usr/bin/env python3
"""
Script de prueba directa para consulta: "quienes son los guardianes del universo"
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from consultar_web import literal_search_response, extract_quotes_with_keyword

class MockDoc:
    def __init__(self, content, source="test_guardianes.srt", timestamp="00:07:49"):
        self.page_content = content
        self.metadata = {"source": source, "timestamp_start": timestamp}

test_docs = [
    MockDoc("Los guardianes del universo protegen la realidad de las fuerzas oscuras.", "SERIE Episodio 1：  ＂El Contacto - Parte 2＂ ｜ Guardianes del Universo A.C. [pdZl-pi48zI].es", "00:07:49"),
    MockDoc("Los guardianes vigilantes de todo lo que existe.", "SERIE Episodio 1：  ＂El Contacto - Parte 2＂ ｜ Guardianes del Universo A.C. [pdZl-pi48zI].es", "00:07:49"),
    MockDoc("El maestro Alaniso enseñó sobre el amor verdadero.", "MEDITACION 833.srt", "00:34:10"),
]

query = "quienes son los guardianes del universo"
print(f"Consulta: {query}")
response = literal_search_response(query, test_docs)
print("Respuesta obtenida:")
print(response)

# Mostrar formato esperado de referencia
print("\nFormato esperado:")
for doc in test_docs:
    print(f"[Fuente: '{doc.metadata['source']}' | Timestamp: '{doc.metadata['timestamp_start']}' | Texto: '{doc.page_content}']")
