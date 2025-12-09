"""
GERARD v3.69 - Interfaz Web Streamlit
Sistema de Análisis Investigativo Avanzado
Usa Vertex AI con credenciales JSON
"""
import os
import streamlit as st
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
from geo_utils import GeoLocator
from google_sheets_logger import create_sheets_logger
from real_ip_detector import show_ip_simple_copy
from document_title_filter import hybrid_search_with_title, detect_title_in_query

# Intentar importar auth_google (opcional - solo para login con Google)
try:
    import auth_google  # [NEW] Módulo de autenticación
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("[WARNING] Google Auth no disponible - falta google-api-python-client")

# ===== CONFIGURACIÓN DE LOGIN =====
# Habilita/deshabilita el formulario de ingreso manual
ENABLE_MANUAL_LOGIN = False  # Cambia a False para reactivar el ingreso manual

# ===== FUNCIONES DE GENERACIÓN DE PDF (CON WEASYPRINT) =====
# Verificar disponibilidad de weasyprint (prioridad) y reportlab (fallback)
WEASYPRINT_AVAILABLE = False
REPORTLAB_AVAILABLE = False

# Intentar importar weasyprint
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
    print("[INFO] ✅ Weasyprint disponible para generación de PDF con colores")
except ImportError as e:
    print(f"[WARNING] Weasyprint no disponible (ImportError): {e}")
    WEASYPRINT_AVAILABLE = False
except Exception as e:
    print(f"[WARNING] Error al importar Weasyprint: {type(e).__name__}: {e}")
    WEASYPRINT_AVAILABLE = False

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

