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
    
    # Intentar encontrar el release más reciente con el índice
    release_urls = [
        f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/faiss-index/index.faiss",
        f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/faiss-index/index.pkl",
    ]
    
    faiss_dir = Path("faiss_index")
    faiss_dir.mkdir(exist_ok=True)
    
    print("[INFO] Intentando descargar índice FAISS desde GitHub Release...")
    
    for url in release_urls:
        filename = url.split("/")[-1]
        target_path = faiss_dir / filename
        
        try:
            print(f"[INFO] Descargando {filename}...")
            response = requests.get(url, stream=True, timeout=300)
            
            if response.status_code == 200:
                with open(target_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                size_mb = target_path.stat().st_size / (1024 * 1024)
                print(f"[SUCCESS] ✅ Descargado {filename} ({size_mb:.2f} MB)")
                return True
            else:
                print(f"[WARNING] No se encontró {filename} (HTTP {response.status_code})")
        
        except Exception as e:
            print(f"[WARNING] Error descargando {filename}: {e}")
    
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

def generate_faiss_from_scratch():
    """Genera índice FAISS desde documentos SRT (fallback)"""
    print("[INFO] Generando índice FAISS desde cero...")
    print("[WARNING] Esto puede tomar 10-15 minutos en Streamlit Cloud")
    
    try:
        # Importar el script de generación
        import ingestar
        
        print("[INFO] Ejecutando ingestar.py...")
        ingestar.main()
        
        if check_faiss_exists():
            print("[SUCCESS] ✅ Índice FAISS generado exitosamente")
            return True
        else:
            print("[ERROR] ❌ Falló la generación del índice")
            return False
    
    except Exception as e:
        print(f"[ERROR] Error generando índice FAISS: {e}")
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
    
    # 3. Generar desde cero (último recurso)
    print("\n[PASO 2] Descarga falló, generando desde cero...")
    if generate_faiss_from_scratch():
        return True
    
    # 4. Error crítico
    print("\n[ERROR] ❌ No se pudo configurar el índice FAISS")
    print("La aplicación no podrá funcionar sin el índice.")
    return False

if __name__ == "__main__":
    success = setup_faiss()
    sys.exit(0 if success else 1)
