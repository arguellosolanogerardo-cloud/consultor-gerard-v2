"""
Script para comprimir y subir índice FAISS a GitHub Release
SOLUCIÓN DEFINITIVA: Nunca más reconstruir
"""
import os
import zipfile
import requests
from pathlib import Path

# Configuración
FAISS_DIR = Path(r"e:\proyecto-gemini-limpio\faiss_index")
OUTPUT_ZIP = Path(r"e:\proyecto-gemini-limpio\faiss_index.zip")
GITHUB_TOKEN = input("Pega tu GitHub Personal Access Token: ").strip()
REPO = "arguellosolanogerardo-cloud/consultor-gerard-v2"
TAG = "faiss-v1.0"

print("\n🗜️  PASO 1: Comprimiendo índice FAISS...")
print(f"   Origen: {FAISS_DIR}")
print(f"   Destino: {OUTPUT_ZIP}\n")

# Comprimir
with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
    for file in FAISS_DIR.glob("*"):
        if file.is_file():
            print(f"   Comprimiendo: {file.name}")
            zipf.write(file, file.name)

zip_size_mb = OUTPUT_ZIP.stat().st_size / 1024 / 1024
print(f"\n✅ Comprimido: {zip_size_mb:.2f} MB\n")

print("📤 PASO 2: Creando GitHub Release...")

# Crear release
url = f"https://api.github.com/repos/{REPO}/releases"
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

release_data = {
    "tag_name": TAG,
    "name": f"FAISS Index {TAG}",
    "body": f"Índice FAISS pre-construido\n- 41,109 chunks\n- Tamaño: {zip_size_mb:.2f} MB comprimido\n- Fecha: 2025-10-13",
    "draft": False,
    "prerelease": False
}

print(f"   Repository: {REPO}")
print(f"   Tag: {TAG}\n")

response = requests.post(url, json=release_data, headers=headers)

if response.status_code == 201:
    release = response.json()
    release_id = release["id"]
    upload_url = release["upload_url"].replace("{?name,label}", "")
    print(f"✅ Release creado: {release['html_url']}\n")
    
    print("📤 PASO 3: Subiendo archivo comprimido...")
    print(f"   Tamaño: {zip_size_mb:.2f} MB")
    print("   Esto puede tomar 2-5 minutos...\n")
    
    # Subir archivo
    with open(OUTPUT_ZIP, 'rb') as f:
        upload_headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/zip"
        }
        upload_response = requests.post(
            f"{upload_url}?name=faiss_index.zip",
            headers=upload_headers,
            data=f
        )
    
    if upload_response.status_code == 201:
        asset = upload_response.json()
        download_url = asset["browser_download_url"]
        print(f"✅ Archivo subido exitosamente!\n")
        print(f"📥 URL de descarga:")
        print(f"   {download_url}\n")
        print("="*60)
        print("✅✅✅ ÉXITO TOTAL")
        print("="*60)
        print("\n🎯 PRÓXIMO PASO:")
        print("   Modificar consultar_web.py para descargar desde Release")
        print("   (Script automático preparado)\n")
        
        # Guardar URL para siguiente paso
        with open("faiss_download_url.txt", "w") as f:
            f.write(download_url)
        
    else:
        print(f"❌ Error subiendo archivo: {upload_response.status_code}")
        print(upload_response.text)
else:
    print(f"❌ Error creando release: {response.status_code}")
    print(response.text)
    if response.status_code == 422:
        print("\n💡 El release ya existe. Eliminando y reintentando...")
        # Eliminar release existente
        get_url = f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}"
        get_response = requests.get(get_url, headers=headers)
        if get_response.status_code == 200:
            release_id = get_response.json()["id"]
            delete_url = f"https://api.github.com/repos/{REPO}/releases/{release_id}"
            requests.delete(delete_url, headers=headers)
            print("   Release eliminado. Ejecuta el script de nuevo.")
