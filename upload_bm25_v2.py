
import os
import sys
import requests
from pathlib import Path

# Configuración
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
# Si no está en env, intentar leer de un archivo temporal si existiera (o pedir al usuario)
if not GITHUB_TOKEN:
    # Intentar buscar en args o input
    if len(sys.argv) > 1:
        GITHUB_TOKEN = sys.argv[1]
    else:
        print("[ERROR] ❌ GITHUB_TOKEN no encontrado. Ejecuta: python upload_bm25_v2.py TU_TOKEN")
        sys.exit(1)

REPO_OWNER = "arguellosolanogerardo-cloud"
REPO_NAME = "consultor-gerard-v2"
RELEASE_TAG = "faiss-index-v1"

# Archivo a subir
FILE_TO_UPLOAD = Path("bm25_index.pkl")

def get_release_id():
    """Obtiene el ID del release existente"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{RELEASE_TAG}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['id']
    else:
        print(f"[ERROR] ❌ No se encontró el release {RELEASE_TAG}: {response.status_code}")
        return None

def upload_file(release_id, file_path):
    """Sube un archivo al release"""
    if not file_path.exists():
        print(f"[ERROR] ❌ Archivo no encontrado: {file_path}")
        return False
    
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"\n[INFO] Subiendo: {file_path.name} ({file_size_mb:.2f} MB)")
    
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
    elif response.status_code == 422:
        print(f"[WARNING] ⚠️ El archivo ya existe en el release.")
        return True
    else:
        print(f"[ERROR] ❌ Error subiendo {file_path.name}: {response.status_code}")
        print(f"[ERROR] {response.text}")
        return False

def main():
    print("=" * 60)
    print("SUBIENDO ÍNDICE BM25 A GITHUB RELEASE")
    print("=" * 60)
    
    release_id = get_release_id()
    if not release_id:
        return
    
    upload_file(release_id, FILE_TO_UPLOAD)

if __name__ == "__main__":
    main()
