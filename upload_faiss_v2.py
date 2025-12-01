"""
Script para subir el índice FAISS a GitHub Release
para el repositorio consultor-gerard-v2
"""

import os
import sys
import requests
from pathlib import Path

# Configuración
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
if not GITHUB_TOKEN:
    print("[ERROR] ❌ GITHUB_TOKEN no encontrado en variables de entorno")
    sys.exit(1)

REPO_OWNER = "arguellosolanogerardo-cloud"
REPO_NAME = "consultor-gerard-v2"
RELEASE_TAG = "faiss-index-v1"
RELEASE_NAME = "FAISS Index v1 - Complete Database"
RELEASE_BODY = "Índice FAISS completo (337 MB) para búsqueda semántica de alta calidad. Contiene embeddings de todos los documentos."

# Archivos a subir
FAISS_DIR = Path("faiss_index")
FILES_TO_UPLOAD = [
    FAISS_DIR / "index.faiss",
    FAISS_DIR / "index.pkl"
]

def create_release():
    """Crea un nuevo release en GitHub"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "tag_name": RELEASE_TAG,
        "name": RELEASE_NAME,
        "body": RELEASE_BODY,
        "draft": False,
        "prerelease": False
    }
    
    print(f"[INFO] Creando release '{RELEASE_TAG}'...")
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 201:
        print(f"[SUCCESS] ✅ Release creado exitosamente")
        return response.json()
    elif response.status_code == 422:
        # Release ya existe, obtenerlo
        print(f"[INFO] Release ya existe, obteniendo información...")
        get_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{RELEASE_TAG}"
        response = requests.get(get_url, headers=headers)
        if response.status_code == 200:
            print(f"[SUCCESS] ✅ Release encontrado")
            return response.json()
    
    print(f"[ERROR] ❌ Error creando release: {response.status_code}")
    print(f"[ERROR] {response.text}")
    return None

def upload_file(release_id, file_path):
    """Sube un archivo al release"""
    if not file_path.exists():
        print(f"[ERROR] ❌ Archivo no encontrado: {file_path}")
        return False
    
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"\n[INFO] Subiendo: {file_path.name} ({file_size_mb:.2f} MB)")
    print(f"[INFO] Esto puede tardar varios minutos...")
    
    url = f"https://uploads.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/{release_id}/assets?name={file_path.name}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/octet-stream",
        "Accept": "application/vnd.github+json"
    }
    
    with open(file_path, 'rb') as f:
        response = requests.post(url, data=f, headers=headers, timeout=300)
    
    if response.status_code == 201:
        print(f"[SUCCESS] ✅ {file_path.name} subido exitosamente")
        return True
    else:
        print(f"[ERROR] ❌ Error subiendo {file_path.name}: {response.status_code}")
        print(f"[ERROR] {response.text}")
        return False

def main():
    print("=" * 60)
    print("SUBIENDO ÍNDICE FAISS A GITHUB RELEASE - V2")
    print("=" * 60)
    
    # Crear o obtener release
    release_data = create_release()
    if not release_data:
        print("\n[ERROR] ❌ No se pudo crear/obtener el release")
        return False
    
    release_id = release_data['id']
    print(f"\n[INFO] Release ID: {release_id}")
    
    # Subir archivos
    success = True
    for file_path in FILES_TO_UPLOAD:
        if not upload_file(release_id, file_path):
            success = False
    
    if success:
        print("\n" + "=" * 60)
        print("✅ TODOS LOS ARCHIVOS SUBIDOS EXITOSAMENTE")
        print("=" * 60)
        print(f"\n[INFO] URL del Release:")
        print(f"       {release_data['html_url']}")
    else:
        print("\n" + "=" * 60)
        print("❌ ALGUNOS ARCHIVOS NO SE SUBIERON")
        print("=" * 60)
    
    return success

if __name__ == "__main__":
    main()
