"""
Módulo de Búsqueda Híbrida con Filtrado por Título
Permite encontrar documentos específicos cuando el usuario pregunta por su título,
incluyendo referencias a "audio", "video", "documento" y "archivo".
"""
import re
from typing import List, Dict, Any
from langchain_core.documents import Document


def detect_title_in_query(query: str) -> Dict[str, Any]:
    """
    Detecta si la pregunta del usuario menciona uno o más títulos específicos de documentos.
    NUEVO: Soporta detección de MÚLTIPLES títulos en una misma query.
    
    Patrones detectados:
    - "MEDITACIÓN 725 y mensaje 725" → detecta ambos
    - "EN EL DOCUMENTO DE TITULO: [título]"
    - "en el documento llamado [título]"
    - "en el archivo [título]"
    - "en el audio [título]" / "en el video [título]"
    - IDs entre corchetes: [ABC123XYZ]
    
    Args:
        query: Pregunta del usuario
        
    Returns:
        dict con:
            - has_title: bool, True si se detectó al menos un título
            - titles: list[dict], lista de títulos detectados, cada uno con:
                - keywords: list[str], palabras clave del título
                - pattern_matched: str, patrón que coincidió
                - raw_title: str, título sin procesar
                - doc_type: str, tipo de documento ('meditacion', 'mensaje', etc.)
            - keywords: list[str], DEPRECATED: keywords del primer título (compatibilidad)
            - pattern_matched: str, DEPRECATED: patrón del primer título (compatibilidad)
            - raw_title: str, DEPRECATED: título del primer título (compatibilidad)
    """
    query_lower = query.lower()
    
    # NUEVO: Patrón específico para "meditación/mensaje [número]"
    # Usa finditer() para encontrar TODAS las ocurrencias
    specific_pattern = r'(meditaci[oó]n|mensaje)\s+(?:n[uú]mero\s+)?(\d+)'
    specific_matches = list(re.finditer(specific_pattern, query_lower, re.IGNORECASE))
    
    titles_detected = []
    
    # Procesar matches específicos de meditación/mensaje
    if specific_matches:
        for match in specific_matches:
            doc_type = match.group(1).lower()
            if 'meditaci' in doc_type:
                doc_type = 'meditacion'
            number = match.group(2)
            
            # Keywords: número + tipo
            keywords = [number, doc_type]
            
            titles_detected.append({
                'keywords': keywords,
                'pattern_matched': 'specific_meditacion_mensaje',
                'raw_title': f"{doc_type} {number}",
                'doc_type': doc_type
            })
    
    # Si ya encontramos títulos específicos, retornar
    if titles_detected:
        # Mantener compatibilidad con versión anterior
        first_title = titles_detected[0]
        return {
            'has_title': True,
            'titles': titles_detected,
            'keywords': first_title['keywords'],
            'pattern_matched': first_title['pattern_matched'],
            'raw_title': first_title['raw_title']
        }
    
    # FALLBACK: Patrones generales (comportamiento original)
    patterns = [
        # Patrón explícito con "DE TITULO:" o "DE TÍTULO:"
        r'(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+de\s+t[ií]tulo\s*:\s*(.+?)(?:\.|¿|\?|$)',
        
        # Patrón "llamado [título]"
        r'(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+llamado\s+(.+?)(?:\.|¿|\?|$)',
        
        # Patrón "en el [tipo] [título]"
        r'en\s+el\s+(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+(.+?)(?:\.|¿|\?|$)',
        
        # Patrón "del [tipo] [título]"
        r'del\s+(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+(.+?)(?:\.|¿|\?|$)',
        
        # Patrón simple "[tipo] [título]"
        r'^(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+(.+?)(?:\.|¿|\?|$)',
    ]
    
    title_found = None
    pattern_matched = None
    
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            title_found = match.group(1).strip()
            pattern_matched = f"pattern_{i+1}"
            break
    
    # Detectar IDs entre corchetes (alta prioridad)
    id_pattern = r'\[([a-zA-Z0-9_-]+)\]'
    id_matches = re.findall(id_pattern, query)
    
    if id_matches:
        # Si hay IDs, siempre se considera que hay título
        keywords = id_matches.copy()
        if title_found:
            # Agregar palabras del título también
            title_words = [w for w in title_found.split() if len(w) > 3]
            keywords.extend(title_words[:5])  # Máximo 5 palabras adicionales
        
        return {
            'has_title': True,
            'titles': [{
                'keywords': keywords,
                'pattern_matched': 'id_brackets',
                'raw_title': ' '.join(id_matches),
                'doc_type': 'unknown'
            }],
            'keywords': keywords,
            'pattern_matched': 'id_brackets',
            'raw_title': ' '.join(id_matches)
        }
    
    # Si no hay IDs pero se encontró un título con patrones generales
    if title_found:
        # NUEVO: Detectar números (alta prioridad para meditaciones/mensajes)
        numeric_keywords = [w for w in title_found.split() if w.isdigit()]
        
        # Detectar tipo de documento de la query original
        doc_type = 'unknown'
        if re.search(r'meditaci[oó]n', query_lower):
            doc_type = 'meditacion'
        elif re.search(r'mensaje', query_lower):
            doc_type = 'mensaje'
        elif re.search(r'audio', query_lower):
            doc_type = 'audio'
        elif re.search(r'video', query_lower):
            doc_type = 'video'
        
        # Palabras clave importantes (meditacion, mensaje, etc.)
        important_words = ['meditacion', 'meditación', 'mensaje', 'audio', 'video', 'documento', 'archivo', 'número', 'numero']
        type_keywords = [w for w in title_found.split() if w.lower() in important_words]
        
        # Si tenemos doc_type, agregarlo
        if doc_type != 'unknown' and doc_type not in [k.lower() for k in type_keywords]:
            type_keywords.insert(0, doc_type)
        
        # Palabras significativas (>3 letras) excluyendo stopwords comunes
        stopwords = {'para', 'como', 'sobre', 'desde', 'hasta', 'cuando', 'donde', 'porque', 'cual', 'esta', 'este', 'estan', 'están'}
        text_keywords = [w for w in title_found.split() 
                        if len(w) > 3 and w.lower() not in stopwords and not w.isdigit()]
        
        # PRIORIDAD: números primero, luego tipos, luego texto significativo
        keywords = numeric_keywords + type_keywords + text_keywords[:4]
        
        # Eliminar duplicados preservando orden
        seen = set()
        keywords = [w for w in keywords if not (w.lower() in seen or seen.add(w.lower()))]
        
        # Limitar a 6 palabras clave
        keywords = keywords[:6]
        
        return {
            'has_title': True,
            'titles': [{
                'keywords': keywords,
                'pattern_matched': pattern_matched,
                'raw_title': title_found,
                'doc_type': doc_type
            }],
            'keywords': keywords,
            'pattern_matched': pattern_matched,
            'raw_title': title_found
        }
    
    # No se detectó título
    return {
        'has_title': False,
        'titles': [],
        'keywords': [],
        'pattern_matched': None,
        'raw_title': ''
    }


