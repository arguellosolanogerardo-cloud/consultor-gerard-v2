"""
Script optimizado para crear índice FAISS con:
- Chunks pequeños (800 chars) preservando timestamps
- Dashboard interactivo de progreso y tokens
- Contador de costos en tiempo real
- Parser especializado de .srt
- Vertex AI embeddings (usa créditos de Google Cloud automáticamente)
- Lógica de reanudación y guardado robusta a prueba de fallos.

Uso:
    python ingestar_optimizado_dashboard.py --force
    python ingestar_optimizado_dashboard.py --resume
"""

import os
import sys
import time
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

from dotenv import load_dotenv
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
import faiss

# Importar el parser optimizado
from srt_parser_timestamps import load_srt_documents_optimized

load_dotenv()

# --- CONFIGURACIÓN ---
# Detectar automáticamente la ruta de credenciales correcta
credential_paths = [
    "google_credentials.json",  # Render/producción sin espacios
    "credencial_json_midyear-node-436821-t3-525a146e96a0.json",  # Alternativa sin espacios
    "credencial json/midyear-node-436821-t3-525a146e96a0.json"  # Local con espacios
]

credentials_file = None
for path in credential_paths:
    if os.path.exists(path):
        credentials_file = path
        print(f"[INFO] Usando credenciales desde: {path}")
        break

if credentials_file:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
else:
    print("[ERROR] No se encontró archivo de credenciales.")
    sys.exit(1)
DATA_PATH = "documentos_srt/"
FAISS_INDEX_PATH = "faiss_index_new"  # Nueva carpeta para índice con timestamps
CHECKPOINT_FILE = "faiss_checkpoint_new.json"  # Checkpoint separado
COST_PER_1K_TOKENS = 0.00001

# --- CLASES AUXILIARES ---

class TokenCounter:
    """Contador de tokens y costos."""
    def __init__(self):
        self.total_tokens = 0
        self.total_chunks = 0
        self.start_time = time.time()

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def add_chunk(self, text: str):
        self.total_tokens += self.estimate_tokens(text)
        self.total_chunks += 1

    def get_stats(self) -> Dict:
        elapsed = time.time() - self.start_time
        cost = (self.total_tokens / 1000) * COST_PER_1K_TOKENS
        return {
            'total_tokens': self.total_tokens,
            'total_chunks': self.total_chunks,
            'elapsed_seconds': elapsed,
            'chunks_per_minute': (self.total_chunks / elapsed) * 60 if elapsed > 0 else 0,
            'estimated_cost_usd': cost
        }

class ProgressDashboard:
    """Dashboard de progreso en terminal."""
    def __init__(self, total_chunks: int):
        self.total_chunks = total_chunks
        self.start_time = time.time()
        self.last_update = time.time()

    def update(self, processed_chunks: int, saved_chunks: int, stats: Dict):
        if time.time() - self.last_update < 1 and processed_chunks < self.total_chunks:
            return
        self.last_update = time.time()

        progress = (saved_chunks / self.total_chunks) * 100 if self.total_chunks > 0 else 0
        elapsed = time.time() - self.start_time
        
        eta_str = "Calculando..."
        if saved_chunks > 0:
            time_per_chunk = elapsed / saved_chunks
            remaining = (self.total_chunks - saved_chunks) * time_per_chunk
            eta = datetime.now() + timedelta(seconds=remaining)
            eta_str = eta.strftime("%H:%M:%S")

        bar_length = 40
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        print("\033[2J\033[H", end="")
        print("╔" + "═" * 78 + "╗")
        print("║" + " 🚀 CREACIÓN DE BASE VECTORIAL - DASHBOARD EN VIVO ".center(78) + "║")
        print("╠" + "═" * 78 + "╣")
        print(f"║  Progreso: [{bar}] {progress:.1f}%".ljust(79) + "║")
        print(f"║  Chunks Procesados: {processed_chunks:,} / {self.total_chunks:,}".ljust(79) + "║")
        print(f"║  💾 Chunks Guardados en Disco: {saved_chunks:,}".ljust(79) + "║")
        print("╠" + "═" * 78 + "╣")
        print(f"║  💰 Tokens consumidos: {stats['total_tokens']:,}".ljust(79) + "║")
        print(f"║  💵 Costo estimado: ${stats['estimated_cost_usd']:.4f} USD".ljust(79) + "║")
        print(f"║  ⚡ Velocidad: {stats['chunks_per_minute']:.1f} chunks/min".ljust(79) + "║")
        print("╠" + "═" * 78 + "╣")
        print(f"║  ⏱️  Tiempo transcurrido: {self._format_time(elapsed)}".ljust(79) + "║")
        print(f"║  🎯 ETA finalización: {eta_str}".ljust(79) + "║")
        print("╚" + "═" * 78 + "╝")
        sys.stdout.flush()

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

