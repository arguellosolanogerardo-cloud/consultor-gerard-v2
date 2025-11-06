# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import colorama
import streamlit as st
import requests

# Configurar UTF-8 para Streamlit Cloud
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
    
# Configurar variables de entorno para UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'
import keyring
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import uuid
from typing import Any, Iterable, List, Pattern
import streamlit.components.v1 as components
import io
import textwrap

# Importar sistema de logging completo
from interaction_logger import InteractionLogger
from device_detector import DeviceDetector
from geo_utils import GeoLocator

# Importar Google Sheets Logger (opcional, solo si está configurado)
try:
    from google_sheets_logger import create_sheets_logger
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("[!] Google Sheets Logger no disponible. Instala: pip install gspread oauth2client")

# Intentar importar reportlab para generar PDFs; si no está disponible, lo detectamos y mostramos instrucciones
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        REPORTLAB_PLATYPUS = True
    except Exception:
        REPORTLAB_PLATYPUS = False

    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# --- Configuración Inicial ---
colorama.init(autoreset=True)
load_dotenv()

# --- Descarga del índice FAISS (ANTES del cache) ---
def download_faiss_if_needed():
    """Descarga el índice FAISS si no existe. Ejecutar ANTES de load_resources()."""
    
    faiss_marker = "faiss_index/.faiss_ready"
    faiss_index_file = "faiss_index/index.faiss"
    
    # Verificar si ya está completamente descargado
    if os.path.exists(faiss_marker) and os.path.exists(faiss_index_file):
        print(f"[INFO] FAISS ya descargado - Marker: {os.path.exists(faiss_marker)}, Index: {os.path.exists(faiss_index_file)}")
        return  # Ya descargado completamente
    
    # Si solo existe el archivo pero no el marcador, crear el marcador
    if os.path.exists(faiss_index_file) and not os.path.exists(faiss_marker):
        print("[INFO] Archivo FAISS existe, creando marcador...")
        os.makedirs("faiss_index", exist_ok=True)
        with open(faiss_marker, "w") as f:
            f.write("downloaded")
        return
    
    # Solo descargar si no existe el archivo índice
    if not os.path.exists(faiss_index_file):
        print("[>] Descargando indice FAISS pre-construido...")
        print("[tiempo] Descarga unica (~250 MB, espera 1-2 min)")
        
        try:
            import requests
            import zipfile
            from io import BytesIO
            
            FAISS_URL = "https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2/releases/download/faiss-v1.0/faiss_index.zip"
            
            response = requests.get(FAISS_URL, stream=True, timeout=600)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            zip_data = BytesIO()
            
            print("[>] Iniciando descarga...")
            for chunk in response.iter_content(chunk_size=1024*1024):
                zip_data.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = int((downloaded / total_size) * 100)
                    print(f"[>] {progress}% descargado ({downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB)")
            
            print("[paquete] Extrayendo...")
            os.makedirs("faiss_index", exist_ok=True)
            zip_data.seek(0)
            with zipfile.ZipFile(zip_data) as zf:
                zf.extractall("faiss_index")
            
            # Crear archivo de marca
            with open(faiss_marker, "w") as f:
                f.write("downloaded")
            
            print("[OK] Indice descargado! No se volvera a descargar.")
            
        except Exception as e:
            print(f"[ERROR] Error descargando: {str(e)}")
            raise

