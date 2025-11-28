import streamlit as st

st.set_page_config(
    page_title="Términos de Servicio - GERARD",
    page_icon="📜",
    layout="wide"
)

st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #61AFEF;
        font-size: 2.5em;
        margin-bottom: 20px;
    }
    .section-title {
        color: #E5C07B;
        font-size: 1.8em;
        margin-top: 30px;
        margin-bottom: 15px;
        border-bottom: 2px solid #E5C07B;
        padding-bottom: 10px;
    }
    .content {
        font-size: 1.1em;
        line-height: 1.8;
        color: #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📜 Términos de Servicio</h1>', unsafe_allow_html=True)

st.markdown(f"""
<div class="content">
<p><strong>Última actualización:</strong> {st.session_state.get('current_date', '28 de noviembre de 2024')}</p>

<h2 class="section-title">1. Aceptación de los Términos</h2>

<p>Al acceder y utilizar GERARD (Agente Analítico Forense), aceptas estar legalmente vinculado por estos Términos de Servicio. Si no estás de acuerdo, no utilices esta aplicación.</p>

<h2 class="section-title">2. Descripción del Servicio</h2>

<p>GERARD es un asistente de inteligencia artificial especializado en:</p>
<ul>
    <li>Búsqueda semántica en base de datos de archivos de subtítulos (.srt)</li>
    <li>Extracción de información textual con referencias precisas</li>
    <li>Análisis de contenido con timestamps exactos</li>
    <li>Consultas sobre enseñanzas espirituales específicas</li>
</ul>

<h2 class="section-title">3. Registro y Acceso</h2>

<h3>3.1 Autenticación</h3>
<p>Puedes acceder mediante:</p>
<ul>
    <li><strong>Google OAuth:</strong> Inicio de sesión con tu cuenta de Google</li>
    <li><strong>Ingreso Manual:</strong> Proporcionando nombre, ciudad y país</li>
</ul>

<h3>3.2 Responsabilidad del Usuario</h3>
<p>Eres responsable de:</p>
<ul>
    <li>Mantener la confidencialidad de tu cuenta</li>
    <li>Todas las actividades bajo tu cuenta</li>
    <li>Notificar inmediatamente cualquier uso no autorizado</li>
</ul>

<h2 class="section-title">4. Uso Aceptable</h2>

<h3>4.1 Usos Permitidos</h3>
<p>Puedes usar GERARD para:</p>
<ul>
    <li>Realizar consultas legítimas sobre el contenido indexado</li>
    <li>Investigación personal y estudio</li>
    <li>Búsqueda de referencias específicas en las enseñanzas</li>
</ul>

<h3>4.2 Usos Prohibidos</h3>
<p>NO puedes:</p>
<ul>
    <li>Usar el servicio para actividades ilegales</li>
    <li>Intentar acceder a datos no autorizados</li>
    <li>Realizar ingeniería inversa del sistema</li>
    <li>Abusar del servicio con consultas automatizadas masivas</li>
    <li>Redistribuir o revender el acceso al servicio</li>
    <li>Usar el servicio para spam o phishing</li>
</ul>

<h2 class="section-title">5. Propiedad Intelectual</h2>

<h3>5.1 Contenido del Servicio</h3>
<p>El contenido indexado (transcripciones, análisis) pertenece a sus respectivos creadores. GERARD solo proporciona acceso organizado a información ya pública.</p>

<h3>5.2 Tecnología</h3>
<p>El código, diseño y tecnología de GERARD están protegidos por derechos de autor y son propiedad de sus desarrolladores.</p>

<h2 class="section-title">6. Limitaciones de Responsabilidad</h2>

<p><strong>GERARD se proporciona "TAL CUAL" sin garantías de ningún tipo.</strong></p>

<h3>6.1 No Garantizamos</h3>
<ul>
    <li>Disponibilidad ininterrumpida del servicio</li>
    <li>Ausencia de errores o bugs</li>
    <li>Exactitud absoluta de las respuestas generadas por IA</li>
    <li>Que el servicio cumpla todos tus requisitos específicos</li>
</ul>

<h3>6.2 Exención de Responsabilidad</h3>
<p>No somos responsables de:</p>
<ul>
    <li>Pérdida de datos</li>
    <li>Daños directos o indirectos derivados del uso</li>
    <li>Decisiones tomadas basándose en información de GERARD</li>
    <li>Interrupciones del servicio por motivos técnicos o de mantenimiento</li>
</ul>

<h2 class="section-title">7. Privacidad y Datos</h2>

<p>El manejo de tus datos personales se rige por nuestra <a href="/privacy_policy" style="color: #61AFEF;">Política de Privacidad</a>.</p>

<p>Resumen:</p>
<ul>
    <li>Recopilamos solo datos necesarios para el funcionamiento</li>
    <li>No vendemos ni compartimos información personal</li>
    <li>Puedes solicitar eliminación de datos</li>
</ul>

<h2 class="section-title">8. Modificaciones del Servicio</h2>

<p>Nos reservamos el derecho de:</p>
<ul>
    <li>Modificar o discontinuar el servicio en cualquier momento</li>
    <li>Cambiar características sin previo aviso</li>
    <li>Actualizar estos términos (se notificará en la app)</li>
</ul>

<h2 class="section-title">9. Terminación</h2>

<h3>9.1 Por tu Parte</h3>
<p>Puedes dejar de usar GERARD en cualquier momento.</p>

<h3>9.2 Por Nuestra Parte</h3>
<p>Podemos suspender o terminar tu acceso si:</p>
<ul>
    <li>Violas estos Términos de Servicio</li>
    <li>Abusas del sistema</li>
    <li>Realizas actividades ilegales</li>
</ul>

<h2 class="section-title">10. Ley Aplicable</h2>

<p>Estos términos se rigen por las leyes de Costa Rica. Cualquier disputa se resolverá en los tribunales competentes de Costa Rica.</p>

<h2 class="section-title">11. Contacto</h2>

<p>Para preguntas sobre estos términos:</p>
<ul>
    <li><strong>Email:</strong> arguellosolanogerardo@gmail.com</li>
    <li><strong>Aplicación:</strong> GERARD - Asistente Analítico Forense</li>
</ul>

<h2 class="section-title">12. Disposiciones Generales</h2>

<h3>12.1 Integridad del Acuerdo</h3>
<p>Estos términos constituyen el acuerdo completo entre tú y GERARD.</p>

<h3>12.2 Divisibilidad</h3>
<p>Si alguna disposición es inválida, las demás seguirán vigentes.</p>

<h3>12.3 No Renuncia</h3>
<p>El no ejercer un derecho no constituye renuncia al mismo.</p>

<hr style="margin: 40px 0; border: 1px solid #61AFEF;">

<p style="text-align: center; color: #98C379; font-size: 1.2em;">
    <strong>Al usar GERARD, confirmas que has leído, entendido y aceptado estos Términos de Servicio.</strong>
</p>

</div>
""", unsafe_allow_html=True)

# Botón para volver
if st.button("⬅️ Volver a la aplicación principal"):
    st.switch_page("app_gerard.py")
