"""
Script para generar automáticamente el índice FAISS si no existe.
Se ejecuta automáticamente desde consultar_web.py en Streamlit Cloud.
"""

import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS

def build_faiss_index(api_key: str, force: bool = False):
    """
    Construye el índice FAISS desde documentos_srt/ si no existe.
    
    Args:
        api_key: Google API Key para embeddings
        force: Si True, reconstruye aunque ya exista
    """
    DATA_PATH = "documentos_srt/"
    FAISS_INDEX_PATH = "faiss_index"
    
    # Verificar si ya existe el índice
    if os.path.exists(FAISS_INDEX_PATH) and not force:
        print(f"✅ Índice FAISS ya existe en {FAISS_INDEX_PATH}")
        return True
    
    # Verificar que existen documentos
    if not os.path.exists(DATA_PATH):
        print(f"❌ No se encontró la carpeta {DATA_PATH}")
        return False
    
    print(f"🔨 Construyendo índice FAISS desde {DATA_PATH}...")
    
    try:
        # Cargar documentos .srt
        loader = DirectoryLoader(
            DATA_PATH,
            glob="**/*.srt",
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'}
        )
        documents = loader.load()
        
        if not documents:
            print(f"❌ No se encontraron archivos .srt en {DATA_PATH}")
            return False
        
        print(f"📄 Cargados {len(documents)} documentos")
        
        # Dividir en chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        print(f"✂️ Creados {len(chunks)} chunks")
        
        # Crear embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        print("🧠 Generando embeddings...")
        
        # Crear índice FAISS
        vectorstore = FAISS.from_documents(chunks, embeddings)
        
        # Guardar
        vectorstore.save_local(FAISS_INDEX_PATH)
        print(f"💾 Índice FAISS guardado en {FAISS_INDEX_PATH}")
        print(f"✅ Construcción exitosa: {len(chunks)} chunks indexados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error construyendo índice FAISS: {e}")
        import traceback
        traceback.print_exc()
        return False
