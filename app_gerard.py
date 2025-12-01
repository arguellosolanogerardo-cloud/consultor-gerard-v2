"""
GERARD v3.69 - Interfaz Web Streamlit
Sistema de Análisis Investigativo Avanzado
Usa Vertex AI con credenciales JSON
"""
import os
import streamlit as st
import pdf_generator
from datetime import datetime
import time
import re
import io
import base64
import uuid
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from cities_data import get_cities_for_country
import streamlit.components.v1 as components

# Intentar importar auth_google (opcional - solo para login con Google)
try:
    import auth_google  # [NEW] Módulo de autenticación
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("[WARNING] Google Auth no disponible - falta google-api-python-client")


# ===== FUNCIONES DE GENERACIÓN DE PDF (CON WEASYPRINT) =====
# Verificar disponibilidad de weasyprint (prioridad) y reportlab (fallback)
WEASYPRINT_AVAILABLE = False
REPORTLAB_AVAILABLE = False
# Intentar importar weasyprint
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
    print("[INFO] Weasyprint disponible para generación de PDF")
except ImportError:
    print("[WARNING] Weasyprint no disponible")
# Intentar importar reportlab SIEMPRE (no solo si weasyprint falla)
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase.pdfmetrics import stringWidth
    REPORTLAB_AVAILABLE = True
    print("[INFO] Reportlab disponible para generación de PDF")
except ImportError:
    print("[ERROR] Reportlab no disponible - instala con: pip install reportlab")

def _escape_ampersand_pdf(text: str) -> str:
    """Escapa el símbolo & para XML"""
    return text.replace('&', '&amp;')

def _strip_html_tags_pdf(html: str) -> str:
    """Elimina todas las etiquetas HTML"""
    return re.sub(r'<[^>]+>', '', html)

def _format_header_pdf(title_base: str, user_name: str | None, max_len: int = None):
    """Construye un encabezado para el PDF sin límite de longitud"""
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_name = (user_name or 'usuario').strip()
    plain = f"{title_base} - {user_name} {date_str}"
    
    # Sin truncar - mostrar título completo
    
    if user_name and user_name in plain:
        html = plain.replace(user_name, f"<b>{user_name}</b>", 1)
    else:
        html = plain
    
    return html, plain

def _convert_spans_to_font_tags_pdf(html: str) -> str:
    """Convierte spans de color a font tags para reportlab"""
    import re
    
    def convert_rgb_to_hex(color_str):
        """Convierte rgb(r,g,b) a #rrggbb"""
        color_str = color_str.strip()
        
        # Si ya es hex, devolver tal cual
        if color_str.startswith('#'):
            return color_str
        
        # Convertir rgb(r, g, b) a hex
        rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str)
        if rgb_match:
            r = int(rgb_match.group(1))
            g = int(rgb_match.group(2))
            b = int(rgb_match.group(3))
            return f'#{r:02x}{g:02x}{b:02x}'
        
        return color_str  # Devolver como está si no se reconoce
    
    s = html
    
    # Convertir spans con colores a font tags
    def replace_color_span(match):
        full_style = match.group(1)
        content = match.group(2)
        
        # Buscar el atributo color en el style
        color_match = re.search(r'color\s*:\s*([^;\"]+)', full_style)
        if color_match:
            original_color = color_match.group(1).strip()
            hex_color = convert_rgb_to_hex(original_color)
            return f'<font color="{hex_color}">{content}</font>'
        else:
            return content
    
    # Reemplazar todos los spans con style que tengan color
    s = re.sub(
        r'<span\s+style="([^"]*)">(.+?)</span>',
        replace_color_span,
        s,
        flags=re.DOTALL
    )
    
    # Eliminar spans restantes sin color
    s = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', s, flags=re.DOTALL)
    
    s = s.replace('\n', '<br/>')
    s = _escape_ampersand_pdf(s)
    return s

def pdf_generator.generate_pdf_from_html(
    html_content: str, 
    title_base: str = "Conversacion GERARD", 
    user_name: str | None = None
) -> bytes:
    """Genera PDF desde HTML - Versión local integrada"""
    if not REPORTLAB_AVAILABLE:
        return b""
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=20, 
            leftMargin=20, 
            topMargin=30, 
            bottomMargin=20
        )
        
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        normal.fontName = 'Helvetica'
        normal.fontSize = 10
        normal.leading = 12
        
        story = []
        
        # Header
        header_html, header_plain = _format_header_pdf(title_base, user_name, max_len=220)
        title_style = styles.get('Heading2', normal)
        story.append(Paragraph(header_html, title_style))
        story.append(Spacer(1, 6))
        
        body = _convert_spans_to_font_tags_pdf(html_content)
        
        try:
            story.append(Paragraph(body, normal))
        except Exception:
            plain = _strip_html_tags_pdf(html_content)
            story.append(Paragraph(plain.replace('&', '&amp;'), normal))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
        
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {e}")
        return b""

