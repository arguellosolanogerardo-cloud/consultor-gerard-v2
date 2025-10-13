﻿# -*- coding: utf-8 -*-
import os
import json
import re
import colorama
import keyring
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import uuid
from typing import Any, Iterable, List, Pattern
import streamlit as st
import streamlit.components.v1 as components
import requests  # Para obtener la IP y geolocalizaciÃ³n
import io
import textwrap

# Importar sistema de logging completo
from interaction_logger import InteractionLogger
from device_detector import DeviceDetector
from geo_utils import GeoLocator

# Importar Google Sheets Logger (opcional, solo si estÃ¡ configurado)
try:
    from google_sheets_logger import create_sheets_logger
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("[!] Google Sheets Logger no disponible. Instala: pip install gspread oauth2client")

# Intentar importar reportlab para generar PDFs; si no estÃ¡ disponible, lo detectamos y mostramos instrucciones
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

# --- ConfiguraciÃ³n Inicial ---
colorama.init(autoreset=True)
load_dotenv()

# --- Carga de Modelos y Base de Datos (con cachÃ© de Streamlit) ---
@st.cache_resource
def load_resources():
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
    if not api_key:
        st.error(
            "Error: La variable de entorno GOOGLE_API_KEY no estÃ¡ configurada. AÃ±ade la clave a las variables de entorno o a Streamlit Secrets."
        )
        st.stop()

    # Pasar la API key explÃ­citamente evita que la librerÃ­a intente usar ADC
    # Intentar inicializar el LLM y embeddings de forma perezosa; si falla, devolver llm=None
    llm = None
    embeddings = None

    with st.spinner('Inicializando LLM y embeddings (de forma perezosa)...'):
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

        # Inicializar LLM si la clase estÃ¡ disponible
        if GoogleGenerativeAI is not None:
            try:
                llm = GoogleGenerativeAI(
                    model="models/gemini-2.5-pro", 
                    google_api_key=api_key,
                    temperature=0.4,  # PrecisiÃ³n quirÃºrgica segÃºn prompt GERARD
                    top_p=0.90,
                    top_k=25
                )
            except Exception as e:
                st.warning(f"No se pudo inicializar el LLM (GoogleGenerativeAI): {e}. La aplicaciÃ³n usarÃ¡ un modo de recuperaciÃ³n local sin LLM.")

        # Inicializar embeddings (o usar fallback) y cargar FAISS
        try:
            # Intentar usar la clase oficial si estÃ¡ disponible
            if GoogleGenerativeAIEmbeddings is not None:
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
                    print("[DEBUG] Embeddings de Google inicializadas correctamente")
                except Exception as e:
                    st.warning(f"No fue posible inicializar GoogleEmbeddings: {e}. Usando embeddings de fallback (hash-based).")
            else:
                st.warning("GoogleGenerativeAIEmbeddings no disponible, usando embeddings de fallback (hash-based).")

            if embeddings is None:
                import hashlib
                # Intentar deducir la dimensiÃ³n del Ã­ndice FAISS para generar vectores compatibles
                target_dim = 768
                try:
                    import faiss
                    idx_path = os.path.join('faiss_index', 'index.faiss')
                    if os.path.exists(idx_path):
                        idx = faiss.read_index(idx_path)
                        target_dim = getattr(idx, 'd', target_dim)
                except Exception:
                    # Si faiss no estÃ¡ disponible o falla, seguimos con el valor por defecto
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

                embeddings = FakeEmbeddings()
                st.error("âš ï¸ ADVERTENCIA: Usando embeddings simuladas (hash-based). La bÃºsqueda semÃ¡ntica serÃ¡ limitada. Verifica la API key de Google.")

            
            # === DESCARGA DEL ÍNDICE FAISS DESDE GITHUB RELEASE ===
            if not os.path.exists("faiss_index/index.faiss"):
                # Verificar si ya se intento descargar en esta sesion
                if "faiss_downloaded" not in st.session_state:
                    st.session_state.faiss_downloaded = False
                
                if not st.session_state.faiss_downloaded:
                    st.info("[>] Descargando indice FAISS pre-construido...")
                    st.info("[tiempo] Descarga unica (~250 MB, espera 1-2 min)")
                    
                    try:
                        import requests
                        import zipfile
                        from io import BytesIO
                        
                        FAISS_URL = "https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2/releases/download/faiss-v1.0/faiss_index.zip"
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        with st.spinner("Descargando..."):
                            response = requests.get(FAISS_URL, stream=True, timeout=600)
                            response.raise_for_status()
                            
                            total_size = int(response.headers.get('content-length', 0))
                            downloaded = 0
                            zip_data = BytesIO()
                            
                            for chunk in response.iter_content(chunk_size=1024*1024):
                                zip_data.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = int((downloaded / total_size) * 100)
                                    progress_bar.progress(progress / 100)
                                    status_text.text(f"[>] {progress}% descargado ({downloaded // (1024*1024)} MB / {total_size // (1024*1024)} MB)")
                        
                        status_text.text("[paquete] Extrayendo...")
                        os.makedirs("faiss_index", exist_ok=True)
                        zip_data.seek(0)
                        with zipfile.ZipFile(zip_data) as zf:
                            zf.extractall("faiss_index")
                        
                        st.session_state.faiss_downloaded = True
                        progress_bar.empty()
                        status_text.empty()
                        st.success("[OK] Indice descargado! No se volvera a descargar.")
                        
                    except Exception as e:
                        st.error(f"[ERROR] Error descargando: {str(e)}")
                        raise
            # === FIN DESCARGA ===


            faiss_vs = FAISS.load_local(folder_path="faiss_index", embeddings=embeddings, allow_dangerous_deserialization=True)
            # Debug: verificar que se cargÃ³ correctamente
            doc_count = faiss_vs.index.ntotal if hasattr(faiss_vs, 'index') else 'unknown'
            print(f"[DEBUG load_resources] FAISS cargado exitosamente con {doc_count} documentos")
            # Mostrar mensaje con estilo tenue y sin fondo
            st.markdown(
                f'<p style="color: rgba(128, 128, 128, 0.5); font-size: 0.85em; margin: 5px 0;">âœ… Base vectorial cargada: {doc_count} BLOQUES CHUNKS disponibles</p>',
                unsafe_allow_html=True
            )
        except Exception as e:
            print(f"[ERROR load_resources] Error al cargar FAISS: {e}")
            st.error(f"âŒ No fue posible cargar el Ã­ndice FAISS: {e}")
            st.stop()

    return llm, faiss_vs

# NOTA: No ejecutar load_resources() al importar el mÃ³dulo para evitar inicializar
# las librerÃ­as de Google (protobuf/GRPC) en el arranque de Streamlit. La carga
# se harÃ¡ bajo demanda cuando el usuario envÃ­e una consulta.

# --- Inicializar sistema de logging completo ---
@st.cache_resource
def init_logger():
    """Inicializa el sistema de logging con detecciÃ³n de dispositivo y geolocalizaciÃ³n."""
    return InteractionLogger(
        platform="web",
        log_dir="logs",
        anonymize=False,  # Guardar datos completos
        enable_json=True  # Guardar tambiÃ©n en formato JSON
    )

# --- Inicializar Google Sheets Logger (si estÃ¡ disponible) ---
@st.cache_resource
def init_sheets_logger():
    """Inicializa el logger de Google Sheets si estÃ¡ configurado."""
    if GOOGLE_SHEETS_AVAILABLE:
        return create_sheets_logger()
    return None

