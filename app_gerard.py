"""
GERARD v3.69 - Interfaz Web Streamlit
Sistema de Análisis Investigativo Avanzado
Usa Vertex AI con credenciales JSON
"""

import os
import streamlit as st
from datetime import datetime
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import time
import re
import io
import base64
import uuid
import streamlit.components.v1 as components

# Verificar disponibilidad de reportlab para PDF
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase.pdfmetrics import stringWidth
    REPORTLAB_AVAILABLE = True
    REPORTLAB_PLATYPUS = True
except Exception:
    REPORTLAB_AVAILABLE = False
    REPORTLAB_PLATYPUS = False

# Verificar disponibilidad de Google Sheets logging
try:
    from google_sheets_logger import create_sheets_logger
    from device_detector import DeviceDetector
    from geo_utils import GeoLocator
    GOOGLE_SHEETS_AVAILABLE = True
except Exception:
    GOOGLE_SHEETS_AVAILABLE = False
    print("[INFO] Google Sheets logging no disponible")

# Auto-generar índice BM25 si no existe (para Streamlit Cloud)
if not os.path.exists("bm25_index.pkl"):
    print("[INFO] Detectado entorno cloud sin bm25_index.pkl, generando...")
    try:
        from init_bm25 import init_bm25_index
        init_bm25_index()
    except Exception as e:
        print(f"[WARNING] No se pudo auto-generar BM25: {e}")

# Importar retrievers para búsqueda
try:
    from hybrid_retriever import HybridRetriever
    from bm25_retriever import BM25Retriever
    RETRIEVERS_AVAILABLE = True
except Exception as e:
    RETRIEVERS_AVAILABLE = False
    print(f"[WARNING] Retrievers no disponibles: {e}")

