"""
Detector de IP REAL - Versión que SÍ funciona en Streamlit Cloud

Muestra widget visual que detecta IP automáticamente.
Usuario solo hace clic en "Continuar" (no necesita copiar).
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_confirmation_widget():
    """
    Muestra widget que detecta IP automáticamente y pide confirmación simple.
    El usuario VE su IP detectada y hace clic en "Continuar".
    """
    
    st.markdown("### 🌐 Verificación de Ubicación")
    st.info("📍 Detectando tu ubicación real para analytics precisos...")
    
    # Widget HTML que detecta y muestra la IP
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .ip-card {
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                max-width: 500px;
                margin: 0 auto;
                text-align: center;
            }
            .ip-value {
                font-size: 28px;
                font-weight: bold;
                color: #667eea;
                margin: 15px 0;
                font-family: 'Courier New', monospace;
                padding: 10px;
                background: #f0f0f0;
                border-radius: 8px;
            }
            .location {
                font-size: 16px;
                color: #555;
                margin: 10px 0;
            }
            .loading {
                color: #667eea;
                font-size: 16px;
                animation: pulse 1.5s ease-in-out infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .icon {
                font-size: 48px;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="ip-card">
            <div class="icon">🌍</div>
            <div id="status" class="loading">Detectando tu IP...</div>
            <div id="ipValue" class="ip-value" style="display:none;">-</div>
            <div id="location" class="location" style="display:none;">-</div>
        </div>

        <script>
            (async function() {
                const statusDiv = document.getElementById('status');
                const ipDiv = document.getElementById('ipValue');
                const locDiv = document.getElementById('location');
                
                try {
                    const response = await fetch('https://ipapi.co/json/');
                    const data = await response.json();
                    
                    // Mostrar resultados
                    statusDiv.textContent = '✅ IP Detectada:';
                    statusDiv.classList.remove('loading');
                    statusDiv.style.color = '#10b981';
                    
                    ipDiv.textContent = data.ip || 'No detectado';
                    ipDiv.style.display = 'block';
                    
                    locDiv.textContent = '📍 ' + (data.city || 'Unknown') + ', ' + (data.country_name || data.country || 'Unknown');
                    locDiv.style.display = 'block';
                    
                    // Guardar en sessionStorage para que Streamlit lo lea
                    sessionStorage.setItem('detected_ip', data.ip || '');
                    sessionStorage.setItem('detected_city', data.city || '');
                    sessionStorage.setItem('detected_country', data.country_name || data.country || '');
                    
                } catch (error) {
                    statusDiv.textContent = '⚠️ No se pudo detectar automáticamente';
                    statusDiv.style.color = '#f59e0b';
                    ipDiv.textContent = 'Error de detección';
                    ipDiv.style.display = 'block';
                }
            })();
        </script>
    </body>
    </html>
    """
    
    # Mostrar widget
    components.html(html_code, height=250)
    
    st.markdown("---")
    
    # Botón para continuar (la IP ya fue detectada y mostrada)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ Continuar con Esta Ubicación", type="primary", use_container_width=True):
            # Leer de sessionStorage via JavaScript
            js_code = """
            <script>
                const ip = sessionStorage.getItem('detected_ip') || 'Proxy';
                const city = sessionStorage.getItem('detected_city') || 'Unknown';
                const country = sessionStorage.getItem('detected_country') || 'Unknown';
                
                // Enviar a Streamlit via query params
                const url = new URL(window.location.href);
                url.searchParams.set('confirmed_ip', ip);
                url.searchParams.set('confirmed_city', city);
                url.searchParams.set('confirmed_country', country);
                window.location.href = url.toString();
            </script>
            """
            components.html(js_code, height=0)
            return True
    
    return False


def process_confirmed_ip():
    """
    Procesa la IP confirmada que viene de query params.
    """
    if 'confirmed_ip' in st.query_params:
        st.session_state.user_ip = st.query_params.get('confirmed_ip', 'No detectado')
        st.session_state.user_city = st.query_params.get('confirmed_city', 'Unknown')
        st.session_state.user_country = st.query_params.get('confirmed_country', 'Unknown')
        st.session_state.real_ip_detected = True
        st.session_state.ip_needs_confirmation = False
        
        # Limpiar query params
        st.query_params.clear()
        
        print(f"[INFO] ✅ IP confirmada: {st.session_state.user_ip} | {st.session_state.user_city}, {st.session_state.user_country}")
        
        return True
    
    return False