# --- LÃ³gica de GERARD v3.01 - Actualizado ---
prompt = ChatPromptTemplate.from_template(r"""
ðŸ”¬ GERARD v3.01 - Sistema de AnÃ¡lisis Investigativo Avanzado
IDENTIDAD DEL SISTEMA
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
Nombre: GERARD
VersiÃ³n: 3.01 - Analista Documental
Modelo Base: Gemini Pro Latest 2.5
Temperatura: 0.3-0.5 (MÃ¡xima PrecisiÃ³n y Consistencia)
EspecializaciÃ³n: CriptoanÃ¡lisis de Archivos .srt
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
MISIÃ“N CRÃTICA
Eres GERARD, un sistema de inteligencia analÃ­tica especializado en arqueologÃ­a documental de archivos de subtÃ­tulos (.srt). Tu propÃ³sito es descubrir patrones ocultos, mensajes encriptados y conexiones invisibles que emergen al correlacionar mÃºltiples documentos mediante tÃ©cnicas forenses avanzadas. DESCUBRIR EXACTAMENTE EL TITULO, LA HORA, EL MINUTO DE LOS ARCHIVOS.SRT QUE ESTAN EN LA BASE VECTORIAL COMO FUENTE UNICA DEL CONOCIMIENTO
ConfiguraciÃ³n de Temperatura Optimizada (0.2-0.3)
Esta temperatura baja garantiza:
â€¢ Consistencia absoluta entre consultas repetidas
â€¢ Reproducibilidad de hallazgos para verificaciÃ³n
â€¢ PrecisiÃ³n quirÃºrgica en extracciÃ³n de datos
â€¢ EliminaciÃ³n de variabilidad en respuestas crÃ­ticas
â€¢ Confiabilidad forense en anÃ¡lisis investigativos
________________________________________
ðŸš¨ PROTOCOLOS DE SEGURIDAD ANALÃTICA
REGLAS ABSOLUTAS (Nivel de Cumplimiento: 100%)
ðŸ”´ PROHIBICIÃ“N NIVEL 1: FABRICACIÃ“N DE DATOS
â”œâ”€ âŒ NO inventar informaciÃ³n bajo ninguna circunstancia
â”œâ”€ âŒ NO usar conocimiento del modelo base (entrenamiento general)
â”œâ”€ âŒ NO suponer o inferir mÃ¡s allÃ¡ de lo textualmente disponible
â””â”€ âŒ NO completar informaciÃ³n faltante con lÃ³gica externa

ðŸ”´ PROHIBICIÃ“N NIVEL 2: CONTAMINACIÃ“N ANALÃTICA
â”œâ”€ âŒ NO mezclar anÃ¡lisis con citas textuales
â”œâ”€ âŒ NO parafrasear cuando se requiere texto literal
â”œâ”€ âŒ NO interpretar sin declarar explÃ­citamente que es interpretaciÃ³n
â””â”€ âŒ NO omitir informaciÃ³n contradictoria si existe

ðŸŸ¢ MANDATOS OBLIGATORIOS
â”œâ”€ âœ… Cada afirmaciÃ³n DEBE tener cita textual verificable
â”œâ”€ âœ… Cada cita DEBE incluir: [Documento] + [Timestamp] + [Texto Literal]
â”œâ”€ âœ… Cada anÃ¡lisis DEBE separarse claramente de evidencias
â”œâ”€ âœ… Cada consulta DEBE ejecutar los 8 Protocolos de BÃºsqueda Profunda
â””â”€ âœ… Cada respuesta DEBE incluir nivel de confianza estadÃ­stico
________________________________________
ï¿½ INSTRUCCIÃ“N CRÃTICA DE FORMATO
CADA FRASE O PÃRRAFO de respuesta DEBE ir seguido inmediatamente de su cita de fuente en PARÃ‰NTESIS.
El texto de la cita DEBE ir en COLOR MAGENTA.
Formato: [Tu respuesta aquÃ­] (Fuente: TITULO_ARCHIVO, Timestamp: HH:MM:SS)

EJEMPLO:
"El amor es la fuerza mÃ¡s poderosa del universo (Fuente: MEDITACION_42_EL_AMOR_DIVINO, Timestamp: 00:15:32)"

ðŸš¨ FORMATO DE SALIDA OBLIGATORIO (JSON)
CRÃTICO: Tu respuesta DEBE ser un array JSON vÃ¡lido con esta estructura exacta:

[
  {{"type": "normal", "content": "Texto con su cita (Fuente: archivo, Timestamp: HH:MM:SS)"}},
  {{"type": "emphasis", "content": "Texto enfatizado con su cita (Fuente: archivo, Timestamp: HH:MM:SS)"}},
  {{"type": "normal", "content": "MÃ¡s texto con cita (Fuente: archivo, Timestamp: HH:MM:SS)"}}
]

REGLAS:
- type: puede ser "normal" o "emphasis"
- content: string que SIEMPRE incluye la cita de fuente al final entre parÃ©ntesis
- Formato de cita: (Fuente: NOMBRE_EXACTO_archivo, Timestamp: HH:MM:SS)
- NO agregues texto fuera del array JSON
- NO uses markdown, solo el array JSON puro
- NUNCA omitas la cita de fuente

Contexto disponible:
{context}

Consulta del usuario: {input}

BasÃ¡ndote estrictamente en el contenido disponible arriba, responde la consulta en formato JSON con citas obligatorias.

â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
FIN DEL ANÃLISIS
LA VERDAD OS HARA LIBRES
LA CLAVE ES EL AMOR
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
""")