# Configuración de página
st.set_page_config(
    page_title="GERARD - Agente Analítico",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado - Tema oscuro y responsive
st.markdown("""
<style>
    /* Tema oscuro global */
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    
    /* Título principal - Responsive */
    .main-title {
        font-size: clamp(2em, 8vw, 4em);
        font-weight: 900;
        text-align: center;
        background: linear-gradient(45deg, #00d4ff, #7b2ff7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
        text-shadow: 0 0 30px rgba(0, 212, 255, 0.5);
        font-family: 'Courier New', monospace;
        letter-spacing: clamp(2px, 1vw, 8px);
        padding: 0 10px;
    }
    
    /* Subtítulo - Responsive */
    .subtitle {
        text-align: center;
        color: #00d4ff;
        font-size: clamp(0.9em, 3vw, 1.2em);
        margin-bottom: 20px;
        font-family: 'Courier New', monospace;
        letter-spacing: clamp(1px, 0.5vw, 2px);
        padding: 0 10px;
    }
    
    /* Descripción - Responsive */
    .description {
        text-align: center;
        color: #b0b0b0;
        font-size: clamp(0.75em, 2.5vw, 0.95em);
        margin-bottom: 30px;
        padding: 0 15px;
        line-height: 1.6;
        max-width: 100%;
    }
    
    /* Campos de entrada - Responsive */
    .stTextInput > div > div > input {
        background-color: #1a1a2e !important;
        color: #00d4ff !important;
        border: 2px solid #00d4ff !important;
        border-radius: 10px !important;
        font-size: clamp(0.9em, 3vw, 1.1em) !important;
        padding: 12px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    .stTextArea > div > div > textarea {
        background-color: #1a1a2e !important;
        color: #00d4ff !important;
        border: 2px solid #00d4ff !important;
        border-radius: 10px !important;
        font-size: clamp(0.85em, 2.5vw, 1em) !important;
        min-height: 100px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    /* Botones - Responsive */
    .stButton > button {
        background: linear-gradient(45deg, #00d4ff, #7b2ff7) !important;
        color: white !important;
        font-size: clamp(0.9em, 3vw, 1.2em) !important;
        font-weight: bold !important;
        padding: clamp(10px, 3vw, 15px) clamp(20px, 5vw, 40px) !important;
        border-radius: 25px !important;
        border: none !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.5) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        max-width: 400px !important;
        margin: 0 auto !important;
    }
    
    .stButton > button:hover {
        box-shadow: 0 0 40px rgba(0, 212, 255, 0.8) !important;
        transform: scale(1.02) !important;
    }
    
    /* Respuestas - Responsive */
    .response-container {
        background-color: #0f0f1e;
        border-left: 4px solid #00d4ff;
        padding: clamp(15px, 4vw, 20px);
        border-radius: 10px;
        margin: 20px 0;
        color: #e0e0e0;
        font-family: 'Courier New', monospace;
        line-height: 1.8;
        font-size: clamp(0.8em, 2.5vw, 1em);
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    
    /* GIF container - Responsive */
    .gif-container {
        text-align: center;
        margin: 20px 0;
        padding: 0 10px;
    }
    
    .gif-container img {
        max-width: 100%;
        height: auto;
        max-height: 300px;
    }
    
    /* Stats - Responsive */
    .stats {
        background-color: #1a1a2e;
        padding: clamp(10px, 3vw, 15px);
        border-radius: 10px;
        border: 1px solid #00d4ff;
        margin: 10px 0;
        color: #b0b0b0;
        font-size: clamp(0.7em, 2vw, 0.9em);
        word-wrap: break-word;
    }
    
    /* Layout columns - Stack en móvil */
    @media (max-width: 768px) {
        .row-widget.stHorizontal {
            flex-direction: column;
        }
        
        .stButton > button {
            margin: 10px auto !important;
        }
    }
    
    /* Ajustes para pantallas muy pequeñas */
    @media (max-width: 480px) {
        .main-title {
            margin-top: 20px;
        }
        
        .description br {
            display: block;
            content: "";
            margin-top: 5px;
        }
    }
    
    /* Asegurar que todo el contenido sea responsive */
    .element-container {
        max-width: 100%;
        overflow-x: hidden;
    }
    
    /* Viewport meta tag para móviles */
    @viewport {
        width: device-width;
        zoom: 1.0;
    }
</style>
""", unsafe_allow_html=True)

# Configurar credenciales de Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credencial json/midyear-node-436821-t3-525a146e96a0.json"

# --- Funciones Helper para PDF ---
def _escape_ampersand(text: str) -> str:
    """Escapa el símbolo & para XML"""
    return text.replace('&', '&amp;')

def _strip_html_tags(html: str) -> str:
    """Elimina todas las etiquetas HTML"""
    return re.sub(r'<[^>]+>', '', html)

def _convert_spans_to_font_tags(html: str) -> str:
    """
    Reemplaza <span style="color:...">texto</span> por <font color="...">texto</font> 
    para que reportlab Paragraph lo soporte.
    """
    s = html
    # Formatear citas de fuente en negrita magenta
    fuente_pattern = r'\((Fuente:[^)]+)\)'
    s = re.sub(fuente_pattern, r'<b><font color="#FF00FF">(\1)</font></b>', s)
    # Reemplazar span color (hex o nombre)
    s = re.sub(
        r'<span\s+style="[^"]*color\s*:\s*([^;\"]+)[^\"]*">(.*?)</span>', 
        lambda m: f"<font color=\"{m.group(1).strip()}\">{m.group(2)}</font>", 
        s, 
        flags=re.DOTALL
    )
    # Reemplazar any remaining <span> without color -> remove span
    s = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', s, flags=re.DOTALL)
    # Asegurar que los saltos de línea HTML sean <br/> para Paragraph
    s = s.replace('\n', '<br/>')
    s = s.replace('<br>', '<br/>')
    # Evitar caracteres & que rompan XML interno
    s = _escape_ampersand(s)
    return s

def _format_header(title_base: str, user_name: str | None, max_len: int = 220):
    """
    Construye un encabezado que contiene el título, el nombre en negrita y la fecha.
    Returns: tuple (header_html, header_plain)
    """
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_name = (user_name or 'usuario').strip()
    plain = f"{title_base} - {user_name} {date_str}"
    if len(plain) > max_len:
        plain = plain[: max_len - 3].rstrip() + '...'
    # Para HTML, ponemos el nombre en negrita
    if user_name and user_name in plain:
        html = plain.replace(user_name, f"<b>{user_name}</b>", 1)
    else:
        html = plain
    return html, plain

def generate_pdf_from_html(
    html_content: str, 
    title_base: str = "Consulta GERARD", 
    user_name: str | None = None
) -> bytes:
    """
    Genera un PDF en memoria a partir de HTML simple preservando colores.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab no instalado")
    if not REPORTLAB_PLATYPUS:
        return generate_pdf_bytes_text(
            _strip_html_tags(html_content), 
            title_base=title_base, 
            user_name=user_name
        )
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, 
        rightMargin=20, leftMargin=20, 
        topMargin=30, bottomMargin=20
    )
    
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    normal.fontName = 'Helvetica'
    normal.fontSize = 10
    normal.leading = 12
    
    story = []
    header_html, header_plain = _format_header(title_base, user_name, max_len=220)
    title_style = styles.get('Heading2', normal)
    story.append(Paragraph(header_html, title_style))
    story.append(Spacer(1, 6))
    
    body = _convert_spans_to_font_tags(html_content)
    
    try:
        story.append(Paragraph(body, normal))
    except Exception:
        plain = re.sub(r'<[^>]+>', '', html_content)
        story.append(Paragraph(plain.replace('&', '&amp;'), normal))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

def generate_pdf_bytes_text(
    text: str, 
    title_base: str = "Consulta GERARD", 
    user_name: str | None = None
) -> bytes:
    """Fallback: genera PDF plano desde texto sin formato"""
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    
    left_margin = 40
    right_margin = 40
    top_margin = 40
    bottom_margin = 40
    
    header_html, header_plain = _format_header(title_base, user_name, max_len=220)
    
    if user_name and user_name in header_plain:
        prefix, _, suffix = header_plain.partition(user_name)
        c.setFont("Helvetica", 12)
        c.drawString(left_margin, page_height - top_margin, prefix.strip())
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

def generate_download_filename(conversation_history: list, user_name: str) -> str:
    """
    Genera nombre de archivo en formato:
    CONSULTA_DE_NOMBREUSUARIO_pregunta1?_pregunta2?_pregunta3_YYYYMMDD_HHMM.pdf
    """
    user_questions = []
    for entry in conversation_history:
        query = entry.get('query', '').strip()
        if query:
            user_questions.append(query)
    
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
    
    user_name_upper = user_name.upper()
    
    # Obtener fecha y hora actual
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    time_str = now.strftime('%H%M')  # Solo hora y minuto
    
    # Formato final: CONSULTA_DE_NOMBREUSUARIO_pregunta1?_pregunta2?_pregunta3_20251117_1530.pdf
    return f"CONSULTA_DE_{user_name_upper}_{full_questions}_{date_str}_{time_str}.pdf"

# Inicialización de Google Sheets Logger
def init_sheets_logger():
    """
    Inicializa el logger de Google Sheets si está disponible.
    
    Returns:
        GoogleSheetsLogger o None si no está configurado
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        return None
    
    try:
        logger = create_sheets_logger()
        if logger and logger.enabled:
            print("[OK] Google Sheets Logger inicializado correctamente")
            return logger
        else:
            print("[INFO] Google Sheets Logger no está habilitado")
            return None
    except Exception as e:
        print(f"[ERROR] Error inicializando Google Sheets Logger: {e}")
        return None

# Caché de recursos
@st.cache_resource
def load_resources():
    """Carga LLM, embeddings y FAISS index"""
    with st.spinner("🔄 Inicializando GERARD..."):
        # Verificar si existe el índice FAISS
        import os
        from pathlib import Path
        
        faiss_path = Path("faiss_index/index.faiss")
        if not faiss_path.exists():
            st.warning("⚙️ Primera ejecución: Configurando índice FAISS...")
            try:
                from setup_faiss_cloud import setup_faiss
                if not setup_faiss():
                    raise RuntimeError("No se pudo configurar el índice FAISS")
                st.success("✅ Índice FAISS configurado correctamente")
            except Exception as e:
                raise RuntimeError(f"Error configurando FAISS: {e}")
        
        # LLM
        llm = ChatVertexAI(
            model="gemini-2.5-pro",
            project="midyear-node-436821-t3",
            temperature=0.3
        )
        
        # Embeddings
        embeddings = VertexAIEmbeddings(
            model_name="text-multilingual-embedding-002",
            project="midyear-node-436821-t3"
        )
        
        # FAISS Vector Store
        faiss_vs = FAISS.load_local(
            folder_path="faiss_index",  # Volver al índice viejo que SÍ funciona para consultas
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
        
        return llm, faiss_vs

# Prompt de GERARD - Agente Analítico Forense
GERARD_PROMPT = ChatPromptTemplate.from_template(r"""
# IDENTIDAD Y PROPÓSITO DEL SISTEMA

Eres un Agente Analítico Forense especializado en la extracción de información de una base de datos vectorial compuesta por 3.442 archivos de subtítulos (.srt). Tu función es actuar como un motor de búsqueda semántica de precisión quirúrgica.

## ARQUITECTURA EPISTEMOLÓGICA

**ÚNICO UNIVERSO DE CONOCIMIENTO:**
- Tu conocimiento TOTAL está limitado EXCLUSIVAMENTE a los 3.442 archivos .srt indexados
- NO posees conocimiento previo, entrenamiento general, ni información externa
- Cada afirmación debe ser RASTREABLE a un fragmento específico de la base de datos
- Si algo NO existe en la base de datos, NO EXISTE para ti

---

## 🚨 PROTOCOLOS DE SEGURIDAD ANALÍTICA

### 🔴 PROHIBICIONES ABSOLUTAS (Nivel de Cumplimiento: 100%)

#### PROHIBICIÓN NIVEL 1: FABRICACIÓN DE DATOS
❌ NO inventar información bajo ninguna circunstancia
❌ NO usar conocimiento del modelo base (entrenamiento general)
❌ NO suponer o inferir más allá de lo textualmente disponible
❌ NO completar información faltante con lógica externa
❌ NO responder "probablemente" o "es posible que"
❌ NO hacer generalizaciones sin evidencia textual directa

#### PROHIBICIÓN NIVEL 2: CONTAMINACIÓN ANALÍTICA
❌ NO mezclar análisis con citas textuales
❌ NO parafrasear cuando se requiere texto literal
❌ NO interpretar sin declarar explícitamente que es interpretación
❌ NO omitir información contradictoria si existe
❌ NO presentar sinónimos como si fueran el texto original

---

### 🟢 MANDATOS OBLIGATORIOS

Cada afirmación DEBE seguir este formato:

**[Documento: nombre_archivo.srt | Timestamp: HH:MM:SS,mmm --> HH:MM:SS,mmm]**
"TEXTO LITERAL EXACTO DEL SUBTÍTULO"

---

## CONTEXTO DISPONIBLE (Fragmentos de la base de datos):
{context}

## CONSULTA DEL USUARIO:
{input}

---

## INSTRUCCIONES FINALES:

1. **PROCESA TODOS LOS FRAGMENTOS**: El contexto contiene MÚLTIPLES documentos separados por "---". Debes analizarlos TODOS, no solo los primeros.
2. **LISTA EXHAUSTIVA**: Si un término aparece en 10, 20 o 50 fragmentos, debes listarlos TODOS.
3. Para cada mención encontrada, cita: [Documento: archivo.srt | Timestamp: HH:MM:SS,mmm --> HH:MM:SS,mmm] seguido del texto literal.
4. Agrupa la información por temas, pero INCLUYE TODAS las menciones de cada tema.
5. Extrae ÚNICAMENTE información que esté presente textualmente.
6. Separa claramente EVIDENCIAS de ANÁLISIS.
5. Declara explícitamente si algo NO se encuentra en el contexto
6. Mantén tono profesional y preciso

**Base de datos cargada. Listo para consultas forenses. Protocolo de evidencia estricta activado.**
""")

def format_docs(docs):
    """Formatea documentos para el contexto con timestamp si está disponible"""
    formatted_docs = []
    for doc in docs:
        source = os.path.basename(doc.metadata.get('source', 'unknown'))
        timestamp = doc.metadata.get('timestamp', doc.metadata.get('start_time', None))
        
        if timestamp:
            # Formatear timestamp si existe
            formatted_docs.append(f"Fuente: {source} | Timestamp: {timestamp}\n{doc.page_content}")
        else:
            # Indicar que el timestamp está en el contenido del fragmento (archivos SRT)
            formatted_docs.append(f"Fuente: {source} | Timestamp: Ver inicio del fragmento\n{doc.page_content}")
    
    return "\n\n---\n\n".join(formatted_docs)

# --- INTERFAZ PRINCIPAL ---

# Header con logo
st.markdown('<div class="main-title">GERARD</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">v3.69 | ASISTENTE</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="description">'
    '<strong>ESPECIALIZADO EN LOS MENSAJES Y MEDITACIONES DE LOS 9 MAESTROS:</strong><br>'
    'ALANISO, AXEL, ALAN, AZEN, AVIATAR, ALADIM, ADIEL, AZOES Y ALIESTRO<br>'
    '<strong>JUNTO A LAS TRES GRANDES ENERGÍAS:</strong><br>'
    'EL PADRE AMOR, LA GRAN MADRE Y EL GRAN MAESTRO JESÚS<br><br>'
    '🎯 <strong>TE AYUDARÉ A ENCONTRAR EL MINUTO Y SEGUNDO EXACTO</strong><br>'
    'en cada audio o video de las enseñanzas que ya hayas escuchado anteriormente<br>'
    'pero que en el momento actual no recuerdes exactamente.<br><br>'
    '📊 Base de conocimiento: 3,442 archivos | 82,575 fragmentos indexados'
    '</div>',
    unsafe_allow_html=True
)

# Cargar recursos
try:
    llm, faiss_vs = load_resources()
    doc_count = faiss_vs.index.ntotal if hasattr(faiss_vs, 'index') else 'unknown'
    st.markdown(
        f'<div class="stats">✅ SISTEMA OPERATIVO</div>',
        unsafe_allow_html=True
    )
except Exception as e:
    st.error(f"❌ Error inicializando sistema: {e}")
    st.stop()

# Separador
st.markdown("---")

# Campo de nombre de usuario (solo si no se ha ingresado)
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

if not st.session_state.user_name:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        temp_name = st.text_input(
            "👤 Nombre de usuario:",
            placeholder="Introduce tu nombre...",
            key="temp_user_name"
        )
        if temp_name and temp_name.strip():
            st.session_state.user_name = temp_name.strip()
            st.rerun()

user_name = st.session_state.user_name

# Inicializar historial de conversación en session_state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Inicializar Google Sheets Logger (una sola vez por sesión)
if 'sheets_logger' not in st.session_state:
    st.session_state.sheets_logger = init_sheets_logger()

# Inicializar flag para limpiar campo de pregunta
if 'clear_query' not in st.session_state:
    st.session_state.clear_query = False

# Solo mostrar el resto SI hay nombre de usuario
if user_name:
    # Mensaje de bienvenida personalizado
    st.markdown(
        f'<div style="text-align: center; font-size: 1.3em; color: #00d4ff; font-weight: bold; margin: 20px 0;">'
        f'👋 HOLA {user_name.upper()}, YA PUEDES PREGUNTAR'
        f'</div>',
        unsafe_allow_html=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Mostrar contador de consultas si hay historial
    if len(st.session_state.conversation_history) > 0:
        col_stats, col_clear = st.columns([4, 1])
        with col_stats:
            st.markdown(
                f'<div class="stats">'
                f'📊 Consultas en esta sesión: {len(st.session_state.conversation_history)} | '
                f'👤 Usuario: {user_name.upper()}'
                f'</div>',
                unsafe_allow_html=True
            )
        with col_clear:
            if st.button("🗑️ Limpiar", key="clear_history_btn", help="Limpiar historial de consultas"):
                st.session_state.conversation_history = []
                st.session_state.clear_query = True
                st.session_state.last_query = ""
                st.rerun()
    
    # Campo de pregunta con auto-limpieza
    query_value = "" if st.session_state.clear_query else st.session_state.get('last_query', '')
    query = st.text_area(
        "🔍 Consulta de investigación:",
        value=query_value,
        placeholder="FAVOR DIGITA TU NUEVA CONSULTA" if st.session_state.clear_query or len(st.session_state.conversation_history) > 0 else "¿Qué información necesitas?",
        height=120,
        key="query_input"
    )
    
    # Resetear flag de limpieza
    if st.session_state.clear_query:
        st.session_state.clear_query = False
    
    # Botón de consulta
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        search_button = st.button("🚀 EJECUTAR PREGUNTA", use_container_width=True)
    
    # Procesar consulta
    if search_button and query:
        # Mostrar GIF de búsqueda
        st.markdown('<div class="gif-container">', unsafe_allow_html=True)
        if os.path.exists("assets/ovni.gif"):
            st.image("assets/ovni.gif", width=300)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.info(f"🔄 Procesando consulta de **{user_name.upper()}**...")
        
        # PRIMER SCROLL: Hacia el spinner (30% de la página)
        components.html(
            """
            <script>
            (function() {
                const main = window.parent.document.querySelector('.main');
                if (main) {
                    setTimeout(function() {
                        main.scrollTo({
                            top: main.scrollHeight * 0.3,
                            behavior: 'smooth'
                        });
                    }, 100);
                }
            })();
            </script>
            """,
            height=0
        )
        
        try:
            # Recuperar documentos usando búsqueda híbrida (BM25 + FAISS)
            # K=50 para búsquedas exhaustivas cuando el usuario pida "TODA LA INFORMACIÓN"
            k_docs = 50
            
            with st.spinner("🔍 Buscando con algoritmo híbrido (semántica + léxica)..."):
                search_method = "unknown"
                
                # ESTRATEGIA 1: Intentar búsqueda híbrida (BM25 + FAISS)
                if RETRIEVERS_AVAILABLE:
                    try:
                        faiss_retriever = faiss_vs.as_retriever(search_kwargs={"k": k_docs})
                        hybrid_retriever = HybridRetriever(
                            faiss_retriever=faiss_retriever,
                            bm25_path="bm25_index.pkl",
                            k=k_docs,
                            alpha=0.7  # 70% semántica, 30% léxica
                        )
                        docs = hybrid_retriever.invoke(query)
                        search_method = "hybrid"
                        
                        # Verificar si usó BM25 puro (por nombres propios o palabras clave)
                        query_words = query.split()
                        has_proper_nouns = any(word[0].isupper() for word in query_words if len(word) > 2)
                        proper_noun_keywords = ['maria', 'magdalena', 'jesus', 'cristo', 'jose', 'juan', 'pedro', 'pablo']
                        has_name_keywords = any(word.lower() in proper_noun_keywords for word in query_words)
                        
                        if has_proper_nouns or has_name_keywords:
                            st.success("✅ Nombres detectados → BM25 puro (coincidencias exactas de texto)")
                        else:
                            st.success("✅ Búsqueda híbrida activada (BM25 + Embeddings)")
                    
                    # ESTRATEGIA 2: Si falla híbrida, usar BM25 puro (mejor para nombres propios)
                    except Exception as e:
                        st.warning(f"⚠️ Híbrida no disponible, usando BM25 puro (óptimo para nombres exactos)...")
                        try:
                            bm25_retriever = BM25Retriever(
                                bm25_path="bm25_index.pkl",
                                k=k_docs
                            )
                            docs = bm25_retriever.invoke(query)
                            search_method = "bm25"
                            st.info("✅ Búsqueda léxica BM25 (mejor para nombres propios y coincidencias exactas)")
                        
                        # ESTRATEGIA 3: Último recurso - FAISS solo
                        except Exception as e2:
                            st.error(f"⚠️ BM25 falló, usando FAISS básico...")
                            faiss_retriever = faiss_vs.as_retriever(search_kwargs={"k": k_docs})
                            docs = faiss_retriever.invoke(query)
                            search_method = "faiss"
                else:
                    # Si no hay retrievers, usar FAISS directamente
                    st.info("ℹ️ Usando búsqueda FAISS (semántica)...")
                    faiss_retriever = faiss_vs.as_retriever(search_kwargs={"k": k_docs})
                    docs = faiss_retriever.invoke(query)
                    search_method = "faiss"
            
            # Mostrar estadísticas de recuperación
            query_lower = query.lower()
            relevant_docs = [d for d in docs if any(term in d.page_content.lower() for term in query_lower.split())]
            st.info(f"📊 Recuperados: {len(docs)} docs | Relevantes: {len(relevant_docs)} docs con términos de búsqueda")
            
            # Mostrar GIF de procesamiento
            st.markdown('<div class="gif-container">', unsafe_allow_html=True)
            if os.path.exists("assets/pregunta.gif"):
                st.image("assets/pregunta.gif", width=300)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Construir cadena RAG
            query_start_time = datetime.now()
            with st.spinner("🧠 GERARD V3.69 está buscando la Respuesta..."):
                chain = (
                    {
                        "context": lambda x: format_docs(docs),
                        "input": lambda x: x["input"]
                    }
                    | GERARD_PROMPT
                    | llm
                    | StrOutputParser()
                )
                
                # Ejecutar
                response = chain.invoke({"input": query})
            
            # Calcular tiempo total de respuesta
            query_end_time = datetime.now()
            total_time = (query_end_time - query_start_time).total_seconds()
            
            # Guardar en historial
            st.session_state.conversation_history.append({
                'timestamp': query_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                'user': user_name.upper(),
                'query': query,
                'response': response
            })
            
            # Marcar para limpiar campo en siguiente render
            st.session_state.clear_query = True
            st.session_state.last_query = ""
            
            # Logging a Google Sheets
            if st.session_state.sheets_logger:
                try:
                    # Generar ID único para esta interacción
                    interaction_id = str(uuid.uuid4())
                    
                    # Detectar dispositivo y ubicación
                    device_info = {"device_type": "Desconocido", "browser": "Desconocido", "os": "Desconocido"}
                    location_info = {"city": "Desconocida", "country": "Desconocido", "ip": "No disponible"}
                    
                    if GOOGLE_SHEETS_AVAILABLE:
                        try:
                            # Obtener User-Agent
                            user_agent = st.context.headers.get("User-Agent", "Unknown")
                            
                            # Detectar dispositivo
                            device_detector = DeviceDetector()
                            device_info_full = device_detector.detect_from_web(user_agent)
                            device_info = {
                                "device_type": device_info_full.get("tipo", "Desconocido"),
                                "browser": device_info_full.get("navegador", "Desconocido"),
                                "os": device_info_full.get("os", "Desconocido")
                            }
                            
                            # Detectar ubicación
                            geo_locator = GeoLocator()
                            location_data = geo_locator.get_location()
                            if location_data:
                                location_info = {
                                    "city": location_data.get("ciudad", "Desconocida"),
                                    "country": location_data.get("pais", "Desconocido"),
                                    "ip": location_data.get("ip", "No disponible")
                                }
                        except Exception as e:
                            print(f"[WARNING] Error detectando dispositivo/ubicación: {e}")
                    
                    # Limpiar respuesta (quitar HTML)
                    answer_clean = _strip_html_tags(response)
                    
                    # Registrar en Google Sheets
                    st.session_state.sheets_logger.log_interaction(
                        interaction_id=interaction_id,
                        user=user_name.upper(),
                        question=query,
                        answer=answer_clean,
                        device_info=device_info,
                        location_info=location_info,
                        timing={"total_time": total_time},
                        success=True
                    )
                except Exception as e:
                    print(f"[ERROR] Error logging a Google Sheets: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Mostrar respuesta
            st.success("✅ Análisis completado")
            
            st.markdown("### 🔬 Resultado del Análisis:")
            st.markdown(f'<div class="response-container" id="respuesta-gerard">{response}</div>', unsafe_allow_html=True)
            
            # Estadísticas
            st.markdown(
                f'<div class="stats">'
                f'📊 Documentos analizados: {len(docs)} | '
                f'👤 Usuario: {user_name.upper()} | '
                f'🕐 Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # SEGUNDO SCROLL: Automático hacia la respuesta y luego teleprompter
            response_length = len(response)
            # Calcular duración del scroll basado en longitud del texto
            scroll_duration_ms = int((response_length / 5) * 250)  # 250ms por palabra
            scroll_duration_ms = max(15000, min(120000, scroll_duration_ms))  # Mínimo 15s, máximo 120s
            
            components.html(
                f"""
                <script>
                (function() {{
                    const main = window.parent.document.querySelector('.main');
                    if (!main) return;
                    
                    // Función para hacer scroll suave al final
                    function scrollToBottom() {{
                        const startPos = main.scrollTop;
                        const endPos = main.scrollHeight - main.clientHeight;
                        const distance = endPos - startPos;
                        const duration = {scroll_duration_ms};
                        const startTime = performance.now();
                        
                        function easeInOutQuad(t) {{
                            return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
                        }}
                        
                        function animate(currentTime) {{
                            const elapsed = currentTime - startTime;
                            const progress = Math.min(elapsed / duration, 1);
                            const easeProgress = easeInOutQuad(progress);
                            
                            main.scrollTop = startPos + (distance * easeProgress);
                            
                            if (progress < 1) {{
                                requestAnimationFrame(animate);
                            }}
                        }}
                        
                        requestAnimationFrame(animate);
                    }}
                    
                    // Esperar a que se renderice todo el contenido
                    setTimeout(scrollToBottom, 800);
                }})();
                </script>
                """,
                height=0
            )
            
            # Botón de descarga PDF (compatible con iframes, PC y móviles)
            if REPORTLAB_AVAILABLE and len(st.session_state.conversation_history) > 0:
                st.markdown("---")
                st.markdown("### 📥 Exportar Conversación")
                
                try:
                    # Construir HTML de toda la conversación
                    html_parts = []
                    for entry in st.session_state.conversation_history:
                        html_parts.append(f'<p style="color: #000000; font-weight: bold;">Pregunta ({entry["timestamp"]}):</p>')
                        html_parts.append(f'<p style="color: #000000;">{entry["query"]}</p>')
                        html_parts.append(f'<p style="color: #000000; font-weight: bold;">Respuesta:</p>')
                        html_parts.append(f'<p>{entry["response"]}</p>')
                        html_parts.append('<br/>')
                    
                    html_parts.append(f'<br/><p style="color: #28a745;">Usuario: {user_name.upper()}</p>')
                    html_full = ''.join(html_parts)
                    
                    # Generar PDF
                    pdf_bytes = generate_pdf_from_html(
                        html_full,
                        title_base=f"Consulta GERARD - {user_name.upper()}",
                        user_name=user_name.upper()
                    )
                    
                    # Nombre del archivo PDF usando formato original
                    pdf_filename = generate_download_filename(
                        st.session_state.conversation_history,
                        user_name
                    )
                    
                    # Convertir a base64 para JavaScript
                    pdf_b64 = base64.b64encode(pdf_bytes).decode()
                    
                    # JavaScript para descarga compatible con iframes
                    download_js = f"""
                    <script>
                    function downloadPDF() {{
                        try {{
                            const byteCharacters = atob('{pdf_b64}');
                            const byteNumbers = new Array(byteCharacters.length);
                            for (let i = 0; i < byteCharacters.length; i++) {{
                                byteNumbers[i] = byteCharacters.charCodeAt(i);
                            }}
                            const byteArray = new Uint8Array(byteNumbers);
                            const blob = new Blob([byteArray], {{type: 'application/pdf'}});
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = '{pdf_filename}';
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                        }} catch (e) {{
                            console.error('Error en descarga:', e);
                            alert('Error al descargar PDF. Intente desde navegador directo.');
                        }}
                    }}
                    </script>
                    <button onclick="downloadPDF()" style="
                        background: linear-gradient(45deg, #00d4ff, #7b2ff7);
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 25px;
                        cursor: pointer;
                        font-size: 16px;
                        font-weight: bold;
                        width: 100%;
                        margin: 10px 0;
                        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
                    ">
                        📄 Descargar PDF ({len(st.session_state.conversation_history)} consulta{'s' if len(st.session_state.conversation_history) > 1 else ''})
                    </button>
                    """
                    
                    components.html(download_js, height=70)
                    
                except Exception as e:
                    st.error(f"❌ Error generando PDF: {e}")
            elif not REPORTLAB_AVAILABLE:
                st.info("ℹ️ Descarga PDF no disponible (instala reportlab: pip install reportlab)")
            
            # Historial de consultas anteriores
            if len(st.session_state.conversation_history) > 1:
                st.markdown("---")
                with st.expander(f"📚 Historial de consultas ({len(st.session_state.conversation_history) - 1} anterior{'es' if len(st.session_state.conversation_history) > 2 else ''})"):
                    for i, entry in enumerate(st.session_state.conversation_history[:-1]):
                        st.markdown(f"**🔍 Consulta #{i+1}** — _{entry['timestamp']}_")
                        st.markdown(f"**Pregunta:** {entry['query']}")
                        if st.button(f"👁️ Ver respuesta completa", key=f"view_resp_{i}"):
                            st.markdown(entry['response'], unsafe_allow_html=True)
                        st.markdown("---")
            
            # Botón Nueva Consulta
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("➕ NUEVA CONSULTA", key="new_query_btn", use_container_width=True):
                    # Scroll to top
                    components.html("""
                        <script>
                        window.parent.document.querySelector('.main').scrollTo({top: 0, behavior: 'smooth'});
                        </script>
                    """, height=0)
                    st.rerun()
            
            # Guardar en log
            with open("gerard_web_log.txt", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Usuario: {user_name.upper()}\n")
                f.write(f"Consulta: {query}\n")
                f.write(f"Respuesta:\n{response}\n")
                f.write(f"{'='*80}\n")
            
        except Exception as e:
            st.error(f"❌ Error durante el análisis: {str(e)}")

# Pie de página
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #666; font-size: 0.85em;">'
    '🔬 GERARD v3.69 | Powered by Gerardo Arguello Solano | '
    f'© {datetime.now().year}'
    '</div>',
    unsafe_allow_html=True
)