class RateLimiter:
    """Control de rate limiting con backoff."""
    def __init__(self, max_requests_per_minute: int):
        self.max_requests_per_minute = max_requests_per_minute
        self.delay = 60.0 / max_requests_per_minute
        self.last_request_time = 0
        self.consecutive_errors = 0

    def wait(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def handle_error(self):
        self.consecutive_errors += 1
        backoff_time = min(120, (2 ** self.consecutive_errors) * 2.0)
        print(f"📉 Error de cuota. Reintentando en {backoff_time:.1f}s...")
        time.sleep(backoff_time)

    def reset_errors(self):
        self.consecutive_errors = 0

# --- FUNCIONES PRINCIPALES ---

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"processed_chunks": 0, "total_tokens": 0}

def save_checkpoint(processed_chunks, total_tokens):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({"processed_chunks": processed_chunks, "total_tokens": total_tokens}, f, indent=2)

def embed_with_retry(embeddings, texts: List[str], rate_limiter: RateLimiter, max_retries: int = 5):
    for attempt in range(max_retries):
        try:
            rate_limiter.wait()
            result = embeddings.embed_documents(texts)
            rate_limiter.reset_errors()
            return result
        except Exception as e:
            error_str = str(e).lower()
            if 'rate' in error_str or 'quota' in error_str or '429' in error_str:
                rate_limiter.handle_error()
                if attempt == max_retries - 1:
                    print("❌ Máximo de reintentos alcanzado. Fallando.")
                    raise
            else:
                print(f"❌ Error no recuperable: {e}")
                raise
    raise Exception("Falló la creación de embeddings después de varios reintentos.")

