#!/usr/bin/env python3
from consultar_web import *

# Cargar recursos
llm, vs = load_resources()

# Probar búsqueda
query = '¿Qué dice Gerard sobre el amor?'
print(f'Buscando: {query}')

docs = hybrid_retrieval(vs, query, k_vector=5, k_keyword=5)
print(f'Encontrados {len(docs)} documentos')

print('\n--- PRIMEROS 3 DOCUMENTOS ---')
for i, doc in enumerate(docs[:3]):
    print(f'Doc {i+1}:')
    print(f'  Contenido: {doc.page_content[:300]}...')
    print(f'  Fuente: {doc.metadata.get("source", "Desconocido")}')
    print()

print('--- CONTEXTO FORMATEADO ---')
formatted = format_docs_with_metadata(docs)
print(formatted[:2000] + '...' if len(formatted) > 2000 else formatted)