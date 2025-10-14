"""
Fix definitivo: Usar archivo .faiss_downloaded como marca persistente
El session_state no persiste entre recargas, usamos archivo en disco
"""
import re

with open('consultar_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el bloque de descarga actual
old_code = '''            # === DESCARGA DEL INDICE FAISS DESDE GITHUB RELEASE ===
            if not os.path.exists("faiss_index/index.faiss"):
                # Verificar si ya se intento descargar en esta sesion
                if "faiss_downloaded" not in st.session_state:
                    st.session_state.faiss_downloaded = False
                
                if not st.session_state.faiss_downloaded:'''

# Nuevo código con archivo de marca
new_code = '''            # === DESCARGA DEL INDICE FAISS DESDE GITHUB RELEASE ===
            # Usar archivo .faiss_ready como marca persistente (mas confiable que session_state)
            faiss_ready_marker = "faiss_index/.faiss_ready"
            
            if not os.path.exists(faiss_ready_marker):'''

content_new = content.replace(old_code, new_code)

# También cambiar donde se marca como descargado
old_mark = '''                        st.session_state.faiss_downloaded = True
                        progress_bar.empty()
                        status_text.empty()
                        st.success("[OK] Indice descargado! No se volvera a descargar.")'''

new_mark = '''                        # Crear archivo de marca para evitar descargas futuras
                        with open(faiss_ready_marker, 'w') as f:
                            f.write("ready")
                        
                        progress_bar.empty()
                        status_text.empty()
                        st.success("[OK] Indice descargado! No se volvera a descargar.")'''

content_new = content_new.replace(old_mark, new_mark)

if content != content_new:
    with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(content_new)
    print("[OK] Fix aplicado: Archivo .faiss_ready como marca persistente")
    print()
    print("Como funciona:")
    print("  1. Descarga el indice")
    print("  2. Crea archivo faiss_index/.faiss_ready")
    print("  3. En proximas cargas: ve el archivo -> NO descarga")
    print()
    print("Ventaja: El archivo persiste en el contenedor de Streamlit Cloud")
else:
    print("[!] No se pudo aplicar el fix - patron no encontrado")
