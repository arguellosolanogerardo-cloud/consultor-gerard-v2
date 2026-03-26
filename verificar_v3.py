from langchain_community.vectorstores import FAISS
from langchain_google_vertexai import VertexAIEmbeddings
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google_credentials.json'

print("Verificando índice descargado de v3...")
emb = VertexAIEmbeddings(
    model_name='text-multilingual-embedding-002',
    project='midyear-node-436821-t3'
)

try:
    faiss = FAISS.load_local('faiss_download_v3', embeddings=emb, allow_dangerous_deserialization=True)
    docs = list(faiss.docstore._dict.values())
    docs_725 = [d for d in docs if '725' in d.metadata.get('source', '')]
    
    print(f"\n✅ Índice de v3 cargado correctamente")
    print(f"   Total docs: {len(docs)}")
    print(f"   Docs con '725': {len(docs_725)}")
    
    if docs_725:
        print("\n   ✅ ¡TIENE DOCUMENTOS CON 725!")
        print("\n   Archivos únicos con '725':")
        sources = set([os.path.basename(d.metadata.get('source')) for d in docs_725])
        for s in sorted(sources):
            print(f"      • {s}")
    else:
        print("\n   ❌ NO TIENE DOCUMENTOS CON '725'")
        print("   Necesitaremos regenerar el índice")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
