"""
Script de inicialización para generar bm25_index.pkl en Streamlit Cloud
DESHABILITADO temporalmente ya que requiere FAISS estar listo primero
"""

import os
import sys

def init_bm25_index():
    """Genera el índice BM25 si no existe"""
    
    # DESHABILITADO: Este proceso requiere que FAISS esté listo primero
    # Por ahora, simplemente retornar True para no bloquear el inicio
    print("[INFO] Inicialización de BM25 deshabilitada temporalmente")
    print("[INFO] La app funcionará solo con FAISS (que es suficiente)")
    return True

if __name__ == "__main__":
    success = init_bm25_index()
    sys.exit(0 if success else 1)
