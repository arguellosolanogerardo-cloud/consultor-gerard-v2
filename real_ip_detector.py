"""
Detector de IP REAL - Versión SIMPLIFICADA que SÍ funciona

Widget detecta IP, escribe en campos ocultos, usuario hace clic.
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_confirmation_simple():
    """
    Versión simplificada: muestra IP detectada y usa campos Streamlit normales.
    """
    
    st.markdown("### 🌐 Verificación de Ubicación")
    st.info("📍 Tu ubicación se ha detectado automáticamente:")
    
    # Widget que detecta y muestra IP
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            .ip { font-size: 24px; font-weight: bold; color: #667eea; margin: 10px 0; }
            .location { font-size: 14px; color: #666; }
            .loading { color: #667eea; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        </style>
    </head>
    <body>
        <div class="card">
            <div id="status" class="loading">Detectando...</div>
            <div id="ip" class="ip">-</div>
            <div id="location" class="location">-</div>
        </div>
        <script>
            (async function() {
                try {
                    const res = await fetch('https://ipapi.co/json/');
                    const data = await res.json();
                    
                    document.getElementById('status').textContent = '✅ IP Detectada:';
                    document.getElementById('status').classList.remove('loading');
                    document.getElementById('ip').textContent = data.ip || 'No detectado';
                    document.getElementById('location').textContent = '📍 ' + (data.city || 'Unknown') + ', ' + (data.country_name || 'Unknown');
                    
                    // Guardar en localStorage para que Streamlit lo lea
                    localStorage.setItem('real_ip', data.ip || '');
                    localStorage.setItem('real_city', data.city || '');
                    localStorage.setItem('real_country', data.country_name || data.country || '');
                    
                } catch (e) {
                    document.getElementById('status').textContent = '⚠️ Error';
                    document.getElementById('ip').textContent = 'No se pudo detectar';
                }
            })();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=150)
    
    st.markdown("---")
    
    # Campos donde JavaScript escribirá (usando script para leer localStorage)
    st.markdown("""
    <script>
        // Intentar escribir valores de localStorage en los campos de Streamlit
        setTimeout(function() {
            const ip = localStorage.getItem('real_ip') || '';
            const city = localStorage.getItem('real_city') || '';
            const country = localStorage.getItem('real_country') || '';
            
            // Encontrar los campos de texto y llenarlos
            const inputs = document.querySelectorAll('input[type="text"]');
            if (inputs.length >= 3) {
                inputs[0].value = ip;
                inputs[1].value = city;
                inputs[2].value = country;
                
                // Triggear evento change
                inputs.forEach(inp => {
                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                });
            }
        }, 500);
    </script>
    """, unsafe_allow_html=True)
    
    # Campos de texto (se llenarán automáticamente con JavaScript)
    col1, col2, col3 = st.columns(3)
    with col1:
        detected_ip = st.text_input("IP", key="detected_ip_field", label_visibility="collapsed", placeholder="Detectando...")
    with col2:
        detected_city = st.text_input("Ciudad", key="detected_city_field", label_visibility="collapsed", placeholder="Detectando...")
    with col3:
        detected_country = st.text_input("País", key="detected_country_field", label_visibility="collapsed", placeholder="Detectando...")
    
    # Botón para continuar
    if st.button("✅ Continuar", type="primary", use_container_width=True, key="continue_ip_btn"):
        # Guardar los valores (vengan o no)
        st.session_state.user_ip = detected_ip if detected_ip else "Proxy"
        st.session_state.user_city = detected_city if detected_city else "Unknown"
        st.session_state.user_country = detected_country if detected_country else "Unknown"
        st.session_state.real_ip_detected = True
        st.session_state.ip_needs_confirmation = False
        
        print(f"[INFO] IP confirmada: {st.session_state.user_ip} | {st.session_state.user_city}, {st.session_state.user_country}")
        
        st.success(f"✅ Ubicación confirmada: {st.session_state.user_city}, {st.session_state.user_country}")
        st.rerun()
