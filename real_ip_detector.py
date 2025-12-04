"""
Detector de IP REAL - Solución que SÍ FUNCIONA (sin redirect)

Usa formulario Streamlit con campos ocultos que JavaScript llena.
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_one_click():
    """
    Versión funcional: detecta IP, llena campos ocultos, botón envía formulario.
    Sin redirect - usa solo mecanismos nativos de Streamlit.
    """
    
    st.markdown("### 🌐 Confirma Tu Ubicación")
    
    # Widget que detecta y muestra SOLO el botón
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 20px;
                text-align: center;
            }
            .loading {
                color: #667eea;
                font-size: 16px;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .country-text {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin: 20px 0;
                display: none;
            }
            .country-text.show {
                display: block;
            }
        </style>
    </head>
    <body>
        <div id="loading" class="loading">Detectando...</div>
        <div id="countryText" class="country-text">-</div>
        <script>
            (async function() {
                try {
                    const res = await fetch('https://ipapi.co/json/');
                    const data = await res.json();
                    
                    // Guardar en localStorage
                    localStorage.setItem('detected_ip', data.ip || 'Proxy');
                    localStorage.setItem('detected_city', data.city || 'Unknown');
                    localStorage.setItem('detected_country', data.country_name || data.country || 'Unknown');
                    
                    // Mostrar país
                    document.getElementById('loading').style.display = 'none';
                    const countryDiv = document.getElementById('countryText');
                    countryDiv.textContent = (data.country_name || data.country || 'Unknown');
                    countryDiv.classList.add('show');
                    
                } catch (e) {
                    document.getElementById('loading').textContent = 'Error';
                }
            })();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=120)
    
    # Formulario Streamlit
    with st.form(key="ip_confirmation_form"):
        st.markdown("**¿Continuar desde este país?**")
        
        # Campo oculto que JavaScript llenará
        col1, col2, col3 = st.columns(3)
        with col1:
            ip_val = st.text_input("IP", key="hidden_ip", label_visibility="collapsed", placeholder="Detectando...")
        with col2:
            city_val = st.text_input("Ciudad", key="hidden_city", label_visibility="collapsed", placeholder="Detectando...")
        with col3:
            country_val = st.text_input("País", key="hidden_country", label_visibility="collapsed", placeholder="Detectando...")
        
        # Script para llenar campos desde localStorage
        st.markdown("""
        <script>
            setTimeout(function() {
                const ip = localStorage.getItem('detected_ip') || '';
                const city = localStorage.getItem('detected_city') || '';
                const country = localStorage.getItem('detected_country') || '';
                
                const inputs = parent.document.querySelectorAll('input[type="text"]');
                if (inputs.length >= 3) {
                    // Buscar los 3 últimos inputs (son los del formulario)
                    const startIdx = Math.max(0, inputs.length - 3);
                    if (inputs[startIdx]) inputs[startIdx].value = ip;
                    if (inputs[startIdx + 1]) inputs[startIdx + 1].value = city;
                    if (inputs[startIdx + 2]) inputs[startIdx + 2].value = country;
                    
                    // Trigger change events
                    for (let i = startIdx; i < inputs.length; i++) {
                        if (inputs[i]) {
                            inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                            inputs[i].dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }
                }
            }, 1000);
        </script>
        """, unsafe_allow_html=True)
        
        submitted = st.form_submit_button("✅ Confirmar", use_container_width=True, type="primary")
        
        if submitted:
            # Usar valores de los campos (que JavaScript llenó)
            st.session_state.user_ip = ip_val if ip_val else "Proxy"
            st.session_state.user_city = city_val if city_val else "Unknown"
            st.session_state.user_country = country_val if country_val else "Unknown"
            st.session_state.real_ip_detected = True
            st.session_state.ip_needs_confirmation = False
            
            print(f"[INFO] ✅ IP confirmada: {st.session_state.user_ip} | {st.session_state.user_city}, {st.session_state.user_country}")
            
            st.success(f"✅ Confirmado: {st.session_state.user_country}")
            st.rerun()
