"""
Remover emojis y acentos de consultar_web.py de forma segura
Reemplaza con texto ASCII puro
"""
import re

# Leer archivo
with open('consultar_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Mapeo de reemplazos seguros (emoji -> texto, acento -> sin acento)
replacements = {
    # Emojis -> Texto descriptivo
    '📥': '[>]',
    '⏱️': '[tiempo]',
    '📦': '[paquete]',
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[!]',
    '🔨': '[build]',
    '🔍': '[buscar]',
    
    # Acentos -> Sin acento
    'Índice': 'Indice',
    'índice': 'indice',
    'única': 'unica',
    'único': 'unico',
    'Descripción': 'Descripcion',
    'descripción': 'descripcion',
    'información': 'informacion',
    'Información': 'Informacion',
    'búsqueda': 'busqueda',
    'Búsqueda': 'Busqueda',
    'semántica': 'semantica',
    'Semántica': 'Semantica',
    'automáticamente': 'automaticamente',
    'Automáticamente': 'Automaticamente',
    'construcción': 'construccion',
    'Construcción': 'Construccion',
    'sesión': 'sesion',
    'Sesión': 'Sesion',
    'volverá': 'volvera',
    'Volverá': 'Volvera',
    'tomará': 'tomara',
    'Tomará': 'Tomara',
    'intentó': 'intento',
    'Intentó': 'Intento',
    'será': 'sera',
    'Será': 'Sera',
    'más': 'mas',
    'Más': 'Mas',
    'también': 'tambien',
    'También': 'Tambien',
    'están': 'estan',
    'Están': 'Estan',
    'está': 'esta',
    'Está': 'Esta',
    'éxito': 'exito',
    'Éxito': 'Exito',
    'exitosamente': 'exitosamente',  # ya está sin acento
    'número': 'numero',
    'Número': 'Numero',
    'código': 'codigo',
    'Código': 'Codigo',
    'válido': 'valido',
    'Válido': 'Valido',
    'inválido': 'invalido',
    'Inválido': 'Invalido',
    'límite': 'limite',
    'Límite': 'Limite',
    'limitada': 'limitada',  # ya está sin acento
    'público': 'publico',
    'Público': 'Publico',
    'después': 'despues',
    'Después': 'Despues',
    'conversación': 'conversacion',
    'Conversación': 'Conversacion',
    'exportación': 'exportacion',
    'Exportación': 'Exportacion',
    'función': 'funcion',
    'Función': 'Funcion',
}

# Aplicar reemplazos
original_content = content
for old, new in replacements.items():
    content = content.replace(old, new)

# Contar cambios
changes = sum(1 for a, b in zip(original_content, content) if a != b)

if changes > 0:
    # Guardar
    with open('consultar_web.py', 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    
    print(f"✅ Emojis y acentos removidos exitosamente")
    print(f"📊 Total de caracteres cambiados: {changes}")
    print()
    print("Ejemplos de cambios:")
    print("  📥 -> [>]")
    print("  ✅ -> [OK]")
    print("  índice -> indice")
    print("  única -> unica")
    print()
    print("⚠️  NOTA: Revisa el archivo antes de commit")
else:
    print("ℹ️  No se encontraron emojis o acentos para reemplazar")
