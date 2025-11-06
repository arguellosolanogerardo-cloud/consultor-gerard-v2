#!/usr/bin/env python3
"""
Script para probar el retrieval chain directamente
"""
import os
import sys
import json
import re
from datetime import datetime
import uuid

# Configurar UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'

# Importar Ollama
try:
    from langchain_ollama import OllamaLLM, OllamaEmbeddings
    OLLAMA_AVAILABLE = True
    print("[INFO] Ollama disponible")
except ImportError as e:
    OLLAMA_AVAILABLE = False
    print(f"[ERROR] Ollama no disponible: {e}")
    exit(1)

# Importar FAISS
from langchain_community.vectorstores import FAISS

def get_llm_with_fallback():
    """Obtiene LLM usando únicamente Ollama con Llama2"""
    if OLLAMA_AVAILABLE:
        try:
            llm = OllamaLLM(
                model="llama2:7b",
                temperature=0.4,
                num_ctx=4096
            )
            print("[DEBUG] LLM Ollama (Llama2 7B) inicializado correctamente")
            return llm
        except Exception as e:
            print(f"[WARNING] Ollama LLM falló: {e}")
    return None

def get_embeddings_with_fallback():
    """Obtiene embeddings usando únicamente Ollama con Llama2"""
    if OLLAMA_AVAILABLE:
        try:
            embeddings = OllamaEmbeddings(
                model="llama2:7b"
            )
            print("[DEBUG] Embeddings Ollama (Llama2 7B) inicializados correctamente")
            return embeddings
        except Exception as e:
            print(f"[WARNING] Ollama embeddings fallaron: {e}")
    return None

def load_resources():
    """Carga LLM y vectorstore"""
    llm = get_llm_with_fallback()
    embeddings = get_embeddings_with_fallback()

    if llm is None or embeddings is None:
        raise Exception("No se pudieron inicializar LLM o embeddings")

    # Cargar FAISS
    faiss_path = os.path.join('faiss_index', 'index.faiss')
    if not os.path.exists(faiss_path):
        raise Exception(f"Índice FAISS no encontrado: {faiss_path}")

    vs = FAISS.load_local('faiss_index', embeddings, allow_dangerous_deserialization=True)
    print(f"[DEBUG] FAISS cargado con {vs.index.ntotal} documentos")

    return llm, vs

def hybrid_retrieval(vs, query, k_vector=100, k_keyword=30):
    """Búsqueda híbrida: vectorial + keyword"""
    try:
        # Búsqueda vectorial
        vector_results = vs.similarity_search(query, k=k_vector)

        # Búsqueda por keyword (usando metadatos)
        keyword_results = []
        for doc in vs.docstore._dict.values():
            content_lower = doc.page_content.lower()
            query_lower = query.lower()
            if any(word in content_lower for word in query_lower.split()):
                keyword_results.append(doc)

        # Combinar y deduplicar
        seen_sources = set()
        combined_results = []

        # Agregar resultados vectoriales primero
        for doc in vector_results:
            source = doc.metadata.get('source', '')
            if source not in seen_sources:
                combined_results.append(doc)
                seen_sources.add(source)

        # Agregar resultados keyword si no están duplicados
        for doc in keyword_results[:k_keyword]:
            source = doc.metadata.get('source', '')
            if source not in seen_sources:
                combined_results.append(doc)
                seen_sources.add(source)

        return combined_results[:k_vector]

    except Exception as e:
        print(f"[ERROR] Error en búsqueda híbrida: {e}")
        # Fallback a búsqueda vectorial simple
        return vs.similarity_search(query, k=k_vector)

def format_docs_with_metadata(docs):
    """Formatea documentos con metadatos"""
    formatted = []
    for doc in docs:
        source = os.path.basename(doc.metadata.get('source', 'desconocido'))
        content = doc.page_content
        formatted.append(f"Fuente: {source}\nContenido: {content}")
    return "\n\n".join(formatted)

# Importar prompt y runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

def main():
    print('Cargando recursos...')
    try:
        llm_loaded, vs = load_resources()
        print(f'LLM: {type(llm_loaded)}, VS: {type(vs)}')
    except Exception as e:
        print(f'Error cargando recursos: {e}')
        import traceback
        traceback.print_exc()
        exit(1)

    # Crear retriever híbrido
    def hybrid_retriever_func(query: str):
        return hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)

    # Crear prompt
    prompt = ChatPromptTemplate.from_template('''[INST] <<SYS>>
Eres Gerard, un analista forense especializado en textos antiguos y documentos históricos. Tu tarea es analizar documentos y responder preguntas basándote únicamente en la información proporcionada en el contexto.

INSTRUCCIONES ESPECÍFICAS:
- Responde ÚNICAMENTE en español
- Si la pregunta no puede responderse con el contexto proporcionado, di explícitamente que no tienes suficiente información
- Mantén un tono profesional y objetivo
- Si encuentras contradicciones en el contexto, mencionalas
- Cita las fuentes cuando sea relevante

Contexto proporcionado:
{context}

Pregunta del usuario: {input}
Fecha actual: {date}
Sesión: {session_hash}
<</SYS>> [/INST]''')

    # Crear retrieval chain
    retrieval_chain = (
        {
            'context': (lambda x: x['input']) | RunnableLambda(hybrid_retriever_func) | format_docs_with_metadata,
            'input': lambda x: x['input'],
            'date': lambda x: x.get('date', ''),
            'session_hash': lambda x: x.get('session_hash', '')
        }
        | prompt
        | llm_loaded
        | StrOutputParser()
    )

    # Probar consulta
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session_hash = str(uuid.uuid4())
    payload = {'input': 'que es el amor', 'date': ts, 'session_hash': session_hash}

    print('Ejecutando consulta...')
    try:
        answer_raw = retrieval_chain.invoke(payload)
        print(f'Respuesta obtenida: {type(answer_raw)}')
        print(f'Contenido: {str(answer_raw)[:500]}...')

        # Verificar si es JSON válido
        match = re.search(r'\[.*\]', answer_raw, re.DOTALL)
        if match:
            print('JSON encontrado en respuesta')
            try:
                data = json.loads(match.group(0))
                print(f'JSON parseado correctamente: {len(data)} items')
            except json.JSONDecodeError as je:
                print(f'Error parseando JSON: {je}')
                print('Contenido del match:', match.group(0))
        else:
            print('No se encontró JSON en la respuesta')
            print('Respuesta completa:')
            print(answer_raw)

    except Exception as e:
        print(f'Error en consulta: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()