"""
Fix definitivo para descargas repetidas - Usar archivo .faiss_ready
"""
import re

with open('consultar_web.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar las líneas exactas a modificar
new_lines = []
inside_download = False
indent_fixed = False

for i, line in enumerate(lines):
    # Encontrar inicio del bloque de descarga
    if '# === DESCARGA DEL INDICE FAISS DESDE GITHUB RELEASE ===' in line:
        new_lines.append(line)
        new_lines.append('            # Usar archivo .faiss_ready como marca persistente\n')
        new_lines.append('            faiss_ready_marker = "faiss_index/.faiss_ready"\n')
        new_lines.append('            \n')
        inside_download = True
        continue
    
    # Reemplazar la verificación complicada con session_state por una simple
    if inside_download and 'if not os.path.exists("faiss_index/index.faiss"):' in line:
        new_lines.append('            if not os.path.exists(faiss_ready_marker):\n')
        # Saltar las siguientes 4 líneas (session_state checks)
        for _ in range(5):  # Saltar verificaciones de session_state
            i += 1
            if i < len(lines):
                next()
        continue
    
    # Reemplazar donde se marca como descargado
    if inside_download and 'st.session_state.faiss_downloaded = True' in line:
        new_lines.append('                        # Crear archivo de marca\n')
        new_lines.append('                        with open(faiss_ready_marker, "w") as f:\n')
        new_lines.append('                            f.write("ready")\n')
        new_lines.append('                        \n')
        continue
    
    # Marcar fin del bloque
    if inside_download and '# === FIN DESCARGA ===' in line:
        inside_download = False
    
    new_lines.append(line)

# Guardar
with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(new_lines)

print("[OK] Fix aplicado con archivo .faiss_ready")
print()
print("Cambios:")
print("  - Usa faiss_index/.faiss_ready como marca")
print("  - No depende de session_state")
print("  - Persiste entre reinicios del contenedor")