def filter_docs_by_title(all_docs: List[Document], title_keywords: List[str]) -> List[Document]:
    """
    Filtra documentos cuyos metadatos (source) contengan las palabras clave del título.
    
    Args:
        all_docs: Lista de todos los documentos disponibles
        title_keywords: Palabras clave del título a buscar
        
    Returns:
        Lista filtrada de documentos que coinciden con el título
    """
    if not title_keywords:
        return all_docs
    
    filtered = []
    
    for doc in all_docs:
        source = doc.metadata.get('source', '').lower()
        
        # Verificar si el source contiene TODAS las palabras clave (AND lógico)
        # O al menos 50% de ellas si hay más de 3 keywords
        if len(title_keywords) <= 3:
            # Para pocas keywords, todas deben estar
            matches = sum(1 for kw in title_keywords if kw.lower() in source)
            if matches == len(title_keywords):
                filtered.append(doc)
        else:
            # Para muchas keywords, al menos 50% deben coincidir
            matches = sum(1 for kw in title_keywords if kw.lower() in source)
            if matches >= len(title_keywords) * 0.5:
                filtered.append(doc)
    
    return filtered


def filter_docs_by_multiple_titles(all_docs: List[Document], titles_info: List[Dict[str, Any]]) -> Dict[str, List[Document]]:
    """
    NUEVO: Filtra documentos para múltiples títulos simultáneamente.
    
    Args:
        all_docs: Lista de todos los documentos disponibles
        titles_info: Lista de diccionarios con información de títulos, cada uno con:
            - keywords: list[str]
            - raw_title: str
            - doc_type: str
            
    Returns:
        Dict con títulos como keys y listas de documentos como values:
        {
            'meditacion 725': [doc1, doc2, ...],
            'mensaje 725': [doc3, doc4, ...]
        }
    """
    results = {}
    
    for title_info in titles_info:
        keywords = title_info.get('keywords', [])
        raw_title = title_info.get('raw_title', 'unknown')
        
        # Filtrar documentos para este título específico
        filtered_docs = filter_docs_by_title(all_docs, keywords)
        
        # Guardar resultados con el raw_title como key
        results[raw_title] = filtered_docs
        
        print(f"[INFO] Título '{raw_title}' - Keywords: {keywords} - Documentos encontrados: {len(filtered_docs)}")
    
    return results



