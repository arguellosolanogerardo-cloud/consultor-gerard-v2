#!/usr/bin/env python3
from consultar_web import *

# Cargar recursos
llm, vs = load_resources()

# Probar búsqueda
query = '¿Qué dice Gerard sobre el amor?'
docs = hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)

# Formatear contexto
formatted = format_docs_with_metadata(docs)

# Buscar todas las menciones de 'amor' en el contexto
import re
amor_matches = re.findall(r'[^.]*?amor[^.]*?\.', formatted, re.IGNORECASE | re.DOTALL)
print(f'Encontradas {len(amor_matches)} frases con "amor":')
for i, match in enumerate(amor_matches[:10], 1):
    print(f'{i}. {match.strip()}')

if len(amor_matches) == 0:
    print('No se encontraron frases con "amor" en el contexto')