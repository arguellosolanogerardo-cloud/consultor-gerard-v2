
import re
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER

def _clean_html_for_pdf(text):
    """
    Convierte HTML básico y estilos CSS inline a tags XML de ReportLab.
    Soporta:
    - Negritas (** o <b>)
    - Colores (span style="color:...")
    - Saltos de línea
    """
    if not text:
        return ""
    
    # 1. Reemplazar saltos de línea
    text = text.replace('\n', '<br/>')
    
    # 2. Reemplazar negritas markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    
    # 3. Convertir colores hexadecimales a tags <font color="...">
    # Mapeo de colores comunes en la app
    # Verde (Citas/Usuario)
    text = re.sub(r'<span[^>]*style="[^"]*color:\s*#28a745[^"]*"[^>]*>(.*?)</span>', r'<font color="#28a745">\1</font>', text, flags=re.IGNORECASE)
    # Azul (Enlaces/Títulos)
    text = re.sub(r'<span[^>]*style="[^"]*color:\s*#007bff[^"]*"[^>]*>(.*?)</span>', r'<font color="#007bff">\1</font>', text, flags=re.IGNORECASE)
    # Rojo (Alertas)
    text = re.sub(r'<span[^>]*style="[^"]*color:\s*#dc3545[^"]*"[^>]*>(.*?)</span>', r'<font color="#dc3545">\1</font>', text, flags=re.IGNORECASE)
    # Rosa/Magenta (Títulos especiales)
    text = re.sub(r'<span[^>]*style="[^"]*color:\s*#e83e8c[^"]*"[^>]*>(.*?)</span>', r'<font color="#e83e8c">\1</font>', text, flags=re.IGNORECASE)
    
    # 4. Limpiar otros tags HTML no soportados pero dejar el contenido
    # (Opcional: si hay tags que rompen el PDF, los quitamos aquí)
    
    return text

def generate_pdf_from_html(html_content, title_base="Consulta GERARD", user_name="Usuario"):
    """
    Genera un PDF profesional preservando estilos y colores.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
        title=title_base
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos Personalizados
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f2937'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    style_subtitle = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    style_body = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )
    
    story = []
    
    # 1. Encabezado
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Paragraph(title_base, style_title))
    story.append(Paragraph(f"Generado para: {user_name} | Fecha: {date_str}", style_subtitle))
    story.append(Spacer(1, 10))
    story.append(Paragraph("_" * 60, style_subtitle)) # Línea separadora
    story.append(Spacer(1, 20))
    
    # 2. Procesar Contenido
    # Dividimos por bloques para manejar mejor los párrafos
    # Asumimos que el contenido viene con <br/> o \n
    
    processed_html = _clean_html_for_pdf(html_content)
    
    # Dividir por <br/> para crear párrafos separados
    paragraphs = processed_html.split('<br/>')
    
    for p_text in paragraphs:
        if not p_text.strip():
            continue
            
        # Detectar si es un título (empieza con ### o similar en markdown, o tiene estilo de título)
        if p_text.strip().startswith('###'):
            # Título nivel 3
            clean_text = p_text.replace('###', '').strip()
            story.append(Paragraph(f"<b>{clean_text}</b>", styles['Heading3']))
        elif p_text.strip().startswith('##'):
             # Título nivel 2
            clean_text = p_text.replace('##', '').strip()
            story.append(Paragraph(f"<b>{clean_text}</b>", styles['Heading2']))
        elif p_text.strip().startswith('**') and p_text.strip().endswith('**'):
            # Posible subtítulo en negrita
            story.append(Paragraph(p_text, styles['Heading4']))
        else:
            # Párrafo normal
            try:
                story.append(Paragraph(p_text, style_body))
            except Exception as e:
                # Fallback si hay tags mal formados
                clean_text = re.sub(r'<[^>]+>', '', p_text)
                story.append(Paragraph(clean_text, style_body))
        
        story.append(Spacer(1, 6))

    # 3. Construir PDF
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"[ERROR PDF] {e}")
        return b""

if __name__ == "__main__":
    # Prueba local
    sample_html = """
    <h3>Título de Prueba</h3>
    <p>Esto es un texto normal.</p>
    <p>Esto es <span style="color: #28a745;">texto verde</span> y esto es **negrita**.</p>
    """
    pdf = generate_pdf_from_html(sample_html, "Prueba", "Tester")
    print(f"PDF generado: {len(pdf)} bytes")