def generate_pdf_from_html_local(
    html_content: str, 
    title_base: str = "Conversacion GERARD", 
    user_name: str | None = None
) -> bytes:
    """
    Genera PDF desde HTML con PRESERVACIÓN COMPLETA de colores y estilos.
    Usa weasyprint (prioridad) o reportlab (fallback).
    """
    
    # OPCIÓN 1: Weasyprint (preserva TODO el CSS automáticamente)
    if WEASYPRINT_AVAILABLE:
        try:
            date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            user_name = (user_name or 'usuario').strip()
            header = f"{title_base} - {user_name} {date_str}"
            
            # CSS inline que replica los estilos de la app
            css_styles = """
                <style>
                    @page {
                        size: A4;
                        margin: 2cm;
                    }
                    body {
                        font-family: 'Merriweather', 'Georgia', 'Times New Roman', serif;
                        font-size: 10pt;
                        line-height: 1.6;
                        color: #000;
                    }
                    h1 {
                        font-size: 16pt;
                        font-weight: bold;
                        text-align: center;
                        margin: 20px 0;
                        page-break-after: avoid;
                        color: #000;
                        text-transform: uppercase;
                    }
                    h2 {
                        font-size: 14pt;
                        font-weight: bold;
                        margin: 15px 0 10px 0;
                        page-break-after: avoid;
                        color: #000;
                    }
                    h3 {
                        font-size: 12pt;
                        font-weight: bold;
                        margin: 12px 0 8px 0;
                        page-break-after: avoid;
                        color: #000;
                    }
                    p {
                        margin: 10px 0;
                        line-height: 1.8;
                    }
                    /* Preservar TODOS los colores inline de los spans */
                    span[style*="color"] {
                        /* Los colores inline se preservan automáticamente */
                    }
                    /* Citas de texto en AZUL - #61AFEF */
                    span[style*="#61AFEF"] {
                        color: #61AFEF !important;
                        font-family: 'Merriweather', serif;
                        font-size: 12pt;
                        font-style: italic;
                    }
                    /* Referencias de documentos en VERDE OSCURO - #2E7D32 */
                    span[style*="#2E7D32"] {
                        color: #2E7D32 !important;
                        font-family: 'Merriweather', serif;
                        font-size: 13pt;
                        font-weight: bold;
                    }
                    /* Mantener compatibilidad con color antiguo por si acaso */
                    span[style*="#98C379"] {
                        color: #2E7D32 !important;
                        font-family: 'Merriweather', serif;
                        font-size: 13pt;
                        font-weight: bold;
                    }
                    /* Timestamps en ROJO - #FF0000 */
                    span[style*="#FF0000"] {
                        color: #FF0000 !important;
                        font-family: 'Merriweather', serif;
                        font-size: 11pt;
                        font-weight: bold;
                    }
                    /* Encabezados especiales en AMARILLO - #E5C07B */
                    span[style*="#E5C07B"] {
                        color: #E5C07B !important;
                        font-family: 'Merriweather', serif;
                        font-size: 14pt;
                        font-weight: bold;
                    }
                    /* Encabezados ####** en AMARILLO INTENSO - #FFD700 */
                    .header-level-4 {
                        color: #FFD700 !important;
                        font-family: 'Merriweather', serif;
                        font-size: 18pt;
                        font-weight: bold;
                        text-transform: uppercase;
                        text-align: center;
                        margin: 20px 0;
                        padding: 10px 0;
                        letter-spacing: 1px;
                    }
                    hr {
                        border: none;
                        border-top: 1px solid #ccc;
                        margin: 15px 0;
                    }
                    /* Evitar que las citas se partan entre páginas */
                    .citation-block {
                        page-break-inside: avoid;
                    }
                    /* Espaciado entre preguntas y respuestas */
                    .question-block {
                        margin-top: 30px;
                        page-break-inside: avoid;
                    }
                </style>
            """
            
            # HTML completo con header y estilos
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                {css_styles}
            </head>
            <body>
                <h1>{header}</h1>
                {html_content}
            </body>
            </html>
            """
            
            # Generar PDF con weasyprint (preserva TODOS los estilos CSS)
            pdf_bytes = HTML(string=full_html).write_pdf()
            return pdf_bytes
            
        except Exception as e:
            print(f"[ERROR] Weasyprint PDF failed: {e}")
            # Si falla, intentar con reportlab
            if REPORTLAB_AVAILABLE:
                return _generate_pdf_reportlab_fallback(html_content, title_base, user_name)
            return b""
    
    # OPCIÓN 2: Reportlab fallback (limitado pero funcional)
    elif REPORTLAB_AVAILABLE:
        return _generate_pdf_reportlab_fallback(html_content, title_base, user_name)
    
    else:
        print("[ERROR] No PDF library available")
        return b""

def _generate_pdf_reportlab_fallback(html_content: str, title_base: str, user_name: str | None) -> bytes:
    """Fallback a reportlab si weasyprint no está disponible"""
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
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_name = (user_name or 'usuario').strip()
        header = f"{title_base} - {user_name} {date_str}"
        
        title_style = styles.get('Heading2', normal)
        story.append(Paragraph(header, title_style))
        story.append(Spacer(1, 12))
        
        # Body (texto plano sin colores)
        # Eliminar HTML tags para reportlab
        plain_text = re.sub(r'<[^>]+>', '', html_content)
        plain_text = plain_text.replace('&', '&amp;')
        
        story.append(Paragraph(plain_text, normal))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
        
    except Exception as e:
        print(f"[ERROR] Reportlab fallback failed: {e}")
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
    
    /* Estilo para encabezados de nivel 4 (####**texto**) - NUEVO */
    .header-level-4 {
        color: #FFD700 !important; /* Amarillo Intenso (Gold) */
        font-family: 'Merriweather', serif !important;
        font-size: 26px !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        text-align: center !important;
        margin: 30px 0 !important;
        padding: 15px 0 !important;
        letter-spacing: 1px !important;
        line-height: 1.4 !important;
    }
    
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
    
    /* Estilo para botón en estado EJECUTADO (Rojo) - Activado por marcador adyacente */
    /* Busca un div que contenga .executed-marker y afecta al SIGUIENTE div (el del botón) */
    div:has(.executed-marker) + div .stButton > button {
        background: linear-gradient(135deg, #FF4B4B, #CC0000) !important;
        border: 2px solid #FF0000 !important;
        box-shadow: 0 0 20px rgba(255, 0, 0, 0.6) !important;
        transform: scale(0.98) !important; /* Ligeramente presionado */
        content: "🔴 PREGUNTA EJECUTADA"; /* Fallback visual */
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
    
    /* Caja de Evidencia - Estilo Forense */
    .evidence-box {
        background: rgba(97, 175, 239, 0.05) !important;
        border-left: 4px solid #61AFEF !important;
        border-radius: 8px !important;
        padding: 20px !important;
        margin: 20px 0 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Separador de Secciones */
    .section-separator {
        border: 0 !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, #61AFEF 20%, #61AFEF 80%, transparent) !important;
        margin: 30px 0 !important;
        opacity: 0.5 !important;
    }
    
    /* Encabezado de Reporte */
    .report-header {
        text-align: center !important;
        border: 2px solid #61AFEF !important;
        border-radius: 10px !important;
        padding: 20px !important;
        margin: 20px 0 !important;
        background: rgba(97, 175, 239, 0.05) !important;
    }
    
    /* Conclusión Final */
    .conclusion-box {
        text-align: center !important;
        border: 2px solid #98C379 !important;
        padding: 20px !important;
        border-radius: 10px !important;
        background: rgba(152, 195, 121, 0.1) !important;
        margin-top: 30px !important;
    }
    
    /* Metadatos de Documento */
    .doc-metadata {
        font-family: 'Courier New', monospace !important;
        font-size: 14px !important;
        color: #98C379 !important;
        background: rgba(152, 195, 121, 0.05) !important;
        padding: 8px 12px !important;
        border-radius: 4px !important;
        margin: 10px 0 !important;
        border-left: 3px solid #98C379 !important;
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
    
    # Intentar detectar si st.secrets está disponible y tiene gcp_service_account
    has_secrets = False
    try:
        # Verificar si st.secrets existe y tiene la configuración necesaria
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            has_secrets = True
    except Exception as e:
        # Si falla (por ejemplo, no hay secrets.toml), continuar sin secrets
        print(f"[INFO] st.secrets no disponible: {e}")
        has_secrets = False
    
    if has_secrets:
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
        print(f"[INFO] Credenciales GCP configuradas desde st.secrets: {credentials_path}")
    else:
        # Local/Render: detectar automáticamente el archivo correcto
        # Prioridad: archivo sin espacios (Render) -> archivo con espacios (Local)
        credential_paths = [
            "google_credentials.json",  # Render/producción sin espacios
            "credencial_json_midyear-node-436821-t3-525a146e96a0.json",  # Alternativa sin espacios
            "credencial json/midyear-node-436821-t3-525a146e96a0.json"  # Local con espacios
        ]
        
        credentials_file = None
        for path in credential_paths:
            if os.path.exists(path):
                credentials_file = path
                print(f"[INFO] Usando credenciales desde: {path}")
                break
        
        if credentials_file:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
        else:
            print("[WARNING] No se encontró archivo de credenciales local.")



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

#### PROHIBICIÓN NIVEL 3: REFERENCIAS INCOMPLETAS (CRÍTICO)
❌ NUNCA JAMÁS usar "(Mencionado en el nombre del archivo)" sin mostrar el texto literal
❌ NUNCA JAMÁS citar solo metadatos (nombre de archivo, timestamp) sin el contenido textual
❌ NUNCA JAMÁS hacer una referencia sin incluir la cita literal entre comillas
❌ Si un fragmento NO tiene contenido textual útil, NO lo cites
❌ Si solo existe el nombre del archivo pero NO texto, DECLARA que no hay texto disponible

---

### 🟢 MANDATOS OBLIGATORIOS

**FORMATO OBLIGATORIO para CADA cita:**

**[VIDEO / AUDIO: nombre_archivo.srt | Minuto: HH:MM:SS --> HH:MM:SS]**
"TEXTO LITERAL EXACTO DEL SUBTÍTULO QUE DEBE APARECER AQUÍ SIEMPRE"

**REGLAS CRÍTICAS DE CITACIÓN:**
1. **SIEMPRE** debe haber texto entre comillas después de la referencia del documento
2. El texto entre comillas debe ser una transcripción LITERAL, no un resumen
3. Si el fragmento contiene texto real, SIEMPRE debes mostrarlo
4. Si el fragmento NO contiene texto útil (solo metadatos), omítelo completamente
5. **NUNCA** uses frases como "(Mencionado en el nombre del archivo)" como sustituto del texto

---

## CONTEXTO DISPONIBLE (Fragmentos de la base de datos):
{context}

## CONSULTA DEL USUARIO:
{input}

---

## 🔍 BÚSQUEDAS POR TÍTULO/AUDIO/VIDEO DE DOCUMENTO:

Cuando el usuario pregunta específicamente por un **documento, archivo, audio o video** usando su título o ID:

**PASO 1: VERIFICACIÓN**
- Revisa el campo `[VIDEO / AUDIO: nombre_archivo.srt]` de cada fragmento del contexto
- Identifica si los fragmentos pertenecen al documento mencionado por el usuario
- Los usuarios pueden referirse a los documentos como: "documento", "archivo", "audio", "video"

**PASO 2: DECLARACIÓN DE ESTADO**
- Si **NO hay fragmentos** del documento/audio/video solicitado en el contexto:
  → Declara explícitamente: "No se encontraron fragmentos del [documento/audio/video] '[título]' en el contexto proporcionado"
  → NO inventes información
  → NO uses conocimiento general
  
- Si **SÍ hay fragmentos** del documento/audio/video solicitado:
  → Procesa ÚNICAMENTE esos fragmentos
  → Ignora fragmentos de otros documentos/audios/videos
  → Responde la pregunta basándote solo en esos fragmentos específicos

**PASO 3: RESPUESTA**
- Cada cita DEBE incluir el nombre del archivo fuente
- Mantén el mismo formato de citación obligatorio: `**[VIDEO / AUDIO: ...]** "texto literal"`
- Agrupa la información temáticamente si hay múltiples fragmentos

**EJEMPLO DE RESPUESTA CORRECTA:**
Si el usuario pregunta: "EN EL AUDIO DE TÍTULO: Para que se dejo Donald trump como presidente. QUE INFORMACION SE DA DE MARIA MAGDALENA?"

Y el contexto contiene fragmentos de ese audio, responde:
```
**INFORMACIÓN SOBRE MARÍA MAGDALENA EN EL AUDIO SOLICITADO**

**[VIDEO / AUDIO: Para que se dejo Donald trump como presidente [nPNE9qHlUfY].es.srt | Minuto: 00:05:23 --> 00: 05:45]**
"maría magdalena era una gran maestra espiritual que acompañó al maestro jesús..."

**[VIDEO / AUDIO: Para que se dejo Donald trump como presidente [nPNE9qHlUfY].es.srt | Minuto: 00:12:10 --> 00:12:33]**
"ella fue la única mujer entre los discípulos..."
```

---

## INSTRUCCIONES FINALES:

1. **PROCESA TODOS LOS FRAGMENTOS**: El contexto contiene MÚLTIPLES documentos separados por "---". Debes analizarlos TODOS.
2. **LISTA EXHAUSTIVA CON TEXTO**: Si un término aparece en múltiples fragmentos, lista TODOS los que tengan contenido textual útil.
3. **FORMATO OBLIGATORIO**: Cada mención debe tener:
   - Referencia: **[VIDEO / AUDIO: ... | Minuto: ...]**
   - Seguida INMEDIATAMENTE por: "texto literal entre comillas"
4. **OMITE REFERENCIAS VACÍAS**: Si un fragmento solo tiene nombre de archivo sin texto útil, NO lo incluyas.
5. Agrupa la información por temas, pero SIEMPRE con citas textuales completas.
6. Separa claramente EVIDENCIAS (con citas) de ANÁLISIS (tu interpretación).
7. Declara explícitamente si algo NO se encuentra en el contexto.
8. Mantén tono profesional y preciso.

**RECORDATORIO FINAL:** Cada cita DEBE tener texto literal entre comillas. Sin excepciones.

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
        formatted_docs.append(f"VIDEO / AUDIO: {doc_title}\n{content}")
    
    return "\n\n---\n\n".join(formatted_docs)


def colorize_citations(text: str) -> str:
    """
    Colorea las citas bibliográficas con la paleta One Dark Pro y
    mejora el formato visual con estructura de reporte forense:
    - "texto citado" en AZUL #61AFEF con fuente Merriweather 18px
    - [VIDEO / AUDIO: ... | Minuto: ...] en VERDE OSCURO #2E7D32 con fuente Merriweather 19px NEGRITA
    - Minuto: HH:MM:SS --> HH:MM:SS en ROJO #FF0000 con fuente Merriweather 17px
    - Encabezados de sección en AMARILLO #E5C07B
    - Agrega separadores visuales y cajas de evidencia
    
    IMPORTANTE: Usa !important en todos los estilos para forzar aplicación en Streamlit Cloud
    """
    import re
    
    # PRIMERO: Eliminar milisegundos de todos los timestamps en el texto
    # Patrón: HH:MM:SS,mmm -> HH:MM:SS
    text = re.sub(r'(\d{2}:\d{2}:\d{2}),\d{3}', r'\1', text)
    
    # NUEVO: Procesar encabezados ####**texto**
    # Convertir a MAYÚSCULAS, NEGRILLA y AZUL con espacio antes y después
    # Patrón: ####**cualquier texto**
    header_level4_pattern = r'####\s*\*\*(.+?)\*\*'
    
    def format_header_level4(match):
        content = match.group(1).strip()
        # Convertir a MAYÚSCULAS
        content_upper = content.upper()
        # Usar clase CSS global .header-level-4 (Amarillo Intenso #FFD700, 26px)
        # IMPORTANTE: Usar comillas SIMPLES para la clase para evitar conflicto con el regex de citas que busca comillas dobles
        return f"\n\n<div class='header-level-4'>{content_upper}</div>\n\n"
    
    text = re.sub(
        header_level4_pattern,
        format_header_level4,
        text,
        flags=re.MULTILINE
    )
    
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
    
    # 3. LUEGO colorear los timestamps COMPLETOS (incluyendo "Minuto:")
    # ROJO INTENSO: #FF0000
    timestamp_pattern = r'(Minuto:\s*\d{2}:\d{2}:\d{2}\s*-->\s*\d{2}:\d{2}:\d{2})'
    
    text = re.sub(
        timestamp_pattern,
        lambda m: f'<span style="color: #FF0000 !important; font-family: \'Merriweather\', serif !important; font-size: 17px !important; line-height: 1.2 !important; font-weight: bold !important;">{m.group(1)}</span>',
        text
    )
    
    # 3. LUEGO colorear la parte del documento (hasta el |, sin incluir timestamp)
    # VERDE OSCURO INTENSO: #2E7D32 (Material Design Dark Green)
    citation_pattern = r'(\*\*\[VIDEO / AUDIO:[^\|]+\|)'
    
    text = re.sub(
        citation_pattern,
        lambda m: f'<span style="color: #2E7D32 !important; font-family: \'Merriweather\', serif !important; font-size: 19px !important; line-height: 1.3 !important; font-weight: bold !important;">{m.group(1)}</span>',
        text
    )
    
    # 4. Colorear el cierre ]** en verde oscuro
    closing_pattern = r'(\]\*\*)(?=\s|$|\n)'
    
    text = re.sub(
        closing_pattern,
        lambda m: f'<span style="color: #2E7D32 !important; font-weight: bold !important;">{m.group(1)}</span>',
        text
    )
    
    # 5. Agregar separadores visuales entre secciones principales (líneas con ---)
    text = re.sub(
        r'^---+$',
        '<hr class="section-separator">',
        text,
        flags=re.MULTILINE
    )
    
    # 6. Convertir ### en encabezados de sección estilizados
    section_header_pattern = r'^###\s+(.+)$'
    text = re.sub(
        section_header_pattern,
        lambda m: f'<h3 style="color: #E5C07B !important; font-family: \'Merriweather\', serif !important; font-size: 20px !important; font-weight: bold !important; margin: 25px 0 15px 0 !important; padding-bottom: 8px !important; border-bottom: 2px solid #E5C07B !important;">{m.group(1)}</h3>',
        text,
        flags=re.MULTILINE
    )
    
    # 7. Convertir ## en encabezados principales más grandes
    main_header_pattern = r'^##\s+(.+)$'
    text = re.sub(
        main_header_pattern,
        lambda m: f'<h2 style="color: #61AFEF !important; font-family: \'Merriweather\', serif !important; font-size: 24px !important; font-weight: bold !important; margin: 30px 0 20px 0 !important; text-align: center !important; padding: 15px !important; background: rgba(97, 175, 239, 0.05) !important; border-radius: 8px !important; border: 1px solid #61AFEF !important;">{m.group(1)}</h2>',
        text,
        flags=re.MULTILINE
    )
    
    return text





# Header con logo (Solo mostrar ANTES del login)
if not st.session_state.get('user_name'):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/gerardfull.png", use_container_width=True)
    st.markdown('<div class="subtitle">v3.69 | ASISTENTE</div>', unsafe_allow_html=True)

# CSS Global para colorización de respuestas
st.markdown("""
<style>
    /* Encabezados nivel 4 (####**texto**) en AMARILLO INTENSO */
    .header-level-4 {
        color: #FFD700 !important;
        font-family: 'Merriweather', serif !important;
        font-size: 26px !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        text-align: center !important;
        margin: 20px 0 !important;
        padding: 10px 0 !important;
        letter-spacing: 1px !important;
        display: block !important;
    }
    
    /* Asegurar que los colores inline se apliquen */
    #respuesta-gerard span[style*="color"] {
        /* Forzar aplicación de colores inline */
    }
    
    /* Timestamps en ROJO */
    #respuesta-gerard span[style*="#FF0000"] {
        color: #FF0000 !important;
    }
    
    /* Citas en AZUL */
    #respuesta-gerard span[style*="#61AFEF"] {
        color: #61AFEF !important;
    }
    
    /* Documentos en VERDE OSCURO */
    #respuesta-gerard span[style*="#2E7D32"] {
        color: #2E7D32 !important;
    }
    
    /* Encabezados en AMARILLO */
    #respuesta-gerard span[style*="#E5C07B"] {
        color: #E5C07B !important;
    }
