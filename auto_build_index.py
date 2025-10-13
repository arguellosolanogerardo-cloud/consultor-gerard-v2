"""
Script para generar automáticamente el índice FAISS si no existe.
Se ejecuta automáticamente desde consultar_web.py en Streamlit Cloud.
"""

import os
import time
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
        
        # Crear embeddings con rate limit handling
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        print(f"🧠 Generando embeddings para {len(chunks)} chunks...")
        print("⏳ Esto puede tomar 10-20 minutos debido a límites de API...")
        print("🛡️ Protección contra rate limits activada (reintentos automáticos)")
        
        # Crear índice FAISS por lotes con manejo robusto de errores
        BATCH_SIZE = 50  # Reducido para menor presión en la API
        MAX_RETRIES = 3
        RETRY_DELAY = 60  # segundos entre reintentos
        
        vectorstore = None
        
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"\n📦 Procesando lote {batch_num}/{total_batches} ({len(batch)} chunks)...")
            
            # Reintentos en caso de error
            retry_count = 0
            success = False
            
            while retry_count < MAX_RETRIES and not success:
                try:
                    if vectorstore is None:
                        # Primer lote: crear vectorstore
                        vectorstore = FAISS.from_documents(batch, embeddings)
                    else:
                        # Lotes siguientes: agregar al vectorstore existente
                        batch_vs = FAISS.from_documents(batch, embeddings)
                        vectorstore.merge_from(batch_vs)
                    
                    success = True
                    print(f"✅ Lote {batch_num}/{total_batches} completado")
                    
                    # Progreso cada 10 lotes
                    if batch_num % 10 == 0:
                        print(f"🎯 PROGRESO GENERAL: {batch_num}/{total_batches} lotes completados ({(batch_num/total_batches)*100:.1f}%)")
                    
                    # Pequeña pausa entre lotes para respetar rate limits
                    if batch_num < total_batches:
                        time.sleep(2)  # 2 segundos entre lotes
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        print(f"⚠️ Error en lote {batch_num}: {str(e)}")
                        print(f"🔄 Reintentando en {RETRY_DELAY} segundos... (Intento {retry_count}/{MAX_RETRIES})")
                        time.sleep(RETRY_DELAY)
                    else:
                        print(f"❌ Error persistente en lote {batch_num} después de {MAX_RETRIES} intentos")
                        raise e
        
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
