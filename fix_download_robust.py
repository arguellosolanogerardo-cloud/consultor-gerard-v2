"""
Reemplazo robusto del código de auto-construcción
"""
import re

# Leer URL
with open('faiss_download_url.txt', 'r') as f:
    DOWNLOAD_URL = f.read().strip()

# Leer archivo como bytes para manejar encodings mixtos
with open('consultar_web.py', 'rb') as f:
    content = f.read()

# Buscar y reemplazar con regex (usando bytes)
pattern = rb'# === AUTO-CONSTRUCCI.*?# === FIN AUTO-CONSTRUCCI.*?==='
replacement = f'''# === DESCARGA DEL ÍNDICE FAISS DESDE GITHUB RELEASE ===
            if not os.path.exists("faiss_index/index.faiss"):
                st.info("📥 Descargando índice FAISS pre-construido...")
                st.info("⏱️ Descarga única (~80 MB, 30-60 segundos)")
                
                try:
                    import requests
                    import zipfile
                    from io import BytesIO
                    
                    FAISS_URL = "{DOWNLOAD_URL}"
                    
                    with st.spinner("Descargando..."):
                        response = requests.get(FAISS_URL, stream=True, timeout=300)
                        response.raise_for_status()
                        
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        zip_data = BytesIO()
                        
                        for chunk in response.iter_content(chunk_size=1024*1024):
                            zip_data.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and downloaded % (10*1024*1024) == 0:
                                progress = int((downloaded / total_size) * 100)
                                st.info(f"📥 {{progress}}% descargado")
                    
                    st.info("📦 Extrayendo...")
                    os.makedirs("faiss_index", exist_ok=True)
                    zip_data.seek(0)
                    with zipfile.ZipFile(zip_data) as zf:
                        zf.extractall("faiss_index")
                    
                    st.success("✅ Listo! (no se volverá a descargar)")
                    
                except Exception as e:
                    st.error(f"❌ Error: {{str(e)}}")
                    raise
            # === FIN DESCARGA ==='''.encode('utf-8')

# Reemplazar
content_new = re.sub(pattern, replacement, content, flags=re.DOTALL)

if content != content_new:
    # Escribir
    with open('consultar_web.py', 'wb') as f:
        f.write(content_new)
    print("✅ Reemplazo exitoso\n")
else:
    print("⚠️  No se encontró el patrón para reemplazar\n")