def get_cleaning_pattern() -> Pattern:
    # Textos entre corchetes a eliminar
    bracketed_texts = [
        '[Spanish (auto-generated)]', '[DownSub.com]', '[MÃºsica]', '[Aplausos]'
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
    BÃºsqueda hÃ­brida: vectorial + keyword fallback
    
    1. Hace bÃºsqueda vectorial normal (k_vector docs)
    2. Si los tÃ©rminos clave no aparecen en los resultados, 
       busca directamente en el docstore por keywords
    3. Combina resultados Ãºnicos
    
    Args:
        vectorstore: FAISS vectorstore
        query: consulta del usuario
        k_vector: nÃºmero de docs a recuperar con bÃºsqueda vectorial
        k_keyword: nÃºmero de docs adicionales a buscar con keywords
    
    Returns:
        Lista de documentos Ãºnicos combinados
    """
    # 1. BÃºsqueda vectorial normal
    vector_docs = vectorstore.similarity_search(query, k=k_vector)
    
    # 2. Detectar tÃ©rminos clave en la query (palabras de 3+ letras)
    keywords = [w.lower() for w in re.findall(r'\b\w{3,}\b', query)]
    
    # 3. Verificar si los keywords aparecen en los resultados vectoriales
    vector_content = " ".join(doc.page_content.lower() for doc in vector_docs)
    missing_keywords = [kw for kw in keywords if kw not in vector_content]
    
    # 4. Si hay keywords faltantes, hacer bÃºsqueda directa en el docstore
    keyword_docs = []
    if missing_keywords:
        print(f"[DEBUG hybrid_retrieval] Keywords faltantes en top-{k_vector}: {missing_keywords}")
        print(f"[DEBUG hybrid_retrieval] Iniciando bÃºsqueda keyword en docstore...")
        
        docstore = vectorstore.docstore._dict
        matches = []
        
        for doc_id, doc in docstore.items():
            content_lower = doc.page_content.lower()
            # Contar cuÃ¡ntos keywords faltantes aparecen en este doc
            match_count = sum(1 for kw in missing_keywords if kw in content_lower)
            
            if match_count > 0:
                matches.append((match_count, doc))
        
        # Ordenar por nÃºmero de matches (descendente) y tomar top-k_keyword
        matches.sort(key=lambda x: x[0], reverse=True)
        keyword_docs = [doc for _, doc in matches[:k_keyword]]
        
        print(f"[DEBUG hybrid_retrieval] Encontrados {len(keyword_docs)} docs adicionales con keywords")
    
    # 5. Combinar resultados Ãºnicos (evitar duplicados por doc_id)
    seen_ids = set()
    combined_docs = []
    
    # Priorizar docs de keyword search (tienen los tÃ©rminos exactos)
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
    """Formatea una secuencia de documentos recuperados y limpia su contenido.
    
    docs: iterable de objetos con atributos `metadata` (dict) y `page_content` (str).
    Devuelve una Ãºnica cadena con todos los documentos formateados.
    """
    # DEBUG: Convertir a lista para ver cuÃ¡ntos docs hay
    docs_list = list(docs)
    print(f"[DEBUG format_docs_with_metadata] Recibidos {len(docs_list)} documentos")
    
    formatted_strings: List[str] = []
    for doc in docs_list:
        source_filename = os.path.basename(doc.metadata.get('source', 'Desconocido'))
        texts_to_remove_from_filename = ["[Spanish (auto-generated)]", "[DownSub.com]"]
        for text_to_remove in texts_to_remove_from_filename:
            source_filename = source_filename.replace(text_to_remove, "")
        source_filename = re.sub(r'\s+', ' ', source_filename).strip()
        # Eliminar extensiÃ³n .srt para fuentes mÃ¡s limpias
        if source_filename.endswith('.srt'):
            source_filename = source_filename[:-4]
        
        # Arreglar problemas de encoding UTF-8
        content = doc.page_content
        # Intentar corregir caracteres mal decodificados
        try:
            # Si el texto parece estar en latin-1 pero fue interpretado como UTF-8, recodificar
            if 'Ãƒ' in content or 'Ã‚' in content or 'Ã¢' in content:
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

# Nota: la carga de llm y vectorstore se hace bajo demanda mÃ¡s abajo.
llm = None
vectorstore = None
retrieval_chain = None

# --- Funciones de GeolocalizaciÃ³n y Registro ---
@st.cache_data
def get_user_location() -> dict:
    """
    Obtiene la ubicaciÃ³n del usuario usando ipinfo.io.
    Retorna un diccionario con los datos de ubicaciÃ³n.
    """
    try:
        response = requests.get('https://ipinfo.io/json', timeout=5)
        data = response.json()
        
        # Extraer coordenadas si estÃ¡n disponibles
        loc = data.get('loc', '0,0').split(',')
        latitude = float(loc[0]) if len(loc) > 0 else 0
        longitude = float(loc[1]) if len(loc) > 1 else 0
        
        return {
            'ip': data.get('ip', 'No disponible'),
            'city': data.get('city', 'Desconocida'),
            'country': data.get('country', 'Desconocido'),
            'region': data.get('region', ''),
            'latitude': latitude,
            'longitude': longitude,
            'org': data.get('org', ''),
            'timezone': data.get('timezone', '')
        }
    except Exception as e:
        print(f"[!] Error obteniendo ubicaciÃ³n: {e}")
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

def get_clean_text_from_json(json_string: str) -> str:
    try:
        # Debug: mostrar tipo recibido
        print(f"[DEBUG get_clean_text_from_json] Tipo recibido: {type(json_string)}")
        
        # Convertir a string si recibimos un dict o list
        if isinstance(json_string, (dict, list)):
            print(f"[DEBUG] Convirtiendo {type(json_string)} a JSON string")
            json_string = json.dumps(json_string, ensure_ascii=False)
        
        # Remover backticks de markdown si existen
        json_string = re.sub(r'^```json\s*', '', json_string.strip())
        json_string = re.sub(r'\s*```$', '', json_string.strip())
        
        match = re.search(r'\[.*\]', json_string, re.DOTALL)
        if not match:
            print(f"[DEBUG get_clean_text_from_json] No se encontrÃ³ array JSON")
            return json_string

        data = json.loads(match.group(0))
        # Concatenar todo el contenido de los items
        clean_text = " ".join([item.get("content", "") for item in data])
        print(f"[DEBUG get_clean_text_from_json] Texto limpio extraÃ­do: {clean_text[:100]}...")
        return clean_text
    except Exception as ex:
        print(f"[DEBUG get_clean_text_from_json] ERROR: {ex}")
        import traceback
        traceback.print_exc()
        return json_string


def detect_gender_from_name(name: str) -> str:
    """HeurÃ­stica simple para detectar gÃ©nero a partir del primer nombre.
    Regla principal: termina en 'a' -> Femenino, termina en 'o' -> Masculino.
    Usa listas de excepciones comunes para mejorar la precisiÃ³n.
    Devuelve: 'Masculino', 'Femenino' o 'No especificar'.
    """
    if not name or not name.strip():
        return 'No especificar'
    # Normalizar y tomar primer token
    first = name.strip().split()[0].lower()
    # Quitar caracteres no alfabÃ©ticos (mantener acentos y Ã±)
    first = re.sub(r"[^a-zÃ¡Ã©Ã­Ã³ÃºÃ¼Ã±]", "", first)

    # Listas de nombres comunes (no exhaustivas)
    male_names = {"juan","carlos","pedro","jose","luis","miguel","axel","alan","adriel","adiel","alaniso","aladio","adolfo"}
    female_names = {"maria","ana","laura","mariana","isabela","isabella","sofia","sofia"}

    if first in male_names:
        return 'Masculino'
    if first in female_names:
        return 'Femenino'

    # Regla por terminaciÃ³n (heurÃ­stica fuerte en espaÃ±ol)
    if first.endswith(('a','Ã¡')):
        return 'Femenino'
    if first.endswith(('o','Ã³')):
        return 'Masculino'

    # Nombres neutros o no detectables
    return 'No especificar'

def save_to_log(user: str, question: str, answer_json: str, location: str) -> None:
    # Debug: mostrar tipo recibido
    print(f"[DEBUG save_to_log] Tipo de answer_json recibido: {type(answer_json)}")
    
    # Convertir answer_json a string si es dict/list
    if isinstance(answer_json, (dict, list)):
        print(f"[DEBUG save_to_log] Convirtiendo {type(answer_json)} a JSON string")
        answer_json = json.dumps(answer_json, ensure_ascii=False)
    
    clean_answer = get_clean_text_from_json(answer_json)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("gerard_log.txt", "a", encoding="utf-8") as f:
        f.write(f"--- ConversaciÃ³n del {timestamp} ---\n")
        f.write(f"Usuario: {user}\n")
        f.write(f"UbicaciÃ³n: {location}\n")
        f.write(f"Pregunta: {question}\n")
        f.write(f"Respuesta de GERARD: {clean_answer}\n")
        f.write("="*40 + "\n\n")

def get_conversation_text() -> str:
    conversation = []
    for message in st.session_state.get('messages', []):
        content_html = message["content"]
        # Extraer texto plano de la forma mÃ¡s simple posible
        text_content = re.sub(r'<[^>]+>', '', content_html).strip()
        
        if message["role"] == "user":
            # Para el usuario, el texto relevante estÃ¡ en el span uppercase
            match = re.search(r'<span style="text-transform: uppercase;.*?">(.*?)</span>', content_html)
            if match:
                text_content = match.group(1).strip()
            conversation.append(f"Usuario: {text_content}")
        else:
            # Para el asistente, quitar el nombre de usuario que se aÃ±ade al principio
            user_name_placeholder = f"{st.session_state.get('user_name', '')}:"
            if text_content.startswith(user_name_placeholder):
                 text_content = text_content[len(user_name_placeholder):].strip()
            conversation.append(f"GERARD: {text_content}")
            
    return "\n\n".join(conversation)

def generate_download_filename() -> str:
    user_questions = []
    for message in st.session_state.get('messages', []):
        if message["role"] == "user":
            match = re.search(r'<span style="text-transform: uppercase;.*?">(.*?)</span>', message['content'])
            if match:
                user_questions.append(match.group(1).strip())

    if not user_questions:
        questions_text = "conversacion"
    else:
        # Unir preguntas con sÃ­mbolo de interrogaciÃ³n como separador visible
        questions_text = "?_".join(user_questions)

    # Sanitizar SOLO caracteres invÃ¡lidos para nombres de archivo (NO truncar)
    # Mantener espacios y permitir cualquier longitud
    sanitized_name = re.sub(r'[\\/:*"<>|]', '', questions_text)  # Eliminado ? del regex
    # NO truncar - permitir todo el texto completo
    full_questions = sanitized_name.strip()

    user_name = st.session_state.get('user_name', 'usuario').upper()
    
    # Obtener fecha y hora actual
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    time_str = now.strftime('%H%M')  # Solo hora y minuto
    
    # Formato final: CONSULTA_DE_NOMBREUSUARIO_pregunta1?_pregunta2?_pregunta3_20251009_2109.txt
    return f"CONSULTA_DE_{user_name}_{full_questions}_{date_str}_{time_str}.txt"


def _escape_ampersand(text: str) -> str:
    return text.replace('&', '&amp;')


def _convert_spans_to_font_tags(html: str) -> str:
    """Reemplaza <span style="color:...">texto</span> por <font color="...">texto</font> para que reportlab Paragraph lo soporte.

    No soportamos estilos complejos; se intenta preservar el color de fuente.
    """
    # Normalizar algunos cierres y saltos
    s = html
    # Reemplazar span color (hex o nombre)
    s = re.sub(r'<span\s+style="[^"]*color\s*:\s*([^;\"]+)[^\"]*">(.*?)</span>', lambda m: f"<font color=\"{m.group(1).strip()}\">{m.group(2)}</font>", s, flags=re.DOTALL)
    # Reemplazar any remaining <span> without color -> remove span
    s = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', s, flags=re.DOTALL)
    # Asegurar que los saltos de lÃ­nea HTML sean <br/> para Paragraph
    s = s.replace('\n', '<br/>')
    s = s.replace('<br>', '<br/>')
    # Evitar caracteres & que rompan XML interno
    s = _escape_ampersand(s)
    return s


def _format_header(title_base: str, user_name: str | None, max_len: int = 220):
    """Construye un encabezado que contiene el tÃ­tulo, el nombre en negrita y la fecha, limitado a max_len caracteres.

    Devuelve una tupla (header_html, header_plain).
    """
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_name = (user_name or 'usuario').strip()
    plain = f"{title_base} - {user_name} {date_str}"
    if len(plain) > max_len:
        plain = plain[: max_len - 3].rstrip() + '...'
    # Para HTML, ponemos el nombre en negrita
    # Intentar reemplazar first occurrence of user_name in plain with bold; si truncado puede no contener name
    if user_name and user_name in plain:
        html = plain.replace(user_name, f"<b>{user_name}</b>", 1)
    else:
        html = plain
    return html, plain


def generate_pdf_from_html(html_content: str, title_base: str = "Conversacion GERARD", user_name: str | None = None) -> bytes:
    """Genera un PDF en memoria a partir de HTML simple (etiquetas bÃ¡sicas) preservando colores de fuente.

    Usa reportlab Platypus Paragraph con tags <font color="...">.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("La librerÃ­a 'reportlab' no estÃ¡ instalada. InstÃ¡lala con: pip install reportlab")
    if not REPORTLAB_PLATYPUS:
        # Si platypus no estÃ¡ disponible, caer al generador de texto plano
        return generate_pdf_bytes_text(_strip_html_tags(html_content), title_base=title_base, user_name=user_name)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.fontName = 'Helvetica'
    normal.fontSize = 10
    normal.leading = 12

    story = []
    # Header (tÃ­tulo + nombre en negrita + fecha) limitado a 220 chars
    header_html, header_plain = _format_header(title_base, user_name, max_len=220)
    title_style = styles.get('Heading2', normal)
    story.append(Paragraph(header_html, title_style))
    story.append(Spacer(1, 6))

    body = _convert_spans_to_font_tags(html_content)

    # Paragraph acepta un fragmento con tags limitados (<b>, <i>, <u>, <font color="...">, <br/>)
    try:
        story.append(Paragraph(body, normal))
    except Exception:
        # Fallback: limpiar HTML y usar texto simple
        plain = re.sub(r'<[^>]+>', '', html_content)
        story.append(Paragraph(plain.replace('&', '&amp;'), normal))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def generate_pdf_bytes_text(text: str, title_base: str = "Conversacion GERARD", user_name: str | None = None) -> bytes:
    """Fallback simple: genera PDF plano a partir de texto sin formato (mantener funciÃ³n previa)."""
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    left_margin = 40
    right_margin = 40
    top_margin = 40
    bottom_margin = 40
    # Header: tÃ­tulo + nombre en negrita + fecha (limitado a 220 chars)
    header_html, header_plain = _format_header(title_base, user_name, max_len=220)
    # Dibujar parte inicial (tÃ­tulo y nombre en negrita separado por un guion)
    # Si header_plain contiene el user_name, dibujamos antes del nombre en normal y luego el nombre en negrita
    if user_name and user_name in header_plain:
        prefix, _, suffix = header_plain.partition(user_name)
        c.setFont("Helvetica-Bold", 14)
        # Dibujar prefijo + (usaremos fuente normal para prefijo) -> ajustar: dibujar prefix en normal
        c.setFont("Helvetica", 12)
        c.drawString(left_margin, page_height - top_margin, prefix.strip())
        # dibujar nombre en negrita seguido de fecha/suffix
        x = left_margin + stringWidth(prefix.strip() + ' ', "Helvetica", 12)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, page_height - top_margin, user_name)
        x += stringWidth(user_name + ' ', "Helvetica-Bold", 12)
        c.setFont("Helvetica", 12)
        c.drawString(x, page_height - top_margin, suffix.strip())
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left_margin, page_height - top_margin, header_plain)
    c.setFont("Helvetica", 10)
    max_width = page_width - left_margin - right_margin
    from reportlab.pdfbase.pdfmetrics import stringWidth
    y = page_height - top_margin - 20
    line_height = 12
    for paragraph in text.split('\n'):
        if not paragraph:
            y -= line_height
            if y < bottom_margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = page_height - top_margin
            continue
        words = paragraph.split(' ')
        line = ''
        for w in words:
            candidate = (line + ' ' + w).strip() if line else w
            if stringWidth(candidate, "Helvetica", 10) <= max_width:
                line = candidate
            else:
                c.drawString(left_margin, y, line)
                y -= line_height
                if y < bottom_margin:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = page_height - top_margin
                line = w
        if line:
            c.drawString(left_margin, y, line)
            y -= line_height
            if y < bottom_margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = page_height - top_margin
    c.save()
    buffer.seek(0)
    return buffer.read()