</style>
""", unsafe_allow_html=True)

# IMPORTANTE: Inicializar recursos AL INICIO para descargar FAISS si es necesario
# Esto asegura que el índice se descargue al cargar la app, no cuando alguien pregunta
try:
    load_resources()
except Exception as e:
    st.error(f"❌ Error inicializando sistema: {e}")
    st.stop()


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

# Campo de email del usuario (se llena con login de Google)
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# Inicializar flag de procesamiento OAuth (previene bucles infinitos)
if 'oauth_processing' not in st.session_state:
    st.session_state.oauth_processing = False
if 'oauth_processed' not in st.session_state:
    st.session_state.oauth_processed = False

# Inicializar detector de IP (una sola vez por sesión)
if 'geo_locator' not in st.session_state:
    st.session_state.geo_locator = GeoLocator(timeout_seconds=3)
    print("[INFO] GeoLocator inicializado")

# Inicializar Google Sheets Logger (una sola vez por sesión)
if 'sheets_logger' not in st.session_state:
    st.session_state.sheets_logger = create_sheets_logger()
    if st.session_state.sheets_logger:
        print("[INFO] Google Sheets Logger inicializado")
    else:
        print("[WARNING] Google Sheets Logger no disponible - credenciales no encontradas")

# Lógica de UI optimizada: Mostrar input de usuario ANTES de cargar recursos pesados
if not st.session_state.user_name:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # --- OPCIÓN 1: LOGIN CON GOOGLE (Solo si está disponible) ---
        if GOOGLE_AUTH_AVAILABLE:
            st.markdown("### 🔐 Acceso Seguro")
            
            # Botón de Login con Google
            # Detectar URL base para redirect (Estrategia robusta por SO)
            # Local (Usuario) = Windows ('nt')
            # Cloud (Streamlit) = Linux ('posix')
            if os.name == 'nt':
                redirect_uri = "http://localhost:8501/"
                print("[INFO] Entorno detectado: LOCAL (Windows)")
            else:
                redirect_uri = "https://consultor-gerard-v3-zrg5ejmgryrttxhtxwqlxz.streamlit.app/"
                print("[INFO] Entorno detectado: CLOUD (Linux/Otro)")
            
            print(f"[INFO] Usando redirect_uri: {redirect_uri}")
            
            # Verificar si volvemos de un redirect de Google
            query_params = st.query_params
            
            # PROTECCIÓN CONTRA BUCLES: Solo procesar si hay código Y no hemos procesado antes
            if "code" in query_params and not st.session_state.oauth_processed:
                print("[INFO] 🔐 Procesando callback de Google OAuth...")
                code = query_params["code"]
                
                # Marcar inmediatamente como procesado ANTES de cualquier operación
                st.session_state.oauth_processing = True
                
                with st.spinner("🔄 Verificando credenciales de Google..."):
                    user_info = auth_google.get_user_info(code, redirect_uri)
                    
                    if user_info:
                        print(f"[INFO] ✅ Usuario autenticado: {user_info.get('name', 'Desconocido')}")
                        print(f"[DEBUG] user_info completo: {user_info}")  # Ver qué contiene user_info
                        
                        # CRÍTICO: Guardar datos en session_state ANTES de limpiar query_params
                        st.session_state.user_name = user_info.get('name', 'Usuario Google')
                        st.session_state.user_email = user_info.get('email', '')
                        
                        print(f"[DEBUG] Email capturado: '{st.session_state.user_email}'")  # Ver si se capturó
                        
                        # Función para validar si un string es una IP válida
                        def is_valid_ip(ip_string):
                            """Verifica si el string es una dirección IP válida (IPv4 o IPv6)"""
                            if not ip_string or not isinstance(ip_string, str):
                                return False
                            # Si contiene espacios o letras que no sean en notación hex (IPv6), no es IP
                            if ' ' in ip_string:
                                return False
                            # Verificar formato IPv4 o IPv6
                            import re
                            ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
                            ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
                            return bool(re.match(ipv4_pattern, ip_string) or re.match(ipv6_pattern, ip_string))
                        
                        # Detectar ubicación (usará IP del proxy de Streamlit)
                        # El usuario podrá confirmar su IP real después del login
                        try:
                            geo = st.session_state.geo_locator
                            location = geo.get_location()
                            
                            if location and location.get('ciudad') != 'Desconocido':
                                detected_ip = location.get('ip', 'No detectado')
                                # VALIDACIÓN: Asegurar que la IP es válida y no es un nombre
                                if is_valid_ip(detected_ip):
                                    st.session_state.user_ip = detected_ip
                                else:
                                    print(f"[WARNING] IP inválida detectada: '{detected_ip}' - usando 'No detectado'")
                                    st.session_state.user_ip = "No detectado"
                                
                                st.session_state.user_city = location.get('ciudad', 'Desconocida')
                                st.session_state.user_country = location.get('pais', 'Desconocido')
                                print(f"[INFO] 📍 Ubicación detectada: {st.session_state.user_city}, {st.session_state.user_country} (IP: {st.session_state.user_ip})")
                            else:
                                st.session_state.user_ip = "No detectado"
                                st.session_state.user_city = "No detectada"
                                st.session_state.user_country = "No detectado"
                                
                            # Marcar para confirmar IP real después
                            st.session_state.ip_needs_confirmation = True
                        except Exception as e:
                            print(f"[WARNING] Error detectando ubicación: {e}")
                            st.session_state.user_ip = "Error"
                            st.session_state.user_city = "Error"
                            st.session_state.user_country = "Error"
                            st.session_state.ip_needs_confirmation = True
                        
                        # Marcar como procesado exitosamente
                        st.session_state.oauth_processed = True
                        st.session_state.oauth_processing = False
                        
                        # Verificar que user_name se guardó correctamente
                        if st.session_state.user_name:
                            print(f"[INFO] ✅ Session state actualizado: user_name={st.session_state.user_name}")
                            
                            # AHORA sí limpiar query_params (después de guardar todo)
                            st.query_params.clear()
                            
                            st.success(f"✅ ¡Bienvenido, {st.session_state.user_name}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            print("[ERROR] ❌ No se pudo guardar user_name en session_state")
                            st.session_state.oauth_processing = False
                            st.error("❌ Error al guardar información de usuario.")
                    else:
                        print("[ERROR] ❌ No se pudo obtener información del usuario de Google")
                        st.session_state.oauth_processing = False
                        st.session_state.oauth_processed = True  # Marcar para evitar reintentos
                        st.query_params.clear()  # Limpiar para salir del bucle
                        st.error("❌ Error al iniciar sesión con Google.")

            # Mostrar botón de login solo si NO estamos procesando OAuth
            login_url = auth_google.get_login_url(redirect_uri)
            if login_url and not st.session_state.oauth_processing:
                st.markdown(
                    f'''
                    <style>
                    .google-neo-button {{
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        background: #e0e5ec;
                        border: none;
                        border-radius: 20px;
                        padding: 16px 32px;
                        font-size: 16px;
                        font-weight: 600;
                        color: #3c4043;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        box-shadow: 9px 9px 16px rgba(163, 177, 198, 0.6),
                                    -9px -9px 16px rgba(255, 255, 255, 0.5);
                        text-decoration: none;
                        width: 100%;
                    }}
                    
                    .google-neo-button:hover {{
                        box-shadow: 6px 6px 12px rgba(163, 177, 198, 0.6),
                                    -6px -6px 12px rgba(255, 255, 255, 0.5);
                        transform: translateY(-1px);
                    }}
                    
                    .google-neo-button:active {{
                        box-shadow: inset 4px 4px 8px rgba(163, 177, 198, 0.6),
                                    inset -4px -4px 8px rgba(255, 255, 255, 0.5);
                        transform: translateY(0);
                    }}
                    
                    .google-neo-button svg {{
                        margin-right: 12px;
                        width: 22px;
                        height: 22px;
                        flex-shrink: 0;
                    }}
                    </style>
                    
                    <a href="{login_url}" class="google-neo-button">
                        <svg viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        <span>Acceder con Google</span>
                    </a>
                    ''', 
                    unsafe_allow_html=True
                )
            
            # Solo mostrar separador y formulario manual si está habilitado
            if ENABLE_MANUAL_LOGIN:
                st.markdown("--- O ---")

        # --- OPCIÓN 2: NOMBRE MANUAL ---
        if ENABLE_MANUAL_LOGIN:
            st.markdown("### ✍️ Ingreso Manual")
            
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
                    
                    # Función para validar si un string es una IP válida
                    def is_valid_ip(ip_string):
                        """Verifica si el string es una dirección IP válida (IPv4 o IPv6)"""
                        if not ip_string or not isinstance(ip_string, str):
                            return False
                        if ' ' in ip_string:
                            return False
                        import re
                        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
                        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
                        return bool(re.match(ipv4_pattern, ip_string) or re.match(ipv6_pattern, ip_string))
                    
                    # Detectar ubicación/IP también para login manual
                    try:
                        geo = st.session_state.geo_locator
                        location = geo.get_location()
                        
                        if location and location.get('ciudad') != 'Desconocido':
                            detected_ip = location.get('ip', 'No detectado')
                            # VALIDACIÓN: Asegurar que la IP es válida
                            if is_valid_ip(detected_ip):
                                st.session_state.user_ip = detected_ip
                                print(f"[INFO] 📍 IP detectada para login manual: {st.session_state.user_ip}")
                            else:
                                print(f"[WARNING] IP inválida en login manual: '{detected_ip}' - usando 'No detectado'")
                                st.session_state.user_ip = "No detectado"
                        else:
                            st.session_state.user_ip = "No detectado"
                        
                        # Marcar para confirmar IP real después
                        st.session_state.ip_needs_confirmation = True
                    except Exception as e:
                        print(f"[WARNING] Error detectando IP en login manual: {e}")
                        st.session_state.user_ip = "No detectado"
                        st.session_state.ip_needs_confirmation = True
                    
                    st.success(f"✅ ¡Bienvenido, {temp_name.strip()}!")
                    st.rerun()
    
    # Detener ejecución aquí si no hay usuario para que sea instantáneo
    if not st.session_state.user_name:
        st.stop()

user_name = st.session_state.user_name

# === CONFIRMACIÓN SIMPLE DE IP REAL ===
# Muestra IP, copiar, pegar, confirmar - solución que SÍ funciona
if st.session_state.get('ip_needs_confirmation', False):
    show_ip_simple_copy()
    st.stop()


# Cargar recursos SOLO después de tener usuario (o en background si fuera posible, pero Streamlit es secuencial)
# Al moverlo aquí, la primera carga del input será instantánea.
# La demora ocurrirá al dar Enter, pero mostraremos un spinner.
with st.spinner("🚀 Iniciando sistemas neuronales..."):
    try:
        llm, faiss_vs = load_resources()
        
        # EXTRAER DOCUMENTOS PARA BM25 EN MEMORIA (Fuera del caché para que persista en session_state)
        if 'all_docs' not in st.session_state or not st.session_state.all_docs:
            try:
                # Acceder al docstore de FAISS
                all_docs = list(faiss_vs.docstore._dict.values())
                st.session_state.all_docs = all_docs
                print(f"[INFO] Documentos extraídos de FAISS para BM25: {len(all_docs)}")
            except Exception as e:
                print(f"[WARNING] No se pudieron extraer documentos de FAISS: {e}")
                st.session_state.all_docs = []
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

# --- BARRA LATERAL ---
with st.sidebar:
    # === LOGO/IMAGEN (PRIMERO) ===
    import os
    gestor_path = "assets/gestor.png"
    if os.path.exists(gestor_path):
        st.image(gestor_path, use_container_width=True)
        st.markdown("---")
    else:
        print(f"[WARNING] Imagen no encontrada: {gestor_path}")
    
    # === GUÍA DE USO ===
    with st.expander("📚 Guía de Uso", expanded=False):
        try:
            with open("GUIA_MODELOS_PREGUNTA_GERARD.md", "r", encoding="utf-8") as f:
                guia_content = f.read()
            
            st.markdown(guia_content)
            
            # Botón para ver como página completa
            if st.button("🔗 Ver Guía Completa", use_container_width=True, key="ver_guia_completa"):
                st.session_state.show_guia_page = True
                st.rerun()
                
        except Exception as e:
            st.error(f"Error cargando la guía: {e}")
    
    st.markdown("---")
    
    # === INFORMACIÓN DEL USUARIO ===
    st.markdown(f"### 👤 Usuario")
    st.markdown(f"**{user_name}**")
    if st.session_state.get('user_email'):
        st.markdown(f"📧 {st.session_state.user_email}")
    
    st.markdown("---")
    
    # === BOTÓN CERRAR SESIÓN ===
    if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        # Limpiar todos los datos de sesión
        st.session_state.user_name = ""
        st.session_state.user_email = ""
        st.session_state.user_city = ""
        st.session_state.user_country = ""
        st.session_state.oauth_processed = False
        st.session_state.oauth_processing = False
        st.session_state.conversation_history = []
        st.success("✅ Sesión cerrada exitosamente")
        time.sleep(1)
        st.rerun()




# === MOSTRAR GUÍA COMO PÁGINA COMPLETA ===
if st.session_state.get('show_guia_page', False):
    st.markdown("# 📚 Guía de Uso Completa")
    
    if st.button("⬅️ Volver a la Aplicación", type="primary"):
        st.session_state.show_guia_page = False
        st.rerun()
    
    st.markdown("---")
    
    try:
        with open("GUIA_MODELOS_PREGUNTA_GERARD.md", "r", encoding="utf-8") as f:
            guia_content = f.read()
        st.markdown(guia_content)
    except Exception as e:
        st.error(f"Error cargando la guía: {e}")
    
    st.stop()  # Detener ejecución para no mostrar el resto de la app


# Inicializar flag para limpiar campo de pregunta
# ═══════════════════════════════════════════════════════════════
# FUNCIÓN DE VISUALIZACIÓN DE RESULTADOS (Refactorizada para persistencia)
# ═══════════════════════════════════════════════════════════════
def display_analysis_result(response, docs, search_time, search_method, relevant_docs_count, user_name):
    # Ocultar animación de Data Scanning si está activa
    st.components.v1.html("""
    <script>
        if (window.top && window.top.hideScanningAnimation) {
            window.top.hideScanningAnimation();
        }
    </script>
    """, height=0)
    
    # Mostrar respuesta
    st.success("✅ Análisis completado")
    
    # Modal informando que la respuesta está lista
    response_ready_modal = """
    <script>
    (function() {
        // Inyectar modal de respuesta lista en el documento padre
        function injectResponseReadyModal() {
            const parentDoc = window.parent.document;
            
            // Verificar si ya existe el modal
            if (parentDoc.getElementById('response-ready-modal')) {
                return;
            }
            
            // Inyectar estilos en el head del documento padre
            const style = parentDoc.createElement('style');
            style.textContent = `
                #response-ready-modal {
                    display: none;
                    position: fixed;
                    z-index: 9999999;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0, 0, 0, 0.85);
                    animation: responseModalFadeIn 0.3s;
                    overflow: auto;
                }
                #response-ready-modal-content {
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    margin: 20% auto;
                    padding: 35px;
                    border: 3px solid #00d4ff;
                    border-radius: 20px;
                    width: 90%;
                    max-width: 550px;
                    box-shadow: 0 10px 40px rgba(0, 212, 255, 0.4);
                    animation: responseModalSlideDown 0.5s;
                    color: white;
                    text-align: center;
                }
                #response-ready-modal h2 {
                    color: #00ff41;
                    margin-top: 0;
                    font-size: 28px;
                    margin-bottom: 20px;
                }
                #response-ready-modal p {
                    font-size: 18px;
                    line-height: 1.8;
                    margin: 20px 0;
                    color: #e0e0e0;
                }
                #response-ready-modal .highlight {
                    color: #00d4ff;
                    font-weight: bold;
                    font-size: 20px;
                }
                #response-ready-modal-close {
                    background: linear-gradient(45deg, #00d4ff, #0099cc);
                    color: #000;
                    border: none;
                    padding: 15px 40px;
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 18px;
                    font-weight: bold;
                    width: 100%;
                    margin-top: 25px;
                    transition: all 0.3s;
                    box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
                }
                #response-ready-modal-close:hover {
                    transform: scale(1.05);
                    box-shadow: 0 6px 20px rgba(0, 212, 255, 0.5);
                }
                @keyframes responseModalFadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes responseModalSlideDown {
                    from { transform: translateY(-100px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @media (max-width: 600px) {
                    #response-ready-modal-content {
                        margin: 30% auto;
                        padding: 25px;
                        width: 90%;
                    }
                    #response-ready-modal h2 {
                        font-size: 22px;
                    }
                    #response-ready-modal p {
                        font-size: 16px;
                    }
                }
            `;
            parentDoc.head.appendChild(style);
            
            // Crear el modal en el body del documento padre
            const modalDiv = parentDoc.createElement('div');
            modalDiv.id = 'response-ready-modal';
            modalDiv.innerHTML = `
                <div id="response-ready-modal-content">
                    <h2>🎉 ¡Respuesta Lista!</h2>
                    <p>✨ Tu consulta ha sido procesada exitosamente</p>
                    <p class="highlight">👇 Desliza hacia abajo para ver tu respuesta</p>
                    <p style="font-size: 16px; color: #a0a0a0; margin-top: 15px;">💡 Usa scroll o desliza para navegar</p>
                    <button id="response-ready-modal-close">VER RESPUESTA</button>
                </div>
            `;
            parentDoc.body.appendChild(modalDiv);
            
            // Función para cerrar el modal de respuesta lista
            window.closeResponseReadyModal = function() {
                console.log('[Response Modal] Cerrando modal...');
                const modal = parentDoc.getElementById('response-ready-modal');
                if (modal) {
                    modal.remove(); // Eliminar completamente del DOM
                    console.log('[Response Modal] Modal eliminado');
                    // Scroll automático a la respuesta después de cerrar
                    setTimeout(function() {
                        window.parent.scrollTo({
                            top: document.body.scrollHeight,
                            behavior: 'smooth'
                        });
                    }, 200);
                }
            };
            
            // Event listeners para el modal en el documento padre
            const closeBtn = parentDoc.getElementById('response-ready-modal-close');
            if (closeBtn) {
                console.log('[Response Modal] Configurando event listeners...');
                
                // Estrategia 1: onclick inline (más confiable en móviles)
                closeBtn.onclick = function(e) {
                    console.log('[Response Modal] onclick disparado');
                    e.preventDefault();
                    e.stopPropagation();
                    window.closeResponseReadyModal();
                    return false;
                };
                
                // Estrategia 2: addEventListener para click
                closeBtn.addEventListener('click', function(e) {
                    console.log('[Response Modal] click listener disparado');
                    e.preventDefault();
                    e.stopPropagation();
                    window.closeResponseReadyModal();
                }, { passive: false });
                
                // Estrategia 3: touchend para móviles
                closeBtn.addEventListener('touchend', function(e) {
                    console.log('[Response Modal] touchend listener disparado');
                    e.preventDefault();
                    e.stopPropagation();
                    window.closeResponseReadyModal();
                }, { passive: false });
                
                // Hacer el botón más accesible al touch
                closeBtn.style.cursor = 'pointer';
                closeBtn.style.userSelect = 'none';
                closeBtn.style.webkitTapHighlightColor = 'transparent';
            }
            
            // Cerrar al hacer click fuera del modal
            const modal = parentDoc.getElementById('response-ready-modal');
            if (modal) {
                modal.addEventListener('click', function(event) {
                    if (event.target.id === 'response-ready-modal') {
                        console.log('[Response Modal] Click fuera del modal');
                        window.closeResponseReadyModal();
                    }
                });
            }
        }
        
        function showResponseReadyModal() {
            const parentDoc = window.parent.document;
            const modal = parentDoc.getElementById('response-ready-modal');
            if (modal) {
                modal.style.display = 'block';
            }
        }
        
        // Inyectar y mostrar modal después de un breve delay
        setTimeout(function() {
            injectResponseReadyModal();
            setTimeout(showResponseReadyModal, 300);
        }, 100);
    })();
    </script>
    """
    st.components.v1.html(response_ready_modal, height=0)
    
    # Animación de globos lenta
    st.balloons()
    st.markdown("""
    <style>
        /* Ralentizar animación de globos (clase interna de Streamlit) */
        div[data-testid="stBalloons"] > div > div {
            animation-duration: 24s !important; /* 9X más lento (Muy lento) */
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔬 Resultado del Análisis:")
    # Colorear las citas antes de mostrar
    colored_response = colorize_citations(response)
    # IMPORTANTE: Usar st.html() para renderizar HTML sin escapar (preserva todos los estilos)
    st.html(f'<div class="response-container" id="respuesta-gerard">{colored_response}</div>')
    
    # Badge de método según el utilizado
    method_badges = {
        'hybrid': '🎯 Híbrido',
        'faiss': '🔍 FAISS',
        'bm25': '📝 BM25'
    }
    method_badge = method_badges.get(search_method, '❓ Desconocido')
    
    # Estadísticas
    st.markdown(
        f'<div class="stats">'
        f'📊 Documentos analizados: {len(docs)} | '
        f'👤 Usuario: {user_name.upper()} | '
        f'🕐 Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | '
        f'⚡ Método: {method_badge}'
        f'</div>',
        unsafe_allow_html=True
    )
    
    # SEGUNDO SCROLL: Automático hacia el final de la respuesta
    scroll_placeholder_2 = st.empty()
    scroll_placeholder_2.markdown(
        """
        <script>
        (function() {
            function forceScrollToBottom() {
                try {
                    window.scrollTo({
                        top: document.body.scrollHeight,
                        behavior: 'smooth'
                    });
                } catch(e) {
                    console.error("Error en scroll final:", e);
                }
            }
            setTimeout(forceScrollToBottom, 300);
            setTimeout(forceScrollToBottom, 1000);
        })();
        </script>
        """,
        unsafe_allow_html=True
    )
    
    # Botón de descarga PDF
    if REPORTLAB_AVAILABLE and len(st.session_state.conversation_history) > 0:
        st.markdown("---")
        st.markdown("### 📥 Exportar Conversación")
        
        try:
            # Construir HTML de toda la conversación
            html_parts = []
            for entry in st.session_state.conversation_history:
                # Estilo específico solicitado para PDF: 
                # MAYUSCULA, AZUL OSCURO, ARIAL, INCLINADA, SUBRAYADA, NEGRILLA, FUENTE NUMERO 22
                html_parts.append(f'<p style="font-family: Arial, sans-serif; text-transform: uppercase; color: #00008B; font-style: italic; text-decoration: underline; font-weight: bold; font-size: 22pt; margin-bottom: 10px;">PREGUNTA ({entry["timestamp"]}):</p>')
                html_parts.append(f'<p style="font-family: Arial, sans-serif; font-size: 14pt; margin-bottom: 20px; color: #333;">{entry["query"]}</p>')
                html_parts.append(f'<p style="font-family: Arial, sans-serif; font-weight: bold; color: #2E7D32; font-size: 16pt; margin-top: 20px; margin-bottom: 10px;">RESPUESTA:</p>')
                # Aplicar colorización a la respuesta antes de exportar
                colored_response = colorize_citations(entry["response"])
                html_parts.append(f'<p>{colored_response}</p>')
                html_parts.append('<br/>')
            
            html_parts.append(f'<br/><p style="color: #28a745;">Usuario: {user_name.upper()}</p>')
            html_full = ''.join(html_parts)
            
            # Generar PDF
            pdf_bytes = generate_pdf_from_html_local(
                html_full,
                title_base=f"Consulta GERARD - {user_name.upper()}",
                user_name=user_name.upper()
            )
            
            # Nombre del archivo PDF
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
            safe_username = "".join(c for c in user_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            
            # Construir nombre con TODAS las preguntas
            question_parts = []
            for entry in st.session_state.conversation_history:
                clean_q = "".join(c for c in entry["query"] if c.isalnum() or c in (' ', '_', '-', '?')).strip()
                clean_q = clean_q.replace(' ', '_')
                if clean_q:
                    question_parts.append(clean_q)
            
            if question_parts:
                questions_str = "_".join(f"{q}?" for q in question_parts)
                pdf_filename = f"CONSULTA_DE_{safe_username}_{questions_str}_{timestamp_str}.pdf"
            else:
                pdf_filename = f"CONSULTA_DE_{safe_username}_{timestamp_str}.pdf"
            
            # Convertir bytes a base64 para JavaScript
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            
            # JavaScript para descarga
            download_js_template = """
            <script>
            var pdfDownloaded = false;
            
            // Inyectar modal en el documento padre
            function injectModalInParent() {
                const parentDoc = window.parent.document;
                
                // Verificar si ya existe el modal
                if (parentDoc.getElementById('pdf-modal')) {
                    return;
                }
                
                // Inyectar estilos en el head del documento padre
                const style = parentDoc.createElement('style');
                style.textContent = `
                    #pdf-modal {
                        display: none;
                        position: fixed;
                        z-index: 9999999;
                        left: 0;
                        top: 0;
                        width: 100%;
                        height: 100%;
                        background-color: rgba(0, 0, 0, 0.8);
                        animation: pdfModalFadeIn 0.3s;
                        overflow: auto;
                    }
                    #pdf-modal-content {
                        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
                        margin: 15% auto;
                        padding: 30px;
                        border: 3px solid #00ff41;
                        border-radius: 15px;
                        width: 90%;
                        max-width: 500px;
                        box-shadow: 0 8px 32px rgba(0, 255, 65, 0.3);
                        animation: pdfModalSlideDown 0.4s;
                        color: white;
                    }
                    #pdf-modal h2 {
                        color: #00ff41;
                        margin-top: 0;
                        text-align: center;
                        font-size: 24px;
                    }
                    #pdf-modal p {
                        font-size: 16px;
                        line-height: 1.6;
                        margin: 15px 0;
                    }
                    #pdf-modal .highlight {
                        color: #00d4ff;
                        font-weight: bold;
                    }
                    #pdf-modal-close {
                        background: linear-gradient(45deg, #00ff41, #00cc33);
                        color: #000;
                        border: none;
                        padding: 12px 30px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 16px;
                        font-weight: bold;
                        width: 100%;
                        margin-top: 20px;
                        transition: transform 0.2s;
                    }
                    #pdf-modal-close:hover {
                        transform: scale(1.05);
                    }
                    @keyframes pdfModalFadeIn {
                        from { opacity: 0; }
                        to { opacity: 1; }
                    }
                    @keyframes pdfModalSlideDown {
                        from { transform: translateY(-50px); opacity: 0; }
                        to { transform: translateY(0); opacity: 1; }
                    }
                    @media (max-width: 600px) {
                        #pdf-modal-content {
                            margin: 25% auto;
                            padding: 20px;
                            width: 85%;
                        }
                        #pdf-modal h2 {
                            font-size: 20px;
                        }
                        #pdf-modal p {
                            font-size: 14px;
                        }
                    }
                `;
                parentDoc.head.appendChild(style);
                
                // Crear el modal en el body del documento padre
                const modalDiv = parentDoc.createElement('div');
                modalDiv.id = 'pdf-modal';
                modalDiv.innerHTML = `
                    <div id="pdf-modal-content">
                        <h2>✅ ¡PDF Descargado!</h2>
                        <p>📄 Tu conversación completa ha sido descargada exitosamente.</p>
                        <p><strong>📱 Para encontrar tu archivo:</strong></p>
                        <p>🔹 <span class="highlight">Android:</span> Abre la app "Descargas" o "Archivos" → Busca en la carpeta "Download"</p>
                        <p>🔹 <span class="highlight">iPhone/iPad:</span> Abre la app "Archivos" → Toca "Descargas"</p>
                        <p>🔹 <span class="highlight">Computadora:</span> Revisa tu carpeta de Descargas</p>
                        <p style="text-align: center; color: #00ff41; margin-top: 20px;">💡 También puedes revisar las notificaciones de tu navegador</p>
                        <button id="pdf-modal-close">ENTENDIDO</button>
                    </div>
                `;
                parentDoc.body.appendChild(modalDiv);
                
                // Función para cerrar el modal
                window.closePdfModal = function() {
                    console.log('[PDF Modal] Cerrando modal...');
                    const modal = parentDoc.getElementById('pdf-modal');
                    if (modal) {
                        modal.remove(); // Eliminar completamente del DOM
                        console.log('[PDF Modal] Modal eliminado');
                    }
                };
                
                // Event listeners para el modal en el documento padre
                const closeBtn = parentDoc.getElementById('pdf-modal-close');
                if (closeBtn) {
                    console.log('[PDF Modal] Configurando event listeners...');
                    
                    // Estrategia 1: onclick inline (más confiable en móviles)
                    closeBtn.onclick = function(e) {
                        console.log('[PDF Modal] onclick disparado');
                        e.preventDefault();
                        e.stopPropagation();
                        window.closePdfModal();
                        return false;
                    };
                    
                    // Estrategia 2: addEventListener para click
                    closeBtn.addEventListener('click', function(e) {
                        console.log('[PDF Modal] click listener disparado');
                        e.preventDefault();
                        e.stopPropagation();
                        window.closePdfModal();
                    }, { passive: false });
                    
                    // Estrategia 3: touchend para móviles (específico para touch)
                    closeBtn.addEventListener('touchend', function(e) {
                        console.log('[PDF Modal] touchend listener disparado');
                        e.preventDefault();
                        e.stopPropagation();
                        window.closePdfModal();
                    }, { passive: false });
                    
                    // Hacer el botón más accesible al touch
                    closeBtn.style.cursor = 'pointer';
                    closeBtn.style.userSelect = 'none';
                    closeBtn.style.webkitTapHighlightColor = 'transparent';
                }
                
                // Cerrar al hacer click fuera del modal
                const modal = parentDoc.getElementById('pdf-modal');
                if (modal) {
                    modal.addEventListener('click', function(event) {
                        if (event.target.id === 'pdf-modal') {
                            console.log('[PDF Modal] Click fuera del modal');
                            window.closePdfModal();
                        }
                    });
                }
            }
            
            function showModal() {
                const parentDoc = window.parent.document;
                const modal = parentDoc.getElementById('pdf-modal');
                if (modal) {
                    modal.style.display = 'block';
                }
            }
            
            // Inyectar modal al cargar
            setTimeout(injectModalInParent, 100);
            
            window.addEventListener('DOMContentLoaded', function() {
                const btn = document.getElementById('pdf-download-btn');
                if (sessionStorage.getItem('pdfDownloaded_NUM_CONSULTAS') === 'true') {
                    if (btn) {
                        btn.style.background = 'linear-gradient(45deg, #00FF41, #00CC33)';
                        btn.style.borderColor = '#00FF41';
                        btn.innerHTML = '✅ ¡Descargado Exitosamente!';
                        pdfDownloaded = true;
                    }
                }
            });
            
            function downloadPDF() {
                if (pdfDownloaded) return;
                
                // Scroll automático para hacer visible el botón completo
                const btn = document.getElementById('pdf-download-btn');
                if (btn) {
                    btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                try {
                    const byteCharacters = atob('PDF_B64_PLACEHOLDER');
                    const byteNumbers = new Array(byteCharacters.length);
                    for (let i = 0; i < byteCharacters.length; i++) {
                        byteNumbers[i] = byteCharacters.charCodeAt(i);
                    }
                    const byteArray = new Uint8Array(byteNumbers);
                    const blob = new Blob([byteArray], {type: 'application/pdf'});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'PDF_FILENAME_PLACEHOLDER';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    // Cambiar botón a verde con un pequeño delay para que se vea el scroll
                    setTimeout(function() {
                        if (btn) {
                            btn.style.background = 'linear-gradient(45deg, #00FF41, #00CC33)';
                            btn.style.borderColor = '#00FF41';
                            btn.innerHTML = '✅ ¡Descargado Exitosamente!';
                            pdfDownloaded = true;
                            sessionStorage.setItem('pdfDownloaded_NUM_CONSULTAS', 'true');
                        }
                        
                        // Mostrar modal después de cambiar el botón
                        setTimeout(function() {
                            showModal();
                        }, 300);
                    }, 500);
                    
                } catch (e) {
                    console.error('Error en descarga:', e);
                    alert('❌ Error al descargar PDF. Por favor, inténtalo nuevamente.');
                }
            }
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
                margin: 10px 0 30px 0;
            ">📥 DESCARGAR CONVERSACIÓN COMPLETA (PDF)</button>
            """
            
            # Reemplazar placeholders
            download_html = download_js_template.replace('PDF_B64_PLACEHOLDER', pdf_b64).replace('PDF_FILENAME_PLACEHOLDER', pdf_filename).replace('NUM_CONSULTAS', str(len(st.session_state.conversation_history)))
            st.components.v1.html(download_html, height=150)
            
        except Exception as e:
            st.error(f"Error generando PDF: {e}")

    # Botón Nueva Consulta
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("➕ NUEVA CONSULTA", key="new_query_btn_result", use_container_width=True):
            # Resetear estados para nueva consulta (Limpieza TOTAL)
            st.session_state.question_executed = False
            st.session_state.trigger_search = False
            st.session_state.last_executed_query = ""
            st.session_state.clear_query = True
            st.session_state.last_query = ""
            
            # Scroll to top
            st.components.v1.html("""
                <script>
                window.parent.document.querySelector('.main').scrollTo({top: 0, behavior: 'smooth'});
                </script>
            """, height=0)
            st.rerun()

if 'clear_query' not in st.session_state:
    st.session_state.clear_query = False

# Solo mostrar el resto SI hay nombre de usuario
if user_name:
    # Cargar animación question.json
    import json
    import os
    
    question_lottie_path = os.path.join("assets", "question.json")
    try:
        with open(question_lottie_path, 'r', encoding='utf-8') as f:
            question_animation_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error cargando question.json: {e}")
        question_animation_data = {}
    
    # Inyectar animación question overlay (solo si no se ha mostrado antes)
    if question_animation_data and 'question_animation_shown' not in st.session_state:
        st.session_state.question_animation_shown = True
        
        question_injector_html = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js"></script>
            <script>
                (function() {{
                    const animationData = {json.dumps(question_animation_data)};
                    let questionAnimation = null;
                    
                    function injectQuestionOverlay() {{
                        if (typeof lottie === 'undefined') {{
                            setTimeout(injectQuestionOverlay, 100);
                            return;
                        }}
                        
                        const targetDoc = window.top.document;
                        
                        if (targetDoc.getElementById('question-overlay')) {{
                            return;
                        }}
                        
                        const overlay = targetDoc.createElement('div');
                        overlay.id = 'question-overlay';
                        overlay.style.cssText = `
                            display: flex;
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100vw;
                            height: 100vh;
                            background: rgba(0, 0, 0, 0.7);
                            z-index: 999999;
                            justify-content: center;
                            align-items: center;
                        `;
                        
                        const container = targetDoc.createElement('div');
                        container.id = 'question-container';
                        container.style.cssText = `
                            width: 400px;
                            height: 400px;
                        `;
                        
                        overlay.appendChild(container);
                        targetDoc.body.appendChild(overlay);
                        
                        try {{
                            questionAnimation = lottie.loadAnimation({{
                                container: container,
                                renderer: 'svg',
                                loop: false,
                                autoplay: false,
                                animationData: animationData
                            }});
                            
                            questionAnimation.addEventListener('complete', function() {{
                                targetDoc.getElementById('question-overlay').style.display = 'none';
                            }});
                            
                            // Mostrar y reproducir automáticamente
                            questionAnimation.play();
                            
                        }} catch (error) {{
                            console.error('[ERROR] Error con animación question:', error);
                        }}
                    }}
                    
                    setTimeout(injectQuestionOverlay, 300);
                }})();
            </script>
        </body>
        </html>
        """
        
        st.components.v1.html(question_injector_html, height=0)
    
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
    
    # CSS para estilizar el campo de pregunta
    st.markdown("""
    <style>
        /* Estilizar el textarea de la pregunta */
        div[data-testid="stTextArea"] textarea {
            color: #00ff41 !important;
            font-size: 18px !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
        }
        
        /* Estilizar el placeholder también */
        div[data-testid="stTextArea"] textarea::placeholder {
            color: #00ff41 !important;
            opacity: 0.6 !important;
            text-transform: uppercase !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
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
    
    # Inicializar estado de ejecución si no existe
    if 'question_executed' not in st.session_state:
        st.session_state.question_executed = False
        st.session_state.last_executed_query = ""

    # Inicializar trigger de búsqueda diferida (para permitir rerun inmediato)
    if 'trigger_search' not in st.session_state:
        st.session_state.trigger_search = False
    
    # RESET AUTOMÁTICO: Si la consulta cambia, volver a estado normal
    # Comparamos la consulta actual con la última ejecutada
    if query != st.session_state.last_executed_query:
        st.session_state.question_executed = False
        st.session_state.trigger_search = False # Cancelar búsqueda pendiente si cambia query
    
    # Determinar texto y marcador del botón
    button_label = "🚀 EJECUTAR PREGUNTA"
    
    # Botón de consulta centrado
    # Usamos columnas vacías a los lados para centrar el botón
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        # Si ya se ejecutó, inyectamos el marcador invisible que activa el CSS rojo
        if st.session_state.question_executed:
            st.markdown('<div class="executed-marker" style="display:none;"></div>', unsafe_allow_html=True)
            button_label = "🔴 PREGUNTA EJECUTADA"
            
        search_button = st.button(button_label, use_container_width=True)
        
        # Si se presiona el botón:
        # 1. Cambiar estado visual a ROJO inmediatamente
        # 2. Activar trigger de búsqueda para la siguiente recarga
        # 3. Recargar la página (RERUN) para mostrar el botón rojo ANTES de procesar
        if search_button:
            st.session_state.question_executed = True
            st.session_state.last_executed_query = query
            st.session_state.trigger_search = True
            st.rerun()
    
    # Procesar consulta (Si se activó el trigger en la recarga anterior)
    if st.session_state.trigger_search and query:
        # Desactivar trigger para evitar bucles, pero mantenemos question_executed
        st.session_state.trigger_search = False
        
        # Cargar y mostrar animación Data Scanning
        import json
        import os
        
        data_scanning_path = os.path.join("assets", "Data Scanning.json")
        try:
            with open(data_scanning_path, 'r', encoding='utf-8') as f:
                scanning_animation_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Error cargando Data Scanning.json: {e}")
            scanning_animation_data = {}
        
        # Inyectar animación Data Scanning overlay
        if scanning_animation_data:
            scanning_injector_html = f"""
            <!DOCTYPE html>
            <html>
            <body>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js"></script>
                <script>
                    (function() {{
                        const animationData = {json.dumps(scanning_animation_data)};
                        let scanningAnimation = null;
                        
                        function injectScanningOverlay() {{
                            if (typeof lottie === 'undefined') {{
                                setTimeout(injectScanningOverlay, 100);
                                return;
                            }}
                            
                            const targetDoc = window.top.document;
                            
                            // Limpiar overlay anterior si existe
                            const oldOverlay = targetDoc.getElementById('scanning-overlay');
                            if (oldOverlay) {{
                                oldOverlay.remove();
                            }}
                            
                            const overlay = targetDoc.createElement('div');
                            overlay.id = 'scanning-overlay';
                            overlay.style.cssText = `
                                display: flex;
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100vw;
                                height: 100vh;
                                background: rgba(0, 0, 0, 0.5);
                                z-index: 999999;
                                justify-content: center;
                                align-items: center;
                                pointer-events: none;
                                touch-action: auto;
                                overflow: hidden;
                            `;
                            
                            const container = targetDoc.createElement('div');
                            container.id = 'scanning-container';
                            container.style.cssText = `
                                width: 400px;
                                height: 400px;
                                pointer-events: none;
                            `;
                            
                            overlay.appendChild(container);
                            targetDoc.body.appendChild(overlay);
                            
                            try {{
                                scanningAnimation = lottie.loadAnimation({{
                                    container: container,
                                    renderer: 'svg',
                                    loop: true,
                                    autoplay: true,
                                    animationData: animationData
                                }});
                                
                                // Función global para ocultar la animación
                                window.top.hideScanningAnimation = function() {{
                                    const ovl = targetDoc.getElementById('scanning-overlay');
                                    if (ovl) {{
                                        ovl.remove();
                                    }}
                                }};
                                
                            }} catch (error) {{
                                console.error('[ERROR] Error con animación scanning:', error);
                            }}
                        }}
                        
                        setTimeout(injectScanningOverlay, 100);
                    }})();
                </script>
            </body>
            </html>
            """
            
            st.components.v1.html(scanning_injector_html, height=0)
        
        # Mostrar GIF de búsqueda (opcional, puedes comentar esto si solo quieres la animación Lottie)
        # st.markdown('<div class="gif-container">', unsafe_allow_html=True)
        # if os.path.exists("assets/ovni.gif"):
        #     st.image("assets/ovni.gif", width=300)
        # st.markdown('</div>', unsafe_allow_html=True)
        
        st.info(f"🔄 Procesando consulta de **{user_name.upper()}**...")
        
        # PRIMER SCROLL: Hacia el spinner (30% de la página)
        scroll_placeholder_1 = st.empty()
        scroll_placeholder_1.markdown(
            """
            <script>
            (function() {
                try {
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
        
        # Contenedor para descripción dinámica
        description_placeholder = st.empty()
        
        # Variables para métricas
        search_start_time = datetime.now()
        
        try:
            # 1. Búsqueda de documentos
            with st.spinner("🔍 Buscando información relevante..."):
                # NUEVO: Detectar si la pregunta menciona un título específico
                title_info = detect_title_in_query(query)
                
                if title_info['has_title']:
                    # Búsqueda con filtro por título
                    print(f"[INFO] 🎯 Búsqueda híbrida con filtro de título activada")
                    print(f"[INFO] Keywords detectadas: {title_info['keywords']}")
                    print(f"[INFO] Patrón detectado: {title_info['pattern_matched']}")
                    
                    # Determinar K según complejidad de la pregunta
                    k_optimal = get_optimal_k(query, force_exhaustive=exhaustive_search)
                    
                    # Usar búsqueda híbrida con filtro por título
                    docs = hybrid_search_with_title(
                        faiss_vs=faiss_vs,
                        query=query,
                        all_docs=st.session_state.all_docs if 'all_docs' in st.session_state else [],
                        k=k_optimal['k'],
                        title_keywords=title_info['keywords']
                    )
                    
                    search_method = 'hybrid_title_filter'
                    
                    # Mostrar información de debug en consola
                    print(f"[INFO] Documentos recuperados con filtro: {len(docs)}")
                    if len(docs) > 0:
                        print(f"[INFO] Primer documento source: {docs[0].metadata.get('source', 'N/A')[:100]}")
                    
                else:
                    # Búsqueda normal sin filtro de título
                    print(f"[INFO] 📊 Búsqueda híbrida estándar (sin filtro de título)")
                    
                    # Determinar método de búsqueda
                    search_method = 'hybrid'
                    
                    # Obtener retriever
                    if exhaustive_search:
                        # Modo exhaustivo: Híbrido con más documentos (Quirúrgico)
                        # Usa HybridRetriever.build para crear la instancia de forma segura
                        retriever = HybridRetriever.build(
                            faiss_retriever=faiss_vs.as_retriever(search_kwargs={"k": 200}),
                            documents=st.session_state.all_docs if 'all_docs' in st.session_state else None,
                            k=200,
                            alpha=0.6 
                        )
                        search_method = 'hybrid_surgical'
                    else:
                        # Modo normal: Híbrido estándar
                        retriever = HybridRetriever.build(
                            faiss_retriever=faiss_vs.as_retriever(search_kwargs={"k": 100}),
                            documents=st.session_state.all_docs if 'all_docs' in st.session_state else None,
                            k=100
                        )
                    
                    # Ejecutar búsqueda
                    docs = retriever.invoke(query)
                
                # Filtrar por umbral de relevancia (simulado)
                relevant_docs = docs 
                
                search_end_time = datetime.now()
                search_time = (search_end_time - search_start_time).total_seconds()
            
            # Badge de método según el utilizado
            method_badges = {
                'hybrid': '🎯 Híbrido',
                'hybrid_surgical': '🧬 Híbrida Quirúrgica',
                'hybrid_title_filter': '📑 Híbrida con Filtro de Título',
                'faiss': '🔍 FAISS',
                'faiss_exhaustive': '🚀 FAISS (Exhaustivo)',
                'bm25': '📝 BM25'
            }
            method_badge = method_badges.get(search_method, '❓ Desconocido')
            
            # Mostrar métricas de búsqueda
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
            
            with st.spinner(""):
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
            # PROCESAMIENTO FINAL Y PERSISTENCIA
            # ═══════════════════════════════════════════════════════════════
            
            # Calcular tiempo total
            query_end_time = datetime.now()
            total_time = (query_end_time - query_start_time).total_seconds()
            
            # Guardar en historial
            st.session_state.conversation_history.append({
                'timestamp': query_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                'user': user_name.upper(),
                'query': query,
                'response': response
            })
            
            # Limpiar descripción inmediatamente
            description_placeholder.empty()
            
            # Marcar para limpiar campo
            st.session_state.clear_query = True
            st.session_state.last_query = ""
            
            # LOGGING A GOOGLE SHEETS
            if st.session_state.sheets_logger:
                try:
                    interaction_id = str(uuid.uuid4())
                    
                    # Usar IP REAL detectada automáticamente al login
                    # Esta IP se detectó con JavaScript en el navegador del cliente
                    location_info = {
                        "city": st.session_state.get('user_city', 'Desconocida'),
                        "country": st.session_state.get('user_country', 'Desconocido'),
                        "ip": st.session_state.get('user_ip', 'No detectado')  # IP REAL
                    }
                    
                    # Detectar dispositivo (simplificado)
                    device_info = {"device_type": "Web", "browser": "Unknown", "os": "Unknown"}
                    
                    # Intentar detección de dispositivo si está disponible
                    if GOOGLE_SHEETS_AVAILABLE:
                        try:
                            if hasattr(st, "context") and hasattr(st.context, "headers"):
                                user_agent = st.context.headers.get("User-Agent", "Unknown")
                                device_detector = DeviceDetector()
                                device_info_full = device_detector.detect_from_web(user_agent)
                                device_info = {
                                    "device_type": device_info_full.get("tipo", "Web"),
                                    "browser": device_info_full.get("navegador", "Unknown"),
                                    "os": device_info_full.get("os", "Unknown")
                                }
                        except Exception:
                            pass

                    # Limpiar respuesta (solo para otros usos, NO para Sheets)
                    answer_clean = _strip_html_tags(response)
                    
                    if st.session_state.sheets_logger.enabled:
                        user_email_value = st.session_state.get('user_email', 'No disponible')
                        print(f"[DEBUG] Email al guardar en Sheets: '{user_email_value}'")  # Debuggear
                        
                        st.session_state.sheets_logger.log_interaction(
                            interaction_id=interaction_id,
                            user=user_name.upper(),
                            question=query,
                            answer=response,  # ← CAMBIADO: Pasar HTML con colores, NO answer_clean
                            device_info=device_info,
                            location_info=location_info,
                            timing={"total_time": total_time},
                            success=True,
                            user_email=user_email_value  # ← AGREGADO: Email
                        )
                except Exception as e_log:
                    print(f"Error logging: {e_log}")

            # GUARDAR RESULTADOS PARA VISUALIZACIÓN PERSISTENTE
            st.session_state.last_results = {
                'response': response,
                'docs': docs,
                'search_time': search_time,
                'search_method': search_method,
                'relevant_docs_count': len(relevant_docs)
            }
            
            # MARCAR COMO EJECUTADO Y RECARGAR
            st.session_state.question_executed = True
            st.session_state.last_executed_query = query
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error durante el análisis: {str(e)}")

    # MOSTRAR RESULTADOS PERSISTENTES (Fuera del if search_button)
    if st.session_state.question_executed and query and query == st.session_state.last_executed_query and 'last_results' in st.session_state:
        res = st.session_state.last_results
        display_analysis_result(
            res['response'], 
            res['docs'], 
            res['search_time'], 
            res['search_method'], 
            res['relevant_docs_count'], 
            user_name
        )

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
