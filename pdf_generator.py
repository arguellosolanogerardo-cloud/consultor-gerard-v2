
import io
import re
from datetime import datetime

# Intentar importar WeasyPrint
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("[WARNING] WeasyPrint no encontrado. Se usará ReportLab como fallback.")

# Importar ReportLab (Fallback)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

def generate_pdf_from_html(html_content, title_base="Consulta GERARD", user_name="Usuario"):
    """
    Genera un PDF profesional.
    Prioridad: WeasyPrint (CSS completo).
    Fallback: ReportLab (Estilos básicos).
    """
    
    # 1. Intentar WeasyPrint (Calidad Profesional)
    if WEASYPRINT_AVAILABLE:
        try:
            return _generate_weasyprint(html_content, title_base, user_name)
        except Exception as e:
            print(f"[ERROR] WeasyPrint falló: {e}. Intentando fallback...")
    
    # 2. Fallback a ReportLab
    return _generate_reportlab(html_content, title_base, user_name)

def _generate_weasyprint(html_content, title_base, user_name):
    """Generación con WeasyPrint (Soporte CSS completo)"""
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # CSS Profesional
    css_string = """
    @page {
        size: A4;
        margin: 2cm;
        @bottom-right {
            content: "Página " counter(page);
            font-family: 'Helvetica', sans-serif;
            font-size: 9pt;
        }
        @bottom-left {
            content: "Generado por Consultor GERARD";
            font-family: 'Helvetica', sans-serif;
            font-size: 9pt;
            color: #666;
        }
    }
    body {
        font-family: 'Helvetica', 'Arial', sans-serif;
        font-size: 11pt;
        line-height: 1.5;
        color: #333;
    }
    h1 {
        color: #1a237e; /* Azul oscuro */
        text-align: center;
        border-bottom: 2px solid #1a237e;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    h2 {
        color: #283593;
        margin-top: 20px;
        border-bottom: 1px solid #eee;
    }
    h3 {
        color: #303f9f;
        margin-top: 15px;
    }
    .meta-info {
        text-align: center;
        color: #666;
        font-size: 10pt;
        margin-bottom: 30px;
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 5px;
    }
    /* Colores específicos de la app */
    .quote-green { color: #28a745; font-weight: bold; }
    .link-blue { color: #007bff; text-decoration: none; }
    .alert-red { color: #dc3545; font-weight: bold; }
    
    /* Preservar estilos inline del HTML original */
    span[style*="color: #28a745"] { color: #28a745 !important; font-weight: bold; }
    span[style*="color: #007bff"] { color: #007bff !important; }
    span[style*="color: #dc3545"] { color: #dc3545 !important; }
    """
    
    # Preparar HTML completo
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title_base}</title>
    </head>
    <body>
        <h1>{title_base}</h1>
        <div class="meta-info">
            <b>Usuario:</b> {user_name} | <b>Fecha:</b> {date_str}
        </div>
        <div class="content">
            {html_content}
        </div>
    </body>
    </html>
    """
    
    # Generar PDF
    buffer = io.BytesIO()
    html = HTML(string=full_html)
    css = CSS(string=css_string)
    html.write_pdf(target=buffer, stylesheets=[css])
    
    buffer.seek(0)
    return buffer.getvalue()

def _generate_reportlab(html_content, title_base, user_name):
    """Generación con ReportLab (Fallback)"""
    # ... (Código ReportLab anterior como fallback) ...
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph(title_base, styles['Heading1']))
    story.append(Paragraph(f"Usuario: {user_name}", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Limpieza básica para ReportLab
    clean_text = re.sub(r'<[^>]+>', '', html_content).replace('\n', '<br/>')
    story.append(Paragraph(clean_text, styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

if __name__ == "__main__":
    print(f"WeasyPrint disponible: {WEASYPRINT_AVAILABLE}")
