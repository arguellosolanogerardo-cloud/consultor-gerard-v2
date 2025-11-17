"""
Crear índice BM25 desde el índice FAISS existente
para búsqueda léxica complementaria
"""
import os
import pickle
import json
from pathlib import Path
from rank_bm25 import BM25Okapi
from tqdm import tqdm

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credencial json/midyear-node-436821-t3-525a146e96a0.json'

from langchain_google_vertexai import VertexAIEmbeddings
from langchain_community.vectorstores import FAISS

print("🔍 Creando índice BM25 desde FAISS...\n")

# 1. Cargar FAISS
print("📥 Cargando índice FAISS...")
embeddings = VertexAIEmbeddings(
    model_name="text-multilingual-embedding-002",
    project="midyear-node-436821-t3"
)

faiss_vs = FAISS.load_local(
    folder_path="faiss_index",
    embeddings=embeddings,
    allow_dangerous_deserialization=True
)

print(f"✅ FAISS cargado: {faiss_vs.index.ntotal:,} documentos\n")

# 2. Extraer textos y metadata
print("📄 Extrayendo textos y metadata...")
docs = []
metadatas = []

# Obtener todos los documentos del docstore
docstore = faiss_vs.docstore._dict
total = len(docstore)

for doc_id, doc in tqdm(docstore.items(), total=total, desc="Procesando"):
    docs.append(doc.page_content)
    metadatas.append(doc.metadata)

print(f"✅ Extraídos {len(docs):,} documentos\n")

# 3. Tokenizar para BM25 con limpieza de puntuación
print("✂️  Tokenizando documentos...")
import re
tokenized_docs = []

def tokenize_clean(text):
    """Tokenización mejorada: lowercase + limpieza de puntuación + split"""
    # Convertir a minúsculas
    text = text.lower()
    # Remover puntuación pero mantener tildes y ñ
    text = re.sub(r'[^\w\sáéíóúñü]', ' ', text)
    # Split y filtrar tokens vacíos
    tokens = [t for t in text.split() if t]
    return tokens

for text in tqdm(docs, desc="Tokenizando"):
    tokens = tokenize_clean(text)
    tokenized_docs.append(tokens)

print(f"✅ Tokenización completada\n")

# 4. Crear índice BM25
print("🔨 Construyendo índice BM25...")
bm25 = BM25Okapi(tokenized_docs)
print("✅ Índice BM25 creado\n")

# 5. Guardar índice BM25 y metadata
print("💾 Guardando índice BM25...")

bm25_data = {
    'bm25': bm25,
    'docs': docs,
    'metadatas': metadatas
}

with open('bm25_index.pkl', 'wb') as f:
    pickle.dump(bm25_data, f)

print(f"✅ Índice guardado en bm25_index.pkl")

# Guardar estadísticas
stats = {
    'total_docs': len(docs),
    'avg_doc_length': sum(len(td) for td in tokenized_docs) / len(tokenized_docs),
    'total_tokens': sum(len(td) for td in tokenized_docs)
}

with open('bm25_stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, indent=2)

print(f"✅ Estadísticas guardadas en bm25_stats.json\n")

# 6. Mostrar resumen
print("=" * 60)
print("📊 RESUMEN DEL ÍNDICE BM25")
print("=" * 60)
print(f"Total documentos: {stats['total_docs']:,}")
print(f"Longitud promedio: {stats['avg_doc_length']:.1f} tokens")
print(f"Total tokens: {stats['total_tokens']:,}")
print(f"Tamaño archivo: {Path('bm25_index.pkl').stat().st_size / (1024*1024):.2f} MB")
print("=" * 60)
print("\n✨ Índice BM25 listo para búsqueda híbrida")
