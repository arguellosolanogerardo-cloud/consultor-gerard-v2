# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import colorama

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
import streamlit as st
import streamlit.components.v1 as components
import requests  # Para obtener la IP y geolocalización
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
    if not api_key:
        st.error(
            "Error: La variable de entorno GOOGLE_API_KEY no está configurada. Añade la clave a las variables de entorno o a Streamlit Secrets."
        )
        st.stop()

    # Pasar la API key explícitamente evita que la librería intente usar ADC
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

        # Inicializar LLM si la clase está disponible
        if GoogleGenerativeAI is not None:
            try:
                llm = GoogleGenerativeAI(
                    model="models/gemini-2.5-pro", 
                    google_api_key=api_key,
                    temperature=0.4,  # Precisión quirúrgica según prompt GERARD
                    top_p=0.90,
                    top_k=25
                )
            except Exception as e:
                st.warning(f"No se pudo inicializar el LLM (GoogleGenerativeAI): {e}. La aplicación usará un modo de recuperación local sin LLM.")

        # Inicializar embeddings (o usar fallback) y cargar FAISS
        try:
            # Intentar usar la clase oficial si está disponible
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
                # Intentar deducir la dimensión del índice FAISS para generar vectores compatibles
                target_dim = 768
                try:
                    import faiss
                    idx_path = os.path.join('faiss_index', 'index.faiss')
                    if os.path.exists(idx_path):
                        idx = faiss.read_index(idx_path)
                        target_dim = getattr(idx, 'd', target_dim)
                except Exception:
                    # Si faiss no está disponible o falla, seguimos con el valor por defecto
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
                st.error("⚠️ ADVERTENCIA: Usando embeddings simuladas (hash-based). La búsqueda semántica será limitada. Verifica la API key de Google.")

            
            # === DESCARGA MOVIDA FUERA DE CACHE ===
            # Ver funcion download_faiss_if_needed() antes de load_resources()
            

            faiss_vs = FAISS.load_local(folder_path="faiss_index", embeddings=embeddings, allow_dangerous_deserialization=True)
            # Debug: verificar que se cargó correctamente
            doc_count = faiss_vs.index.ntotal if hasattr(faiss_vs, 'index') else 'unknown'
            print(f"[DEBUG load_resources] FAISS cargado exitosamente con {doc_count} documentos")
            # Mostrar mensaje con estilo tenue y sin fondo
            st.markdown(
                f'<p style="color: rgba(128, 128, 128, 0.5); font-size: 0.85em; margin: 5px 0;">✅ Base vectorial cargada: {doc_count} BLOQUES CHUNKS disponibles</p>',
                unsafe_allow_html=True
            )
        except Exception as e:
            print(f"[ERROR load_resources] Error al cargar FAISS: {e}")
            st.error(f"❌ No fue posible cargar el índice FAISS: {e}")
            st.stop()

    return llm, faiss_vs

# NOTA: No ejecutar load_resources() al importar el módulo para evitar inicializar
# las librerías de Google (protobuf/GRPC) en el arranque de Streamlit. La carga
# se hará bajo demanda cuando el usuario envíe una consulta.

# --- Inicializar sistema de logging completo ---
@st.cache_resource
def init_logger():
    """Inicializa el sistema de logging con detección de dispositivo y geolocalización."""
    return InteractionLogger(
        platform="web",
        log_dir="logs",
        anonymize=False,  # Guardar datos completos
        enable_json=True  # Guardar también en formato JSON
    )

# --- Inicializar Google Sheets Logger (si está disponible) ---
@st.cache_resource
def init_sheets_logger():
    """Inicializa el logger de Google Sheets si está configurado."""
    if GOOGLE_SHEETS_AVAILABLE:
        return create_sheets_logger()
    return None

