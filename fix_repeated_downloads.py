"""
Fix definitivo: Evitar descargas repetidas usando session_state
"""
import re

with open('consultar_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el bloque de descarga actual (sin bytes, string normal)
pattern = r'# === DESCARGA DEL.*?FAISS DESDE GITHUB RELEASE ===.*?# === FIN DESCARGA ==='

# Nuevo código con session_state para evitar repeticiones
replacement = '''# === DESCARGA DEL ÍNDICE FAISS DESDE GITHUB RELEASE ===
            if not os.path.exists("faiss_index/index.faiss"):
                # Verificar si ya se intentó descargar en esta sesión
                if "faiss_downloaded" not in st.session_state:
                    st.session_state.faiss_downloaded = False
                
                if not st.session_state.faiss_downloaded:
                    st.info("📥 Descargando índice FAISS pre-construido...")
                    st.info("⏱️ Descarga única (~250 MB, espera 1-2 min)")
                    
                    try:
                        import requests
                        import zipfile
                        from io import BytesIO
                        
                        FAISS_URL = "https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2/releases/download/faiss-v1.0/faiss_index.zip"
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        with st.spinner("Descargando..."):
                            response = requests.get(FAISS_URL, stream=True, timeout=600)
                            response.raise_for_status()
                            
                            total_size = int(response.headers.get('content-length', 0))
                            downloaded = 0
                            zip_data = BytesIO()
                            
                            for chunk in response.iter_content(chunk_size=1024*1024):
                                zip_data.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = int((downloaded / total_size) * 100)
                                    progress_bar.progress(progress / 100)
                                    status_text.text(f"📥 {progress}% descargado ({downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB)")
                        
                        status_text.text("📦 Extrayendo...")
                        os.makedirs("faiss_index", exist_ok=True)
                        zip_data.seek(0)
                        with zipfile.ZipFile(zip_data) as zf:
                            zf.extractall("faiss_index")
                        
                        st.session_state.faiss_downloaded = True
                        progress_bar.empty()
                        status_text.empty()
                        st.success("✅ Índice descargado! No se volverá a descargar.")
                        
                    except Exception as e:
                        st.error(f"❌ Error descargando: {str(e)}")
                        raise
            # === FIN DESCARGA ==='''

content_new = re.sub(pattern, replacement, content, flags=re.DOTALL)

if content != content_new:
    with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(content_new)
    print("✅ Fix aplicado: session_state evitará descargas repetidas")
    print("📍 Ahora solo descargará si:")
    print("   1. No existe el índice localmente")
    print("   2. No se ha descargado ya en esta sesión del usuario")
else:
    print("⚠️ No se encontró el patrón a reemplazar")
