"""
Script para subir índice FAISS a GitHub Release
Ejecutar SOLO UNA VEZ para crear el release con el índice

IMPORTANTE: Este script ya se ejecutó y el release está creado.
No necesitas ejecutarlo de nuevo a menos que quieras actualizar el índice.
"""
import requests
import os

# ========== CONFIGURACIÓN ==========
GITHUB_TOKEN = "TU_TOKEN_AQUI"  # ← PEGA TU TOKEN AQUÍ (NO LO SUBAS A GITHUB)
REPO = "arguellosolanogerardo-cloud/consultor-gerard-v2"
TAG = "faiss-index-v2"
RELEASE_NAME = "FAISS Index v2"
FAISS_DIR = "faiss_index"

print("🚀 Iniciando upload de índice FAISS a GitHub Release...")

# ========== 1. Crear Release ==========
print(f"\n📦 Creando release '{TAG}'...")
url = f"https://api.github.com/repos/{REPO}/releases"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

response = requests.post(url, json={
    "tag_name": TAG,
    "name": RELEASE_NAME,
    "body": "Índice FAISS completo para consultor-gerard-v2\\n\\nArchivos:\\n- index.faiss (253 MB)\\n- index.pkl (83 MB)\\n\\nTotal: ~337 MB",
    "draft": False,
    "prerelease": False
}, headers=headers)

if response.status_code == 201:
    release_id = response.json()["id"]
    print(f"✅ Release creado exitosamente (ID: {release_id})")
elif response.status_code == 422:
    # El release ya existe, obtener su ID
    print("ℹ️ Release ya existe, obteniendo ID...")
    response = requests.get(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}", headers=headers)
    release_id = response.json()["id"]
    print(f"✅ Release encontrado (ID: {release_id})")
else:
    print(f"❌ Error creando release: {response.status_code}")
    print(response.json())
    exit(1)

# ========== 2. Subir archivos ==========
files_to_upload = [
    ("index.faiss", "application/octet-stream"),
    ("index.pkl", "application/octet-stream"),
]

for filename, content_type in files_to_upload:
    filepath = os.path.join(FAISS_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"⚠️ Archivo no encontrado: {filepath}")
        continue
    
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"\n📤 Subiendo {filename} ({file_size_mb:.1f} MB)...")
    
    upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets?name={filename}"
    
    with open(filepath, "rb") as f:
        response = requests.post(
            upload_url,
            data=f,
            headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Content-Type": content_type
            }
        )
    
    if response.status_code == 201:
        print(f"✅ {filename} subido exitosamente")
    else:
        print(f"❌ Error subiendo {filename}: {response.status_code}")
        print(response.json())

print("\n" + "="*60)
print("✅ PROCESO COMPLETADO")
print("="*60)
print(f"\n📍 Release creado en:")
print(f"https://github.com/{REPO}/releases/tag/{TAG}")
print(f"\n🔗 URLs de descarga:")
print(f"index.faiss: https://github.com/{REPO}/releases/download/{TAG}/index.faiss")
print(f"index.pkl: https://github.com/{REPO}/releases/download/{TAG}/index.pkl")
print("\n✅ Ahora puedes ejecutar el código de la app para descargar automáticamente")