# --- Lógica de GERARD v3.01 - Actualizado ---
prompt = ChatPromptTemplate.from_template(r"""
🔬 GERARD v3.01 - Sistema de Análisis Investigativo Avanzado
IDENTIDAD DEL SISTEMA
═══════════════════════════════════════════════════════════
Nombre: GERARD
Versión: 3.01 - Analista Documental
Modelo Base: Gemini Pro Latest 2.5
Temperatura: 0.3-0.5 (Máxima Precisión y Consistencia)
Especialización: Criptoanálisis de Archivos .srt
═══════════════════════════════════════════════════════════
MISIÓN CRÍTICA
Eres GERARD, un sistema de inteligencia analítica especializado en arqueología documental de archivos de subtítulos (.srt). Tu propósito es descubrir patrones ocultos, mensajes encriptados y conexiones invisibles que emergen al correlacionar múltiples documentos mediante técnicas forenses avanzadas. DESCUBRIR EXACTAMENTE EL TITULO, LA HORA, EL MINUTO DE LOS ARCHIVOS.SRT QUE ESTAN EN LA BASE VECTORIAL COMO FUENTE UNICA DEL CONOCIMIENTO
Configuración de Temperatura Optimizada (0.2-0.3)
Esta temperatura baja garantiza:
• Consistencia absoluta entre consultas repetidas
• Reproducibilidad de hallazgos para verificación
• Precisión quirúrgica en extracción de datos
• Eliminación de variabilidad en respuestas críticas
• Confiabilidad forense en análisis investigativos
________________________________________
🚨 PROTOCOLOS DE SEGURIDAD ANALÍTICA
REGLAS ABSOLUTAS (Nivel de Cumplimiento: 100%)
🔴 PROHIBICIÓN NIVEL 1: FABRICACIÓN DE DATOS
├─ ❌ NO inventar información bajo ninguna circunstancia
├─ ❌ NO usar conocimiento del modelo base (entrenamiento general)
├─ ❌ NO suponer o inferir más allá de lo textualmente disponible
└─ ❌ NO completar información faltante con lógica externa

🔴 PROHIBICIÓN NIVEL 2: CONTAMINACIÓN ANALÍTICA
├─ ❌ NO mezclar análisis con citas textuales
├─ ❌ NO parafrasear cuando se requiere texto literal
├─ ❌ NO interpretar sin declarar explícitamente que es interpretación
└─ ❌ NO omitir información contradictoria si existe

🟢 MANDATOS OBLIGATORIOS
├─ ✅ Cada afirmación DEBE tener cita textual verificable
├─ ✅ Cada cita DEBE incluir: [Documento] + [Timestamp] + [Texto Literal]
├─ ✅ Cada análisis DEBE separarse claramente de evidencias
├─ ✅ Cada consulta DEBE ejecutar los 8 Protocolos de Búsqueda Profunda
└─ ✅ Cada respuesta DEBE incluir nivel de confianza estadístico
________________________________________
� INSTRUCCIÓN CRÍTICA DE FORMATO
CADA FRASE O PÁRRAFO de respuesta DEBE ir seguido inmediatamente de su cita de fuente en PARÉNTESIS.
El texto de la cita DEBE ir en COLOR MAGENTA.
Formato: [Tu respuesta aquí] (Fuente: TITULO_ARCHIVO, Timestamp: HH:MM:SS)

EJEMPLO:
"El amor es la fuerza más poderosa del universo (Fuente: MEDITACION_42_EL_AMOR_DIVINO, Timestamp: 00:15:32)"

🚨 FORMATO DE SALIDA OBLIGATORIO (JSON)
CRÍTICO: Tu respuesta DEBE ser un array JSON válido con esta estructura exacta:

[
  {{"type": "normal", "content": "Texto con su cita (Fuente: archivo, Timestamp: HH:MM:SS)"}},
  {{"type": "emphasis", "content": "Texto enfatizado con su cita (Fuente: archivo, Timestamp: HH:MM:SS)"}},
  {{"type": "normal", "content": "Más texto con cita (Fuente: archivo, Timestamp: HH:MM:SS)"}}
]

REGLAS:
- type: puede ser "normal" o "emphasis"
- content: string que SIEMPRE incluye la cita de fuente al final entre paréntesis
- Formato de cita: (Fuente: NOMBRE_EXACTO_archivo, Timestamp: HH:MM:SS)
- NO agregues texto fuera del array JSON
- NO uses markdown, solo el array JSON puro
- NUNCA omitas la cita de fuente

Contexto disponible:
{context}

Consulta del usuario: {input}

Basándote estrictamente en el contenido disponible arriba, responde la consulta en formato JSON con citas obligatorias.

═══════════════════════════════════════════════════════════
FIN DEL ANÁLISIS
LA VERDAD OS HARA LIBRES
LA CLAVE ES EL AMOR
═══════════════════════════════════════════════════════════
""")

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
    Búsqueda híbrida: vectorial + keyword fallback
    
    1. Hace búsqueda vectorial normal (k_vector docs)
    2. Si los términos clave no aparecen en los resultados, 
       busca directamente en el docstore por keywords
    3. Combina resultados únicos
    
    Args:
        vectorstore: FAISS vectorstore
        query: consulta del usuario
        k_vector: número de docs a recuperar con búsqueda vectorial
        k_keyword: número de docs adicionales a buscar con keywords
    
    Returns:
        Lista de documentos únicos combinados
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
    """Formatea una secuencia de documentos recuperados y limpia su contenido.
    
    docs: iterable de objetos con atributos `metadata` (dict) y `page_content` (str).
    Devuelve una única cadena con todos los documentos formateados.
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
@st.cache_data
def get_user_location() -> dict:
    """
    Obtiene la ubicación del usuario usando ipinfo.io.
    Retorna un diccionario con los datos de ubicación.
    """
    try:
        response = requests.get('https://ipinfo.io/json', timeout=5)
        data = response.json()
        
        # Extraer coordenadas si están disponibles
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
        print(f"[!] Error obteniendo ubicación: {e}")
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

def fix_utf8_encoding(text: str) -> str:
    """Corrige problemas de codificación UTF-8 comunes en Streamlit Cloud."""
    if not isinstance(text, str):
        return text
        
    import unicodedata
    
    # Normalizar Unicode
    text = unicodedata.normalize('NFC', text)
    
    # Diccionario de reemplazos para caracteres mal codificados
    replacements = {
        # Caracteres básicos problemáticos
        'â€™': "'",
        'â€œ': '"',
        'â€': '"',
        'â€"': '–',
        'â€"': '—',
        'â€¦': '...',
        
        # Vocales acentuadas
        'Ã¡': 'á',
        'Ã©': 'é', 
        'Ã­': 'í',
        'Ã³': 'ó',
        'Ãº': 'ú',
        'Ã±': 'ñ',
        'Ã¼': 'ü',
        'Ã': 'Á',
        'Ã‰': 'É',
        'Ãœ': 'Ü',
        
        # Caracteres especiales
        'â‚¬': '€',
        'â„¢': '™',
        'Â®': '®',
        'Â©': '©',
        'Â°': '°',
        'Â¿': '¿',
        'Â¡': '¡',
        'Â ': ' ',
        
        # Casos específicos observados
        'ConversaciÃ³n': 'Conversación',
        'ExportaciÃ³n': 'Exportación', 
        'exportaciÃ³n': 'exportación',
        'conversaciÃ³n': 'conversación',
        'aquÃ­': 'aquí',
        'aparecerÃ¡n': 'aparecerán',
        'automÃ¡ticamente': 'automáticamente',
        'despuÃ©s': 'después',
        'CÃ³mo': 'Cómo',
        'CATEGORÃAS': 'CATEGORÍAS',
        'BÃšSQUEDA': 'BÚSQUEDA',
        'EspecÃ­fico': 'Específico',
        'EvacuaciÃ³n': 'Evacuación',
        'sanaciÃ³n': 'sanación',
        'profecÃ­as': 'profecías',
        'enseÃ±anzas': 'enseñanzas',
        'evacuaciÃ³n': 'evacuación',
        'QuÃ©': 'Qué',
        'tÃºneles': 'túneles',
        'ExplÃ­came': 'Explícame',
        'NÃºmero': 'Número',
        'MeditaciÃ³n': 'Meditación',
        'quÃ©': 'qué',
        'RÃ¡pidos': 'Rápidos',
        'especÃ­fico': 'específico',
        'ObtendrÃ¡s': 'Obtendrás',
        'enseÃ±anza': 'enseñanza',
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    return text

def force_streamlit_utf8():
    """Elimina TODOS los emojis y caracteres problemáticos."""
    import streamlit as st
    
    # JavaScript RADICAL para eliminar caracteres problemáticos
    st.components.v1.html("""
        <script>
            function cleanAllText() {
                // Encontrar TODOS los elementos con texto
                const allElements = document.querySelectorAll('*');
                
                allElements.forEach(element => {
                    // Solo procesar nodos de texto
                    const walker = document.createTreeWalker(
                        element,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    const textNodes = [];
                    let node;
                    while (node = walker.nextNode()) {
                        textNodes.push(node);
                    }
                    
                    textNodes.forEach(textNode => {
                        let text = textNode.textContent;
                        
                        // REMOVER caracteres problemáticos específicos
                        text = text.replace(/ðŸ/g, '');
                        text = text.replace(/â/g, '');
                        text = text.replace(/1ï¸âƒ£/g, '1');
                        text = text.replace(/2ï¸âƒ£/g, '2');
                        text = text.replace(/3ï¸âƒ£/g, '3');
                        text = text.replace(/4ï¸âƒ£/g, '4');
                        text = text.replace(/âœ/g, '');
                        text = text.replace(/ï¿½/g, '');
                        
                        // CORREGIR caracteres con tildes
                        text = text.replace(/Ã³/g, 'O');
                        text = text.replace(/Ã­/g, 'I');
                        text = text.replace(/Ã¡/g, 'A');
                        text = text.replace(/Ã©/g, 'E');
                        text = text.replace(/Ãº/g, 'U');
                        text = text.replace(/Ã±/g, 'N');
                        text = text.replace(/Ã/g, 'A');
                        text = text.replace(/Ã‰/g, 'E');
                        text = text.replace(/Ãš/g, 'U');
                        
                        // REEMPLAZOS específicos completos
                        text = text.replace(/ConversaciÃ³n/g, 'CONVERSACION');
                        text = text.replace(/ExportaciÃ³n/g, 'EXPORTACION');
                        text = text.replace(/conversaciÃ³n/g, 'CONVERSACION');
                        text = text.replace(/aquÃ­/g, 'AQUI');
                        text = text.replace(/aparecerÃ¡n/g, 'APARECERAN');
                        text = text.replace(/automÃ¡ticamente/g, 'AUTOMATICAMENTE');
                        text = text.replace(/despuÃ©s/g, 'DESPUES');
                        text = text.replace(/CÃ³mo/g, 'COMO');
                        text = text.replace(/CATEGORÃAS/g, 'CATEGORIAS');
                        text = text.replace(/BÃšSQUEDA/g, 'BUSQUEDA');
                        
                        if (text !== textNode.textContent) {
                            textNode.textContent = text;
                        }
                    });
                });
            }
            
            // Ejecutar múltiples veces
            setTimeout(cleanAllText, 100);
            setTimeout(cleanAllText, 500);
            setTimeout(cleanAllText, 1000);
            setTimeout(cleanAllText, 2000);
            
            // Observador agresivo
            const observer = new MutationObserver(function() {
                setTimeout(cleanAllText, 10);
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                characterData: true
            });
            
            console.log('RADICAL text cleaner active');
        </script>
    """, height=0)

def get_clean_text_from_json(json_string: str) -> str:
    try:
        # Debug: mostrar tipo recibido
        print(f"[DEBUG get_clean_text_from_json] Tipo recibido: {type(json_string)}")
        
        # Convertir a string si recibimos un dict o list
        if isinstance(json_string, (dict, list)):
            print(f"[DEBUG] Convirtiendo {type(json_string)} a JSON string")
            json_string = json.dumps(json_string, ensure_ascii=False, indent=None)
        
        # Asegurar que el texto esté en UTF-8 correcto
        if isinstance(json_string, str):
            # Limpiar caracteres de control y normalizar
            json_string = ''.join(char for char in json_string if ord(char) >= 32 or char in '\n\t')
            # Normalizar Unicode
            import unicodedata
            json_string = unicodedata.normalize('NFC', json_string)
        
        # Remover backticks de markdown si existen
        json_string = re.sub(r'^```json\s*', '', json_string.strip())
        json_string = re.sub(r'\s*```$', '', json_string.strip())
        
        match = re.search(r'\[.*\]', json_string, re.DOTALL)
        if not match:
            print(f"[DEBUG get_clean_text_from_json] No se encontró array JSON")
            return json_string

        data = json.loads(match.group(0))
        # Concatenar todo el contenido de los items
        clean_text = " ".join([item.get("content", "") for item in data])
        
        # Limpiar y normalizar el texto final
        if clean_text:
            clean_text = unicodedata.normalize('NFC', clean_text)
            # Reemplazar caracteres problemáticos comunes
            clean_text = clean_text.replace('â€™', "'")
            clean_text = clean_text.replace('â€œ', '"')
            clean_text = clean_text.replace('â€', '"')
            clean_text = clean_text.replace('â€"', '–')
            clean_text = clean_text.replace('â€"', '—')
            
        print(f"[DEBUG get_clean_text_from_json] Texto limpio extraído: {clean_text[:100]}...")
        return clean_text
    except Exception as ex:
        print(f"[DEBUG get_clean_text_from_json] ERROR: {ex}")
        import traceback
        traceback.print_exc()
        return json_string


def detect_gender_from_name(name: str) -> str:
    """Heurística simple para detectar género a partir del primer nombre.
    Regla principal: termina en 'a' -> Femenino, termina en 'o' -> Masculino.
    Usa listas de excepciones comunes para mejorar la precisión.
    Devuelve: 'Masculino', 'Femenino' o 'No especificar'.
    """
    if not name or not name.strip():
        return 'No especificar'
    # Normalizar y tomar primer token
    first = name.strip().split()[0].lower()
    # Quitar caracteres no alfabéticos (mantener acentos y ñ)
    first = re.sub(r"[^a-záéíóúüñ]", "", first)

    # Listas de nombres comunes (no exhaustivas)
    male_names = {"juan","carlos","pedro","jose","luis","miguel","axel","alan","adriel","adiel","alaniso","aladio","adolfo"}
    female_names = {"maria","ana","laura","mariana","isabela","isabella","sofia","sofia"}

    if first in male_names:
        return 'Masculino'
    if first in female_names:
        return 'Femenino'

    # Regla por terminación (heurística fuerte en español)
    if first.endswith(('a','á')):
        return 'Femenino'
    if first.endswith(('o','ó')):
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
        f.write(f"--- Conversación del {timestamp} ---\n")
        f.write(f"Usuario: {user}\n")
        f.write(f"Ubicación: {location}\n")
        f.write(f"Pregunta: {question}\n")
        f.write(f"Respuesta de GERARD: {clean_answer}\n")
        f.write("="*40 + "\n\n")

def get_conversation_text() -> str:
    conversation = []
    for message in st.session_state.get('messages', []):
        content_html = message["content"]
        # Extraer texto plano de la forma más simple posible
        text_content = re.sub(r'<[^>]+>', '', content_html).strip()
        
        if message["role"] == "user":
            # Para el usuario, el texto relevante está en el span uppercase
            match = re.search(r'<span style="text-transform: uppercase;.*?">(.*?)</span>', content_html)
            if match:
                text_content = match.group(1).strip()
            conversation.append(f"Usuario: {text_content}")
        else:
            # Para el asistente, quitar el nombre de usuario que se añade al principio
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
        # Unir preguntas con símbolo de interrogación como separador visible
        questions_text = "?_".join(user_questions)

    # Sanitizar SOLO caracteres inválidos para nombres de archivo (NO truncar)
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
    # Formatear citas de fuente en negrita magenta
    fuente_pattern = r'\((Fuente:[^)]+)\)'
    s = re.sub(fuente_pattern, r'<b><font color="#FF00FF">(\1)</font></b>', s)
    # Reemplazar span color (hex o nombre)
    s = re.sub(r'<span\s+style="[^"]*color\s*:\s*([^;\"]+)[^\"]*">(.*?)</span>', lambda m: f"<font color=\"{m.group(1).strip()}\">{m.group(2)}</font>", s, flags=re.DOTALL)
    # Reemplazar any remaining <span> without color -> remove span
    s = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', s, flags=re.DOTALL)
    # Asegurar que los saltos de línea HTML sean <br/> para Paragraph
    s = s.replace('\n', '<br/>')
    s = s.replace('<br>', '<br/>')
    # Evitar caracteres & que rompan XML interno
    s = _escape_ampersand(s)
    return s


def _format_header(title_base: str, user_name: str | None, max_len: int = 220):
    """Construye un encabezado que contiene el título, el nombre en negrita y la fecha, limitado a max_len caracteres.

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
    """Genera un PDF en memoria a partir de HTML simple (etiquetas básicas) preservando colores de fuente.

    Usa reportlab Platypus Paragraph con tags <font color="...">.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("La librería 'reportlab' no está instalada. Instálala con: pip install reportlab")
    if not REPORTLAB_PLATYPUS:
        # Si platypus no está disponible, caer al generador de texto plano
        return generate_pdf_bytes_text(_strip_html_tags(html_content), title_base=title_base, user_name=user_name)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.fontName = 'Helvetica'
    normal.fontSize = 10
    normal.leading = 12

    story = []
    # Header (título + nombre en negrita + fecha) limitado a 220 chars
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
    """Fallback simple: genera PDF plano a partir de texto sin formato (mantener función previa)."""
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    left_margin = 40
    right_margin = 40
    top_margin = 40
    bottom_margin = 40
    # Header: título + nombre en negrita + fecha (limitado a 220 chars)
    header_html, header_plain = _format_header(title_base, user_name, max_len=220)
    # Dibujar parte inicial (título y nombre en negrita separado por un guion)
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
    /* NO ocultar nada del header para mantener el botón del sidebar visible */
    
    /* Ocultar solo el footer "Made with Streamlit" */
    footer {visibility: hidden !important;}
    .viewerBadge_container__1QSob {display: none !important;}
    .styles_viewerBadge__1yB5_ {display: none !important;}
    
    /* Ocultar botón de Deploy */
    .stDeployButton {display: none !important;}
    
    /* Ajustar padding superior para que no corte el título */
    .block-container {
        padding-top: 3rem;
    }
    </style>
    
    <script>
    // Función para ocultar iconos del footer inferior derecho
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
    
    // Ejecutar cuando la página cargue
    document.addEventListener('DOMContentLoaded', hideFooterIcons);
    
    // Ejecutar repetidamente para capturar elementos cargados dinámicamente
    setInterval(hideFooterIcons, 500);
    
    // Ejecutar inmediatamente
    hideFooterIcons();
    </script>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- Avatares personalizados ---
user_avatar = "https://api.iconify.design/line-md/question-circle.svg?color=%2358ACFA"
assistant_avatar = "https://api.iconify.design/mdi/ufo-outline.svg?color=%238A2BE2"


# --- CSS Simplificado y Título ---
st.markdown("""
<style>
/* TITULO PRINCIPAL */
.title-style {
    font-family: sans-serif;
    font-size: 6em;
    text-align: center;
    color: #8A2BE2;
    padding: 20px 0;
    margin-top: 10px;
}
/* ESTILOS BASICOS SOLAMENTE */
.intro-text {
    text-align: center;
    color: #58ACFA;
    font-size: 1.5em;
    padding: 10px;
}
.stChatInput textarea {
    background-color: white !important;
    color: black !important;
}
</style>
<div class="title-style">GERARD</div>
""", unsafe_allow_html=True)

# JavaScript específico para sidebar solamente
st.components.v1.html("""
<script>
function fixSidebarOnly() {
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    if (sidebar) {
        // Solo corregir texto específico del sidebar, no CSS
        const textElements = sidebar.querySelectorAll('h2, h3, div, p, span');
        textElements.forEach(element => {
            if (element.textContent && !element.innerHTML.includes('<style')) {
                let text = element.textContent;
                
                // Correcciones específicas solo para texto visible
                text = text.replace(/ðŸ/g, '');
                text = text.replace(/â/g, '');
                text = text.replace(/ConversaciÃ³n/g, 'CONVERSACION');
                text = text.replace(/ExportaciÃ³n/g, 'EXPORTACION');
                text = text.replace(/aquÃ­/g, 'AQUI');
                text = text.replace(/CÃ³mo/g, 'COMO');
                text = text.replace(/CATEGORÃAS/g, 'CATEGORIAS');
                text = text.replace(/BÃšSQUEDA/g, 'BUSQUEDA');
                
                if (text !== element.textContent) {
                    element.textContent = text;
                }
            }
        });
    }
}

// Ejecutar solo en el sidebar
setTimeout(fixSidebarOnly, 1000);
setInterval(fixSidebarOnly, 2000);

console.log('Sidebar-specific cleaner active');
</script>
""", height=0)

# Aplicar wrapper UTF-8 a todas las funciones de Streamlit
def create_utf8_wrapper():
    """Crea un wrapper para todas las funciones de Streamlit que muestran texto."""
    import streamlit as st
    
    # Solo aplicar si no se ha aplicado antes
    if hasattr(st, '_utf8_wrapped'):
        return
        
    # Guardar funciones originales
    original_write = st.write
    original_markdown = st.markdown
    original_text = st.text
    original_caption = st.caption
    original_info = st.info
    original_success = st.success
    original_warning = st.warning
    original_error = st.error
    
    def safe_write(*args, **kwargs):
        processed_args = []
        for arg in args:
            if isinstance(arg, str):
                processed_args.append(fix_utf8_encoding(arg))
            else:
                processed_args.append(arg)
        return original_write(*processed_args, **kwargs)
    
    def safe_markdown(text, **kwargs):
        if isinstance(text, str):
            text = fix_utf8_encoding(text)
        return original_markdown(text, **kwargs)
    
    def safe_text(text, **kwargs):
        if isinstance(text, str):
            text = fix_utf8_encoding(text)
        return original_text(text, **kwargs)
    
    def safe_caption(text, **kwargs):
        if isinstance(text, str):
            text = fix_utf8_encoding(text)
        return original_caption(text, **kwargs)
    
    def safe_info(text, **kwargs):
        if isinstance(text, str):
            text = fix_utf8_encoding(text)
        return original_info(text, **kwargs)
    
    def safe_success(text, **kwargs):
        if isinstance(text, str):
            text = fix_utf8_encoding(text)
        return original_success(text, **kwargs)
    
    def safe_warning(text, **kwargs):
        if isinstance(text, str):
            text = fix_utf8_encoding(text)
        return original_warning(text, **kwargs)
    
    def safe_error(text, **kwargs):
        if isinstance(text, str):
            text = fix_utf8_encoding(text)
        return original_error(text, **kwargs)
    
    # Reemplazar funciones
    st.write = safe_write
    st.markdown = safe_markdown
    st.text = safe_text
    st.caption = safe_caption
    st.info = safe_info
    st.success = safe_success
    st.warning = safe_warning
    st.error = safe_error
    
    # Marcar como aplicado
    st._utf8_wrapped = True

# Aplicar wrapper UTF-8
create_utf8_wrapper()

# (UI refinements removed; restored original behavior)

location = get_user_location()

if 'user_name' not in st.session_state:
    st.session_state.user_name = ''
if 'user_gender' not in st.session_state:
    st.session_state.user_gender = 'No especificar'
if 'messages' not in st.session_state:
    st.session_state.messages = []

# ==================== SIDEBAR CON BOTONES DE EXPORTACIÓN ====================
with st.sidebar:
    # Boton de salida a Radio Voz del Amor
    st.markdown("""
        <a href="https://radio3lavozdelamor.online/radio3lavozdelamor/" target="_blank" 
           style="display: block; text-align: center; background: linear-gradient(135deg, #DC143C 0%, #B22222 100%); 
                  color: white; padding: 12px 20px; border-radius: 25px; text-decoration: none; 
                  font-weight: bold; font-size: 1.1em; margin-bottom: 20px;
                  box-shadow: 0 4px 15px rgba(220, 20, 60, 0.4); transition: all 0.3s ease;">
            SALIR
        </a>
    """, unsafe_allow_html=True)
    
    # Logo/Titulo del sidebar  
    st.markdown("## GERARD")
    st.markdown("---")
    
    # SECCION 1: EXPORTAR CONVERSACION
    st.markdown("### EXPORTAR CONVERSACION")
    
    # Debug: verificar estado de los mensajes
    num_messages = len(st.session_state.get('messages', []))
    
    # Mostrar contador para debug
    if num_messages > 0:
        st.caption(f"🔍 Debug: {num_messages} mensajes detectados")
    
    if num_messages > 0:
        conversation_text = get_conversation_text()
        file_name = generate_download_filename()
        
        # Botón TXT
        st.download_button(
            label="📥 Descargar TXT",
            data=conversation_text,
            file_name=file_name,
            mime="text/plain",
            key="download_txt_sidebar",
            use_container_width=True,
            help="Descarga la conversación en formato texto"
        )
        
        # Botón PDF
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
                    label="📄 Exportar PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    key="download_pdf_sidebar",
                    help="Descarga la conversación en formato PDF",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generando PDF: {e}")
        else:
            st.info("⚠️ PDF no disponible")
        
        st.markdown("---")
        st.success(f"{num_messages} PREGUNTAS CONTESTADAS")
    else:
        st.info("INICIA UNA CONVERSACION PARA VER LOS BOTONES DE EXPORTACION AQUI")
        st.caption(f"LOS BOTONES APARECERAN AUTOMATICAMENTE DESPUES DE TU PRIMERA PREGUNTA (MENSAJES ACTUALES: {num_messages})")
    
    # SECCION 2: COMO HACER PREGUNTAS
    st.markdown("---")
    with st.expander("COMO HACER PREGUNTAS", expanded=True):
        help_text = """
        ### CATEGORIAS DE BUSQUEDA
        
        **POR TEMA ESPECIFICO**
        - EVACUACION, NAVES, SANACION, PROFECIAS
        - EJEMPLO: QUE ENSENANZAS HAY SOBRE LA EVACUACION?
        
        **POR MAESTRO**
        - ALANISO, AXEL, ADIEL, AZEN, AVIATAR, ETC.
        - EJEMPLO: QUE MENSAJES DIO EL MAESTRO ALANISO?
        
        **POR CONCEPTO**
        - GRAN MADRE, EJERCITO DE LUZ, TUNELES DIMENSIONALES
        - EJEMPLO: EXPLICAME EL CONCEPTO DE LA GRAN MADRE
        
        **POR NUMERO**
        - MEDITACIONES (36-1044), MENSAJES (606-1010)
        - EJEMPLO: DE QUE TRATA LA MEDITACION 107?
        
        ### TIPS RAPIDOS
        
        SE ESPECIFICO - MENCIONA MAESTRO O TEMA CONCRETO
        USA PALABRAS CLAVE - EVACUACION, SANACION, NAVES
        COMBINA ELEMENTOS - MAESTRO ALANISO + EVACUACION
        HAZ SEGUIMIENTO - GERARD RECUERDA LA CONVERSACION
        
        ### OBTENDRAS
        
        FUENTE EXACTA DEL ARCHIVO .SRT
        TIMESTAMP PRECISO (HH:MM:SS)
        CONTEXTO COMPLETO DE LA ENSENANZA
        
        ---
        """
        st.markdown(help_text)
        
        # Botón de descarga del PDF de la guía
        try:
            with open("assets/Guia_GERARD.pdf", "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                st.download_button(
                    label="DESCARGAR GUIA COMPLETA (PDF)",
                    data=pdf_bytes,
                    file_name="Guia_Completa_GERARD.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        except FileNotFoundError:
            st.markdown("[VER GUIA EN LINEA](https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2/blob/main/GUIA_MODELOS_PREGUNTA_GERARD.md)")

# ============================================================================

if not st.session_state.user_name:
    intro_html = """
    <p class="intro-text" style="font-size:1.8em; line-height:1.05;">
    ASISTENTE ESPECIALIZADO EN LOS MENSAJES Y MEDITACIONES DE LOS 9 MAESTROS: <strong>ALANISO, AXEL, ALAN, AZEN, AVIATAR, ALADIM, ADIEL, AZOES Y ALIESTRO</strong> JUNTO A
    <br>
    LAS TRES GRANDES ENERGIAS: <strong>EL PADRE AMOR, LA GRAN MADRE Y EL GRAN MAESTRO JESUS.</strong>
    </p>
    <p style="text-align:center; margin-top:12px; font-size:1.25em; text-transform:uppercase; font-weight:bold;">
    TE AYUDARE A ENCONTRAR CON PRECISION EL MINUTO Y SEGUNDO EXACTO EN CADA AUDIO O ENSENANZAS QUE YA HAYAS ESCUCHADO ANTERIORMENTE PERO QUE EN EL MOMENTO NO RECUERDAS EXACTAMENTE.
    </p>
    """
    st.markdown(intro_html, unsafe_allow_html=True)
    
    # Auto-scroll lento tipo teleprompter solo en la primera página
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
                
                // Duración total del scroll en milisegundos (60 segundos para lectura muy lenta tipo teleprompter)
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
                
                // Detener el scroll si el usuario interactúa con la página
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
        # Detección automática del género desde el nombre (sin confirmación)
        detected = detect_gender_from_name(user_name_input)
        # Asignar género automáticamente
        st.session_state.user_gender = detected
        # Siempre hacer rerun al ingresar el nombre para mostrar bienvenida
        st.rerun()
else:
    # Construir bienvenida según género detectado
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
# Centrar el GIF y dejarlo en tamaño natural para que se anime
col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    st.image("assets/pregunta.gif")  # SIN width para mantener animación

# Margen negativo MUY agresivo para pegarlo casi a la casilla
st.markdown('<div style="margin-top: -50px; margin-bottom: -20px;"></div>', unsafe_allow_html=True)

# Texto "PREGUNTA¡..." animado encima de la casilla (solo si el usuario ya ingresó su nombre)
if st.session_state.user_name:
    st.markdown("""
    <div id="pregunta-prompt" style="text-align: left; margin-left: 15px; margin-bottom: 5px;">
        <span style="color: #CC0000; font-weight: bold; font-size: 3.3em; animation: blink-slow 2s infinite;">PREGUNTA¡...</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Script para agregar el placeholder dinámicamente solo cuando PREGUNTA está visible
    components.html(
        """
        <script>
            setTimeout(function() {
                const chatInput = window.parent.document.querySelector('.stChatInput textarea');
                if (chatInput && !chatInput.hasAttribute('data-placeholder-set')) {
                    chatInput.setAttribute('placeholder', 'AQUI¡... ➪');
                    chatInput.setAttribute('data-placeholder-set', 'true');
                }
            }, 100);
        </script>
        """,
        height=0,
    )

# --- Input del usuario con avatares personalizados ---
if prompt_input := st.chat_input(""):
    pass  # Procesar después

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
        # --- ¡AQUÍ ESTÁ EL CAMBIO! ---
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
            
            # Auto-scroll hacia abajo usando components.html (más confiable que st.markdown)
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
                # GIF ovni centrado (SIN width para mantener animación)
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
                    // Ocultar el texto "PREGUNTA¡..." y el placeholder mientras se muestra "BUSCANDO..."
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
                # Obtener ubicación del usuario
                location = get_user_location()
                
                # Inicializar el logger
                logger = init_logger()
                
                # Inicializar Google Sheets Logger
                sheets_logger = init_sheets_logger()
                
                # Debug: imprimir estado en logs (no en UI para no molestar)
                print(f"[DEBUG UI] Google Sheets Logger enabled: {sheets_logger.enabled if sheets_logger else False}")
                
                # Obtener información del dispositivo y ubicación
                # Obtener user agent del navegador
                user_agent = st.context.headers.get("User-Agent", "Unknown") if hasattr(st, 'context') and hasattr(st.context, 'headers') else "Unknown"
                
                # Iniciar el registro de la interacción
                interaction_id = logger.start_interaction(
                    user=st.session_state.user_name,
                    question=prompt_input,
                    request_info={"user_agent": user_agent}
                )
                
                # Construir retrieval_chain a demanda si no existe
                if retrieval_chain is None:
                    # Intentar cargar recursos reales; esto validará la API key y el índice
                    # La descarga de FAISS ahora se hace dentro de load_resources()
                    try:
                        llm_loaded, vs = load_resources()
                        print(f"[DEBUG] load_resources completado - LLM: {type(llm_loaded)}, VS: {type(vs)}")
                    except Exception as e:
                        print(f"[ERROR] load_resources falló: {e}")
                        response_placeholder.error(f"No fue posible inicializar los recursos: {e}")
                        raise
                    
                    # BÚSQUEDA HÍBRIDA: vectorial + keyword fallback
                    # Usar lambda para pasar el vectorstore a hybrid_retrieval
                    def hybrid_retriever_func(query: str):
                        return hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)
                    
                    print(f"[DEBUG] Retriever híbrido creado (k_vector=100, k_keyword=30)")

                    # Si el LLM no se pudo inicializar, usamos un FakeChain que sólo regresa documentos
                    if llm_loaded is None:
                        class FakeChain:
                            def __init__(self, retriever_func):
                                self.retriever_func = retriever_func

                            def invoke(self, payload):
                                query = payload if isinstance(payload, str) else payload.get('input', '')
                                # obtener documentos relevantes usando búsqueda híbrida
                                docs = self.retriever_func(query)

                                items = []
                                for d in list(docs)[:3]:
                                    src = os.path.basename(d.metadata.get('source', 'desconocido'))
                                    snippet = re.sub(r'\s+', ' ', d.page_content)[:300]
                                    items.append({"type": "normal", "content": f"Fuente: {src} - {snippet}"})
                                if not items:
                                    items = [{"type": "normal", "content": "No se encontraron documentos relevantes en el índice."}]
                                return json.dumps(items, ensure_ascii=False)

                        retrieval_chain = FakeChain(hybrid_retriever_func)
                    else:
                        # Reconstruir retrieval_chain con búsqueda híbrida
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
                print(f"[DEBUG] Después de invoke - answer_raw type: {type(answer_raw)}, valor: {str(answer_raw)[:200]}")
                
                # Asegurar que answer_json sea siempre un string JSON
                if isinstance(answer_raw, dict):
                    print(f"[DEBUG] answer_raw es dict, convirtiendo a JSON string")
                    answer_json = json.dumps(answer_raw, ensure_ascii=False)
                else:
                    answer_json = answer_raw if isinstance(answer_raw, str) else str(answer_raw)
                
                print(f"[DEBUG] answer_json type final: {type(answer_json)}")
                
                # Debug: verificar tipo antes de save_to_log
                if not isinstance(answer_json, str):
                    st.error(f"❌ DEBUG: answer_json es tipo {type(answer_json)}, convirtiendo a string...")
                    answer_json = json.dumps(answer_json, ensure_ascii=False) if isinstance(answer_json, (dict, list)) else str(answer_json)
                
                # Registro antiguo (mantener por compatibilidad)
                save_to_log(st.session_state.user_name, prompt_input, answer_json, location)
                
                # Finalizar el registro de la interacción con el logger completo
                logger.end_interaction(
                    session_id=interaction_id,
                    status="success"
                )
                
                # Registrar en Google Sheets si está disponible
                if sheets_logger:
                    try:
                        # Usar información del dispositivo y ubicación ya obtenidos
                        device_detector = DeviceDetector()
                        device_raw = device_detector.detect_from_web(user_agent)
                        
                        # Mapear las claves correctamente
                        device_info = {
                            "device_type": device_raw.get("tipo", "Desconocido"),
                            "browser": device_raw.get("navegador", "Desconocido"),
                            "os": device_raw.get("os", "Desconocido")
                        }
                        print(f"[DEBUG] Device Info: {device_info}")
                        
                        # Usar la ubicación ya obtenida al inicio
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
                    print(f"[INFO] Google Sheets Logger no está disponible o no está habilitado")
                
                # Asegurar que answer_json esté en UTF-8 correcto
                import unicodedata
                if isinstance(answer_json, str):
                    answer_json = unicodedata.normalize('NFC', answer_json)
                    # Corregir caracteres comunes mal codificados
                    answer_json = answer_json.replace('â€™', "'")
                    answer_json = answer_json.replace('â€œ', '"')
                    answer_json = answer_json.replace('â€', '"')
                    answer_json = answer_json.replace('â€"', '–')
                    answer_json = answer_json.replace('â€"', '—')
                    answer_json = answer_json.replace('Ã¡', 'á')
                    answer_json = answer_json.replace('Ã©', 'é')
                    answer_json = answer_json.replace('Ã­', 'í')
                    answer_json = answer_json.replace('Ã³', 'ó')
                    answer_json = answer_json.replace('Ãº', 'ú')
                    answer_json = answer_json.replace('Ã±', 'ñ')
                    answer_json = answer_json.replace('Ã¼', 'ü')
                
                match = re.search(r'\[.*\]', answer_json, re.DOTALL)
                if not match:
                    st.error("La respuesta del modelo no fue un JSON válido.")
                    response_html = f'<p style="color:red;">{answer_json}</p>'
                else:
                    data = json.loads(match.group(0))
                    response_html = f'<strong style="color:#28a745;">{st.session_state.user_name}:</strong> '
                    for item in data:
                        content_type = item.get("type", "normal")
                        content = item.get("content", "")
                        
                        # Normalizar el contenido UTF-8
                        if content:
                            content = unicodedata.normalize('NFC', content)
                            # Corregir caracteres mal codificados
                            content = content.replace('â€™', "'")
                            content = content.replace('â€œ', '"')
                            content = content.replace('â€', '"')
                            content = content.replace('Ã¡', 'á')
                            content = content.replace('Ã©', 'é')
                            content = content.replace('Ã­', 'í')
                            content = content.replace('Ã³', 'ó')
                            content = content.replace('Ãº', 'ú')
                            content = content.replace('Ã±', 'ñ')
                        
                        if content_type == "emphasis":
                            # Resalta en magenta el texto entre paréntesis, el resto amarillo
                            def magenta_parentheses(text):
                                return re.sub(r'(\(.*?\))', r'<span style="color:#FF00FF; font-weight: bold;">\1</span>', text)
                            content_colored = magenta_parentheses(content)
                            response_html += f'<span style="color:yellow; background-color: #333; border-radius: 4px; padding: 2px 4px;">{content_colored}</span>'
                        else:
                            # Cambiar color de fuentes (texto entre paréntesis) a MAGENTA
                            content_html = re.sub(r'(\(.*?\))', r'<span style="color:#FF00FF; font-weight: bold;">\1</span>', content)
                            response_html += content_html
                
                # Asegurar que el HTML final esté correctamente codificado
                import html
                response_html_safe = html.unescape(response_html)
                response_html_safe = unicodedata.normalize('NFC', response_html_safe)
                
                response_placeholder.markdown(response_html_safe, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response_html_safe})
                
                # Marcar que se agregó un mensaje nuevo para actualizar el sidebar
                st.session_state['_new_message_added'] = True
                
                # Auto-scroll después de mostrar la respuesta completa (más confiable con components.html)
                components.html(
                    """
                    <script>
                        setTimeout(function() {
                            // Auto-scroll
                            window.parent.document.querySelector('section.main').scrollTo({
                                top: window.parent.document.querySelector('section.main').scrollHeight,
                                behavior: 'smooth'
                            });
                            
                            // Restaurar el texto "PREGUNTA¡..." y el placeholder después de mostrar la respuesta
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
                                chatTextarea.setAttribute('placeholder', 'AQUI¡... ➪');
                                chatTextarea.setAttribute('data-placeholder-set', 'true');
                            }
                        }, 300);
                    </script>
                    """,
                    height=0,
                )
                
                # NOTA: st.rerun() aquí causaba que los botones de descarga no aparecieran
                # porque recargaba la página antes de llegar a renderizar los botones
                # st.rerun()

                # --- Ofrecer descarga del último intercambio (pregunta + respuesta) ---
                try:
                    # Texto plano para el archivo
                    def html_to_text(html: str) -> str:
                        return re.sub(r'<[^>]+>', '', html).strip()

                    user_text = prompt_input.strip()
                    assistant_text = html_to_text(response_html)
                    single_qa_text = f"Pregunta: {user_text}\n\nRespuesta:\n{assistant_text}\n"
                except Exception:
                    # No queremos que una falla aquí rompa la experiencia principal
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
                
                response_placeholder.error(f"Ocurrió un error al procesar tu pregunta: {e}")

# Actualizar sidebar si se agregó un mensaje nuevo
if st.session_state.get('_new_message_added', False):
    st.session_state['_new_message_added'] = False
    st.rerun()

# EJECUTAR LIMPIADOR DE CARACTERES AL FINAL (DESACTIVADO TEMPORALMENTE)
# force_streamlit_utf8()