# ===== FIN FUNCIONES PDF =====


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
    /* Importar fuentes */
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,400;0,700;1,400;1,700&display=swap');
    
    /* ONE DARK PRO - Tema Global */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e0e0e0;
    }
    
    /* Título principal */
    .main-title {
        font-size: clamp(2em, 8vw, 3.5em);
        font-weight: bold;
        text-align: center;
        color: #61AFEF;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: clamp(2px, 1vw, 4px);
        padding: 0 10px;
        text-shadow: 0 0 20px rgba(97, 175, 239, 0.5);
    }
    
    /* Subtítulo */
    .subtitle {
        text-align: center;
        color: #56B6C2;
        font-size: clamp(1em, 3vw, 1.4em);
        margin-bottom: 20px;
        letter-spacing: clamp(1px, 0.5vw, 2px);
        padding: 0 10px;
    }
    
    /* Descripción */
    .description {
        text-align: center;
        color: #98C379;
        font-size: clamp(0.85em, 2.5vw, 1em);
        margin-bottom: 30px;
        padding: 0 15px;
        line-height: 1.6;
        max-width: 100%;
    }
    
    /* Inputs y TextArea */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: rgba(30, 30, 46, 0.95) !important;
        color: #61AFEF !important;
        border: 2px solid #61AFEF !important;
        border-radius: 8px !important;
        font-size: clamp(0.9em, 2.5vw, 1em) !important;
        padding: 12px !important;
    }
    
    /* Botones */
    .stButton > button {
        background: linear-gradient(135deg, #61AFEF, #C678DD) !important;
        color: white !important;
        font-size: clamp(0.9em, 2.5vw, 1.1em) !important;
        font-weight: bold !important;
        padding: clamp(12px, 3vw, 15px) clamp(25px, 5vw, 40px) !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(97, 175, 239, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        box-shadow: 0 6px 25px rgba(97, 175, 239, 0.5) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Contenedor de respuestas */
    .response-container {
        background: rgba(30, 30, 46, 0.95);
        border-left: 4px solid #61AFEF;
        border-radius: 10px;
        padding: clamp(20px, 5vw, 40px);
        margin: 30px auto;
        max-width: 1200px;
        color: #e0e0e0;
        font-family: 'Merriweather', serif;
        line-height: 1.8;
        font-size: clamp(0.9em, 2.5vw, 1em);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    /* Headers dentro de respuestas - Centrados y con espaciado */
    .response-container h1 {
        color: #61AFEF !important;
        font-size: clamp(1.8em, 5vw, 2.2em) !important;
        text-align: center !important;
        border-bottom: 3px solid #61AFEF !important;
        padding: 20px 0 15px 0 !important;
        margin: 40px 0 30px 0 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
    }
    
    .response-container h2 {
        color: #E5C07B !important;
        font-size: clamp(1.4em, 4vw, 1.8em) !important;
        text-align: center !important;
        border-bottom: 2px solid #E5C07B !important;
        padding: 15px 0 12px 0 !important;
        margin: 35px 0 25px 0 !important;
        letter-spacing: 1px !important;
    }
    
    .response-container h3 {
        color: #56B6C2 !important;
        font-size: clamp(1.2em, 3.5vw, 1.5em) !important;
        text-align: left !important;
        padding: 10px 0 !important;
        margin: 30px 0 20px 0 !important;
        border-left: 4px solid #56B6C2 !important;
        padding-left: 15px !important;
    }
    
    .response-container h4 {
        color: #C678DD !important;
        font-size: clamp(1.1em, 3vw, 1.3em) !important;
        text-align: left !important;
        padding: 8px 0 !important;
        margin: 25px 0 15px 0 !important;
        border-left: 3px solid #C678DD !important;
        padding-left: 12px !important;
    }
    
    /* Strong/Bold text */
    .response-container strong,
    .response-container b {
        color: #E5C07B !important;
        font-weight: bold !important;
    }
    
    /* Párrafos con más espaciado */
    .response-container p {
        margin: 20px 0 !important;
        line-height: 1.8 !important;
        text-align: justify !important;
    }
    
    /* Listas con mejor espaciado */
    .response-container ul,
    .response-container ol {
        margin: 25px 0 !important;
        padding-left: 40px !important;
    }
    
    .response-container li {
        margin: 15px 0 !important;
        line-height: 1.7 !important;
    }
    
    /* Líneas horizontales más prominentes */
    .response-container hr {
        border: none !important;
        border-top: 3px solid #E06C75 !important;
        margin: 50px auto !important;
        width: 80% !important;
        opacity: 0.6 !important;
    }
    
    /* Separación entre bloques de documentos/referencias */
    .response-container > *:not(:last-child) {
        margin-bottom: 25px !important;
    }
    
    /* Stats */
    .stats {
        background: rgba(97, 175, 239, 0.1);
        border-left: 4px solid #61AFEF;
        padding: clamp(12px, 3vw, 15px);
        border-radius: 8px;
        margin: 15px 0;
        color: #98C379;
        font-size: clamp(0.8em, 2vw, 0.9em);
    }
    
    /* Scrollbar personalizado */
    ::-webkit-scrollbar {
        width: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a2e;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #61AFEF;
        border-radius: 6px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #56B6C2;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .row-widget.stHorizontal {
            flex-direction: column;
        }
        
        .stButton > button {
            width: 100% !important;
        }
    }
    
    /* Color overrides - FORZAR con máxima especificidad */
    .response-container span[style*="#61AFEF"] {
        color: #61AFEF !important;
    }
    
    .response-container span[style*="#98C379"] {
        color: #98C379 !important;
    }
    
    .response-container span[style*="#56B6C2"] {
        color: #56B6C2 !important;
    }
    
    .response-container span[style*="#FF0000"] {
        color: #FF0000 !important;
    }
    
    .response-container span[style*="#E5C07B"] {
        color: #E5C07B !important;
        font-size: 22px !important;
        font-weight: bold !important;
    }
    
    .response-container span[style*="#C678DD"] {
        color: #C678DD !important;
    }
    
    .response-container span[style*="#E06C75"] {
        color: #E06C75 !important;
    }
</style>
""", unsafe_allow_html=True)

# Configurar credenciales de Vertex AI
# En Streamlit Cloud usa secrets, localmente usa archivo
# @st.cache_resource - REMOVIDO para asegurar que os.environ se configure en cada worker/hilo
def setup_gcp_credentials():
    """Configura las credenciales de GCP una sola vez por sesión"""
    if "gcp_service_account" in st.secrets:
        # Streamlit Cloud: usa secrets
        import json
        import tempfile
        
        # Verificar si ya está configurado en el entorno
        if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ and os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
            return
            
        service_account_info = dict(st.secrets["gcp_service_account"])
        
        # Crear archivo temporal con las credenciales
        # Usamos delete=False para que persista mientras corre la app
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(service_account_info, f)
            credentials_path = f.name
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        print(f"[INFO] Credenciales GCP configuradas en: {credentials_path}")
    else:
        # Local: usa google_credentials.json que tiene Drive API habilitada
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"

# Ejecutar configuración de credenciales
setup_gcp_credentials()

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
    Soporta: color (hex o rgb), font-weight:bold, font-style:italic, font-family, font-size
    
    IMPORTANTE: Maneja !important en los estilos
    """
    s = html
    # Formatear citas de fuente en negrita magenta (legacy, por si acaso)
    fuente_pattern = r'\((Fuente:[^)]+)\)'
    s = re.sub(fuente_pattern, r'<b><font color="#FF00FF">(\1)</font></b>', s)
    
    # Reemplazar <span> con color y font-weight/font-style
    def replace_span(match):
        style = match.group(1)
        content = match.group(2)
        
        # Eliminar !important de los estilos para procesarlos
        style = style.replace(' !important', '')
        
        # Extraer color (soporta hex, rgb, rgba)
        color_match = re.search(r'color\s*:\s*([^;\"]+)', style)
        color = None
        if color_match:
            color_value = color_match.group(1).strip()
            # Convertir rgb(39, 97, 245) a hex
            rgb_match = re.match(r'rgba?\((\d+),?\s*(\d+),?\s*(\d+)', color_value)
            if rgb_match:
                r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
                color = f'#{r:02x}{g:02x}{b:02x}'
            else:
                color = color_value  # Ya es hex o nombre
        
        # Extraer font-weight
        bold = re.search(r'font-weight\s*:\s*bold', style) is not None
        
        # Extraer font-style
        italic = re.search(r'font-style\s*:\s*italic', style) is not None

        # Extraer font-family (Merriweather -> Times-Roman para PDF)
        # Times-Roman es la fuente serif más cercana a Merriweather en reportlab
        font_face = None
        if 'Merriweather' in style or 'serif' in style:
            font_face = 'Times-Roman'
        
        # Extraer font-size y convertir px a pt (más preciso)
        # Conversión: 1px ≈ 0.75pt
        size_match = re.search(r'font-size\s*:\s*(\d+)px', style)
        font_size = None
        if size_match:
            px = int(size_match.group(1))
            # Conversión más precisa: px * 0.75 = pt
            # 18px → 13.5pt ≈ 14pt
            # 17px → 12.75pt ≈ 13pt
            if px == 18:
                font_size = 14  # Citas azules
            elif px == 17:
                font_size = 13  # Referencias verdes y timestamps rosas
            elif px >= 16:
                font_size = 12
            else:
                font_size = int(px * 0.75)
        
        # Construir tags
        result = content
        
        font_attrs = []
        if color:
            font_attrs.append(f'color="{color}"')
        if font_face:
            font_attrs.append(f'face="{font_face}"')
        if font_size:
            font_attrs.append(f'size="{font_size}"')
            
        if font_attrs:
            attrs_str = " ".join(font_attrs)
            result = f'<font {attrs_str}>{result}</font>'

        if bold:
            result = f'<b>{result}</b>'
        if italic:
            result = f'<i>{result}</i>'
        
        return result
    
    s = re.sub(
        r'<span\s+style="([^"]*)">(.+?)</span>', 
        replace_span,
        s, 
        flags=re.DOTALL
    )
    
    # Reemplazar any remaining <span> without style -> remove span
    s = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', s, flags=re.DOTALL)
    # Asegurar que los saltos de línea HTML sean <br/> para Paragraph
    s = s.replace('\n', '<br/>')
    s = s.replace('<br>', '<br/>')
    # Evitar caracteres & que rompan XML interno
    s = _escape_ampersand(s)
    return s

def _format_header(title_base: str, user_name: str | None, max_len: int = None):
    """
    Construye un encabezado que contiene el título, el nombre en negrita y la fecha.
    Returns: tuple (header_html, header_plain)
    Sin límite de longitud - muestra el título completo
    """
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_name = (user_name or 'usuario').strip()
    plain = f"{title_base} - {user_name} {date_str}"
    # Sin truncar - mostrar título completo
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
def get_optimal_k(query: str, force_exhaustive: bool = False) -> dict:
    """
    Determina el número óptimo de documentos (K) a recuperar basándose en la complejidad de la pregunta.
    
    Args:
        query: Pregunta del usuario
        force_exhaustive: Si True, fuerza búsqueda exhaustiva (K=200)
    
    Returns:
        dict con:
            - k: número de documentos a recuperar
            - level: nivel de complejidad ('simple', 'media', 'compleja', 'exhaustiva')
            - reason: razón de la decisión
            - indicators: dict con indicadores de complejidad detectados
    """
    
    # Si el usuario fuerza búsqueda exhaustiva
    if force_exhaustive:
        return {
            'k': 200,
            'level': 'exhaustiva',
            'reason': 'Búsqueda exhaustiva activada manualmente',
            'indicators': {'manual_override': True}
        }
    
    # Análisis de complejidad
    words = query.split()
    word_count = len(words)
    
    # Indicadores de complejidad
    indicators = {
        'word_count': word_count,
        'multiple_questions': query.count('?') > 1,
        'has_conjunctions': any(conj in query.lower() for conj in [
            ' y ', ' o ', ' además', ' también', ' asimismo', ' igualmente',
            ' por otro lado', ' en relación', ' respecto a'
        ]),
        'has_complex_keywords': any(kw in query.lower() for kw in [
            'compara', 'contrasta', 'analiza', 'profundiza', 'explica detalladamente',
            'todos los', 'todas las', 'exhaustivamente', 'completamente',
            'en profundidad', 'detallado', 'extenso', 'amplio'
        ]),
        'has_multiple_subjects': query.count(',') >= 2,
        'asks_for_listing': any(pattern in query.lower() for pattern in [
            'lista', 'enumera', 'cuáles son', 'qué son', 'menciona todos',
            'dame todos', 'dame todas', 'todos los nombres', 'todas las'
        ])
    }
    
    # Lógica de decisión basada en indicadores
    complexity_score = 0
    
    # Peso por longitud de pregunta
    if word_count > 40:
        complexity_score += 3
    elif word_count > 25:
        complexity_score += 2
    elif word_count > 15:
        complexity_score += 1
    
    # Peso por otros indicadores
    if indicators['multiple_questions']:
        complexity_score += 2
    if indicators['has_conjunctions']:
        complexity_score += 1
    if indicators['has_complex_keywords']:
        complexity_score += 2
    if indicators['has_multiple_subjects']:
        complexity_score += 1
    if indicators['asks_for_listing']:
        complexity_score += 2
    
    # Determinar K basado en score de complejidad
    if complexity_score >= 5:
        # Pregunta COMPLEJA
        return {
            'k': 180,
            'level': 'compleja',
            'reason': f'Pregunta compleja (score: {complexity_score})',
            'indicators': indicators
        }
    elif complexity_score >= 2:
        # Pregunta MEDIA
        return {
            'k': 165,
            'level': 'media',
            'reason': f'Pregunta de complejidad media (score: {complexity_score})',
            'indicators': indicators
        }
    else:
        # Pregunta SIMPLE
        return {
            'k': 150,
            'level': 'simple',
            'reason': f'Pregunta simple (score: {complexity_score})',
            'indicators': indicators
        }
# Inicialización de Google Sheets Logger con Caché Global
@st.cache_resource(show_spinner=False)
def get_shared_sheets_logger():
    """
    Inicializa y cachea el logger de Google Sheets para toda la aplicación.
    Evita reconexiones lentas en cada recarga.
    """
    if not GOOGLE_SHEETS_AVAILABLE:
        return None
    
    try:
        logger = create_sheets_logger()
        if logger and logger.enabled:
            print("[OK] Google Sheets Logger inicializado y cacheado")
            return logger
        else:
            print("[INFO] Google Sheets Logger no está habilitado")
            return None
    except Exception as e:
        print(f"[ERROR] Error inicializando Google Sheets Logger: {e}")
        return None

def init_sheets_logger():
    """Wrapper para mantener compatibilidad con código existente"""
    return get_shared_sheets_logger()

# Caché de recursos
@st.cache_resource(show_spinner="Iniciando motores neuronales...")
def load_resources():
    """Carga LLM, embeddings y FAISS index"""
    # Verificar si existe el índice FAISS (solo la primera vez)
    import os
    from pathlib import Path
    
    faiss_path = Path("faiss_index/index.faiss")
    if not faiss_path.exists():
        # Setup sin mensajes de Streamlit (los muestra setup_faiss_cloud.py en consola)
        try:
            from setup_faiss_cloud import setup_faiss
            if not setup_faiss():
                raise RuntimeError("No se pudo configurar el índice FAISS")
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

**[Documento: nombre_archivo.srt | Timestamp: HH:MM:SS --> HH:MM:SS]**
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
3. Para cada mención encontrada, cita: [Documento: archivo.srt | Timestamp: HH:MM:SS --> HH:MM:SS] seguido del texto literal.
4. Agrupa la información por temas, pero INCLUYE TODAS las menciones de cada tema.
5. Extrae ÚNICAMENTE información que esté presente textualmente.
6. Separa claramente EVIDENCIAS de ANÁLISIS.
5. Declara explícitamente si algo NO se encuentra en el contexto
6. Mantén tono profesional y preciso

**Base de datos cargada. Listo para consultas forenses. Protocolo de evidencia estricta activado.**
""")

def format_docs(docs):
    """Formatea documentos para el contexto con timestamp extraído de metadatos"""
    formatted_docs = []
    for doc in docs:
        # Obtener el nombre completo del archivo sin usar basename
        source = doc.metadata.get('source', 'unknown')
        
        # Intentar obtener el título completo del documento si existe
        doc_title = doc.metadata.get('title', None)
        if not doc_title:
            doc_title = doc.metadata.get('document_title', None)
        
        # Si no hay título, usar el nombre del archivo
        if not doc_title:
            if '/' in source or '\\' in source:
                doc_title = source.replace('\\', '/').split('/')[-1]
            else:
                doc_title = source
        
        # === EXTRACCIÓN DE TIMESTAMPS DESDE METADATOS ===
        # Los fragmentos tienen timestamps en metadatos (start_time, end_time)
        # Los extraemos y agregamos al contenido para que el LLM los vea
        start_time = doc.metadata.get('start_time', '')
        end_time = doc.metadata.get('end_time', '')
        
        content = doc.page_content
        
        # Si tiene timestamps en metadatos, agregarlos al inicio del contenido
        if start_time and end_time:
            # Limpiar milisegundos: HH:MM:SS,mmm --> HH:MM:SS
            start_clean = start_time.split(',')[0] if ',' in start_time else start_time
            end_clean = end_time.split(',')[0] if ',' in end_time else end_time
            
            # Agregar timestamp al inicio del contenido en formato esperado
            # Formato: [HH:MM:SS --> HH:MM:SS]
            timestamp_header = f"[{start_clean} --> {end_clean}]\n"
            content = timestamp_header + content
        
        # Formatear con el título del documento y el contenido (ahora con timestamps)
        formatted_docs.append(f"Documento: {doc_title}\n{content}")
    
    return "\n\n---\n\n".join(formatted_docs)


def colorize_citations(text: str) -> str:
    """
    Colorea las citas bibliográficas con la paleta One Dark Pro:
    - "texto citado" en AZUL #61AFEF con fuente Merriweather 18px
    - [Documento: ... | Timestamp: ...] en VERDE #98C379 con fuente Merriweather 17px
    - Timestamp: HH:MM:SS --> HH:MM:SS en CYAN #56B6C2 con fuente Merriweather 17px
    
    IMPORTANTE: Usa !important en todos los estilos para forzar aplicación en Streamlit Cloud
    """
    import re
    
    # PRIMERO: Eliminar milisegundos de todos los timestamps en el texto
    # Patrón: HH:MM:SS,mmm -> HH:MM:SS
    text = re.sub(r'(\d{2}:\d{2}:\d{2}),\d{3}', r'\1', text)
    
    # 1. Primero colorear texto entre comillas (antes de introducir HTML de los documentos)
    # AZUL ONE DARK PRO: #61AFEF con fuente Merriweather 18px
    quote_pattern = r'\"([^\"]+)\"'
    
    text = re.sub(
        quote_pattern,
        lambda m: f'<span style="color: #61AFEF !important; font-family: \'Merriweather\', serif !important; font-size: 18px !important; line-height: 1.2 !important; font-style: italic !important;">"{m.group(1)}"</span>',
        text
    )
    
    # 2. Colorear textos específicos en AMARILLO con tamaño aumentado
    # AMARILLO ONE DARK PRO: #E5C07B
    special_headers = [
        r'(###\s*\*\*EVIDENCIA\s+TEXTUAL\*\*)',
        r'(###\s*\*\*ANÁLISIS\s+FORENSE\*\*)',
        r'(\*\*INFORME\s+DE\s+ANÁLISIS\s+FORENSE\*\*)',
        r'(\*\*REF:\*\*)',
        r'(\*\*FIN\s+DEL\s+INFORME\*\*)'
    ]
    
    for pattern in special_headers:
        text = re.sub(
            pattern,
            lambda m: f'<span style="color: #E5C07B !important; font-family: \'Merriweather\', serif !important; font-size: 22px !important; line-height: 1.3 !important; font-weight: bold !important; display: block !important; margin: 20px 0 !important;">{m.group(1)}</span>',
            text,
            flags=re.IGNORECASE
        )
    
    # Agregar línea en blanco antes de "FIN DEL INFORME"
    text = re.sub(
        r'(\*\*FIN\s+DEL\s+INFORME\*\*)',
        r'\n\n\1',
        text,
        flags=re.IGNORECASE
    )
    
    # 3. LUEGO colorear los timestamps COMPLETOS (incluyendo "Timestamp:")
    # ROJO INTENSO: #FF0000
    timestamp_pattern = r'(Timestamp:\s*\d{2}:\d{2}:\d{2}\s*-->\s*\d{2}:\d{2}:\d{2})'
    
    text = re.sub(
        timestamp_pattern,
        lambda m: f'<span style="color: #FF0000 !important; font-family: \'Merriweather\', serif !important; font-size: 17px !important; line-height: 1.2 !important; font-weight: bold !important;">{m.group(1)}</span>',
        text
    )
    
    # 3. LUEGO colorear la parte del documento (hasta el |, sin incluir timestamp)
    # VERDE ONE DARK PRO: #98C379
    citation_pattern = r'(\*\*\[Documento:[^\|]+\|)'
    
    text = re.sub(
        citation_pattern,
        lambda m: f'<span style="color: #98C379 !important; font-family: \'Merriweather\', serif !important; font-size: 17px !important; line-height: 1.2 !important; font-style: italic !important;">{m.group(1)}</span>',
        text
    )
    
    # 4. Colorear el cierre ]** en verde
    closing_pattern = r'(\]\*\*)(?=\s|$|\n)'
    
    text = re.sub(
        closing_pattern,
        lambda m: f'<span style="color: #98C379 !important;">{m.group(1)}</span>',
        text
    )
    
    return text



# Header con logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("assets/gerardfull.jpg", use_container_width=True)
st.markdown('<div class="subtitle">v3.69 | ASISTENTE</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ╔══════════════════════════════════════════════════════════════════╗
# ║  DETECTOR DE IP REAL DEL USUARIO - SE EJECUTA EN CADA CARGA     ║
# ╚══════════════════════════════════════════════════════════════════╝
#  CRÍTICO: Este JavaScript DEBE ejecutarse AL INICIO de la aplicación
#  para capturar la IP real del usuario ANTES de cualquier otra lógica
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
# NOTA IMPORTANTE: En Streamlit Cloud es IMPOSIBLE obtener la IP real del cliente
# porque todo pasa por proxies. En su lugar, detectamos si es un servidor cloud
# y mostramos información genérica del usuario.
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════


# Placeholder para descripción (permite borrarla dinámicamente)
description_placeholder = st.empty()

# Mostrar descripción SOLO si NO hay nombre de usuario ingresado
# El usuario solicitó que este texto desaparezca apenas se ingrese el nombre
if not st.session_state.get('user_name'):
    description_placeholder.markdown(
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

# Campo de nombre de usuario (solo si no se ha ingresado)
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

# Lógica de UI optimizada: Mostrar input de usuario ANTES de cargar recursos pesados
if not st.session_state.user_name:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # --- OPCIÓN 1: LOGIN CON GOOGLE (Solo si está disponible) ---
        if GOOGLE_AUTH_AVAILABLE:
            
            # Botón de Login con Google
            # Detectar URL base para redirect
            if "streamlit.app" in str(st.query_params) or os.getenv("STREAMLIT_SERVER_HEADLESS") == "true":
                 redirect_uri = "https://consultor-gerard-v2-zrg5ejmgryrttxhtxwqlxz.streamlit.app/"
            else:
                 redirect_uri = "http://localhost:8501/"
                 
            login_url = auth_google.get_login_url(redirect_uri) 
            
            # Verificar si volvemos de un redirect de Google
            query_params = st.query_params
            if "code" in query_params:
                code = query_params["code"]
                st.query_params.clear()
                
                with st.spinner("🔄 Verificando credenciales de Google..."):
                    user_info = auth_google.get_user_info(code, redirect_uri)
                    
                    if user_info:
                        st.session_state.user_name = user_info.get('name', 'Usuario Google')
                        st.session_state.user_email = user_info.get('email', '')
                        # Para usuarios de Google, ciudad y país se detectarán automáticamente
                        st.session_state.user_city = "Detectando..."
                        st.session_state.user_country = "Detectando..."
                        st.success(f"✅ ¡Bienvenido, {st.session_state.user_name}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Error al iniciar sesión con Google.")

            # Ocultando botón de Google temporalmente

        # --- OPCIÓN 2: NOMBRE MANUAL ---
        st.markdown("### 🔐 ACCESO SEGURO")
        
        # Lista de países más comunes (puede expandirse)
        PAISES = [
            "", "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia", "Australia", 
            "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", 
            "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", 
            "Bulgaria", "Burkina Faso", "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", 
            "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", 
            "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Denmark", "Djibouti", "Dominica", 
            "Dominican Republic", "East Timor", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", 
            "Eritrea", "España", "Estonia", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", 
            "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", 
            "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", 
            "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jordan", "Kazakhstan", 
            "Kenya", "Kiribati", "North Korea", "South Korea", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", 
            "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", 
            "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", 
            "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", 
            "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", 
            "Nicaragua", "Niger", "Nigeria", "Norway", "Oman", "Pakistan", "Palau", "Panama", 
            "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar", 
            "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia", 
            "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", 
            "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", 
            "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Sudan", "Spain", "Sri Lanka", 
            "Sudan", "Suriname", "Swaziland", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", 
            "Tanzania", "Thailand", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", 
            "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", 
            "United States", "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", 
            "Yemen", "Zambia", "Zimbabwe"
        ]
        
        # Usamos contenedores para organizar, pero SIN st.form para permitir interactividad
        # Esto permite que al seleccionar país, se actualice la lista de ciudades
        
        temp_name = st.text_input(
            "👤 Nombre completo:",
            placeholder="Ej: Juan Pérez",
            key="temp_user_name",
            help="Escribe tu nombre completo"
        )
        
        temp_country = st.selectbox(
            "🌍 País:",
            options=PAISES,
            index=0,
            key="temp_user_country",
            help="Selecciona tu país de la lista"
        )
        
        # Lógica dinámica para ciudad basada en el país
        temp_city = ""
        cities_list = get_cities_for_country(temp_country)
        
        if cities_list:
            # Si hay ciudades para este país, mostrar dropdown
            city_options = ["Seleccionar..."] + sorted(cities_list) + ["Otra ciudad..."]
            selected_city_option = st.selectbox(
                "🏙️ Ciudad:",
                options=city_options,
                key="temp_user_city_select",
                help="Selecciona tu ciudad o elige 'Otra ciudad...' para escribirla"
            )
            
            if selected_city_option == "Otra ciudad...":
                temp_city = st.text_input(
                    "Escribe el nombre de tu ciudad:",
                    placeholder="Ej: Mi Ciudad",
                    key="temp_user_city_manual"
                )
            elif selected_city_option != "Seleccionar...":
                temp_city = selected_city_option
        else:
            # Si no hay lista de ciudades (o no se seleccionó país), mostrar text input normal
            temp_city = st.text_input(
                "🏙️ Ciudad:",
                placeholder="Ej: Madrid, Barcelona...",
                key="temp_user_city_manual_fallback",
                help="Escribe el nombre de tu ciudad"
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        submit_button = st.button("🚀 Continuar", use_container_width=True, key="manual_login_btn")
        
        if submit_button:
            # Validar que todos los campos estén llenos
            if not temp_name or not temp_name.strip():
                st.error("❌ Por favor ingresa tu nombre")
            elif not temp_country or temp_country == "":
                st.error("❌ Por favor selecciona tu país de la lista")
            elif not temp_city or not temp_city.strip():
                st.error("❌ Por favor selecciona o ingresa tu ciudad")
            # Validar que la ciudad sea un nombre válido (sin números)
            elif not temp_city.replace(" ", "").replace("-", "").isalpha():
                st.error("❌ El nombre de la ciudad no es válido. Solo debe contener letras, espacios y guiones")
            elif len(temp_city.strip()) < 2:
                st.error("❌ El nombre de la ciudad es demasiado corto")
            else:
                # Guardar datos en session_state
                st.session_state.user_name = temp_name.strip()
                st.session_state.user_city = temp_city.strip().title()  # Capitalizar correctamente
                st.session_state.user_country = temp_country.strip()
                st.success(f"✅ ¡Bienvenido, {temp_name.strip()}!")
                st.rerun()
    
    # Detener ejecución aquí si no hay usuario para que sea instantáneo
    if not st.session_state.user_name:
        st.stop()

user_name = st.session_state.user_name

# Cargar recursos SOLO después de tener usuario (o en background si fuera posible, pero Streamlit es secuencial)
# Al moverlo aquí, la primera carga del input será instantánea.
# La demora ocurrirá al dar Enter, pero mostraremos un spinner.
with st.spinner("🚀 Iniciando sistemas neuronales..."):
    try:
        llm, faiss_vs = load_resources()
        doc_count = faiss_vs.index.ntotal if hasattr(faiss_vs, 'index') else 0
        
        # Detectar si es un índice placeholder vacío
        if doc_count <= 1:
            st.error("⚠️ **ÍNDICE FAISS NO DISPONIBLE**")
            st.warning("""
            Esta instancia de Streamlit Cloud no tiene acceso a los documentos fuente.
            
            **Para usar la app completa:**
            - Ejecuta localmente desde tu computadora
            - O espera a que se publique el índice completo en GitHub Release
            
            **Archivos faltantes:** 3,442 archivos SRT (~2GB)
            """)
            st.stop()
        
        st.markdown(
            f'<div class="stats">✅ SISTEMA OPERATIVO | {doc_count:,} fragmentos <span style="color: #bf40ff; font-weight: bold;">EN LINEA</span></div>',
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"❌ Error inicializando sistema: {e}")
        st.stop()

# Separador
st.markdown("---")

# Inicializar historial de conversación en session_state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Inicializar Google Sheets Logger (una sola vez por sesión)
if 'sheets_logger' not in st.session_state:
    st.session_state.sheets_logger = init_sheets_logger()

# --- BARRA LATERAL: GUÍA DE USO ---
# (Reemplaza al indicador de estado de Google Sheets)

st.sidebar.success("✅ v2.5 - SIN BOTON")

with st.sidebar.expander("📚 Guía de Uso", expanded=False):
    try:
        with open("GUIA_MODELOS_PREGUNTA_GERARD.md", "r", encoding="utf-8") as f:
            guia_content = f.read()
        
        st.markdown(guia_content)
            
    except Exception as e:
        st.error(f"Error cargando la guía: {e}")


# Inicializar flag para limpiar campo de pregunta
if 'clear_query' not in st.session_state:
    st.session_state.clear_query = False

# Solo mostrar el resto SI hay nombre de usuario
if user_name:
    # Mensaje de bienvenida personalizado
    st.markdown(
        f'<div style="text-align: center; font-weight: bold; margin: 20px 0;">'
        f'<span style="font-size: 1.3em; color: #00ff41;">👋 HOLA </span>'
        f'<span style="font-size: 2em; color: #00d4ff;">{user_name.upper()}</span>'
        f'<span style="font-size: 1.3em; color: #00ff41;">, YA PUEDES PREGUNTAR</span>'
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
    
    # Checkbox de búsqueda exhaustiva
    col_checkbox, col_info = st.columns([1, 3])
    with col_checkbox:
        exhaustive_search = st.checkbox(
            "🔬 Exhaustiva", 
            value=st.session_state.get('exhaustive_search', False),
            help="Activa búsqueda exhaustiva (recupera hasta 200 documentos en lugar del modo adaptativo)"
        )
        # Guardar estado
        st.session_state.exhaustive_search = exhaustive_search
    
    with col_info:
        if exhaustive_search:
            st.markdown(
                '<div style="color: #00ff41; font-size: 0.9em; padding: 5px;">⚡ Modo exhaustivo: se recuperarán 200 documentos (~+2s tiempo)</div>',
                unsafe_allow_html=True
            )
    
    # Resetear flag de limpieza
    if st.session_state.clear_query:
        st.session_state.clear_query = False
    
    # Botón de consulta centrado
    # Usamos columnas vacías a los lados para centrar el botón
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
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
        # PRIMER SCROLL: Hacia el spinner para mostrar actividad
        # SOLUCIÓN RADICAL: Inyectar script directamente en el DOM usando st.markdown
        # Esto evita el problema del iframe aislado de components.html
        
        scroll_placeholder_1 = st.empty()
        scroll_placeholder_1.markdown(
            """
            <script>
            (function() {
                // Ejecutar inmediatamente sin timeout para asegurar que se ejecuta
                try {
                    // Lista de posibles contenedores scrollables en Streamlit
                    const scrollTargets = [
                        document.querySelector('.main'),
                        document.querySelector('[data-testid="stAppViewContainer"]'),
                        document.querySelector('.stApp'),
                        document.documentElement, // html
                        document.body
                    ];

                    // Intentar scroll en todos los contenedores posibles
                    scrollTargets.forEach(target => {
                        if (target) {
                            try {
                                // Bajar 300px desde la posición actual
                                const currentScroll = target.scrollTop;
                                target.scrollTo({
                                    top: currentScroll + 300,
                                    behavior: 'smooth'
                                });
                            } catch(e) {
                                console.log("Error scrolling target:", e);
                            }
                        }
                    });
                    
                    // Fallback global window scroll
                    window.scrollBy({
                        top: 300,
                        behavior: 'smooth'
                    });
                    
                } catch(e) {
                    console.error("Error en primer scroll:", e);
                }
            })();
            </script>
            """,
            unsafe_allow_html=True
        )
        
        try:
           # Recuperar documentos usando búsqueda híbrida (BM25 + FAISS)
            # SISTEMA ADAPTATIVO: K se ajusta según complejidad de la pregunta
            k_info = get_optimal_k(query, force_exhaustive=exhaustive_search)
            k_docs = k_info['k']
            
            # Mostrar información de búsqueda
            st.markdown(
                f'<div style="background: rgba(97, 175, 239, 0.1); border-left: 4px solid #61AFEF; padding: 12px; border-radius: 6px; margin: 10px 0;">'
                f'<span style="color: #61AFEF; font-weight: bold;">📊 Búsqueda {k_info["level"].upper()}</span> '
                f'<span style="color: #98C379;">• {k_docs} documentos</span> '
                f'<span style="color: #E5C07B; font-size: 0.85em;">• {k_info["reason"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            with st.spinner(f"🔍 Buscando con algoritmo híbrido (recuperando {k_docs} docs)..."):
                search_method = "unknown"
                search_start_time = time.time()  # Iniciar cronómetro de búsqueda
                
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
                        query_lower = query.lower()
                        asks_for_names = any(pattern in query_lower for pattern in [
                            'nombre', 'nombres', 'quien', 'quienes', 'guardianes', 'maestros'
                        ])
                        query_words = query.split()
                        has_proper_nouns = any(word[0].isupper() for word in query_words if len(word) > 2)
                        proper_noun_keywords = [
                            'maria', 'magdalena', 'jesus', 'cristo', 'jose', 'juan', 'pedro', 'pablo',
                            'azoes', 'azen', 'aviatar', 'alaniso', 'axel', 'adiel', 'aladim', 'aliestro',
                            'maestro', 'maestros', 'guardianes', 'guardian'
                        ]
                        has_name_keywords = any(word.lower() in proper_noun_keywords for word in query_words)
                        
                        if has_proper_nouns or has_name_keywords or asks_for_names:
                            st.success("✅ Búsqueda de nombres/identidades → BM25 prioritario (coincidencias exactas)")
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
            
          # Calcular tiempo de búsqueda
            search_time = time.time() - search_start_time
            
            # Mostrar estadísticas de recuperación mejoradas
            query_lower = query.lower()
            relevant_docs = [d for d in docs if any(term in d.page_content.lower() for term in query_lower.split())]
            
            # Badge de método según el utilizado
            method_badges = {
                'hybrid': '🎯 Híbrido',
                'faiss': '🔍 FAISS',
                'bm25': '📝 BM25'
            }
            method_badge = method_badges.get(search_method, '❓ Desconocido')
            
            st.markdown(
                f'<div style="background: rgba(152, 195, 121, 0.1); border-left: 4px solid #98C379; padding: 12px; border-radius: 6px; margin: 10px 0;">'
                f'<span style="color: #98C379; font-weight: bold;">✅ BÚSQUEDA COMPLETADA</span><br/>'
                f'<span style="color: #E5C07B;">📊 Recuperados: {len(docs)} docs</span> • '
                f'<span style="color: #61AFEF;">⚡ Relevantes: {len(relevant_docs)} docs</span> • '
                f'<span style="color: #C678DD;">⏱️ Tiempo: {search_time:.2f}s</span> • '
                f'<span style="color: #56B6C2;">{method_badge}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # Mostrar GIF de procesamiento animado
            if os.path.exists("assets/pregunta.gif"):
                # Usar HTML directo para que el GIF se anime correctamente
                st.markdown(
                    '''<div class="gif-container" style="text-align: center;">
                        <img src="data:image/gif;base64,{}" width="300">
                    </div>'''.format(
                        base64.b64encode(open("assets/pregunta.gif", "rb").read()).decode()
                    ),
                    unsafe_allow_html=True
                )
            
            # Construir cadena RAG
            query_start_time = datetime.now()

            # Crear banderas para saber si estamos en Streamlit Cloud
            if "running_in_cloud" not in st.session_state:
                # Streamlit Cloud define esta variable en secrets
                st.session_state.running_in_cloud = bool(os.getenv("STREAMLIT_RUNTIME", "")) or bool(os.getenv("STREAMLIT_CLOUD", ""))

            # Mensaje de búsqueda grande en verde neón
            status_placeholder = st.empty()
            status_placeholder.markdown(
                '<div style="text-align: center; font-size: 3em; color: #00ff41; font-weight: bold; margin: 30px 0; animation: pulse 1.5s ease-in-out infinite;">'
                '🧠 GERARD V3.69 está buscando la Respuesta...'
                '</div>'
                '<style>'
                '@keyframes pulse {'
                '  0%, 100% { opacity: 1; }'
                '  50% { opacity: 0.6; }'
                '}'
                '</style>',
                unsafe_allow_html=True
            )
            
            with st.spinner(""):  # Spinner vacío para mantener el estado de carga
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
            
            # Limpiar mensaje de estado
            status_placeholder.empty()
            
            # ═══════════════════════════════════════════════════════════════
            # 🎉 NOTIFICACIONES DE RESPUESTA LISTA
            # ═══════════════════════════════════════════════════════════════
            
            # 1. Toast notification (esquina superior derecha)
            st.toast('✨ ¡Respuesta lista! Desplázate hacia arriba para leerla.', icon='✅')
            
            # 2. Animación de globos
            st.balloons()
            
            # 3. Sonido de aviso (campana)
            st.markdown("""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAADhAC7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7u7/////////////////////////////////////////////////////////////////wAAAABMYXZmNTguNzYuMTAwAAAAAAAAAAAAAAAAJAAAAAAAAAAAA4TjGlKMAAAAAAAAAAAAAAAAAAAA//sQZAAP8AAAaQAAAAgAAA0gAAABAAABpAAAACAAADSAAAAETEFNRTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV" type="audio/mpeg">
                </audio>
                <script>
                    // Sonido de campana corto y agradable
                    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    const oscillator = audioContext.createOscillator();
                    const gainNode = audioContext.createGain();
                    
                    oscillator.connect(gainNode);
                    gainNode.connect(audioContext.destination);
                    
                    // Sonido tipo "ding" (campana)
                    oscillator.frequency.value = 880; // A5 (nota aguda)
                    oscillator.type = 'sine';
                    
                    // Envelope: ataque rápido, decay suave
                    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
                    gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                    
                    oscillator.start(audioContext.currentTime);
                    oscillator.stop(audioContext.currentTime + 0.5);
                </script>
            """, unsafe_allow_html=True)
            
            # ═══════════════════════════════════════════════════════════════
            
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
            
            # Limpiar descripción inmediatamente si era la primera pregunta
            description_placeholder.empty()
            
            # Marcar para limpiar campo en siguiente render
            st.session_state.clear_query = True
            st.session_state.last_query = ""
            
            # Logging a Google Sheets
            if st.session_state.sheets_logger:
                try:
                    # Generar ID único para esta interacción
                    interaction_id = str(uuid.uuid4())
                    
                    # Detectar dispositivo y ubicación
                    device_info = {"device_type": "PC", "browser": "Local", "os": "Windows"}
                    
                    # Usar ciudad y país del usuario si están disponibles (ingreso manual)
                    user_city = st.session_state.get('user_city', 'Local')
                    user_country = st.session_state.get('user_country', 'Colombia')
                    location_info = {"city": user_city, "country": user_country, "ip": "127.0.0.1"}
                    
                    # Detectar dispositivo y ubicación SOLO en Streamlit Cloud
                    if GOOGLE_SHEETS_AVAILABLE:
                        try:
                            # Intentar obtener User-Agent (solo disponible en Cloud)
                            if hasattr(st, "context") and hasattr(st.context, "headers"):
                                user_agent = st.context.headers.get("User-Agent", "Unknown")
                                
                                # Detectar dispositivo
                                device_detector = DeviceDetector()
                                device_info_full = device_detector.detect_from_web(user_agent)
                                device_info = {
                                    "device_type": device_info_full.get("tipo", "PC"),
                                    "browser": device_info_full.get("navegador", "Local"),
                                    "os": device_info_full.get("os", "Windows")
                                }
                                
                                
                                # ═══════════════════════════════════════════════════════════════
                                # GEOLOCALIZACIÓN CON IP REAL DEL USUARIO
                                # La IP se obtiene del JavaScript que se ejecuta AL INICIO de la app
                                # ═══════════════════════════════════════════════════════════════
                                
                                geo_locator = GeoLocator()
                                
                                # Obtener IP (probablemente será del servidor en Streamlit Cloud)
                                location_data = geo_locator.get_location()
                                detected_ip = location_data.get('ip', '')
                                
                                # ═══════════════════════════════════════════════════════════════
                                # DETECCIÓN DE SERVIDORES CLOUD (Streamlit, Google Cloud, AWS, etc.)
                                # ═══════════════════════════════════════════════════════════════
                                cloud_ip_ranges = [
                                    "35.203.",   # Streamlit Cloud - The Dalles, Oregon
                                    "35.245.",   # Google Cloud
                                    "35.247.",   # Google Cloud
                                    "34.86.",    # Google Cloud
                                    "34.87.",    # Google Cloud
                                    "34.105.",   # Google Cloud
                                    "35.184.",   # Google Cloud
                                    "35.188.",   # Google Cloud
                                ]
                                
                                is_cloud_server = any(detected_ip.startswith(prefix) for prefix in cloud_ip_ranges)
                                
                                if is_cloud_server:
                                    # SOBRESCRIBIR datos con información genérica
                                    location_data = {
                                        "ciudad": "🌐 Usuario Web",
                                        "pais": "Acceso Remoto",
                                        "ip": "Protegido",
                                        "region": "N/A",
                                        "codigo_pais": "N/A",
                                        "timezone": "N/A",
                                        "org": "Streamlit Cloud",
                                        "fuente": "cloud_detection"
                                    }
                                    print(f"")
                                    print(f"{'='*60}")
                                    print(f"🌐 SERVIDOR CLOUD DETECTADO (IP: {detected_ip})")
                                    print(f"✓ Mostrando: Usuario Web / Acceso Remoto")
                                    print(f"{'='*60}")
                                    print(f"")
                                else:
                                    # IP real del usuario (ejecución local)
                                    print(f"")
                                    print(f"{'='*60}")
                                    print(f"✓✓✓ IP DEL USUARIO: {detected_ip}")
                                    print(f"✓✓✓ Ciudad: {location_data.get('ciudad', 'N/A')}")
                                    print(f"✓✓✓ País: {location_data.get('pais', 'N/A')}")
                                    print(f"✓✓✓ Fuente API: {location_data.get('fuente', 'N/A')}")
                                    print(f"{'='*60}")
                                    print(f"")

                                
                                if location_data:
                                    location_info = {
                                        "city": location_data.get("ciudad", "Desconocido"),
                                        "country": location_data.get("pais", "Desconocido"),
                                        "ip": location_data.get("ip", "Desconocido")
                                    }
                                    print(f"[INFO] Geolocalización FINAL: {location_info['city']}, {location_info['country']} - IP: {location_info['ip']}")


                        except Exception as e:
                            print(f"[WARNING] Error detectando dispositivo/ubicación (usando valores por defecto): {e}")
                    
                    # Limpiar respuesta (quitar HTML)
                    answer_clean = _strip_html_tags(response)
                    
                    # Registrar en Google Sheets (solo si el logger está habilitado)
                    if st.session_state.sheets_logger and st.session_state.sheets_logger.enabled:
                        print(f"[DEBUG] Intentando registrar interacción: {user_name.upper()} - {query[:50]}...")
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
                        print(f"[OK] Interacción registrada exitosamente")
                    else:
                        print("[WARNING] Google Sheets Logger no está habilitado - interacción no registrada")
                except Exception as e:
                    print(f"[ERROR] Error logging a Google Sheets: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Mostrar respuesta
            st.success("✅ Análisis completado")
            
            st.markdown("### 🔬 Resultado del Análisis:")
            # Colorear las citas antes de mostrar
            colored_response = colorize_citations(response)
            # IMPORTANTE: Usar st.html() en vez de st.markdown() para preservar los estilos inline
            st.html(f'<div class="response-container" id="respuesta-gerard">{colored_response}</div>')
            
            # Estadísticas
            st.markdown(
                f'<div class="stats">'
                f'📊 Documentos analizados: {len(docs)} | '
                f'👤 Usuario: {user_name.upper()} | '
                f'🕐 Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # SEGUNDO SCROLL: Automático hacia el final de la respuesta
            # SOLUCIÓN RADICAL: Inyectar script directamente en el DOM usando st.markdown
            # Esto evita el problema del iframe aislado de components.html
            
            scroll_placeholder_2 = st.empty()
            scroll_placeholder_2.markdown(
                """
                <script>
                (function() {
                    function forceScrollToBottom() {
                        try {
                            // Identificar todos los posibles contenedores de scroll
                            const targets = [
                                document.querySelector('[data-testid="stAppViewContainer"]'), // Principal en versiones nuevas
                                document.querySelector('.main'), // Principal en versiones viejas
                                document.querySelector('.stApp'),
                                document.documentElement,
                                document.body
                            ];

                            targets.forEach(target => {
                                if (target) {
                                    try {
                                        // Calcular el máximo scroll posible
                                        const maxScroll = target.scrollHeight - target.clientHeight;
                                        
                                        if (maxScroll > 0 && maxScroll > target.scrollTop) {
                                            // Usar scrollTo nativo con behavior smooth
                                            target.scrollTo({
                                                top: maxScroll,
                                                behavior: 'smooth'
                                            });
                                        }
                                    } catch(e) {
                                        console.log("Error scrolling target:", e);
                                    }
                                }
                            });
                            
                            // Intento global en window
                            window.scrollTo({
                                top: document.body.scrollHeight,
                                behavior: 'smooth'
                            });
                            
                        } catch(e) {
                            console.error("Error en scroll final:", e);
                        }
                    }
                    
                    // Ejecutar múltiples veces para asegurar que carga todo el contenido dinámico
                    // Tiempos escalonados para capturar diferentes velocidades de renderizado
                    setTimeout(forceScrollToBottom, 300);
                    setTimeout(forceScrollToBottom, 1000);
                    setTimeout(forceScrollToBottom, 2500);
                    setTimeout(forceScrollToBottom, 5000); // Último intento tardío para móviles lentos
                    
                })();
                </script>
                """,
                unsafe_allow_html=True
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
                        # Aplicar colorización a la respuesta antes de exportar
                        colored_response = colorize_citations(entry["response"])
                        html_parts.append(f'<p>{colored_response}</p>')
                        html_parts.append('<br/>')
                    
                    html_parts.append(f'<br/><p style="color: #28a745;">Usuario: {user_name.upper()}</p>')
                    html_full = ''.join(html_parts)
                    
                    # Generar PDF con título completo y sin cortes
                    pdf_bytes = pdf_generator.generate_pdf_from_html(
                        html_full,
                        title_base=f"Consulta GERARD - {user_name.upper()}",
                        user_name=user_name.upper()
                    )
                    
                    # Nombre del archivo PDF usando formato original con preguntas
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
                    safe_username = "".join(c for c in user_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                    
                    # Construir nombre con TODAS las preguntas (sin límite)
                    question_parts = []
                    for entry in st.session_state.conversation_history:
                        # Limpiar pregunta (SIN truncar - mostrar pregunta completa)
                        clean_q = "".join(c for c in entry["query"] if c.isalnum() or c in (' ', '_', '-', '?')).strip()
                        clean_q = clean_q.replace(' ', '_')
                        # SIN límite de longitud - pregunta completa
                        if clean_q:
                            question_parts.append(clean_q)
                    
                    # Formato: CONSULTA_DE_[USUARIO]_[pregunta1]?_[pregunta2]?_[pregunta3]?_..._[FECHA]_[HORA].pdf
                    if question_parts:
                        questions_str = "_".join(f"{q}?" for q in question_parts)
                        pdf_filename = f"CONSULTA_DE_{safe_username}_{questions_str}_{timestamp_str}.pdf"
                    else:
                        # Fallback si no hay preguntas
                        pdf_filename = f"CONSULTA_DE_{safe_username}_{timestamp_str}.pdf"
                    
                    # Convertir bytes a base64 para JavaScript
                    pdf_b64 = base64.b64encode(pdf_bytes).decode()
                    
                    # JavaScript para descarga compatible con iframes, PC y móviles
                    download_js = f"""
                    <script>
                    var pdfDownloaded = false;
                    
                    // Verificar si ya se descargó este PDF al cargar la página
                    window.addEventListener('DOMContentLoaded', function() {{
                        const btn = document.getElementById('pdf-download-btn');
                        if (sessionStorage.getItem('pdfDownloaded_{len(st.session_state.conversation_history)}') === 'true') {{
                            if (btn) {{
                                btn.style.background = 'linear-gradient(45deg, #00FF41, #00CC33)';
                                btn.style.borderColor = '#00FF41';
                                btn.style.boxShadow = '0 0 20px rgba(0, 255, 65, 0.6)';
                                btn.innerHTML = '✅ ¡Descargado Exitosamente!';
                                pdfDownloaded = true;
                            }}
                        }}
                    }});
                    
                    function downloadPDF() {{
                        if (pdfDownloaded) return; // Evitar descargas múltiples
                        
                        try {{
                            // Crear blob desde base64
                            const byteCharacters = atob('{pdf_b64}');
                            const byteNumbers = new Array(byteCharacters.length);
                            for (let i = 0; i < byteCharacters.length; i++) {{
                                byteNumbers[i] = byteCharacters.charCodeAt(i);
                            }}
                            const byteArray = new Uint8Array(byteNumbers);
                              const blob = new Blob([byteArray], {type: 'application/pdf'});
                              const link = document.createElement('a');
                              link.href = window.URL.createObjectURL(blob);
                              link.download = '{pdf_filename}';
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
    
                            const blob = new Blob([byteArray], {{type: 'application/pdf'}});

                            // Crear enlace de descarga
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = '{pdf_filename}';
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                            
                            // Cambiar botón a VERDE NEÓN y mostrar éxito
                            const btn = document.getElementById('pdf-download-btn');
                            if (btn) {{
                                btn.style.background = 'linear-gradient(45deg, #00FF41, #00CC33)';
                                btn.style.borderColor = '#00FF41';
                                btn.style.boxShadow = '0 0 20px rgba(0, 255, 65, 0.6)';
                                btn.innerHTML = '✅ ¡Descargado Exitosamente!';
                                pdfDownloaded = true;
                                
                                // Guardar estado en sessionStorage para persistir
                                sessionStorage.setItem('pdfDownloaded_{len(st.session_state.conversation_history)}', 'true');
                            }}
                            
                            // Mostrar alerta nativa de éxito
                            alert('✅ PDF descargado exitosamente. Revisa tu carpeta de descargas.');
                            
                        }} catch (e) {{
                            console.error('Error en descarga:', e);
                            alert('❌ Error al descargar PDF. Intente nuevamente.');
                        }}
                    }}
                    </script>
                    <button id="pdf-download-btn" onclick="downloadPDF()" style="
                        background: linear-gradient(45deg, #ff4b4b, #ff8080);
                        color: white;
                        border: 2px solid #ff4b4b;
                        padding: 12px 20px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 16px;
                        font-weight: bold;
                        width: 100%;
                        margin: 10px 0;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    " onmouseover="if(!pdfDownloaded) this.style.transform='scale(1.02)'" 
                       onmouseout="if(!pdfDownloaded) this.style.transform='scale(1)'">
                        📄 Descargar PDF ({len(st.session_state.conversation_history)} consulta{"s" if len(st.session_state.conversation_history) > 1 else ""})
                    </button>
                    """
                    
                    st.components.v1.html(download_js, height=80)
                    
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
# Pie de página fijo y estilizado
st.markdown(
    f"""
    <style>
    /* Ocultar footer nativo de Streamlit */
    footer {{
        visibility: hidden;
    }}
    
    /* Ajustar margen inferior del contenido principal */
    .block-container {{
        padding-bottom: 80px !important;
    }}
    </style>
    
    <!-- Footer inyectado directamente con estilos inline para máxima prioridad -->
    <div style="
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100vw;
        background-color: #0a0a0a;
        color: #e0e0e0;
        text-align: center;
        font-size: 13px;
        padding: 10px 0;
        border-top: 2px solid #00d4ff;
        z-index: 999999;
        box-shadow: 0 -5px 10px rgba(0,0,0,0.5);
        padding-bottom: env(safe-area-inset-bottom, 10px);
    ">
        🔬 GERARD v3.69 | Powered by Gerardo Arguello Solano | © {datetime.now().year}
    </div>
    """,
    unsafe_allow_html=True
)