def hybrid_search_with_title(
    faiss_vs,
    query: str,
    all_docs: List[Document],
    k: int = 150,
    title_keywords: List[str] = None
) -> List[Document]:
    """
    Búsqueda híbrida que combina filtrado por título + búsqueda semántica.
    NUEVO: Soporta búsqueda en MÚLTIPLES títulos simultáneamente.
    
    Estrategia:
    1. Detecta uno o más títulos en la query
    2. Filtra documentos para cada título
    3. Combina todos los documentos filtrados
    4. Realiza búsqueda semántica en el conjunto combinado
    
    Args:
        faiss_vs: Vector store de FAISS
        query: Pregunta del usuario
        all_docs: Todos los documentos disponibles
        k: Número de documentos a retornar
        title_keywords: DEPRECATED, se ignora (se auto-detecta desde query)
        
    Returns:
        Lista de documentos más relevantes
    """
    # Auto-detectar títulos
    title_info = detect_title_in_query(query)
    
    if not title_info['has_title']:
        # No hay título específico, búsqueda semántica normal
        return faiss_vs.similarity_search(query, k=k)
    
    # Obtener lista de títulos detectados
    titles_detected = title_info.get('titles', [])
    
    if len(titles_detected) == 0:
        # Fallback por compatibilidad
        return faiss_vs.similarity_search(query, k=k)
    
    print(f"[INFO] Búsqueda híbrida activada")
    print(f"[INFO] Número de títulos detectados: {len(titles_detected)}")
    
    # Filtrar documentos para cada título
    filtered_by_title = filter_docs_by_multiple_titles(all_docs, titles_detected)
    
    # Combinar todos los documentos filtrados (sin duplicados)
    all_filtered_docs = []
    seen_docs = set()
    
    for title, docs in filtered_by_title.items():
        for doc in docs:
            # Usar source + page_content[:100] como identificador único
            doc_id = (doc.metadata.get('source', ''), doc.page_content[:100])
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                all_filtered_docs.append(doc)
    
    print(f"[INFO] Total de documentos únicos filtrados: {len(all_filtered_docs)} de {len(all_docs)}")
    
    # Reportar títulos que NO se encontraron
    for title, docs in filtered_by_title.items():
        if len(docs) == 0:
            print(f"[WARNING] ⚠️ Título '{title}' NO ENCONTRADO en la base de datos")
    
    if len(all_filtered_docs) == 0:
        # No se encontró ningún documento para ningún título
        print(f"[WARNING] No se encontraron documentos para ninguno de los títulos especificados")
        # Retornar búsqueda semántica normal como fallback
        return faiss_vs.similarity_search(query, k=k)
    
    # Búsqueda semántica en el subset filtrado
    try:
        filtered_texts = [doc.page_content for doc in all_filtered_docs]
        filtered_metadatas = [doc.metadata for doc in all_filtered_docs]
        
        # Crear FAISS temporal con documentos filtrados
        from langchain_community.vectorstores import FAISS
        temp_vs = FAISS.from_texts(
            filtered_texts,
            embedding=faiss_vs.embedding_function,
            metadatas=filtered_metadatas
        )
        
        # Búsqueda semántica en el subset filtrado
        results = temp_vs.similarity_search(query, k=min(k, len(all_filtered_docs)))
        print(f"[INFO] Retornando {len(results)} documentos más relevantes del subset filtrado")
        return results
        
    except Exception as e:
        print(f"[ERROR] Error en búsqueda semántica del subset: {e}")
        # Fallback: retornar los filtrados en orden original
        return all_filtered_docs[:k]



# Función de utilidad para testing
def test_detection():
    """Función de prueba para verificar detección de títulos"""
    test_cases = [
        "EN EL DOCUMENTO DE TITULO: Para que se dejo Donald trump como presidente. QUE INFORMACION SE DA?",
        "en el video llamado amor divino que dice?",
        "en el audio sobre maria magdalena [ABC123] que menciona?",
        "¿Qué dice el documento Para que se dejo Donald trump?",
        "¿Qué información hay sobre María Magdalena?",  # Sin título
        "Del archivo [nPNE9qHlUfY] dame toda la info",
    ]
    
    print("="*80)
    print("PRUEBAS DE DETECCIÓN DE TÍTULOS")
    print("="*80)
    
    for query in test_cases:
        result = detect_title_in_query(query)
        print(f"\nQuery: {query}")
        print(f"  ✓ Tiene título: {result['has_title']}")
        if result['has_title']:
            print(f"  ✓ Keywords: {result['keywords']}")
            print(f"  ✓ Patrón: {result['pattern_matched']}")
            print(f"  ✓ Título raw: {result['raw_title']}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    test_detection()