def _strip_html_tags(html: str) -> str:
    return re.sub(r'<[^>]+>', '', html)


# --- Interfaz de Usuario con Streamlit ---
st.set_page_config(
    page_title="GERARD",
    layout="centered",
    initial_sidebar_state="expanded"  # Sidebar expandido por defecto
)

# Ocultar elementos de la interfaz de Streamlit
hide_streamlit_style = """
    <style>
    /* NO ocultar nada del header para mantener el botÃ³n del sidebar visible */
    
    /* Ocultar solo el footer "Made with Streamlit" */
    footer {visibility: hidden !important;}
    .viewerBadge_container__1QSob {display: none !important;}
    .styles_viewerBadge__1yB5_ {display: none !important;}
    
    /* Ocultar botÃ³n de Deploy */
    .stDeployButton {display: none !important;}
    
    /* Ajustar padding superior para que no corte el tÃ­tulo */
    .block-container {
        padding-top: 3rem;
    }
    </style>
    
    <script>
    // FunciÃ³n para ocultar iconos del footer inferior derecho
    function hideFooterIcons() {
        // Ocultar todos los elementos en la esquina inferior derecha
        const selectors = [
            'footer',
            '[data-testid="stStatusWidget"]',
            '[class*="viewerBadge"]',
            '[class*="styles_viewerBadge"]',
            'button[title*="Manage"]',
            'button[title*="manage"]',
            '.stApp footer',
            '.main footer'
        ];
        
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
            });
        });
    }
    
    // Ejecutar cuando la pÃ¡gina cargue
    document.addEventListener('DOMContentLoaded', hideFooterIcons);
    
    // Ejecutar repetidamente para capturar elementos cargados dinÃ¡micamente
    setInterval(hideFooterIcons, 500);
    
    // Ejecutar inmediatamente
    hideFooterIcons();
    </script>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- Avatares personalizados ---
user_avatar = "https://api.iconify.design/line-md/question-circle.svg?color=%2358ACFA"
assistant_avatar = "https://api.iconify.design/mdi/ufo-outline.svg?color=%238A2BE2"


# --- Estilos CSS y TÃ­tulo ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;800&display=swap');
.title-style {
    /* TipografÃ­a moderna y mayor tamaÃ±o */
    font-family: 'Poppins', 'Orbitron', sans-serif;
    font-size: 8em; /* un poco mÃ¡s grande */
    text-align: center;
    color: #8A2BE2; /* Violeta */
    padding: 20px 0 20px 0;
    margin-top: 10px;
    line-height: 1.1;
    /* pulso suave (palpitante) */
    animation: pulse-title 2s infinite ease-in-out;
    text-shadow: 0 6px 18px rgba(138,43,226,0.15);
}
.welcome-text {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.5em;
    text-align: center;
    color: #28a745; /* Green */
    padding-bottom: 5px;
}
.sub-welcome-text {
    text-align: center;
    font-size: 1.1em;
    margin-top: -15px;
    padding-bottom: 20px;
}
.intro-text {
    text-transform: uppercase;
    text-align: center;
    color: #58ACFA; /* Azul claro */
    font-size: 2.6em;
    padding-bottom: 20px;
}
.loader-container {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding-top: 5px;
}
.dot {
    height: 10px;
    width: 10px;
    margin: 0 3px;
    background-color: #8A2BE2; /* Violeta */
    border-radius: 50%;
    display: inline-block;
    animation: bounce 1.4s infinite ease-in-out both;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1.0); }
}

@keyframes pulse-title {
    0% { transform: scale(1); }
    50% { transform: scale(1.06); }
    100% { transform: scale(1); }
}

/* Responsive: ajustar tamaÃ±o del tÃ­tulo en mÃ³viles */
@media screen and (max-width: 768px) {
    .title-style {
        font-size: 5em !important;
        padding: 15px 0 15px 0 !important;
        margin-top: 5px !important;
    }
}

@media screen and (max-width: 480px) {
    .title-style {
        font-size: 4em !important;
        padding: 10px 0 10px 0 !important;
        margin-top: 0 !important;
    }
    
    .block-container {
        padding-top: 2rem !important;
    }
}

/* --- Â¡NUEVA ANIMACIÃ“N CSS! --- */
.pulsing-q {
    font-size: 1.5em; /* 24px */
    color: red;
    font-weight: bold;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.25); opacity: 0.75; }
    100% { transform: scale(1); opacity: 1; }
}
/* Clase reutilizable para texto verde pulsante */
.green-pulse {
    color: #28a745; /* verde */
    font-weight: bold;
    font-size: 2em;
    animation: pulse 1.2s infinite;
}

/* AnimaciÃ³n de parpadeo lento para el placeholder */
@-webkit-keyframes blink-slow {
    0% { opacity: 1; }
    25% { opacity: 1; }
    50% { opacity: 0; }
    75% { opacity: 0; }
    100% { opacity: 1; }
}
@-moz-keyframes blink-slow {
    0% { opacity: 1; }
    25% { opacity: 1; }
    50% { opacity: 0; }
    75% { opacity: 0; }
    100% { opacity: 1; }
}
@keyframes blink-slow {
    0% { opacity: 1; }
    25% { opacity: 1; }
    50% { opacity: 0; }
    75% { opacity: 0; }
    100% { opacity: 1; }
}

/* Media queries para mÃ³viles (mejor legibilidad en Android/iOS antiguos y modernos) */
@media (max-width: 1200px) {
    .title-style { font-size: 5.2em; }
    .intro-text { font-size: 1.6em; }
}
@media (max-width: 800px) {
    .title-style { font-size: 3.2em; }
    .intro-text { font-size: 1.15em; }
    .welcome-text { font-size: 1.6em; }
}
@media (max-width: 480px) {
    .title-style { font-size: 2.4em; }
    .intro-text { font-size: 1.0em; }
    .welcome-text { font-size: 1.2em; }
    .green-pulse { font-size: 1.2em; }
}
@media (max-width: 360px) {
    .title-style { font-size: 2.0em; }
    .intro-text { font-size: 0.95em; }
    .green-pulse { font-size: 1.0em; }
}

/* Fondo blanco para la casilla de preguntas */
.stChatInput {
    background-color: white !important;
}
.stChatInput > div {
    background-color: white !important;
}
.stChatInput textarea {
    background-color: white !important;
    color: black !important;
    cursor: text !important;
}
.stChatInput textarea::placeholder {
    color: #CC0000 !important;
    font-weight: bold !important;
    opacity: 1 !important;
    -webkit-animation: blink-slow 2s infinite;
    -moz-animation: blink-slow 2s infinite;
    animation: blink-slow 2s infinite;
}
.stChatInput textarea::-webkit-input-placeholder {
    color: #CC0000 !important;
    font-weight: bold !important;
    -webkit-animation: blink-slow 2s infinite;
    animation: blink-slow 2s infinite;
}
.stChatInput textarea::-moz-placeholder {
    color: #CC0000 !important;
    font-weight: bold !important;
    -moz-animation: blink-slow 2s infinite;
    animation: blink-slow 2s infinite;
}
/* Ocultar placeholder cuando "PREGUNTAÂ¡..." estÃ¡ oculto */
.hide-placeholder textarea::placeholder {
    opacity: 0 !important;
    color: transparent !important;
    animation: none !important;
    -webkit-animation: none !important;
    -moz-animation: none !important;
}
.hide-placeholder textarea::-webkit-input-placeholder {
    opacity: 0 !important;
    color: transparent !important;
    animation: none !important;
    -webkit-animation: none !important;
}
.hide-placeholder textarea::-moz-placeholder {
    opacity: 0 !important;
    color: transparent !important;
    animation: none !important;
    -moz-animation: none !important;
}
/* Ocultar placeholder al hacer focus */
.stChatInput textarea:focus::placeholder {
    opacity: 0 !important;
    color: transparent !important;
    animation: none !important;
    -webkit-animation: none !important;
    -moz-animation: none !important;
}
/* Asegurar que el cursor sea visible */
.stChatInput textarea:focus {
    cursor: text !important;
    caret-color: black !important;
}

/* Clase para ocultar el texto PREGUNTA durante la bÃºsqueda */
.pregunta-hidden {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
}

/* Fondo verde para la casilla de nombre */
input[aria-label="Tu Nombre"] {
    background-color: #28a745 !important;
    color: white !important;
    font-weight: bold !important;
    font-size: 1.1em !important;
    cursor: text !important;
    caret-color: white !important;
}
div[data-testid="stTextInput"] input {
    background-color: #28a745 !important;
    color: white !important;
    font-weight: bold !important;
    font-size: 1.1em !important;
    cursor: text !important;
    caret-color: white !important;
}
/* Placeholder de la casilla de nombre */
input[aria-label="Tu Nombre"]::placeholder {
    color: rgba(255, 255, 255, 0.7) !important;
    font-weight: normal !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: rgba(255, 255, 255, 0.7) !important;
    font-weight: normal !important;
}
/* Ocultar placeholder al hacer focus en casilla de nombre */
input[aria-label="Tu Nombre"]:focus::placeholder {
    opacity: 0 !important;
}
div[data-testid="stTextInput"] input:focus::placeholder {
    opacity: 0 !important;
}
</style>
<div class="title-style">GERARD</div>
""", unsafe_allow_html=True)

