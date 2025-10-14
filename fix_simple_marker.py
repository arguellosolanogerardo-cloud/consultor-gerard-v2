"""
Solucion simple: Agregar archivo .faiss_ready y verificarlo al inicio
"""

with open('consultar_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Paso 1: Agregar verificacion al inicio del bloque
old_start = '''            # === DESCARGA DEL INDICE FAISS DESDE GITHUB RELEASE ===
            if not os.path.exists("faiss_index/index.faiss"):'''

new_start = '''            # === DESCARGA DEL INDICE FAISS DESDE GITHUB RELEASE ===
            # Verificar archivo de marca (persiste entre sesiones)
            faiss_marker = "faiss_index/.faiss_ready"
            if os.path.exists(faiss_marker):
                pass  # Ya descargado previamente
            elif not os.path.exists("faiss_index/index.faiss"):'''

content = content.replace(old_start, new_start)

# Paso 2: Crear el archivo de marca despues de extraccion exitosa
old_extract = '''                        with zipfile.ZipFile(zip_data) as zf:
                            zf.extractall("faiss_index")

                        # Crear archivo de marca para evitar descargas futuras
                        with open(faiss_ready_marker, 'w') as f:
                            f.write("ready")'''

new_extract = '''                        with zipfile.ZipFile(zip_data) as zf:
                            zf.extractall("faiss_index")
                        
                        # Crear archivo de marca para evitar descargas futuras
                        with open(faiss_marker, 'w') as f:
                            f.write("downloaded")'''

content = content.replace(old_extract, new_extract)

# Guardar
with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("[OK] Solucion aplicada")
print()
print("Logica:")
print("  1. Verificar si existe faiss_index/.faiss_ready")
print("  2. Si existe: skip (ya descargado)")
print("  3. Si no: descargar y crear el archivo")
print("  4. Proximas veces: detecta el archivo y no descarga")
