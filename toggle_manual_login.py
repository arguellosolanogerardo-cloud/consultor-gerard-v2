"""
Script para ocultar/mostrar el formulario de ingreso manual en app_gerard.py
Cambia el valor de ENABLE_MANUAL_LOGIN entre True y False
"""

import os

def toggle_manual_login():
    file_path = "app_gerard.py"
    
    if not os.path.exists(file_path):
        print(f"❌ Error: No se encontró el archivo {file_path}")
        return
    
    # Leer el archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Buscar y cambiar la línea de ENABLE_MANUAL_LOGIN
    modified = False
    current_state = None
    
    for i, line in enumerate(lines):
        if 'ENABLE_MANUAL_LOGIN' in line and '=' in line and not line.strip().startswith('#'):
            # Extraer el valor actual
            if 'False' in line:
                current_state = False
                # Cambiar a True
                lines[i] = line.replace('False', 'True')
                modified = True
                print(f"✅ Formulario manual ACTIVADO (ENABLE_MANUAL_LOGIN = True)")
            elif 'True' in line:
                current_state = True
                # Cambiar a False
                lines[i] = line.replace('True', 'False')
                modified = True
                print(f"✅ Formulario manual DESACTIVADO (ENABLE_MANUAL_LOGIN = False)")
            break
    
    if not modified:
        print("❌ No se encontró la variable ENABLE_MANUAL_LOGIN en el archivo")
        return
    
    # Guardar el archivo
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Mostrar el estado resultante
    if current_state == False:
        print("\n📝 Ahora se mostrará:")
        print("   - Botón 'Acceder con Google'")
        print("   - Separador '--- O ---'")
        print("   - Formulario de Ingreso Manual (Nombre, País, Ciudad)")
    else:
        print("\n📝 Ahora se mostrará:")
        print("   - SOLO el botón 'Acceder con Google'")
        print("   - El formulario manual está OCULTO")
    
    print(f"\n🔄 Recuerda reiniciar la aplicación para ver los cambios")

if __name__ == "__main__":
    print("=" * 60)
    print("   🔧 Toggle Formulario de Ingreso Manual")
    print("=" * 60)
    print()
    toggle_manual_login()
    print()
    print("=" * 60)