def create_faiss_index_optimized(force_recreate: bool = False, resume: bool = False):
    index_file_path = Path(FAISS_INDEX_PATH) / "index.faiss"

    if force_recreate and os.path.exists(FAISS_INDEX_PATH):
        print("\n🗑️ Eliminando índice y checkpoint existentes...")
        shutil.rmtree(FAISS_INDEX_PATH)
    if force_recreate and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    
    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)

    print("\n" + "=" * 80)
    print("PASO 1: Cargando y parseando archivos .srt...".center(80))
    print("=" * 80)
    
    documents, stats = load_srt_documents_optimized(DATA_PATH, 800, 150)
    if not documents:
        print("\n❌ No se encontraron documentos. Verifica la ruta.")
        return
    
    total_chunks = len(documents)
    print(f"\n✅ Archivos procesados: {stats['total_files']}. Chunks generados: {total_chunks:,}")

    embeddings = VertexAIEmbeddings(
        model_name="text-multilingual-embedding-002",
        project="midyear-node-436821-t3"
    )
    
    start_chunk = 0
    vectorstore = None
    token_counter = TokenCounter()

    if resume and index_file_path.exists() and os.path.exists(CHECKPOINT_FILE):
        checkpoint = load_checkpoint()
        start_chunk = checkpoint.get("processed_chunks", 0)
        token_counter.total_tokens = checkpoint.get("total_tokens", 0)
        print(f"\n🔄 Reanudando. Cargando índice con {start_chunk} chunks desde el disco.")
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        if resume:
            print(f"\n⚠️ No se encontró un índice válido para reanudar. Creando uno nuevo.")
        print("\n✨ Creando nuevo índice FAISS.")
        dimension = len(embeddings.embed_query("test"))
        index = faiss.IndexFlatL2(dimension)
        docstore = InMemoryDocstore({})
        index_to_docstore_id = {}
        vectorstore = FAISS(embeddings.embed_query, index, docstore, index_to_docstore_id)

    dashboard = ProgressDashboard(total_chunks)
    rate_limiter = RateLimiter(max_requests_per_minute=10)  # Más conservador
    batch_size = 3  # Lotes más pequeños

    print("\n" + "=" * 80)
    print("PASO 2: Creando embeddings y guardando progreso...".center(80))
    print("=" * 80)
    print(f"   • Rate limit: {rate_limiter.max_requests_per_minute} peticiones/minuto")
    print(f"   • Batch size: {batch_size} documentos/lote")
    print(f"   • Guardado: Atómico después de cada lote.")

    try:
        for i in range(start_chunk, total_chunks, batch_size):
            batch_docs = documents[i:i+batch_size]
            if not batch_docs:
                continue

            batch_texts = [doc.page_content for doc in batch_docs]
            
            # --- ESTA ES LA PARTE CRÍTICA QUE HA SIDO CORREGIDA ---
            # 1. Obtener embeddings con control de velocidad
            embedded_vectors = embed_with_retry(embeddings, batch_texts, rate_limiter)
            
            # 2. Añadir al índice usando la API correcta de FAISS
            # Convertir vectores a numpy array
            vectors_array = np.array(embedded_vectors, dtype='float32')
            
            # Obtener el índice FAISS subyacente y añadir vectores
            start_id = vectorstore.index.ntotal
            vectorstore.index.add(vectors_array)
            
            # Añadir documentos al docstore
            for j, doc in enumerate(batch_docs):
                doc_id = str(start_id + j)
                vectorstore.docstore.add({doc_id: doc})
                vectorstore.index_to_docstore_id[start_id + j] = doc_id
            # --- FIN DE LA CORRECCIÓN CRÍTICA ---

            # 3. Guardado atómico en disco
            vectorstore.save_local(FAISS_INDEX_PATH)
            
            # 4. Actualiza contadores y checkpoint
            for text in batch_texts:
                token_counter.add_chunk(text)
            
            current_total_saved = i + len(batch_docs)
            save_checkpoint(current_total_saved, token_counter.total_tokens)

            # 5. Actualiza dashboard
            dashboard.update(current_total_saved, current_total_saved, token_counter.get_stats())

        print("\n\n" + "=" * 80)
        print("✅ ÍNDICE CREADO Y GUARDADO EXITOSAMENTE".center(80))
        print("=" * 80)
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)

    except KeyboardInterrupt:
        print("\n\n⚠️  PROCESO INTERRUMPIDO POR EL USUARIO.")
        print("💾 El último lote completado ha sido guardado de forma segura.")
        print(f"🔄 Para continuar, ejecuta: python {os.path.basename(__file__)} --resume")
    except Exception as e:
        print(f"\n\n❌ ERROR INESPERADO: {e}")
        print("💾 El progreso hasta el último lote completado está guardado.")
        print(f"🔄 Para continuar, ejecuta: python {os.path.basename(__file__)} --resume")
        raise

def main():
    parser = argparse.ArgumentParser(description="Creación robusta de índice FAISS.")
    parser.add_argument("--force", action="store_true", help="Forzar recreación del índice.")
    parser.add_argument("--resume", action="store_true", help="Reanudar desde el último checkpoint.")
    args = parser.parse_args()
    create_faiss_index_optimized(force_recreate=args.force, resume=args.resume)

if __name__ == "__main__":
    main()