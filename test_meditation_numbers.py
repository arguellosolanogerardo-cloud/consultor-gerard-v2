from document_title_filter import detect_title_in_query

test_queries = [
    "En el video meditacion 725 que informacion hay sobre jesus",
    "mensaje 725",
    "MEDITACION 1",
    "video meditacion 1113",
    "en el documento mensaje 600",
    "meditacion numero 50 que dice",
]

print("="*80)
print("PRUEBA DE DETECCIÓN DE NÚMEROS EN MEDITACIONES/MENSAJES")
print("="*80)

for query in test_queries:
    result = detect_title_in_query(query)
    print(f"\nQuery: {query}")
    print(f"  ✓ Keywords: {result['keywords']}")
    print(f"  ✓ Has title: {result['has_title']}")
    print(f"  ✓ Pattern: {result['pattern_matched']}")