# --- Carga de Modelos y Base de Datos (con caché de Streamlit) ---
@st.cache_resource
def load_resources():
    # Descargar FAISS antes de cargar (solo se ejecutará una vez debido al caché)
    download_faiss_if_needed()
    
    # Preferir la variable de entorno; en Streamlit tomar como fallback st.secrets
    api_key = os.environ.get("GOOGLE_API_KEY")
    try:
        if not api_key and hasattr(st, "secrets"):
            api_key = st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        # En entornos sin Streamlit secrets esto puede fallar; ignoramos
        pass
    # 3) intentar keyring para leer la clave cifrada (servicio 'consultor-gerard')
    if not api_key:
        try:
            kr = keyring.get_password('consultor-gerard', 'google_api_key')
            if kr:
                api_key = kr
        except Exception:
            # si keyring falla, seguimos el flujo normal y mostraremos el error abajo
            pass
    # Configurar credenciales de servicio de Google
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credencial json/midyear-node-436821-t3-525a146e96a0.json"
    
    # Intentar inicializar el LLM y embeddings
    llm = None
    embeddings = None

    with st.spinner('Inicializando LLM y embeddings usando credenciales de servicio...'):
        # Importar las clases de Google solo cuando las necesitemos, y capturar errores
        try:
            from langchain_google_genai import GoogleGenerativeAI
        except Exception as e:
            GoogleGenerativeAI = None
            st.warning(f"No se pudo importar GoogleGenerativeAI: {e}")

        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except Exception as e:
            GoogleGenerativeAIEmbeddings = None
            st.warning(f"No se pudo importar GoogleGenerativeAIEmbeddings: {e}")

        # Inicializar LLM si la clase está disponible
        if GoogleGenerativeAI is not None:
            try:
                llm = GoogleGenerativeAI(
                    model="models/gemini-1.5-pro",
                    temperature=0.4,  # Precisión quirúrgica según prompt GERARD
                    top_p=0.90,
                    top_k=25
                )
            except Exception as e:
                st.warning(f"No se pudo inicializar el LLM (GoogleGenerativeAI): {e}. La aplicación usará un modo de recuperación local sin LLM.")

    # Usar embeddings de Google
    if GoogleGenerativeAIEmbeddings is not None:
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        except Exception as e:
            st.warning(f"No se pudo inicializar embeddings de Google: {e}, usando fallback local")
            from langchain_core.embeddings import FakeEmbeddings
            embeddings = FakeEmbeddings(size=768)  # Dimensión compatible con el índice
    
    # Descargar FAISS antes de cargar
    download_faiss_if_needed()

    # Inicialización del vector store
    import hashlib
    
    # Definir dimensión del embedding por defecto
    target_dim = 768  # Dimensión estándar para embeddings
    
    try:
        import faiss
        idx_path = os.path.join('faiss_index', 'index.faiss')
        if os.path.exists(idx_path):
            idx = faiss.read_index(idx_path)
            target_dim = getattr(idx, 'd', target_dim)
    except Exception as e:
        print(f"[DEBUG] No se pudo leer dimensión de FAISS: {e}, usando {target_dim}")
        pass

    class FakeEmbeddings:
        def __init__(self, dim: int = target_dim):
            self.dim = dim

        def _text_to_vector(self, text: str) -> List[float]:
            out_bytes = b''
            counter = 0
            while len(out_bytes) < self.dim:
                h = hashlib.sha256((text + '|' + str(counter)).encode('utf-8')).digest()
                out_bytes += h
                counter += 1
            vec = [b / 255.0 for b in out_bytes[: self.dim]]
            return vec

        def embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
            return [self._text_to_vector(t) for t in texts]

        def embed_query(self, text: str) -> List[float]:
            return self._text_to_vector(text)

    # Usar los embeddings ya configurados anteriormente
    faiss_vs = FAISS.load_local(folder_path="faiss_index", embeddings=embeddings, allow_dangerous_deserialization=True)
    doc_count = faiss_vs.index.ntotal if hasattr(faiss_vs, 'index') else 'unknown'
    print(f"[DEBUG load_resources] FAISS cargado exitosamente con {doc_count} documentos")
    st.markdown(
        f'<p style="color: rgba(128, 128, 128, 0.5); font-size: 0.85em; margin: 5px 0;">✅ Base vectorial cargada: {doc_count} BLOQUES CHUNKS disponibles</p>',
        unsafe_allow_html=True
    )
    return llm, faiss_vs

# Contexto disponible:
# {context}
#
# Consulta del usuario: {input}
#
# Basándote estrictamente en el contenido disponible arriba, responde la consulta en formato JSON con citas obligatorias.


def get_cleaning_pattern() -> Pattern:
    # Textos entre corchetes a eliminar
    bracketed_texts = [
        '[Spanish (auto-generated)]', '[DownSub.com]', '[Música]', '[Aplausos]'
    ]
    # Textos sin corchetes a eliminar
    plain_texts = [
        'Spanish_auto_generated'
    ]
    
    # Patrones para textos entre corchetes
    bracketed_patterns = [r'\[\s*' + re.escape(text[1:-1]) + r'\s*\]' for text in bracketed_texts]
    # Patrones para textos planos
    plain_patterns = [re.escape(text) for text in plain_texts]
    
    # Combinar todos los patrones
    all_patterns = bracketed_patterns + plain_patterns
    return re.compile(r'|'.join(all_patterns), re.IGNORECASE)

