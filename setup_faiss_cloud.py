"""
Script para configurar índice FAISS en Streamlit Cloud
Descarga desde GitHub Release o genera desde cero
"""

import os
import sys
import requests
from pathlib import Path

def download_faiss_from_release():
    """Descarga índice FAISS desde GitHub Release"""
    
    # URL del índice FAISS en GitHub Release
    REPO_OWNER = "arguellosolanogerardo-cloud"
    REPO_NAME = "consultor-gerard-v2"
    
    # URL del archivo comprimido
    zip_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/faiss-index/faiss_index.zip"
    
    faiss_dir = Path("faiss_index")
    faiss_dir.mkdir(exist_ok=True)
    
    zip_path = Path("faiss_index.zip")
    
    print("[INFO] Descargando índice FAISS comprimido desde GitHub Release...")
    print(f"[INFO] URL: {zip_url}")
    
    try:
        # Descargar archivo ZIP
        response = requests.get(zip_url, stream=True, timeout=600)
        
        if response.status_code == 200:
            print("[INFO] Descargando archivo...")
            
            # Guardar ZIP
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(f"[SUCCESS] ✅ Descargado: faiss_index.zip ({size_mb:.2f} MB)")
            
            # Descomprimir
            print("[INFO] Descomprimiendo archivo...")
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(faiss_dir)
            
            print("[SUCCESS] ✅ Índice FAISS extraído correctamente")
            
            # Limpiar ZIP temporal
            zip_path.unlink()
            
            # Verificar archivos
            if (faiss_dir / "index.faiss").exists():
                print("[SUCCESS] ✅ Índice FAISS listo para usar")
                return True
            else:
                print("[ERROR] ❌ Falta index.faiss después de extraer")
                return False
        
        else:
            print(f"[WARNING] No se encontró el release (HTTP {response.status_code})")
            print("[INFO] Asegúrate de haber publicado el release 'faiss-index' en GitHub")
            return False
    
    except Exception as e:
        print(f"[ERROR] Error descargando/descomprimiendo: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_faiss_exists():
    """Verifica si ya existe el índice FAISS"""
    faiss_files = [
        Path("faiss_index/index.faiss"),
        Path("faiss_index/index.pkl"),
    ]
    
    for f in faiss_files:
        if f.exists():
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"[INFO] Índice FAISS encontrado: {f} ({size_mb:.2f} MB)")
            return True
    
    return False

def create_empty_faiss_placeholder():
    """Crea un índice FAISS vacío como placeholder"""
    print("[INFO] Creando índice FAISS placeholder...")
    
    try:
        from langchain_google_vertexai import VertexAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain.schema import Document
        from pathlib import Path
        
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

def create_empty_faiss_placeholder():
    """Crea un índice FAISS vacío como placeholder"""
    print("[INFO] Creando índice FAISS placeholder...")
    
    try:
        from langchain_google_vertexai import VertexAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        from pathlib import Path
        
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