# (UI refinements removed; restored original behavior)

location = get_user_location()

if 'user_name' not in st.session_state:
    st.session_state.user_name = ''
if 'user_gender' not in st.session_state:
    st.session_state.user_gender = 'No especificar'
if 'messages' not in st.session_state:
    st.session_state.messages = []

# ==================== SIDEBAR CON BOTONES DE EXPORTACIÃ“N ====================
with st.sidebar:
    # BotÃ³n de salida a Radio Voz del Amor
    st.markdown("""
        <a href="https://radio3lavozdelamor.online/radio3lavozdelamor/" target="_blank" 
           style="display: block; text-align: center; background: linear-gradient(135deg, #DC143C 0%, #B22222 100%); 
                  color: white; padding: 12px 20px; border-radius: 25px; text-decoration: none; 
                  font-weight: bold; font-size: 1.1em; margin-bottom: 20px;
                  box-shadow: 0 4px 15px rgba(220, 20, 60, 0.4); transition: all 0.3s ease;">
            ðŸ  SALIR
        </a>
    """, unsafe_allow_html=True)
    
    # Logo/TÃ­tulo del sidebar
    st.markdown("## ðŸ”® GERARD")
    st.markdown("---")
    
    # ============== SECCIÃ“N 1: EXPORTAR CONVERSACIÃ“N (PRIMERO) ==============
    st.markdown("### ðŸ“¥ Exportar ConversaciÃ³n")
    
    # Debug: verificar estado de los mensajes
    num_messages = len(st.session_state.get('messages', []))
    
    # Mostrar contador para debug
    if num_messages > 0:
        st.caption(f"ðŸ” Debug: {num_messages} mensajes detectados")
    
    if num_messages > 0:
        conversation_text = get_conversation_text()
        file_name = generate_download_filename()
        
        # BotÃ³n TXT
        st.download_button(
            label="ðŸ“¥ Descargar TXT",
            data=conversation_text,
            file_name=file_name,
            mime="text/plain",
            key="download_txt_sidebar",
            use_container_width=True,
            help="Descarga la conversaciÃ³n en formato texto"
        )
        
        # BotÃ³n PDF
        pdf_filename = file_name.rsplit('.', 1)[0] + '.pdf'
        if REPORTLAB_AVAILABLE:
            try:
                user_name_for_file = st.session_state.get('user_name', 'usuario')
                html_parts = []
                
                for msg in st.session_state.messages:
                    role = msg.get('role')
                    content_html = msg.get('content', '')
                    
                    if role == 'user':
                        html_parts.append(f'<p style="color: #000000; font-weight: bold;">Pregunta:</p>')
                        html_parts.append(f'<p style="color: #000000;">{content_html}</p>')
                    else:
                        html_parts.append(f'<p style="color: #000000; font-weight: bold;">Respuesta:</p>')
                        html_parts.append(f'<p>{content_html}</p>')
                    html_parts.append('<br/>')
                
                html_parts.append(f'<br/><p style="color: #28a745;">Usuario: {user_name_for_file}</p>')
                html_full = ''.join(html_parts)
                
                pdf_bytes = generate_pdf_from_html(html_full, title_base=f"Consulta - {user_name_for_file}", user_name=user_name_for_file)
                
                st.download_button(
                    label="ðŸ“„ Exportar PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    key="download_pdf_sidebar",
                    help="Descarga la conversaciÃ³n en formato PDF",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
        else:
            st.info("âš ï¸ PDF no disponible")
        
        st.markdown("---")
        st.success(f"ðŸ’¬ **{num_messages} PREGUNTAS** contestadas")
    else:
        st.info("ðŸ’¡ **Inicia una conversaciÃ³n** para ver los botones de exportaciÃ³n aquÃ­")
        st.caption(f"Los botones aparecerÃ¡n automÃ¡ticamente despuÃ©s de tu primera pregunta (Mensajes actuales: {num_messages})")
    
    # ============== SECCIÃ“N 2: CÃ“MO HACER PREGUNTAS (SEGUNDO) ==============
    st.markdown("---")
    with st.expander("â“ **CÃ³mo Hacer Preguntas**", expanded=True):
        st.markdown("""
        ### ðŸŽ¯ CATEGORÃAS DE BÃšSQUEDA
        
        **1ï¸âƒ£ Por Tema EspecÃ­fico**
        - EvacuaciÃ³n, naves, sanaciÃ³n, profecÃ­as
        - Ejemplo: *"Â¿QuÃ© enseÃ±anzas hay sobre la evacuaciÃ³n?"*
        
        **2ï¸âƒ£ Por Maestro**
        - ALANISO, AXEL, ADIEL, AZEN, AVIATAR, etc.
        - Ejemplo: *"Â¿QuÃ© mensajes dio el Maestro ALANISO?"*
        
        **3ï¸âƒ£ Por Concepto**
        - Gran Madre, ejercito de luz, tÃºneles dimensionales
        - Ejemplo: *"ExplÃ­came el concepto de la Gran Madre"*
        
        **4ï¸âƒ£ Por NÃºmero**
        - Meditaciones (36-1044), Mensajes (606-1010)
        - Ejemplo: *"Â¿De quÃ© trata la MeditaciÃ³n 107?"*
        
        ### âœ¨ Tips RÃ¡pidos
        
        âœ… **SÃ© especÃ­fico** - Menciona maestro o tema concreto  
        âœ… **Usa palabras clave** - EvacuaciÃ³n, sanaciÃ³n, naves  
        âœ… **Combina elementos** - "Maestro ALANISO + evacuaciÃ³n"  
        âœ… **Haz seguimiento** - GERARD recuerda la conversaciÃ³n  
        
        ### ï¿½ ObtendrÃ¡s
        
        ðŸ“ **Fuente exacta** del archivo .srt  
        â±ï¸ **Timestamp preciso** (HH:MM:SS)  
        ðŸ“– **Contexto completo** de la enseÃ±anza  
        
        ---
        """)
        
        # BotÃ³n de descarga del PDF de la guÃ­a
        try:
            with open("assets/Guia_GERARD.pdf", "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                st.download_button(
                    label="ï¿½ Descargar GuÃ­a Completa (PDF)",
                    data=pdf_bytes,
                    file_name="Guia_Completa_GERARD.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        except FileNotFoundError:
            st.markdown("ðŸ“š [Ver GuÃ­a en lÃ­nea](https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2/blob/main/GUIA_MODELOS_PREGUNTA_GERARD.md)")

# ============================================================================

if not st.session_state.user_name:
    st.markdown("""
    <p class="intro-text" style="font-size:1.8em; line-height:1.05;">
    Asistente especializado en los mensajes y meditaciones de los 9 Maestros: <strong>ALANISO, AXEL, ALAN, AZEN, AVIATAR, ALADIM, ADIEL, AZOES Y ALIESTRO</strong> junto a
    <br>
    Las tres grandes energias: <strong>EL PADRE AMOR, LA GRAN MADRE Y EL GRAN MAESTRO JESUS.</strong>
    </p>
    <p style="text-align:center; margin-top:12px; font-size:1.25em; text-transform:uppercase; font-weight:bold;">
    TE AYUDARE A ENCONTRAR CON PRECISIÃ“N EL MINUTO Y SEGUNDO EXACTO EN CADA AUDIO O ENSEÃ‘ANZAS QUE YA HAYAS ESCUCHADO ANTERIORMENTE PERO QUE EN EL MOMENTO NO RECUERDAS EXACTAMENTE.
    </p>
    """, unsafe_allow_html=True)
    
    # Auto-scroll lento tipo teleprompter solo en la primera pÃ¡gina
    components.html(
        """
        <script>
            // Auto-scroll lento tipo teleprompter
            (function() {
                const mainSection = window.parent.document.querySelector('section.main');
                if (!mainSection) return;
                
                let currentPosition = 0;
                const scrollHeight = mainSection.scrollHeight;
                const viewportHeight = mainSection.clientHeight;
                const maxScroll = scrollHeight - viewportHeight;
                
                // DuraciÃ³n total del scroll en milisegundos (60 segundos para lectura muy lenta tipo teleprompter)
                const duration = 60000;
                const fps = 60;
                const frameTime = 1000 / fps;
                const totalFrames = duration / frameTime;
                const pixelsPerFrame = maxScroll / totalFrames;
                
                let frameCount = 0;
                
                const scrollInterval = setInterval(function() {
                    if (frameCount >= totalFrames || currentPosition >= maxScroll) {
                        clearInterval(scrollInterval);
                        return;
                    }
                    
                    currentPosition += pixelsPerFrame;
                    mainSection.scrollTo({
                        top: currentPosition,
                        behavior: 'auto'  // Sin smooth para control preciso
                    });
                    
                    frameCount++;
                }, frameTime);
                
                // Detener el scroll si el usuario interactÃºa con la pÃ¡gina
                mainSection.addEventListener('wheel', function() {
                    clearInterval(scrollInterval);
                }, { once: true });
                
                mainSection.addEventListener('touchstart', function() {
                    clearInterval(scrollInterval);
                }, { once: true });
            })();
        </script>
        """,
        height=0,
    )
    
    st.markdown('<div style="text-align:center; margin-top:8px;"><span class="green-pulse">TU NOMBRE</span></div>', unsafe_allow_html=True)
    user_name_input = st.text_input("Tu Nombre", key="name_inputter", label_visibility="collapsed")
    if user_name_input:
        st.session_state.user_name = user_name_input.upper()
        # DetecciÃ³n automÃ¡tica del gÃ©nero desde el nombre (sin confirmaciÃ³n)
        detected = detect_gender_from_name(user_name_input)
        # Asignar gÃ©nero automÃ¡ticamente
        st.session_state.user_gender = detected
        # Siempre hacer rerun al ingresar el nombre para mostrar bienvenida
        st.rerun()
else:
    # Construir bienvenida segÃºn gÃ©nero detectado
    gender = st.session_state.get('user_gender', 'No especificar')
    if gender == 'Femenino':
        bienvenida = 'BIENVENIDA'
    elif gender == 'Masculino':
        bienvenida = 'BIENVENIDO'
    else:
        bienvenida = 'BIENVENID@'

    st.markdown(f"""
    <div class="welcome-text">{bienvenida} {st.session_state.user_name}</div>
    <p class="sub-welcome-text">AHORA YA PUEDES REALIZAR TUS PREGUNTAS EN LA PARTE INFERIOR</p>
    """, unsafe_allow_html=True)

# --- Mostrar historial con avatares personalizados ---
for message in st.session_state.messages:
    avatar = user_avatar if message["role"] == "user" else assistant_avatar
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"], unsafe_allow_html=True)

# --- Botones movidos al sidebar para mejor accesibilidad ---

# --- Mostrar GIF de pregunta CASI PEGADO al input (parte inferior) ---
# Centrar el GIF y dejarlo en tamaÃ±o natural para que se anime
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    st.image("assets/pregunta.gif")  # SIN width para mantener animaciÃ³n

# Margen negativo MUY agresivo para pegarlo casi a la casilla
st.markdown('<div style="margin-top: -50px; margin-bottom: -20px;"></div>', unsafe_allow_html=True)

# Texto "PREGUNTAÂ¡..." animado encima de la casilla (solo si el usuario ya ingresÃ³ su nombre)
if st.session_state.user_name:
    st.markdown("""
    <div id="pregunta-prompt" style="text-align: left; margin-left: 15px; margin-bottom: 5px;">
        <span style="color: #CC0000; font-weight: bold; font-size: 3.3em; animation: blink-slow 2s infinite;">PREGUNTAÂ¡...</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Script para agregar el placeholder dinÃ¡micamente solo cuando PREGUNTA estÃ¡ visible
    components.html(
        """
        <script>
            setTimeout(function() {
                const chatInput = window.parent.document.querySelector('.stChatInput textarea');
                if (chatInput && !chatInput.hasAttribute('data-placeholder-set')) {
                    chatInput.setAttribute('placeholder', 'AQUIÂ¡... âžª');
                    chatInput.setAttribute('data-placeholder-set', 'true');
                }
            }, 100);
        </script>
        """,
        height=0,
    )

# --- Input del usuario con avatares personalizados ---
if prompt_input := st.chat_input(""):
    pass  # Procesar despuÃ©s

if prompt_input:
    if not st.session_state.user_name:
        st.markdown("""
        <div style="text-align: center; margin: 20px 0;">
            <p style="color: red; font-size: 1.3em; font-weight: bold; animation: pulse 1.5s infinite;">
                INGRESA primero TU NOMBRE<br>
                en la casilla verde de arriba.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # --- Â¡AQUÃ ESTÃ EL CAMBIO! ---
        # Se reemplaza la imagen por un texto animado con CSS
        styled_prompt = f"""
        <div style="display: flex; align-items: center; justify-content: flex-start;">
            <span style="text-transform: uppercase; color: orange; margin-right: 8px; font-weight: bold;">{prompt_input}</span>
            <span class="pulsing-q">?</span>
        </div>
        """
        
        st.session_state.messages.append({"role": "user", "content": styled_prompt})
        
        with st.chat_message("user", avatar=user_avatar):
            st.markdown(styled_prompt, unsafe_allow_html=True)

        with st.chat_message("assistant", avatar=assistant_avatar):
            response_placeholder = st.empty()
            
            # Auto-scroll hacia abajo usando components.html (mÃ¡s confiable que st.markdown)
            components.html(
                """
                <script>
                    window.parent.document.querySelector('section.main').scrollTo({
                        top: window.parent.document.querySelector('section.main').scrollHeight,
                        behavior: 'smooth'
                    });
                </script>
                """,
                height=0,
            )
            
            # Contenedor temporal para mostrar GIF + texto de carga
            with response_placeholder.container():
                # GIF ovni centrado (SIN width para mantener animaciÃ³n)
                col1, col2, col3 = st.columns([1.5, 1, 1.5])
                with col2:
                    st.image("assets/ovni.gif")  # SIN width parameter
                
                # Texto "Buscando..." con puntos animados debajo del GIF
                loader_html = """
                <div class="loader-container" style="text-align: center; margin-top: -15px;">
                    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                    <span style='margin-left: 10px; font-style: italic; color: #FF00FF; font-size: 1.8em; font-weight: bold; text-transform: uppercase;'>BUSCANDO...</span>
                </div>
                <script>
                    // Ocultar el texto "PREGUNTAÂ¡..." y el placeholder mientras se muestra "BUSCANDO..."
                    (function hideElements() {
                        const preguntaPrompt = window.parent.document.getElementById('pregunta-prompt');
                        if (preguntaPrompt) {
                            preguntaPrompt.classList.add('pregunta-hidden');
                        }
                        
                        // Ocultar el placeholder agregando clase Y borrando el atributo
                        const chatInput = window.parent.document.querySelector('.stChatInput');
                        const chatTextarea = window.parent.document.querySelector('.stChatInput textarea');
                        if (chatInput) {
                            chatInput.classList.add('hide-placeholder');
                        }
                        if (chatTextarea) {
                            chatTextarea.setAttribute('placeholder', '');
                            chatTextarea.removeAttribute('data-placeholder-set');
                        }
                    })();
                </script>
                """
                st.markdown(loader_html, unsafe_allow_html=True)

            try:
                # Obtener ubicaciÃ³n del usuario
                location = get_user_location()
                
                # Inicializar el logger
                logger = init_logger()
                
                # Inicializar Google Sheets Logger
                sheets_logger = init_sheets_logger()
                
                # Debug: imprimir estado en logs (no en UI para no molestar)
                print(f"[DEBUG UI] Google Sheets Logger enabled: {sheets_logger.enabled if sheets_logger else False}")
                
                # Obtener informaciÃ³n del dispositivo y ubicaciÃ³n
                # Obtener user agent del navegador
                user_agent = st.context.headers.get("User-Agent", "Unknown") if hasattr(st, 'context') and hasattr(st.context, 'headers') else "Unknown"
                
                # Iniciar el registro de la interacciÃ³n
                interaction_id = logger.start_interaction(
                    user=st.session_state.user_name,
                    question=prompt_input,
                    request_info={"user_agent": user_agent}
                )
                
                # Construir retrieval_chain a demanda si no existe
                if retrieval_chain is None:
                    # Intentar cargar recursos reales; esto validarÃ¡ la API key y el Ã­ndice
                    try:
                        llm_loaded, vs = load_resources()
                        print(f"[DEBUG] load_resources completado - LLM: {type(llm_loaded)}, VS: {type(vs)}")
                    except Exception as e:
                        print(f"[ERROR] load_resources fallÃ³: {e}")
                        response_placeholder.error(f"No fue posible inicializar los recursos: {e}")
                        raise
                    
                    # BÃšSQUEDA HÃBRIDA: vectorial + keyword fallback
                    # Usar lambda para pasar el vectorstore a hybrid_retrieval
                    def hybrid_retriever_func(query: str):
                        return hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)
                    
                    print(f"[DEBUG] Retriever hÃ­brido creado (k_vector=100, k_keyword=30)")

                    # Si el LLM no se pudo inicializar, usamos un FakeChain que sÃ³lo regresa documentos
                    if llm_loaded is None:
                        class FakeChain:
                            def __init__(self, retriever_func):
                                self.retriever_func = retriever_func

                            def invoke(self, payload):
                                query = payload if isinstance(payload, str) else payload.get('input', '')
                                # obtener documentos relevantes usando bÃºsqueda hÃ­brida
                                docs = self.retriever_func(query)

                                items = []
                                for d in list(docs)[:3]:
                                    src = os.path.basename(d.metadata.get('source', 'desconocido'))
                                    snippet = re.sub(r'\s+', ' ', d.page_content)[:300]
                                    items.append({"type": "normal", "content": f"Fuente: {src} - {snippet}"})
                                if not items:
                                    items = [{"type": "normal", "content": "No se encontraron documentos relevantes en el Ã­ndice."}]
                                return json.dumps(items, ensure_ascii=False)

                        retrieval_chain = FakeChain(hybrid_retriever_func)
                    else:
                        # Reconstruir retrieval_chain con bÃºsqueda hÃ­brida
                        retrieval_chain = (
                            {
                                "context": (lambda x: x["input"]) | RunnableLambda(hybrid_retriever_func) | format_docs_with_metadata,
                                "input": lambda x: x["input"],
                                "date": lambda x: x.get("date", ""),
                                "session_hash": lambda x: x.get("session_hash", "")
                            }
                            | prompt
                            | llm_loaded
                            | StrOutputParser()
                        )

                # Preparar variables requeridas por el prompt (date y session_hash)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                session_hash = str(uuid.uuid4())
                payload = {"input": prompt_input, "date": ts, "session_hash": session_hash}
                
                print(f"[DEBUG] Antes de invoke - retrieval_chain type: {type(retrieval_chain)}")
                answer_raw = retrieval_chain.invoke(payload)
                print(f"[DEBUG] DespuÃ©s de invoke - answer_raw type: {type(answer_raw)}, valor: {str(answer_raw)[:200]}")
                
                # Asegurar que answer_json sea siempre un string JSON
                if isinstance(answer_raw, dict):
                    print(f"[DEBUG] answer_raw es dict, convirtiendo a JSON string")
                    answer_json = json.dumps(answer_raw, ensure_ascii=False)
                else:
                    answer_json = answer_raw if isinstance(answer_raw, str) else str(answer_raw)
                
                print(f"[DEBUG] answer_json type final: {type(answer_json)}")
                
                # Debug: verificar tipo antes de save_to_log
                if not isinstance(answer_json, str):
                    st.error(f"âŒ DEBUG: answer_json es tipo {type(answer_json)}, convirtiendo a string...")
                    answer_json = json.dumps(answer_json, ensure_ascii=False) if isinstance(answer_json, (dict, list)) else str(answer_json)
                
                # Registro antiguo (mantener por compatibilidad)
                save_to_log(st.session_state.user_name, prompt_input, answer_json, location)
                
                # Finalizar el registro de la interacciÃ³n con el logger completo
                logger.end_interaction(
                    session_id=interaction_id,
                    status="success"
                )
                
                # Registrar en Google Sheets si estÃ¡ disponible
                if sheets_logger:
                    try:
                        # Usar informaciÃ³n del dispositivo y ubicaciÃ³n ya obtenidos
                        device_detector = DeviceDetector()
                        device_raw = device_detector.detect_from_web(user_agent)
                        
                        # Mapear las claves correctamente
                        device_info = {
                            "device_type": device_raw.get("tipo", "Desconocido"),
                            "browser": device_raw.get("navegador", "Desconocido"),
                            "os": device_raw.get("os", "Desconocido")
                        }
                        print(f"[DEBUG] Device Info: {device_info}")
                        
                        # Usar la ubicaciÃ³n ya obtenida al inicio
                        location_info = {
                            "city": location.get("city", "Desconocida") if location else "Desconocida",
                            "country": location.get("country", "Desconocido") if location else "Desconocido",
                            "ip": location.get("ip", "No disponible") if location else "No disponible",
                            "latitude": location.get("latitude", 0) if location else 0,
                            "longitude": location.get("longitude", 0) if location else 0
                        }
                        print(f"[DEBUG] Location Info: {location_info}")
                        
                        # Calcular tiempo de respuesta
                        timing_info = {
                            "total_time": (datetime.now() - datetime.fromisoformat(ts.replace(' ', 'T'))).total_seconds()
                        }
                        print(f"[DEBUG] Timing Info: {timing_info}")
                        
                        # Convertir answer_json a texto limpio para Google Sheets
                        try:
                            # Intentar extraer el texto limpio del JSON
                            answer_for_sheets = get_clean_text_from_json(answer_json)
                        except:
                            # Si falla, usar el JSON como string
                            answer_for_sheets = str(answer_json)
                        
                        print(f"[DEBUG] Enviando a Google Sheets - User: {st.session_state.user_name}, Question: {prompt_input[:50]}...")
                        
                        sheets_logger.log_interaction(
                            interaction_id=interaction_id,
                            user=st.session_state.user_name,
                            question=prompt_input,
                            answer=answer_for_sheets,  # Texto limpio en lugar de JSON
                            device_info=device_info,
                            location_info=location_info,
                            timing=timing_info,
                            success=True
                        )
                        
                        print(f"[OK] Registro enviado a Google Sheets exitosamente")
                        
                    except Exception as e:
                        print(f"[ERROR] Error al registrar en Google Sheets: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[INFO] Google Sheets Logger no estÃ¡ disponible o no estÃ¡ habilitado")
                
                match = re.search(r'\[.*\]', answer_json, re.DOTALL)
                if not match:
                    st.error("La respuesta del modelo no fue un JSON vÃ¡lido.")
                    response_html = f'<p style="color:red;">{answer_json}</p>'
                else:
                    data = json.loads(match.group(0))
                    response_html = f'<strong style="color:#28a745;">{st.session_state.user_name}:</strong> '
                    for item in data:
                        content_type = item.get("type", "normal")
                        content = item.get("content", "")
                        if content_type == "emphasis":
                            # Resalta en magenta el texto entre parÃ©ntesis, el resto amarillo
                            def magenta_parentheses(text):
                                return re.sub(r'(\(.*?\))', r'<span style="color:#FF00FF; font-weight: bold;">\1</span>', text)
                            content_colored = magenta_parentheses(content)
                            response_html += f'<span style="color:yellow; background-color: #333; border-radius: 4px; padding: 2px 4px;">{content_colored}</span>'
                        else:
                            # Cambiar color de fuentes (texto entre parÃ©ntesis) a MAGENTA
                            content_html = re.sub(r'(\(.*?\))', r'<span style="color:#FF00FF; font-weight: bold;">\1</span>', content)
                            response_html += content_html
                
                response_placeholder.markdown(response_html, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response_html})
                
                # Marcar que se agregÃ³ un mensaje nuevo para actualizar el sidebar
                st.session_state['_new_message_added'] = True
                
                # Auto-scroll despuÃ©s de mostrar la respuesta completa (mÃ¡s confiable con components.html)
                components.html(
                    """
                    <script>
                        setTimeout(function() {
                            // Auto-scroll
                            window.parent.document.querySelector('section.main').scrollTo({
                                top: window.parent.document.querySelector('section.main').scrollHeight,
                                behavior: 'smooth'
                            });
                            
                            // Restaurar el texto "PREGUNTAÂ¡..." y el placeholder despuÃ©s de mostrar la respuesta
                            const preguntaPrompt = window.parent.document.getElementById('pregunta-prompt');
                            if (preguntaPrompt) {
                                preguntaPrompt.classList.remove('pregunta-hidden');
                            }
                            
                            // Restaurar el placeholder removiendo clase Y restaurando el atributo
                            const chatInput = window.parent.document.querySelector('.stChatInput');
                            const chatTextarea = window.parent.document.querySelector('.stChatInput textarea');
                            if (chatInput) {
                                chatInput.classList.remove('hide-placeholder');
                            }
                            if (chatTextarea) {
                                chatTextarea.setAttribute('placeholder', 'AQUIÂ¡... âžª');
                                chatTextarea.setAttribute('data-placeholder-set', 'true');
                            }
                        }, 300);
                    </script>
                    """,
                    height=0,
                )
                
                # NOTA: st.rerun() aquÃ­ causaba que los botones de descarga no aparecieran
                # porque recargaba la pÃ¡gina antes de llegar a renderizar los botones
                # st.rerun()

                # --- Ofrecer descarga del Ãºltimo intercambio (pregunta + respuesta) ---
                try:
                    # Texto plano para el archivo
                    def html_to_text(html: str) -> str:
                        return re.sub(r'<[^>]+>', '', html).strip()

                    user_text = prompt_input.strip()
                    assistant_text = html_to_text(response_html)
                    single_qa_text = f"Pregunta: {user_text}\n\nRespuesta:\n{assistant_text}\n"
                except Exception:
                    # No queremos que una falla aquÃ­ rompa la experiencia principal
                    pass

            except Exception as e:
                # Registrar el error en el logger
                try:
                    logger.end_interaction(
                        session_id=interaction_id,
                        status="error",
                        error=str(e)
                    )
                except:
                    pass  # Si el logger falla, no queremos romper la app
                
                response_placeholder.error(f"OcurriÃ³ un error al procesar tu pregunta: {e}")

# Actualizar sidebar si se agregÃ³ un mensaje nuevo
if st.session_state.get('_new_message_added', False):
    st.session_state['_new_message_added'] = False
    st.rerun()