"""
Script para modificar consultar_web.py: 
Descargar índice desde Release en lugar de construir
"""

# Leer URL de descarga
with open('faiss_download_url.txt', 'r') as f:
    DOWNLOAD_URL = f.read().strip()

print(f"📥 URL de descarga: {DOWNLOAD_URL}\n")

# Leer consultar_web.py
with open('consultar_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Código a reemplazar (auto-construcción)
old_code = '''    # === AUTO-CONSTRUCCIÓN DEL ÍNDICE FAISS ===
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

# Nuevo código (descarga desde Release)
new_code = f'''    # === DESCARGA DEL ÍNDICE FAISS DESDE GITHUB RELEASE ===
    if not os.path.exists("faiss_index/index.faiss"):
        st.info("📥 Descargando índice FAISS pre-construido desde GitHub...")
        st.info("⏱️ Este proceso tomará 30-60 segundos (descarga única)...")
        
        try:
            import requests
            import zipfile
            from io import BytesIO
            
            # URL del índice pre-construido
            FAISS_URL = "{DOWNLOAD_URL}"
            
            # Descargar archivo ZIP
            with st.spinner("Descargando..."):
                response = requests.get(FAISS_URL, stream=True)
                response.raise_for_status()
                
                # Total size
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                # Download with progress
                zip_data = BytesIO()
                for chunk in response.iter_content(chunk_size=8192):
                    zip_data.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if int(progress) % 10 == 0:  # Log every 10%
                            st.info(f"📥 Descargando: {{int(progress)}}%")
            
            # Extraer ZIP
            st.info("📦 Extrayendo archivos...")
            os.makedirs("faiss_index", exist_ok=True)
            with zipfile.ZipFile(zip_data) as zf:
                zf.extractall("faiss_index")
            
            st.success("✅ Índice FAISS descargado y listo!")
            st.info("💡 Este índice se reutilizará en futuros accesos (no se descarga de nuevo)")
            
        except Exception as e:
            st.error(f"❌ Error descargando índice: {{str(e)}}")
            st.error("💡 Contacta al administrador si el problema persiste")
            raise
    # === FIN DESCARGA ==='''

# Reemplazar
if old_code in content:
    content = content.replace(old_code, new_code)
    
    # Escribir archivo
    with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    print("✅ consultar_web.py modificado correctamente\n")
    print("🎯 CAMBIOS APLICADOS:")
    print("   ❌ ANTES: Construir índice (30 min, $$$ API)")
    print("   ✅ AHORA: Descargar índice (30 seg, $0)\n")
    print("📦 Próximo paso: git commit y push")
else:
    print("⚠️  No se encontró el código de auto-construcción")
    print("   (quizás ya fue modificado)\n")