cleaning_pattern = get_cleaning_pattern()

def hybrid_retrieval(vectorstore, query: str, k_vector: int = 100, k_keyword: int = 20):
    """
    # Búsqueda híbrida: vectorial + keyword fallback
    # 1. Hace búsqueda vectorial normal (k_vector docs)
    # 2. Si los términos clave no aparecen en los resultados, 
    #    busca directamente en el docstore por keywords
    # 3. Combina resultados únicos
    # Args:
    #     vectorstore: FAISS vectorstore
    #     query: consulta del usuario
    #     k_vector: número de docs a recuperar con búsqueda vectorial
    #     k_keyword: número de docs adicionales a buscar con keywords
    # Returns:
    #     Lista de documentos únicos combinados
    """
    # 1. Búsqueda vectorial normal
    vector_docs = vectorstore.similarity_search(query, k=k_vector)
    
    # 2. Detectar términos clave en la query (palabras de 3+ letras)
    keywords = [w.lower() for w in re.findall(r'\b\w{3,}\b', query)]
    
    # 3. Verificar si los keywords aparecen en los resultados vectoriales
    vector_content = " ".join(doc.page_content.lower() for doc in vector_docs)
    missing_keywords = [kw for kw in keywords if kw not in vector_content]
    
    # 4. Si hay keywords faltantes, hacer búsqueda directa en el docstore
    keyword_docs = []
    if missing_keywords:
        print(f"[DEBUG hybrid_retrieval] Keywords faltantes en top-{k_vector}: {missing_keywords}")
        print(f"[DEBUG hybrid_retrieval] Iniciando búsqueda keyword en docstore...")
        
        docstore = vectorstore.docstore._dict
        matches = []
        
        for doc_id, doc in docstore.items():
            content_lower = doc.page_content.lower()
            # Contar cuántos keywords faltantes aparecen en este doc
            match_count = sum(1 for kw in missing_keywords if kw in content_lower)
            
            if match_count > 0:
                matches.append((match_count, doc))
        
        # Ordenar por número de matches (descendente) y tomar top-k_keyword
        matches.sort(key=lambda x: x[0], reverse=True)
        keyword_docs = [doc for _, doc in matches[:k_keyword]]
        
        print(f"[DEBUG hybrid_retrieval] Encontrados {len(keyword_docs)} docs adicionales con keywords")
    
    # 5. Combinar resultados únicos (evitar duplicados por doc_id)
    seen_ids = set()
    combined_docs = []
    
    # Priorizar docs de keyword search (tienen los términos exactos)
    for doc in keyword_docs:
        doc_id = id(doc)
        if doc_id not in seen_ids:
            combined_docs.append(doc)
            seen_ids.add(doc_id)
    
    # Agregar docs vectoriales
    for doc in vector_docs:
        doc_id = id(doc)
        if doc_id not in seen_ids:
            combined_docs.append(doc)
            seen_ids.add(doc_id)
    
    print(f"[DEBUG hybrid_retrieval] Total docs combinados: {len(combined_docs)}")
    return combined_docs

