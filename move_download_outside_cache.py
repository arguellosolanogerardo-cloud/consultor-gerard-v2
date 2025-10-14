"""
Mover descarga FUERA de @st.cache_resource
"""

with open('consultar_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar dónde termina load_resources()
# La idea es mover la descarga ANTES de @st.cache_resource

# Paso 1: Eliminar el bloque de descarga de dentro de load_resources()
old_download_block = '''            # === DESCARGA DEL ÍNDICE FAISS DESDE GITHUB RELEASE ===
            # Usar archivo .faiss_ready como marca persistente
            faiss_marker = "faiss_index/.faiss_ready"
            if os.path.exists(faiss_marker):
                pass  # Ya descargado previamente
            elif not os.path.exists("faiss_index/index.faiss"):
                st.info("[>] Descargando indice FAISS pre-construido...")
                st.info("[tiempo] Descarga unica (~250 MB, espera 1-2 min)")
                
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
                                status_text.text(f"[>] {progress}% descargado ({downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB)")
                    
                    status_text.text("[paquete] Extrayendo...")
                    os.makedirs("faiss_index", exist_ok=True)
                    zip_data.seek(0)
                    with zipfile.ZipFile(zip_data) as zf:
                        zf.extractall("faiss_index")
                    
                    # Crear archivo de marca para evitar descargas futuras
                    with open(faiss_marker, "w") as f:
                        f.write("downloaded")
                    
                    progress_bar.empty()
                    status_text.empty()
                    st.success("[OK] Indice descargado! No se volvera a descargar.")
                    
                except Exception as e:
                    st.error(f"[ERROR] Error descargando: {str(e)}")
                    raise
            # === FIN DESCARGA ===

'''

# Reemplazar por un comentario simple
new_placeholder = '''            # === DESCARGA MOVIDA FUERA DE CACHE ===
            # Ver funcion download_faiss_if_needed() antes de load_resources()
            
'''

content = content.replace(old_download_block, new_placeholder)

# Paso 2: Agregar la función de descarga ANTES de @st.cache_resource
insertion_point = '# --- Carga de Modelos y Base de Datos (con cachÃ© de Streamlit) ---\n@st.cache_resource'

new_function = '''# --- Descarga del Ã­ndice FAISS (ANTES del cache) ---
def download_faiss_if_needed():
    """Descarga el Ã­ndice FAISS si no existe. Ejecutar ANTES de load_resources()."""
    import streamlit as st
    
    faiss_marker = "faiss_index/.faiss_ready"
    
    # Verificar si ya existe
    if os.path.exists(faiss_marker):
        return  # Ya descargado
    
    if not os.path.exists("faiss_index/index.faiss"):
        st.info("[>] Descargando indice FAISS pre-construido...")
        st.info("[tiempo] Descarga unica (~250 MB, espera 1-2 min)")
        
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
                        status_text.text(f"[>] {progress}% descargado ({downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB)")
            
            status_text.text("[paquete] Extrayendo...")
            os.makedirs("faiss_index", exist_ok=True)
            zip_data.seek(0)
            with zipfile.ZipFile(zip_data) as zf:
                zf.extractall("faiss_index")
            
            # Crear archivo de marca
            with open(faiss_marker, "w") as f:
                f.write("downloaded")
            
            progress_bar.empty()
            status_text.empty()
            st.success("[OK] Indice descargado! No se volvera a descargar.")
            
        except Exception as e:
            st.error(f"[ERROR] Error descargando: {str(e)}")
            raise

# --- Carga de Modelos y Base de Datos (con cachÃ© de Streamlit) ---
@st.cache_resource'''

content = content.replace(insertion_point, new_function)

# Guardar
with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("[OK] Descarga movida FUERA de @st.cache_resource")
print()
print("Cambios:")
print("  1. Nueva funcion: download_faiss_if_needed()")
print("  2. Se ejecuta ANTES de load_resources()")
print("  3. No esta afectada por el cache")
print()
print("IMPORTANTE: Necesitas llamar download_faiss_if_needed() en main()")
