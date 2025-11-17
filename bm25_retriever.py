"""
Retriever BM25 puro (sin FAISS)
Usa solo búsqueda léxica, útil cuando hay problemas con embeddings
"""
import pickle
import re
import numpy as np
from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun


def tokenize_clean(text: str) -> List[str]:
    """Tokenización mejorada: lowercase + limpieza de puntuación + split"""
    # Convertir a minúsculas
    text = text.lower()
    # Remover puntuación pero mantener tildes y ñ
    text = re.sub(r'[^\w\sáéíóúñü]', ' ', text)
    # Split y filtrar tokens vacíos
    tokens = [t for t in text.split() if t]
    return tokens


class BM25Retriever(BaseRetriever):
    """
    Retriever que usa SOLO BM25 (búsqueda léxica)
    Perfecto para nombres propios y coincidencias exactas
    """
    
    bm25_index: any
    bm25_docs: List[str]
    bm25_metadatas: List[dict]
    k: int = 10
    
    def __init__(self, bm25_path: str = "bm25_index.pkl", k: int = 10):
        """
        Args:
            bm25_path: Ruta al índice BM25
            k: Número de documentos a retornar
        """
        # Cargar índice BM25
        with open(bm25_path, 'rb') as f:
            bm25_data = pickle.load(f)
        
        super().__init__(
            bm25_index=bm25_data['bm25'],
            bm25_docs=bm25_data['docs'],
            bm25_metadatas=bm25_data['metadatas'],
            k=k
        )
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """Obtiene documentos usando solo BM25"""
        
        # Tokenizar query con limpieza de puntuación
        query_tokens = tokenize_clean(query)
        
        # Obtener scores BM25
        bm25_scores = self.bm25_index.get_scores(query_tokens)
        
        # Obtener top-k indices
        top_indices = np.argsort(bm25_scores)[::-1][:self.k]
        
        # Crear documentos
        docs = []
        for idx in top_indices:
            if bm25_scores[idx] > 0:  # Solo scores positivos
                doc = Document(
                    page_content=self.bm25_docs[idx],
                    metadata=self.bm25_metadatas[idx]
                )
                docs.append(doc)
        
        return docs