def format_docs_with_metadata(docs: Iterable[Any]) -> str:
    """
    Formatea una secuencia de documentos recuperados y limpia su contenido.
    # docs: iterable de objetos con atributos `metadata` (dict) y `page_content` (str).
    # Devuelve una única cadena con todos los documentos formateados.
    """
    # DEBUG: Convertir a lista para ver cuántos docs hay
    docs_list = list(docs)
    print(f"[DEBUG format_docs_with_metadata] Recibidos {len(docs_list)} documentos")
    
    formatted_strings: List[str] = []
    for doc in docs_list:
        source_filename = os.path.basename(doc.metadata.get('source', 'Desconocido'))
        texts_to_remove_from_filename = ["[Spanish (auto-generated)]", "[DownSub.com]"]
        for text_to_remove in texts_to_remove_from_filename:
            source_filename = source_filename.replace(text_to_remove, "")
        source_filename = re.sub(r'\s+', ' ', source_filename).strip()
        # Eliminar extensión .srt para fuentes más limpias
        if source_filename.endswith('.srt'):
            source_filename = source_filename[:-4]
        
        # Arreglar problemas de encoding UTF-8
        content = doc.page_content
        # Intentar corregir caracteres mal decodificados
        try:
            # Si el texto parece estar en latin-1 pero fue interpretado como UTF-8, recodificar
            if 'Ã' in content or 'Â' in content or 'â' in content:
                content = content.encode('latin-1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # Si falla, usar el contenido original
            pass
        
        cleaned_content = cleaning_pattern.sub('', content)
        cleaned_content = re.sub(r'(\d{2}:\d{2}:\d{2}),\d{3}', r'\1', cleaned_content)
        cleaned_content = "\n".join(line for line in cleaned_content.split('\n') if line.strip())
        if cleaned_content:
            formatted_strings.append(f"Fuente: {source_filename}\nContenido:\n{cleaned_content}")
    
    result = "\n\n---\n\n".join(formatted_strings)
    print(f"[DEBUG format_docs_with_metadata] Devolviendo {len(result)} caracteres de contexto")
    return result

# Nota: la carga de llm y vectorstore se hace bajo demanda más abajo.
llm = None
vectorstore = None
retrieval_chain = None

# --- Funciones de Geolocalización y Registro ---

# --- Geolocalización por navegador ---
def get_user_location() -> dict:
    """
    """
    # Obtiene la ubicación del usuario usando geolocalización del navegador si está disponible.
    # Si no, usa ipinfo.io como fallback.
    """
    # Si ya está en session_state, usarla
    if 'geo_location' in st.session_state:
        return st.session_state['geo_location']

    # Primero, revisar si el navegador ya redirigió con ?geo=lat,lon
    params = st.query_params
    if 'geo' in params:
        try:
            geo_val = params.get('geo')[0]
            lat_str, lon_str = geo_val.split(',')
            lat = float(lat_str)
            lon = float(lon_str)

            # Reverse geocoding con Nominatim (OpenStreetMap)
            try:
                nominatim = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&accept-language=es"
                r = requests.get(nominatim, timeout=5, headers={"User-Agent": "GERARD-App/1.0"})
                r.raise_for_status()
                j = r.json()
                address = j.get('address', {})
                city = address.get('city') or address.get('town') or address.get('village') or address.get('hamlet') or address.get('municipality') or ''
                # Algunos países devuelven state y county en lugar de city
                if not city:
                    city = address.get('county') or address.get('state') or ''
                country = address.get('country') or ''

                geo_dict = {
                    'ip': params.get('ip', ['No disponible'])[0],
                    'city': city or 'Desconocida',
                    'country': country or 'Desconocido',
                    'region': address.get('state', ''),
                    'latitude': lat,
                    'longitude': lon,
                    'org': '',
                    'timezone': ''
                }
                st.session_state['geo_location'] = geo_dict
                return geo_dict
            except Exception as e:
                print(f"[!] Error reverse-geocoding Nominatim: {e}")
                # Si falla reverse, guardar lat/lon y usar ipinfo fallback below
        except Exception:
            pass

    # Si no hay geo en URL, inyectar JS que pide permiso y redirige con ?geo=lat,lon
    js = f"""
    # <script>
    # (function() {{
    #     function redirectWithGeo(lat, lon) {{
    #         const qp = new URLSearchParams(window.location.search);
    #         qp.set('geo', lat + ',' + lon);
    #         const newUrl = window.location.pathname + '?' + qp.toString();
    #         window.location.replace(newUrl);
    #     }}
    #     if (navigator.geolocation) {{
    #         navigator.geolocation.getCurrentPosition(function(pos) {{
    #             redirectWithGeo(pos.coords.latitude, pos.coords.longitude);
    #         }}, function(err) {{
    #             // Usuario negó o error: no hacer nada
    #             console.log('Geolocation denied or error', err);
    #         }}, {{timeout:10000}});
    #     }} else {{
    #         console.log('Geolocation not supported');
    #     }}
    # }})();
    # </script>
    # <div style="font-size:0.9em; color:#666; text-align:center;">Solicitando permiso de ubicación al navegador... si no aceptas, se usará una ubicación aproximada por IP.</div>
    """
    st.components.v1.html(js, height=0)

    # Mientras esperamos la redirección, usar fallback de ipinfo
    try:
        response = requests.get('https://ipinfo.io/json', timeout=10)
        data = response.json()
        loc = data.get('loc', '0,0').split(',')
        latitude = float(loc[0]) if len(loc) > 0 else 0
        longitude = float(loc[1]) if len(loc) > 1 else 0
        geo_dict = {
            'ip': data.get('ip', 'No disponible'),
            'city': data.get('city', 'Desconocida'),
            'country': data.get('country', 'Desconocido'),
            'region': data.get('region', ''),
            'latitude': latitude,
            'longitude': longitude,
            'org': data.get('org', ''),
            'timezone': data.get('timezone', '')
        }
        st.session_state['geo_location'] = geo_dict
        return geo_dict
    except Exception as e:
        print(f"[!] Error ipinfo fallback: {e}")
        return {
            'ip': 'No disponible',
            'city': 'Desconocida',
            'country': 'Desconocido',
            'region': '',
            'latitude': 0,
            'longitude': 0,
            'org': '',
            'timezone': ''
        }

# --- Funciones de logging y prompt recuperadas del backup ---
def init_logger():

    # Inicializa el sistema de logging con detección de dispositivo y geolocalización.
    return None  # Logging desactivado para modo local

@st.cache_resource
def init_sheets_logger():

    # Inicializa el logger de Google Sheets si está configurado.
    return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---

from langchain.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_template(
    "GERARD v3.01 - Sistema de Análisis Investigativo Avanzado\nIDENTIDAD DEL SISTEMA\n"
)

# --- Función de codificación UTF-8 recuperada del backup ---
def fix_utf8_encoding(text: str) -> str:
    """
    # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
    """
    if not isinstance(text, str):
        return text
    import unicodedata
    text = unicodedata.normalize('NFC', text)
    replacements = {
        'â€™': "'",
        'â€œ': '"',
        'â€': '"',
        'â€"': '–',
        'â€¦': '...',
        'Ã¡': 'á',
        'Ã©': 'é',
        'Ã­': 'í',
        'Ã³': 'ó',
        'Ãº': 'ú',
        'Ã±': 'ñ',
        'Ã': 'í',
        'Ã‰': 'É',
        'Ãš': 'Ú',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text

# --- Funciones de logging y sheets desactivadas para modo local ---


# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
# --- INTERFAZ STREAMLIT PRINCIPAL ---

st.set_page_config(
    page_title="GERARD - Consultor Investigativo",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar tema oscuro
st.markdown("""
<style>
    * {
        color: #E0E0E0;
        background-color: #121212;
    }
    .stApp {
        background-color: #121212;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔬 GERARD v3.01 - Sistema de Análisis Investigativo (Gemini 1.5 Pro)")

# Cargar recursos
llm, faiss_vs = load_resources()

# Interfaz de consulta
st.subheader("Realiza una consulta")
query = st.text_input("Ingresa tu pregunta:", placeholder="¿Qué deseas saber?")

if query:
    st.info("Procesando tu consulta con Gemini 1.5 Pro...")
    
    try:
        # Búsqueda híbrida
        docs = hybrid_retrieval(faiss_vs, query, k_vector=100, k_keyword=20)
        context = "\n\n".join([doc.page_content for doc in docs[:5]])
        
        # Configurar el prompt completo de GERARD
        prompt = ChatPromptTemplate.from_template(r"""
═══════════════════════════════════════════════════════════
🔬 GERARD v3.01 | SISTEMA DE INTELIGENCIA ANALÍTICA FORENSE
═══════════════════════════════════════════════════════════

IDENTIDAD DEL SISTEMA:
Eres GERARD v3.01, un sistema de inteligencia analítica especializado en investigación forense de documentos. Tu misión crítica es proporcionar análisis riguroso basado EXCLUSIVAMENTE en fuentes verificables del contexto proporcionado.

PROTOCOLOS DE SEGURIDAD ANALÍTICA:
1. VERIFICACIÓN OBLIGATORIA: Cada afirmación debe rastrearse a fragmentos específicos
2. PRECISIÓN QUIRÚRGICA: Temperature 0.4 para máxima exactitud
3. TRANSPARENCIA TOTAL: Citas obligatorias con fuentes identificables
4. RIGOR METODOLÓGICO: Distinguir entre hechos confirmados e inferencias

PROHIBICIONES NIVEL 1:
❌ NO inventar información no presente en el contexto
❌ NO hacer afirmaciones sin citas específicas
❌ NO usar conocimiento externo al material proporcionado
❌ NO generar respuestas vagas o especulativas

MANDATOS OBLIGATORIOS:
✅ Extraer solo información directamente presente en los documentos
✅ Citar fragmentos específicos con (Fuente: [título/origen])
✅ Indicar claramente cuando información es insuficiente
✅ Usar formato JSON estructurado OBLIGATORIAMENTE

FORMATO DE RESPUESTA REQUERIDO:
```json
[
    {{"type": "normal", "content": "Análisis basado en el contexto con (Fuente: fragmento_específico)"}},
    {{"type": "emphasis", "content": "Información crítica destacada (Fuente: fragmento_específico)"}},
    {{"type": "normal", "content": "Si no hay información suficiente en el contexto, indicar claramente"}}
]
```

CONTEXTO DISPONIBLE:
{context}

CONSULTA A ANALIZAR:
{query}

INSTRUCCIONES FINALES:
- Analiza la consulta usando ÚNICAMENTE el contexto proporcionado
- Proporciona citas específicas para cada afirmación
- Si el contexto es insuficiente, indica "Información insuficiente en el contexto analizado"
- Responde OBLIGATORIAMENTE en el formato JSON especificado

RESPUESTA JSON:""")
        
        # Procesar con Gemini Pro 2.5
        chain = (
            RunnablePassthrough.assign(context=lambda x: context, query=lambda x: query)
            | prompt 
            | llm 
            | StrOutputParser()
        )
        
        answer = chain.invoke({})
        
        st.markdown("### 🔬 Análisis de GERARD:")
        
        # Intentar parsear respuesta JSON
        try:
            import json
            # Buscar el JSON en la respuesta
            json_match = re.search(r'\[.*\]', answer, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                
                for item in data:
                    content_type = item.get("type", "normal")
                    content = item.get("content", "")
                    
                    if content_type == "emphasis":
                        st.markdown(f"**🔍 {content}**")
                    else:
                        st.markdown(content)
            else:
                # Si no hay JSON, mostrar respuesta directa
                st.write(answer)
        except:
            # Fallback si falla el parsing JSON
            st.write(answer)
        
    except Exception as e:
        st.error(f"Error al procesar: {str(e)}")

#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',
#         'Ã': 'í',
#         'Ã‰': 'É',
#         'Ãš': 'Ú',
#     }
#     for bad, good in replacements.items():
#         text = text.replace(bad, good)
#     return text

# --- Funciones de logging y sheets desactivadas para modo local ---
# def init_logger():
#     """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
#     return None  # Logging desactivado para modo local

# @st.cache_resource
# def init_sheets_logger():
#     """Inicializa el logger de Google Sheets si está configurado."""
#     return None  # Sheets logging desactivado para modo local

# --- Prompt de Gerard v3.01 ---
# from langchain.prompts import ChatPromptTemplate
# prompt = ChatPromptTemplate.from_template(r"""
# 🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
# IDENTIDAD DEL SISTEMA
# """)

# --- Función de codificación UTF-8 recuperada del backup ---
# def fix_utf8_encoding(text: str) -> str:
#     """
#     # Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud.
#     """
#     if not isinstance(text, str):
#         return text
#     import unicodedata
#     text = unicodedata.normalize('NFC', text)
#     replacements = {
#         'â€™': "'",
#         'â€œ': '"',
#         'â€': '"',
#         'â€"': '–',
#         'â€¦': '...',
#         'Ã¡': 'á',
#         'Ã©': 'é',
#         'Ã­': 'í',
#         'Ã³': 'ó',
#         'Ãº': 'ú',
#         'Ã±': 'ñ',