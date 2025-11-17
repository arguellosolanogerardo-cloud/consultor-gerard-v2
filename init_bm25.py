"""
Script de inicialización para generar bm25_index.pkl en Streamlit Cloud
Se ejecuta automáticamente si el índice no existe
"""

import os
import sys

def init_bm25_index():
    """Genera el índice BM25 si no existe"""
    
    # Verificar si ya existe
    if os.path.exists("bm25_index.pkl"):
        print("[INFO] bm25_index.pkl ya existe, no se requiere generación")
        return True
    
    print("[INFO] bm25_index.pkl no encontrado, generando...")
    
    try:
        # Importar el creador de índice
        from crear_indice_bm25 import main as crear_indice
        
        # Ejecutar creación
        print("[INFO] Iniciando generación de índice BM25...")
        crear_indice()
        
        # Verificar creación exitosa
        if os.path.exists("bm25_index.pkl"):
            size_mb = os.path.getsize("bm25_index.pkl") / (1024 * 1024)
            print(f"[SUCCESS] ✅ Índice BM25 creado exitosamente ({size_mb:.2f} MB)")
            return True
        else:
            print("[ERROR] ❌ Falló la creación del índice")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error al generar índice BM25: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_bm25_index()
    sys.exit(0 if success else 1)
