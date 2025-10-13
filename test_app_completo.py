"""
Test completo de funcionalidad de GERARD v2.0
Verifica que todos los componentes funcionen correctamente
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test 1: Verificar que todas las dependencias se importen correctamente"""
    print("\n" + "="*60)
    print("TEST 1: VERIFICACIÓN DE IMPORTS")
    print("="*60)
    
    try:
        import streamlit as st
        print("✅ Streamlit importado")
        
        from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
        print("✅ LangChain Google GenAI importado")
        
        from langchain_community.vectorstores import FAISS
        print("✅ FAISS importado")
        
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        print("✅ Text Splitter importado")
        
        return True
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        return False

def test_api_key():
    """Test 2: Verificar que la API key esté configurada"""
    print("\n" + "="*60)
    print("TEST 2: VERIFICACIÓN DE API KEY")
    print("="*60)
    
    api_key = os.getenv('GOOGLE_API_KEY')
    
    if api_key:
        print(f"✅ API Key encontrada: {api_key[:20]}...")
        return True
    else:
        print("❌ API Key no encontrada en variables de entorno")
        return False

def test_faiss_index():
    """Test 3: Verificar que el índice FAISS existe y es válido"""
    print("\n" + "="*60)
    print("TEST 3: VERIFICACIÓN DE ÍNDICE FAISS")
    print("="*60)
    
    faiss_path = Path("faiss_index")
    
    if not faiss_path.exists():
        print("❌ Carpeta faiss_index no existe")
        return False
    
    index_file = faiss_path / "index.faiss"
    pkl_file = faiss_path / "index.pkl"
    
    if not index_file.exists():
        print("❌ Archivo index.faiss no existe")
        return False
    
    if not pkl_file.exists():
        print("❌ Archivo index.pkl no existe")
        return False
    
    index_size = index_file.stat().st_size / (1024 * 1024)  # MB
    pkl_size = pkl_file.stat().st_size / (1024 * 1024)  # MB
    
    print(f"✅ index.faiss encontrado: {index_size:.2f} MB")
    print(f"✅ index.pkl encontrado: {pkl_size:.2f} MB")
    print(f"✅ Tamaño total: {index_size + pkl_size:.2f} MB")
    
    return True

def test_load_faiss():
    """Test 4: Intentar cargar el índice FAISS"""
    print("\n" + "="*60)
    print("TEST 4: CARGA DE ÍNDICE FAISS")
    print("="*60)
    
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain_community.vectorstores import FAISS
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("❌ No se puede cargar FAISS sin API key")
            return False
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        print("⏳ Cargando índice FAISS...")
        vectorstore = FAISS.load_local(
            "faiss_index",
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Verificar número de documentos
        index_size = vectorstore.index.ntotal
        print(f"✅ Índice FAISS cargado exitosamente")
        print(f"✅ Número de chunks: {index_size:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cargando FAISS: {e}")
        return False

def test_query():
    """Test 5: Hacer una consulta de prueba"""
    print("\n" + "="*60)
    print("TEST 5: CONSULTA DE PRUEBA")
    print("="*60)
    
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
        from langchain_community.vectorstores import FAISS
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("❌ No se puede hacer consulta sin API key")
            return False
        
        # Cargar índice
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        print("⏳ Cargando índice...")
        vectorstore = FAISS.load_local(
            "faiss_index",
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Hacer búsqueda
        pregunta = "QUIEN ES EL PADRE"
        print(f"\n📝 Pregunta: {pregunta}")
        print("⏳ Buscando contexto relevante...")
        
        docs = vectorstore.similarity_search(pregunta, k=4)
        
        print(f"✅ Encontrados {len(docs)} documentos relevantes")
        
        if docs:
            print("\n📄 Primer documento:")
            print(f"   Fuente: {docs[0].metadata.get('source', 'Desconocido')}")
            print(f"   Contenido (primeros 200 chars): {docs[0].page_content[:200]}...")
            return True
        else:
            print("❌ No se encontraron documentos")
            return False
            
    except Exception as e:
        print(f"❌ Error en consulta: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdf_exists():
    """Test 6: Verificar que el PDF de la guía existe"""
    print("\n" + "="*60)
    print("TEST 6: VERIFICACIÓN DE PDF")
    print("="*60)
    
    pdf_path = Path("assets") / "Guia_GERARD.pdf"
    
    if not pdf_path.exists():
        print("❌ Archivo Guia_GERARD.pdf no existe")
        return False
    
    pdf_size = pdf_path.stat().st_size / 1024  # KB
    print(f"✅ Guia_GERARD.pdf encontrado: {pdf_size:.2f} KB")
    
    if pdf_size < 10:
        print("⚠️ Advertencia: PDF muy pequeño, podría estar corrupto")
        return False
    
    return True

def test_encoding():
    """Test 7: Verificar función de fix de encoding"""
    print("\n" + "="*60)
    print("TEST 7: VERIFICACIÓN DE ENCODING UTF-8")
    print("="*60)
    
    def fix_encoding(text: str) -> str:
        """Función de fix de encoding (copiada de consultar_web.py)"""
        try:
            if any(char in text for char in ['Â', 'Ã', 'â']):
                return text.encode('latin-1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        return text
    
    # Tests
    tests = [
        ("PREGUNTAÂ¡", "PREGUNTA¡"),
        ("â CÃ³mo", "¿Cómo"),
        ("niÃ±o", "niño"),
        ("Text normal", "Text normal")
    ]
    
    all_passed = True
    for input_text, expected in tests:
        result = fix_encoding(input_text)
        if result == expected:
            print(f"✅ '{input_text}' → '{result}'")
        else:
            print(f"❌ '{input_text}' → '{result}' (esperado: '{expected}')")
            all_passed = False
    
    return all_passed

def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*60)
    print("🧪 TEST COMPLETO DE GERARD v2.0")
    print("="*60)
    print(f"Directorio: {os.getcwd()}")
    print(f"Python: {sys.version}")
    
    results = {
        "Imports": test_imports(),
        "API Key": test_api_key(),
        "Índice FAISS (archivos)": test_faiss_index(),
        "Carga de FAISS": test_load_faiss(),
        "Consulta de prueba": test_query(),
        "PDF de guía": test_pdf_exists(),
        "Fix de encoding": test_encoding()
    }
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*60)
    print(f"RESULTADO FINAL: {passed}/{total} tests pasados")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("✅ La aplicación está lista para producción")
    else:
        print(f"\n⚠️ {total - passed} test(s) fallaron")
        print("⚠️ Revisar los errores antes de desplegar")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
