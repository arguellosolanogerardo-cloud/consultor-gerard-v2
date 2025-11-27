import io
import re
from datetime import datetime

# Flag para verificar disponibilidad de reportlab
REPORTLAB_AVAILABLE = False
REPORTLAB_PLATYPUS = False

try:
    import reportlab
    REPORTLAB_AVAILABLE = True
    REPORTLAB_PLATYPUS = True
except ImportError:
    pass

def _escape_ampersand(text: str) -> str:
    """Escapa el símbolo & para XML"""
    return text.replace('&', '&amp;')

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
    Construye un encabezado que contiene el título, el nombre en negrita y la fecha, 
    limitado a max_len caracteres.
    """
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_name = (user_name or 'usuario').strip()
    plain = f"{title_base} - {user_name} {date_str}"
    
    # Aumentar límite de longitud para evitar cortes agresivos
    if len(plain) > max_len:
        # Intentar cortar solo si es extremadamente largo
        plain = plain[: max_len - 3].rstrip() + '...'
    
    # Para HTML, ponemos el nombre en negrita
    if user_name and user_name in plain:
        html = plain.replace(user_name, f"<b>{user_name}</b>", 1)
    else:
        html = plain
    
    return html, plain

def _strip_html_tags(html: str) -> str:
    """Elimina todas las etiquetas HTML"""
    return re.sub(r'<[^>]+>', '', html)

def generate_pdf_bytes_text(
    text: str, 
    title_base: str = "Documento GERARD", 
    user_name: str | None = None
) -> bytes:
    """
    Fallback simple: genera PDF plano a partir de texto sin formato.
    """
    if not REPORTLAB_AVAILABLE:
        return b""
    
    # Importar aquí para evitar errores si reportlab no está disponible
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase.pdfmetrics import stringWidth
    except ImportError:
        return b""

    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    
    left_margin = 40
    right_margin = 40
    top_margin = 40
    bottom_margin = 40
    
    # Header
    header_html, header_plain = _format_header(title_base, user_name, max_len=220)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, page_height - top_margin, header_plain)
    
    c.setFont("Helvetica", 10)
    max_width = page_width - left_margin - right_margin
    y = page_height - top_margin - 20
    line_height = 12
    
    # Procesar texto párrafo por párrafo
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

def generate_pdf_from_html(
    html_content: str, 
    title_base: str = "Conversacion GERARD", 
    user_name: str | None = None
) -> bytes:
    """
    Genera un PDF en memoria a partir de HTML simple.
    Completamente auto-contenido con todas las importaciones dentro.
    """
    if not REPORTLAB_AVAILABLE:
        # Fallback: generar PDF de texto simple
        return generate_pdf_bytes_text(
            _strip_html_tags(html_content), 
            title_base=title_base, 
            user_name=user_name
        )
    
    try:
        # Importar TODAS las dependencias aquí dentro
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import io
        
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
        header_html, header_plain = _format_header(title_base, user_name, max_len=220)
        title_style = styles.get('Heading2', normal)
        story.append(Paragraph(header_html, title_style))
        story.append(Spacer(1, 6))
        
        body = _convert_spans_to_font_tags(html_content)
        
        try:
            story.append(Paragraph(body, normal))
        except Exception:
            # Si falla el parsing HTML, usar texto plano
            plain = re.sub(r'<[^>]+>', '', html_content)
            story.append(Paragraph(plain.replace('&', '&amp;'), normal))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
        
    except Exception as e:
        # Si CUALQUIER cosa falla, usar fallback de texto
        print(f"[ERROR] PDF generation failed: {e}, using text fallback")
        return generate_pdf_bytes_text(
            _strip_html_tags(html_content), 
            title_base=title_base, 
            user_name=user_name
        )
