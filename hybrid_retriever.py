"""
Retriever híbrido que combina búsqueda semántica (FAISS) y léxica (BM25)
Con soporte para filtrado por título de documento
"""
import pickle
import re
import numpy as np
from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from document_title_filter import detect_title_in_query, filter_docs_by_title


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
    
    @classmethod
    def build(cls, faiss_retriever, bm25_path: str = "bm25_index.pkl", documents: List[Document] = None, k: int = 10, alpha: float = 0.7):
        """
        Factory method para crear HybridRetriever de forma segura con Pydantic.
        Maneja la lógica de carga/generación del índice antes de instanciar la clase.
        """
        import os
        from rank_bm25 import BM25Okapi
        
        bm25_index = None
        bm25_docs = []
        bm25_metadatas = []
        
        if documents:
            # Construir índice en memoria (Ideal para Cloud)
            print(f"[INFO] Construyendo índice BM25 en memoria con {len(documents)} documentos...")
            bm25_docs = [doc.page_content for doc in documents]
            bm25_metadatas = [doc.metadata for doc in documents]
            
            # Tokenizar todos los documentos
            tokenized_docs = [tokenize_clean(doc) for doc in bm25_docs]
            bm25_index = BM25Okapi(tokenized_docs)
            print("[INFO] Índice BM25 construido exitosamente.")
            
        else:
            # Cargar desde archivo (Fallback local)
            if not os.path.exists(bm25_path):
                raise FileNotFoundError(f"Índice BM25 no encontrado en: {bm25_path}")
                
            # Cargar índice BM25
            try:
                with open(bm25_path, 'rb') as f:
                    bm25_data = pickle.load(f)
                
                bm25_index = bm25_data['bm25']
                bm25_docs = bm25_data['docs']
                bm25_metadatas = bm25_data['metadatas']
            except Exception as e:
                raise ValueError(f"Error cargando índice BM25 (posible corrupción): {e}")
        
        # Instanciar la clase usando el constructor estándar de Pydantic
        return cls(
            faiss_retriever=faiss_retriever,
            bm25_index=bm25_index,
            bm25_docs=bm25_docs,
            bm25_metadatas=bm25_metadatas,
            k=k,
            alpha=alpha
        )
    
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """Obtiene documentos combinando FAISS y BM25, con filtrado opcional por título"""
        
        # ===== PASO 0A: BÚSQUEDA ADAPTATIVA - Detectar si necesitamos más documentos =====
        # Patrones que indican búsqueda forense/específica (requieren alta cobertura)
        query_lower = query.lower()
        forensic_patterns = [
            'se afirma', 'se dice', 'se menciona', 'dice que', 'afirma que',
            'en que mensaje', 'en qué mensaje', 'en cual mensaje', 'en cuál mensaje',
            'donde se dice', 'dónde se dice', 'donde dice', 'dónde dice',
            'cual es el mensaje', 'cuál es el mensaje', 'que mensaje', 'qué mensaje'
        ]
        
        # Detectar si la query contiene algún patrón forense
        is_forensic_search = any(pattern in query_lower for pattern in forensic_patterns)
        
        # Ajustar k dinámicamente
        if is_forensic_search:
            effective_k = self.k * 2  # 150 → 300 para búsquedas forenses
            print(f"[ADAPTIVE SEARCH] 🔬 Búsqueda forense detectada, k aumentado a {effective_k}")
        else:
            effective_k = self.k  # 150 (modo normal)
        
        # ===== PASO 0B: Detectar si la query menciona un título específico de documento =====
        title_info = detect_title_in_query(query)
        title_filtered_indices = None  # Índices filtrados por título
        
        if title_info['has_title']:
            print(f"[TITLE FILTER] 🎯 Título detectado en query")
            print(f"[TITLE FILTER]    Keywords: {title_info['keywords']}")
            print(f"[TITLE FILTER]    Patrón: {title_info['pattern_matched']}")
            
            # Filtrar documentos BM25 por título (metadatos de source)
            title_filtered_indices = []
            
            # Separar keywords numéricas y no-numéricas
            numeric_keywords = [kw for kw in title_info['keywords'] if kw.isdigit()]
            non_numeric_keywords = [kw for kw in title_info['keywords'] if not kw.isdigit()]
            
            print(f"[TITLE FILTER]    Numeric keywords (obligatorios): {numeric_keywords}")
            print(f"[TITLE FILTER]    Non-numeric keywords (opcionales): {non_numeric_keywords}")
            
            for idx, metadata in enumerate(self.bm25_metadatas):
                source = metadata.get('source', '').lower()
                
                # ESTRATEGIA: Si hay números, SOLO los números son obligatorios
                if numeric_keywords:
                    # Todos los números deben estar presentes
                    numeric_matches = sum(1 for kw in numeric_keywords if kw.lower() in source)
                    if numeric_matches == len(numeric_keywords):
                        title_filtered_indices.append(idx)
                else:
                    # Si NO hay números, usar lógica normal de keywords
                    if len(title_info['keywords']) <= 3:
                        # Pocas keywords: todas deben estar
                        matches = sum(1 for kw in title_info['keywords'] if kw.lower() in source)
                        if matches == len(title_info['keywords']):
                            title_filtered_indices.append(idx)
                    else:
                        # Muchas keywords: al menos 50%
                        matches = sum(1 for kw in title_info['keywords'] if kw.lower() in source)
                        if matches >= len(title_info['keywords']) * 0.5:
                            title_filtered_indices.append(idx)
            
            print(f"[TITLE FILTER]    Documentos filtrados: {len(title_filtered_indices)} de {len(self.bm25_docs)}")
            
            # Si no hay documentos filtrados, advertir pero continuar con búsqueda normal
            if len(title_filtered_indices) == 0:
                print(f"[TITLE FILTER]    ⚠️ WARNING: No se encontraron documentos con ese título")
                print(f"[TITLE FILTER]    Continuando con búsqueda normal...")
                title_filtered_indices = None  # Reset para búsqueda normal
        
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
        
        # ===== PASO 1: Búsqueda léxica (BM25) con tokenización mejorada =====
        # ===== PASO 1: Búsqueda léxica (BM25) con tokenización mejorada =====
        # [CORREGIDO] Se elimina normalización numérica forzada que rompía búsquedas exactas como "somos nueve"
        
        # Tokenizar la query original
        query_tokens = tokenize_clean(query)
        bm25_scores = self.bm25_index.get_scores(query_tokens)
        
        # Si hay filtrado por título, restringir la búsqueda SOLO a esos documentos
        if title_filtered_indices is not None:
            print(f"[TITLE FILTER]    Aplicando filtro de título a búsqueda BM25...")
            
            # Crear array de scores filtrado (poner -inf a los no filtrados)
            filtered_bm25_scores = np.full_like(bm25_scores, -np.inf)
            for idx in title_filtered_indices:
                filtered_bm25_scores[idx] = bm25_scores[idx]
            
            # Usar scores filtrados para el resto del procesamiento
            bm25_scores = filtered_bm25_scores
            
            # Obtener top-k solo de los documentos filtrados
            top_bm25_indices = np.argsort(bm25_scores)[::-1][:min(effective_k * 2, len(title_filtered_indices))]
            print(f"[TITLE FILTER]    Top BM25 indices seleccionados: {len(top_bm25_indices)}")
            
        # ESTRATEGIA ESPECIAL: Si pregunta por "guardianes" o "maestros", buscar TODOS los nombres
        elif asks_for_names and ('guardianes' in query_lower or 'maestros' in query_lower):
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
            top_bm25_indices = np.argsort(bm25_scores)[::-1][:effective_k * 2]
            combined_indices = list(all_maestro_indices.union(set(top_bm25_indices)))
            
            # Ordenar por score original
            combined_indices.sort(key=lambda idx: bm25_scores[idx], reverse=True)
            top_bm25_indices = combined_indices[:effective_k * 4]  # Más documentos para cubrir todos
        else:
            # Obtener top-k de BM25 (más documentos si busca nombres)
            multiplier = 4 if use_bm25_only else 2
            top_bm25_indices = np.argsort(bm25_scores)[::-1][:effective_k * multiplier]
        
        bm25_docs = []
        for idx in top_bm25_indices:
            if bm25_scores[idx] > 0:
                doc = Document(
                    page_content=self.bm25_docs[idx],
                    metadata=self.bm25_metadatas[idx]
                )
                bm25_docs.append(doc)
        
        # ===== RETORNO TEMPRANO si hay filtrado por título =====
        # NUNCA mezclar con FAISS cuando buscamos título específico
        if title_filtered_indices is not None:
            print(f"[TITLE FILTER]    ✅ Retornando {len(bm25_docs)} documentos filtrados (sin FAISS)")
            return bm25_docs[:effective_k]
        
        # Si detectamos nombres propios Y BM25 encontró resultados, usar SOLO BM25
        if use_bm25_only and len(bm25_docs) >= effective_k // 2:
            return bm25_docs[:effective_k]
        
        # 2. Búsqueda semántica (FAISS) - Solo si no hay nombres o BM25 no encontró suficiente
        try:
            faiss_docs = self.faiss_retriever.invoke(query)
        except Exception as e:
            # Si FAISS falla, usar solo BM25
            return bm25_docs[:effective_k]
        
        # 3. Fusionar resultados usando Reciprocal Rank Fusion (RRF)
        # Alpha más bajo para nombres propios (más peso a BM25)
        effective_alpha = 0.05 if use_bm25_only else self.alpha
        
        merged_docs = self._reciprocal_rank_fusion(
            faiss_docs[:effective_k * 2],
            bm25_docs[:effective_k * 2],
            effective_alpha
        )
        
        return merged_docs[:effective_k]
    
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
