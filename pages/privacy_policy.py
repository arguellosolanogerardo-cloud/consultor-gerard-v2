import streamlit as st

st.set_page_config(
    page_title="Política de Privacidad - GERARD",
    page_icon="🔒",
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

st.markdown('<h1 class="main-title">🔒 Política de Privacidad</h1>', unsafe_allow_html=True)

st.markdown(f"""
<div class="content">
<p><strong>Última actualización:</strong> {st.session_state.get('current_date', '28 de noviembre de 2024')}</p>

<h2 class="section-title">1. Información que Recopilamos</h2>

<h3>1.1 Información de Autenticación con Google</h3>
<p>Cuando inicias sesión con Google, recopilamos:</p>
<ul>
    <li>Tu nombre completo</li>
    <li>Tu dirección de correo electrónico</li>
    <li>Tu foto de perfil (si está disponible)</li>
</ul>

<h3>1.2 Información de Uso</h3>
<p>Registramos:</p>
<ul>
    <li>Consultas realizadas al sistema</li>
    <li>Fecha y hora de acceso</li>
    <li>Ciudad y país (si se proporciona manualmente o se autoriza detección)</li>
    <li>Tipo de dispositivo (móvil/escritorio)</li>
</ul>

<h2 class="section-title">2. Cómo Usamos tu Información</h2>

<p>Utilizamos la información recopilada para:</p>
<ul>
    <li><strong>Autenticación:</strong> Verificar tu identidad y permitir acceso seguro</li>
    <li><strong>Personalización:</strong> Mejorar tu experiencia de usuario</li>
    <li><strong>Análisis:</strong> Entender patrones de uso y mejorar el servicio</li>
    <li><strong>Registro:</strong> Mantener logs de Google Sheets para análisis estadístico</li>
</ul>

<h2 class="section-title">3. Compartir Información</h2>

<p><strong>NO compartimos, vendemos ni alquilamos tu información personal a terceros.</strong></p>

<p>Tu información solo se almacena en:</p>
<ul>
    <li>Google Sheets (para logs de uso interno)</li>
    <li>Streamlit Cloud (infraestructura de hosting)</li>
    <li>Google Cloud Platform (para servicios de autenticación y procesamiento)</li>
</ul>

<h2 class="section-title">4. Seguridad de los Datos</h2>

<p>Implementamos medidas de seguridad técnicas y organizativas para proteger tu información:</p>
<ul>
    <li>Conexiones HTTPS cifradas</li>
    <li>Autenticación OAuth 2.0 con Google</li>
    <li>Secrets encriptados en Streamlit Cloud</li>
    <li>Acceso restringido a datos sensibles</li>
</ul>

<h2 class="section-title">5. Retención de Datos</h2>

<p>Conservamos tus datos mientras:</p>
<ul>
    <li>Mantengas una cuenta activa</li>
    <li>Sea necesario para proporcionar servicios</li>
    <li>Sea requerido por ley</li>
</ul>

<p>Puedes solicitar la eliminación de tus datos en cualquier momento contactando a: 
<strong>arguellosolanogerardo@gmail.com</strong></p>

<h2 class="section-title">6. Cookies y Tecnologías Similares</h2>

<p>Utilizamos session storage y cookies de sesión de Streamlit para:</p>
<ul>
    <li>Mantener tu sesión activa</li>
    <li>Recordar tus preferencias durante la sesión</li>
    <li>Mejorar el rendimiento de la aplicación</li>
</ul>

<h2 class="section-title">7. Tus Derechos</h2>

<p>Tienes derecho a:</p>
<ul>
    <li><strong>Acceder</strong> a tu información personal</li>
    <li><strong>Rectificar</strong> datos incorrectos</li>
    <li><strong>Eliminar</strong> tu información</li>
    <li><strong>Oponerte</strong> al procesamiento de datos</li>
    <li><strong>Portabilidad</strong> de tus datos</li>
</ul>

<h2 class="section-title">8. Cambios a esta Política</h2>

<p>Podemos actualizar esta política ocasionalmente. Te notificaremos de cambios significativos mediante:</p>
<ul>
    <li>Actualización de la fecha "Última actualización"</li>
    <li>Aviso en la aplicación</li>
</ul>

<h2 class="section-title">9. Contacto</h2>

<p>Para preguntas sobre esta política de privacidad:</p>
<ul>
    <li><strong>Email:</strong> arguellosolanogerardo@gmail.com</li>
    <li><strong>Aplicación:</strong> GERARD - Asistente Analítico Forense</li>
</ul>

<hr style="margin: 40px 0; border: 1px solid #61AFEF;">

<p style="text-align: center; color: #98C379;">
    <strong>Al usar GERARD, aceptas esta Política de Privacidad.</strong>
</p>

</div>
""", unsafe_allow_html=True)

# Botón para volver
if st.button("⬅️ Volver a la aplicación principal"):
    st.switch_page("app_gerard.py")
