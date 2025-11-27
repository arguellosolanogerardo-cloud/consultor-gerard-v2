"""
Retriever híbrido que combina búsqueda semántica (FAISS) y léxica (BM25)
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


class HybridRetriever(BaseRetriever):
    """
    Retriever que combina:
    - Búsqueda semántica (FAISS con embeddings)
    - Búsqueda léxica (BM25)
    
    Fusiona resultados usando Reciprocal Rank Fusion (RRF)
    """
    
    faiss_retriever: any
    bm25_index: any
    bm25_docs: List[str]
    bm25_metadatas: List[dict]
    k: int = 10
    alpha: float = 0.7  # Peso para FAISS (0.7 = 70% semántica, 30% léxica)
    
    def __init__(self, faiss_retriever, bm25_path: str = "bm25_index.pkl", k: int = 10, alpha: float = 0.7):
        """
        Args:
            faiss_retriever: Retriever de FAISS
            bm25_path: Ruta al índice BM25
            k: Número de documentos a retornar
            alpha: Peso para resultados FAISS (0-1)
        """
        # Cargar índice BM25
        with open(bm25_path, 'rb') as f:
            bm25_data = pickle.load(f)
        
        super().__init__(
            faiss_retriever=faiss_retriever,
            bm25_index=bm25_data['bm25'],
            bm25_docs=bm25_data['docs'],
            bm25_metadatas=bm25_data['metadatas'],
            k=k,
            alpha=alpha
        )
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """Obtiene documentos combinando FAISS y BM25"""
        
        # Detectar términos que sugieren búsqueda exacta (nombres, apellidos, lugares)
        # Palabras capitalizadas O palabras comunes de nombres propios
        query_words = query.split()
        has_proper_nouns = any(word[0].isupper() for word in query_words if len(word) > 2)
        
        # Lista completa de nombres de maestros y términos relacionados
        proper_noun_keywords = [
            'maria', 'magdalena', 'jesus', 'cristo', 'jose', 'juan', 'pedro', 'pablo',
            'azoes', 'azen', 'aviatar', 'alaniso', 'alan', 'axel', 'adiestro', 'adiel', 'aladim',
            'aliestro', 'trey', 'totero', 'ra',
            'thor', 'arcangel', 'maestro', 'maestros', 'guardianes', 'guardian',
            'nombre', 'nombres', 'quien', 'quienes'
        ]
        has_name_keywords = any(word.lower() in proper_noun_keywords for word in query_words)
        
        # Detectar preguntas sobre nombres/identidades
        query_lower = query.lower()
        asks_for_names = any(pattern in query_lower for pattern in [
            'nombre', 'nombres', 'quien', 'quienes', 'guardianes', 'maestros'
        ])
        
        use_bm25_only = has_proper_nouns or has_name_keywords or asks_for_names
        
        # 1. Búsqueda léxica (BM25) con tokenización mejorada
        query_tokens = tokenize_clean(query)
        bm25_scores = self.bm25_index.get_scores(query_tokens)
        
        # ESTRATEGIA ESPECIAL: Si pregunta por "guardianes" o "maestros", buscar TODOS los nombres
        if asks_for_names and ('guardianes' in query_lower or 'maestros' in query_lower):
            # Lista de los 9 maestros guardianes
            maestros_guardianes = ['alaniso', 'axel', 'alan', 'azen', 'aviatar', 'aladim', 'adiel', 'azoes', 'aliestro']
            
            # Buscar documentos que mencionen cualquier maestro
            all_maestro_indices = set()
            for maestro in maestros_guardianes:
                maestro_tokens = tokenize_clean(maestro)
                maestro_scores = self.bm25_index.get_scores(maestro_tokens)
                # Top 30 para cada maestro (capturar todos sus menciones)
                maestro_indices = np.argsort(maestro_scores)[::-1][:30]
                for idx in maestro_indices:
                    if maestro_scores[idx] > 0:
                        all_maestro_indices.add(idx)
            
            # Combinar con búsqueda original
            top_bm25_indices = np.argsort(bm25_scores)[::-1][:self.k * 2]
            combined_indices = list(all_maestro_indices.union(set(top_bm25_indices)))
            
            # Ordenar por score original
            combined_indices.sort(key=lambda idx: bm25_scores[idx], reverse=True)
            top_bm25_indices = combined_indices[:self.k * 4]  # Más documentos para cubrir todos
        else:
            # Obtener top-k de BM25 (más documentos si busca nombres)
            multiplier = 4 if use_bm25_only else 2
            top_bm25_indices = np.argsort(bm25_scores)[::-1][:self.k * multiplier]
        
        bm25_docs = []
        for idx in top_bm25_indices:
            if bm25_scores[idx] > 0:
                doc = Document(
                    page_content=self.bm25_docs[idx],
                    metadata=self.bm25_metadatas[idx]
                )
                bm25_docs.append(doc)
        
        # Si detectamos nombres propios Y BM25 encontró resultados, usar SOLO BM25
        if use_bm25_only and len(bm25_docs) >= self.k // 2:
            return bm25_docs[:self.k]
        
        # 2. Búsqueda semántica (FAISS) - Solo si no hay nombres o BM25 no encontró suficiente
        try:
            faiss_docs = self.faiss_retriever.invoke(query)
        except Exception as e:
            # Si FAISS falla, usar solo BM25
            return bm25_docs[:self.k]
        
        # 3. Fusionar resultados usando Reciprocal Rank Fusion (RRF)
        # Alpha más bajo para nombres propios (más peso a BM25)
        effective_alpha = 0.05 if use_bm25_only else self.alpha
        
        merged_docs = self._reciprocal_rank_fusion(
            faiss_docs[:self.k * 2],
            bm25_docs[:self.k * 2],
            effective_alpha
        )
        
        return merged_docs[:self.k]
    
    def _reciprocal_rank_fusion(
        self,
        faiss_docs: List[Document],
        bm25_docs: List[Document],
        alpha: float
    ) -> List[Document]:
        """
        Fusiona resultados usando Reciprocal Rank Fusion
        
        Score = alpha * (1/(rank_faiss + 60)) + (1-alpha) * (1/(rank_bm25 + 60))
        """
        # Crear diccionario de scores
        doc_scores = {}
        
        # Scores de FAISS
        for rank, doc in enumerate(faiss_docs):
            key = doc.page_content[:100]  # Usar primeros 100 chars como key
            doc_scores[key] = {
                'doc': doc,
                'faiss_rank': rank,
                'bm25_rank': None,
                'score': 0
            }
        
        # Scores de BM25
        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content[:100]
            if key in doc_scores:
                doc_scores[key]['bm25_rank'] = rank
            else:
                doc_scores[key] = {
                    'doc': doc,
                    'faiss_rank': None,
                    'bm25_rank': rank,
                    'score': 0
                }
        
        # Calcular score combinado
        k = 60  # Constante RRF
        for key, data in doc_scores.items():
            faiss_score = alpha / (data['faiss_rank'] + k) if data['faiss_rank'] is not None else 0
            bm25_score = (1 - alpha) / (data['bm25_rank'] + k) if data['bm25_rank'] is not None else 0
            data['score'] = faiss_score + bm25_score
        
        # Ordenar por score descendente
        sorted_docs = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
        
        return [item['doc'] for item in sorted_docs]
