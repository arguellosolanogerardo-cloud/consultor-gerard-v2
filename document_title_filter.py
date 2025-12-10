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
    Detecta si la pregunta del usuario menciona un título específico de documento.
    
    Patrones detectados:
    - "EN EL DOCUMENTO DE TITULO: [título]"
    - "en el documento llamado [título]"
    - "en el archivo [título]"
    - "en el audio [título]"
    - "en el video [título]"
    - "documento [título]"
    - "audio de título [título]"
    - "video llamado [título]"
    - IDs entre corchetes: [ABC123XYZ]
    
    Args:
        query: Pregunta del usuario
        
    Returns:
        dict con:
            - has_title: bool, True si se detectó un título
            - keywords: list[str], palabras clave del título detectado
            - pattern_matched: str, patrón que coincidió
            - raw_title: str, título sin procesar
    """
    query_lower = query.lower()
    
    # Patrones para detectar títulos (ordenados por especificidad)
    patterns = [
        # Patrón explícito con "DE TITULO:" o "DE TÍTULO:"
        r'(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+de\s+t[ií]tulo\s*:\s*(.+?)(?:\.|¿|\?|$)',
        
        # Patrón "llamado [título]"
        r'(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+llamado\s+(.+?)(?:\.|¿|\?|$)',
        
        # Patrón "en el [tipo] [título]"
        r'en\s+el\s+(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+(.+?)(?:\.|¿|\?|$)',
        
        # Patrón "del [tipo] [título]"
        r'del\s+(?:documento|archivo|audio|video|meditaci[oó]n|mensaje)\s+(.+?)(?:\.|¿|\?|$)',
        
        # Patrón NUEVO: "meditacion/mensaje [numero] [numero]" - sin prefijo
        r'(?:meditaci[oó]n|mensaje)\s+(?:n[uú]mero\s+)?(\d+)(?:\s|¿|\?|$)',
        
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
            'keywords': keywords,
            'pattern_matched': 'id_brackets',
            'raw_title': ' '.join(id_matches)
        }
    
    # Si no hay IDs pero se encontró un título
    if title_found:
        # NUEVO: Detectar números (alta prioridad para meditaciones/mensajes)
        numeric_keywords = [w for w in title_found.split() if w.isdigit()]
        
        # Detectar tipo de documento de la query original (para pattern_5)
        doc_type = None
        if pattern_matched == 'pattern_5':
            # Extraer si es meditacion o mensaje de la query original
            if re.search(r'meditaci[oó]n', query_lower):
                doc_type = 'meditacion'
            elif re.search(r'mensaje', query_lower):
                doc_type = 'mensaje'
        
        # Palabras clave importantes (meditacion, mensaje, etc.)
        important_words = ['meditacion', 'meditación', 'mensaje', 'audio', 'video', 'documento', 'archivo', 'número', 'numero']
        type_keywords = [w for w in title_found.split() if w.lower() in important_words]
        
        # Si pattern_5 y tenemos doc_type, agregarlo
        if doc_type and doc_type not in [k.lower() for k in type_keywords]:
            type_keywords.insert(0, doc_type)
        
        # Palabras significativas (>3 letras) excluyendo stopwords comunes
        stopwords = {'para', 'como', 'sobre', 'desde', 'hasta', 'cuando', 'donde', 'porque', 'cual', 'esta', 'este', 'estan', 'están'}
        text_keywords = [w for w in title_found.split() 
                        if len(w) > 3 and w.lower() not in stopwords and not w.isdigit()]
        
        # PRIORIDAD: números primero, luego tipos, luego texto significativo
        # Esto es crítico para "meditacion 725" → ['725', 'meditacion']
        keywords = numeric_keywords + type_keywords + text_keywords[:4]
        
        # Eliminar duplicados preservando orden
        seen = set()
        keywords = [w for w in keywords if not (w.lower() in seen or seen.add(w.lower()))]
        
        # Limitar a 6 palabras clave
        keywords = keywords[:6]
        
        return {
            'has_title': True,
            'keywords': keywords,
            'pattern_matched': pattern_matched,
            'raw_title': title_found
        }
    
    # No se detectó título
    return {
        'has_title': False,
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


def hybrid_search_with_title(
    faiss_vs,
    query: str,
    all_docs: List[Document],
    k: int = 150,
    title_keywords: List[str] = None
) -> List[Document]:
    """
    Búsqueda híbrida que combina filtrado por título + búsqueda semántica.
    
    Estrategia:
    1. Filtra documentos por título (si se detectó)
    2. Realiza búsqueda semántica SOLO en esos documentos filtrados
    3. Si no hay suficientes resultados, expande a búsqueda normal
    
    Args:
        faiss_vs: Vector store de FAISS
        query: Pregunta del usuario
        all_docs: Todos los documentos disponibles
        k: Número de documentos a retornar
        title_keywords: Keywords del título (opcional, se auto-detecta si no se provee)
        
    Returns:
        Lista de documentos más relevantes
    """
    # Auto-detectar título si no se proveyó
    if title_keywords is None:
        title_info = detect_title_in_query(query)
        if not title_info['has_title']:
            # No hay título específico, búsqueda semántica normal
            return faiss_vs.similarity_search(query, k=k)
        title_keywords = title_info['keywords']
    
    # Filtrar documentos por título
    filtered_docs = filter_docs_by_title(all_docs, title_keywords)
    
    print(f"[INFO] Búsqueda híbrida activada")
    print(f"[INFO] Keywords de título: {title_keywords}")
    print(f"[INFO] Documentos filtrados: {len(filtered_docs)} de {len(all_docs)}")
    
    if len(filtered_docs) == 0:
        # No se encontraron documentos con ese título
        print(f"[WARNING] No se encontraron documentos con título matching")
        # Retornar búsqueda semántica normal como fallback
        return faiss_vs.similarity_search(query, k=k)
    
    if len(filtered_docs) <= k:
        # Hay pocos documentos filtrados, retornarlos todos priorizando por similitud semántica
        # Crear un vector store temporal SOLO con los documentos filtrados
        # y hacer búsqueda semántica en ellos
        try:
            # Extraer page_content para similitud
            filtered_texts = [doc.page_content for doc in filtered_docs]
            filtered_metadatas = [doc.metadata for doc in filtered_docs]
            
            # Crear FAISS temporal con documentos filtrados
            from langchain_community.vectorstores import FAISS
            temp_vs = FAISS.from_texts(
                filtered_texts,
                embedding=faiss_vs.embedding_function,
                metadatas=filtered_metadatas
            )
            
            # Búsqueda semántica en el subset filtrado
            results = temp_vs.similarity_search(query, k=min(k, len(filtered_docs)))
            print(f"[INFO] Retornando {len(results)} documentos del subset filtrado")
            return results
            
        except Exception as e:
            print(f"[ERROR] Error en búsqueda semántica del subset: {e}")
            # Fallback: retornar los filtrados en orden original
            return filtered_docs[:k]
    
    else:
        # Hay suficientes documentos filtrados, hacer búsqueda semántica en ellos
        try:
            filtered_texts = [doc.page_content for doc in filtered_docs]
            filtered_metadatas = [doc.metadata for doc in filtered_docs]
            
            from langchain_community.vectorstores import FAISS
            temp_vs = FAISS.from_texts(
                filtered_texts,
                embedding=faiss_vs.embedding_function,
                metadatas=filtered_metadatas
            )
            
            results = temp_vs.similarity_search(query, k=k)
            print(f"[INFO] Retornando top-{k} de {len(filtered_docs)} documentos filtrados")
            return results
            
        except Exception as e:
            print(f"[ERROR] Error en búsqueda semántica del subset: {e}")
            return filtered_docs[:k]


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
