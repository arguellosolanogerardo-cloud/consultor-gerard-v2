"""
Modificar consultar_web.py para descargar desde Release
"""

# Leer URL
with open('faiss_download_url.txt', 'r') as f:
    DOWNLOAD_URL = f.read().strip()

print(f"📥 URL: {DOWNLOAD_URL}\n")

# Leer archivo
with open('consultar_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el código actual
old_code = '''            # === AUTO-CONSTRUCCIÓN DEL ÍNDICE FAISS ===
            if not os.path.exists("faiss_index/index.faiss"):
                st.warning("🔨 Índice FAISS no encontrado. Construyendo automáticamente...")
                st.info("⏱️ Este proceso tomará aproximadamente 25-30 minutos. Por favor espera...")

                try:
                    from auto_build_index import build_faiss_index
                    success = build_faiss_index(api_key, force=True)

                    if success:
                        st.success("✅ Índice FAISS construido exitosamente!")
                    else:
                        st.error("❌ Error construyendo el índice FAISS")
                        raise Exception("Failed to build FAISS index")
                except ImportError:
                    st.error("❌ auto_build_index.py no encontrado")
                    raise
                except Exception as e:
                    st.error(f"❌ Error en construcción: {str(e)}")
                    raise
            # === FIN AUTO-CONSTRUCCIÓN ==='''

new_code = f'''            # === DESCARGA DEL ÍNDICE FAISS DESDE GITHUB RELEASE ===
            if not os.path.exists("faiss_index/index.faiss"):
                st.info("📥 Descargando índice FAISS pre-construido...")
                st.info("⏱️ Descarga única de ~80 MB (30-60 segundos)")
                
                try:
                    import requests
                    import zipfile
                    from io import BytesIO
                    
                    FAISS_URL = "{DOWNLOAD_URL}"
                    
                    with st.spinner("Descargando índice..."):
                        response = requests.get(FAISS_URL, stream=True, timeout=300)
                        response.raise_for_status()
                        
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        zip_data = BytesIO()
                        
                        for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                            zip_data.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and downloaded % (10*1024*1024) == 0:  # Every 10MB
                                progress = int((downloaded / total_size) * 100)
                                st.info(f"📥 {{progress}}% descargado...")
                    
                    st.info("📦 Extrayendo archivos...")
                    os.makedirs("faiss_index", exist_ok=True)
                    zip_data.seek(0)
                    with zipfile.ZipFile(zip_data) as zf:
                        zf.extractall("faiss_index")
                    
                    st.success("✅ Índice descargado y listo (no se volverá a descargar)")
                    
                except Exception as e:
                    st.error(f"❌ Error descargando índice: {{str(e)}}")
                    st.info("💡 Si persiste, contacta al administrador")
                    raise
            # === FIN DESCARGA ==='''

# Reemplazar
content = content.replace(old_code, new_code)

# Escribir
with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("✅ consultar_web.py modificado exitosamente\n")
print("🎯 CAMBIO APLICADO:")
print("   ❌ Antes: Construir 30 min + $$$ API")
print("   ✅ Ahora: Descargar 30 seg + $0\n")
