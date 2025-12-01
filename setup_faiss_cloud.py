"""
Script para configurar índice FAISS en Streamlit Cloud
Descarga desde GitHub Release v3
"""

import os
import sys
import requests
from pathlib import Path

def download_faiss_from_release():
    """Descarga índice FAISS desde GitHub Release"""
    
    # URL del índice FAISS en GitHub Release (NUEVO - v3)
    REPO_OWNER = "arguellosolanogerardo-cloud"
    REPO_NAME = "consultor-gerard-v3"
    TAG = "faiss-index-v1"
    
    faiss_dir = Path("faiss_index")
    faiss_dir.mkdir(exist_ok=True)
    
    # Archivos a descargar
    files = {
        "index.faiss": f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{TAG}/index.faiss",
        "index.pkl": f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{TAG}/index.pkl"
    }
    
    print("[INFO] Descargando índice FAISS desde GitHub Release...")
    print(f"[INFO] Repository: {REPO_OWNER}/{REPO_NAME}")
    print(f"[INFO] Tag: {TAG}")
    
    try:
        for filename, url in files.items():
            filepath = faiss_dir / filename
            
            print(f"[INFO] Descargando {filename}...")
            print(f"[INFO] URL: {url}")
            
            # Descargar archivo
            response = requests.get(url, stream=True, timeout=600)
            
            if response.status_code == 200:
                # Guardar archivo
                with open(filepath, 'wb') as f:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                
                size_mb = filepath.stat().st_size / (1024 * 1024)
                print(f"[SUCCESS] ✅ Descargado: {filename} ({size_mb:.2f} MB)")
            else:
                print(f"[ERROR] ❌ Error descargando {filename} (HTTP {response.status_code})")
                return False
        
        # Verificar que ambos archivos existen
        if (faiss_dir / "index.faiss").exists() and (faiss_dir / "index.pkl").exists():
            print("[SUCCESS] ✅ Índice FAISS completo descargado y listo para usar")
            
            # Crear marcador de descarga completa
            with open(faiss_dir / ".faiss_ready", "w") as f:
                f.write("downloaded_from_release")
            
            return True
        else:
            print("[ERROR] ❌ Faltan archivos después de la descarga")
            return False
    
    except Exception as e:
        print(f"[ERROR] Error descargando: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_faiss_exists():
    """Verifica si ya existe el índice FAISS COMPLETO desde GitHub Release"""
    faiss_files = [
        Path("faiss_index/index.faiss"),
        Path("faiss_index/index.pkl"),
    ]
    
    # Verificar que todos los archivos existan
    all_exist = all(f.exists() for f in faiss_files)
    
    if not all_exist:
        return False
    
    # Verificar que tenga el marcador de descarga desde Release
    marker = Path("faiss_index/.faiss_ready")
    if not marker.exists():
        print("[WARNING] ⚠️  Índice FAISS existe pero NO tiene marcador de Release")
        print("[WARNING] ⚠️  Probablemente es un placeholder antiguo")
        print("[INFO] Se eliminará y descargará el índice completo")
        
        # Eliminar índice antiguo
        import shutil
        try:
            shutil.rmtree("faiss_index")
            print("[INFO] Índice antiguo eliminado")
        except Exception as e:
            print(f"[WARNING] Error eliminando índice antiguo: {e}")
        
        return False
    
    # Si tiene el marcador, verificar contenido
    with open(marker, 'r') as f:
        content = f.read().strip()
    
    if content == "downloaded_from_release":
        # Mostrar tamaño de archivos
        for f in faiss_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"[INFO] Índice FAISS encontrado: {f} ({size_mb:.2f} MB)")
        return True
    else:
        print("[WARNING] ⚠️  Marcador de índice inválido")
        return False


def create_empty_faiss_placeholder():
    """Crea un índice FAISS vacío como placeholder"""
    print("[INFO] Creando índice FAISS placeholder...")
    
    try:
        from langchain_google_vertexai import VertexAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        
        # Crear embeddings
        embeddings = VertexAIEmbeddings(
            model_name="text-multilingual-embedding-002",
            project="midyear-node-436821-t3"
        )
        
        # Crear un documento placeholder
        placeholder_doc = Document(
            page_content="ÍNDICE FAISS NO DISPONIBLE - Los documentos fuente no están en Streamlit Cloud. Para usar la app completa, descarga el índice desde GitHub Release o ejecútala localmente.",
            metadata={"source": "placeholder", "timestamp": "00:00:00,000 --> 00:00:00,000"}
        )
        
        # Crear índice FAISS con el placeholder
        faiss_vs = FAISS.from_documents([placeholder_doc], embeddings)
        
        # Guardar
        faiss_dir = Path("faiss_index")
        faiss_dir.mkdir(exist_ok=True)
        faiss_vs.save_local(str(faiss_dir))
        
        print("[SUCCESS] ✅ Índice FAISS placeholder creado")
        print("[WARNING] ⚠️  Este índice está VACÍO - no contiene documentos reales")
        return True
    
    except Exception as e:
        print(f"[ERROR] Error creando placeholder: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_faiss():
    """Configuración principal del índice FAISS"""
    
    print("\n" + "="*60)
    print("CONFIGURACIÓN DE ÍNDICE FAISS PARA STREAMLIT CLOUD")
    print("="*60 + "\n")
    
    # 1. Verificar si ya existe
    if check_faiss_exists():
        print("[INFO] ✅ Índice FAISS ya disponible")
        return True
    
    # 2. Intentar descargar desde GitHub Release
    print("\n[PASO 1] Intentando descarga desde GitHub Release...")
    if download_faiss_from_release():
        return True
    
    # 3. Crear placeholder (ya que no hay documentos SRT en la nube)
    print("\n[PASO 2] Descarga falló, creando índice placeholder...")
    print("[INFO] Los documentos SRT no están disponibles en Streamlit Cloud")
    print("[INFO] Se creará un índice vacío para evitar errores")
    
    if create_empty_faiss_placeholder():
        return True
    
    # 4. Error crítico
    print("\n[ERROR] ❌ No se pudo configurar el índice FAISS")
    print("La aplicación no podrá funcionar sin el índice.")
    return False

if __name__ == "__main__":
    success = setup_faiss()
    sys.exit(0 if success else 1)
