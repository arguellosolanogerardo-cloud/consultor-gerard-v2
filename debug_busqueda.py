import os
import sys
import re
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
import hashlib

# Configurar UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Embeddings de fallback
class HashEmbeddings(Embeddings):
    def __init__(self, dim: int = 768):
        self.dim = dim

    def _text_to_vector(self, text: str) -> list[float]:
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        vec = []
        for i in range(self.dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            normalized = (byte_val / 255.0) * 2 - 1
            vec.append(normalized)
        return vec

    def embed_documents(self, texts):
        return [self._text_to_vector(t) for t in texts]

    def embed_query(self, text: str):
        return self._text_to_vector(text)

def load_faiss():
    """Cargar FAISS con embeddings de fallback"""
    embeddings = HashEmbeddings(768)
    try:
        faiss_vs = FAISS.load_local(
            folder_path="vectorstore/faiss_index",
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
        return faiss_vs
    except Exception as e:
        print(f"Error cargando FAISS: {e}")
        return None

def debug_vector_search(vectorstore, query, k=10):
    """Debug de búsqueda vectorial"""
    print(f"\n=== DEBUG BÚSQUEDA VECTORIAL PARA: '{query}' ===")

    # Búsqueda vectorial
    vector_docs = vectorstore.similarity_search(query, k=k)

    print(f"Documentos encontrados por búsqueda vectorial: {len(vector_docs)}")

    for i, doc in enumerate(vector_docs[:5]):  # Mostrar solo primeros 5
        content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        print(f"\nDoc {i+1}:")
        print(f"Contenido: {content_preview}")
        print(f"Metadata: {doc.metadata}")

    # Verificar si contienen "amor"
    amor_count = sum(1 for doc in vector_docs if "amor" in doc.page_content.lower())
    print(f"\nDocumentos que contienen 'amor': {amor_count}/{len(vector_docs)}")

    return vector_docs

def debug_keyword_search(vectorstore, keywords, k=20):
    """Debug de búsqueda por keywords"""
    print(f"\n=== DEBUG BÚSQUEDA KEYWORD PARA: {keywords} ===")

    docstore = vectorstore.docstore._dict
    matches = []

    for doc_id, doc in docstore.items():
        content_lower = doc.page_content.lower()
        match_count = sum(1 for kw in keywords if kw in content_lower)

        if match_count > 0:
            matches.append((match_count, doc))

    # Ordenar por matches
    matches.sort(key=lambda x: x[0], reverse=True)
    keyword_docs = [doc for _, doc in matches[:k]]

    print(f"Documentos encontrados por keyword: {len(keyword_docs)}")

    # Contar documentos con "amor"
    amor_count = sum(1 for doc in keyword_docs if "amor" in doc.page_content.lower())
    print(f"Documentos que contienen 'amor': {amor_count}/{len(keyword_docs)}")

    for i, doc in enumerate(keyword_docs[:3]):  # Mostrar solo primeros 3
        content_preview = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
        print(f"\nDoc {i+1}:")
        print(f"Contenido: {content_preview}")
        print(f"Metadata: {doc.metadata}")

    return keyword_docs

def main():
    print("=== DEBUG SISTEMA DE BÚSQUEDA ===")

    # Cargar FAISS
    vectorstore = load_faiss()
    if not vectorstore:
        return

    query = "¿Qué dice Gerard sobre el amor?"

    # Extraer keywords
    keywords = [w.lower() for w in re.findall(r'\b\w{3,}\b', query)]
    print(f"Query: {query}")
    print(f"Keywords extraídos: {keywords}")

    # Debug búsqueda vectorial
    vector_docs = debug_vector_search(vectorstore, query, k=100)

    # Debug búsqueda keyword
    keyword_docs = debug_keyword_search(vectorstore, ["amor"], k=30)

    # Verificar documentos totales en el índice
    total_docs = len(vectorstore.docstore._dict)
    print(f"\nTotal de documentos en el índice: {total_docs}")

    # Contar documentos que contienen "amor" en todo el índice
    amor_total = 0
    for doc_id, doc in vectorstore.docstore._dict.items():
        if "amor" in doc.page_content.lower():
            amor_total += 1

    print(f"Documentos que contienen 'amor' en TODO el índice: {amor_total}")

if __name__ == "__main__":
    main()