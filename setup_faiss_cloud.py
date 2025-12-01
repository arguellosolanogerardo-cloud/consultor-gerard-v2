
"""
Script para configurar índice FAISS y BM25 en Streamlit Cloud
Descarga desde GitHub Release v3
"""

import os
import sys
import requests
from pathlib import Path

# Configuración del Repositorio
REPO_OWNER = "arguellosolanogerardo-cloud"
REPO_NAME = "consultor-gerard-v3"
TAG = "faiss-index-v1"

def download_file(url, filepath):
    """Descarga un archivo individual con barra de progreso"""
    try:
        print(f"[INFO] Descargando {filepath.name}...")
        print(f"[INFO] URL: {url}")
        
        response = requests.get(url, stream=True, timeout=600)
        
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"[SUCCESS] ✅ Descargado: {filepath.name} ({size_mb:.2f} MB)")
            return True
        else:
            print(f"[WARNING] ⚠️  No se pudo descargar {filepath.name} (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"[ERROR] Error descargando {filepath.name}: {e}")
        return False

def download_faiss_from_release():
    """Descarga índice FAISS desde GitHub Release"""
    
    faiss_dir = Path("faiss_index")
    faiss_dir.mkdir(exist_ok=True)
    
    # Archivos FAISS (Mandatorios)
    files = {
        "index.faiss": f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{TAG}/index.faiss",
        "index.pkl": f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{TAG}/index.pkl"
    }
    
    print("[INFO] Descargando índice FAISS desde GitHub Release...")
    
    success = True
    for filename, url in files.items():
        filepath = faiss_dir / filename
        if not download_file(url, filepath):
            success = False
    
    if success:
        # Crear marcador de descarga completa
        with open(faiss_dir / ".faiss_ready", "w") as f:
            f.write("downloaded_from_release")
        print("[SUCCESS] ✅ Índice FAISS completo listo")
        return True
    else:
        print("[ERROR] ❌ Faltan archivos FAISS")
        return False

def download_bm25_if_missing():
    """Descarga BM25 si no existe (Opcional)"""
    bm25_path = Path("bm25_index.pkl")
    
    if bm25_path.exists():
        print("[INFO] ✅ Índice BM25 ya disponible")
        return True
        
    print("[INFO] Índice BM25 no encontrado. Intentando descargar...")
    url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{TAG}/bm25_index.pkl"
    
    if download_file(url, bm25_path):
        print("[SUCCESS] ✅ Índice BM25 descargado y listo")
        return True
    else:
        print("[WARNING] ⚠️  BM25 no disponible en Release. La búsqueda híbrida estará desactivada.")
        return False

def check_faiss_exists():
    """Verifica si ya existe el índice FAISS COMPLETO"""
    faiss_files = [Path("faiss_index/index.faiss"), Path("faiss_index/index.pkl")]
    marker = Path("faiss_index/.faiss_ready")
    
    if all(f.exists() for f in faiss_files) and marker.exists():
        # Verificar contenido del marcador
        try:
            with open(marker, 'r') as f:
                if f.read().strip() == "downloaded_from_release":
                    return True
        except:
            pass
            
    return False

def create_empty_faiss_placeholder():
    """Crea un índice FAISS vacío como placeholder"""
    print("[INFO] Creando índice FAISS placeholder...")
    try:
        from langchain_google_vertexai import VertexAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        
        embeddings = VertexAIEmbeddings(model_name="text-multilingual-embedding-002", project="midyear-node-436821-t3")
        placeholder_doc = Document(page_content="ÍNDICE NO DISPONIBLE", metadata={"source": "placeholder"})
        faiss_vs = FAISS.from_documents([placeholder_doc], embeddings)
        
        faiss_dir = Path("faiss_index")
        faiss_dir.mkdir(exist_ok=True)
        faiss_vs.save_local(str(faiss_dir))
        return True
    except Exception as e:
        print(f"[ERROR] Error creando placeholder: {e}")
        return False

def setup_faiss():
    """Configuración principal"""
    print("\n" + "="*60)
    print("CONFIGURACIÓN DE ÍNDICES (FAISS + BM25)")
    print("="*60 + "\n")
    
    # 1. Configurar FAISS (Prioridad)
    faiss_ready = False
    if check_faiss_exists():
        print("[INFO] ✅ Índice FAISS verificado")
        faiss_ready = True
    else:
        if download_faiss_from_release():
            faiss_ready = True
        else:
            print("[WARNING] Falló descarga FAISS. Creando placeholder...")
            create_empty_faiss_placeholder()
            # No retornamos False aquí para permitir que la app arranque aunque sea vacía
    
    # 2. Configurar BM25 (Complementario)
    # Intentamos descargar siempre si falta, independientemente de FAISS
    download_bm25_if_missing()
    
    return True

if __name__ == "__main__":
    success = setup_faiss()
    sys.exit(0 if success else 1)
