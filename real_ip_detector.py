"""
Detector de IP REAL - Solución MANUAL (única que funciona 100%)

Muestra IP detectada, usuario copia y pega manualmente.
Es un paso extra, pero GARANTIZA que funcione.
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_manual_confirmation():
    """
    Muestra widget que detecta IP y pide al usuario copiar/pegar.
    Es manual pero es la ÚNICA forma que funciona en Streamlit Cloud.
    """
    
    st.markdown("### 🌐 Confirma Tu Ubicación Real")
    st.info("📍 **Por qué esto es necesario:** Para obtener tu IP REAL (no la del servidor), necesitamos tu ayuda.")
    
    # Widget que detecta IP
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 25px;
                text-align: center;
                box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            }
            .title {
                font-size: 14px;
                color: #666;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .ip-display {
                background: #f0f0f0;
                border: 2px dashed #667eea;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
            }
            .ip-value {
                font-size: 32px;
                font-weight: bold;
                color: #667eea;
                font-family: 'Courier New', monospace;
                letter-spacing: 2px;
                margin: 10px 0;
                user-select: all;
            }
            .location-value {
                font-size: 18px;
                color: #555;
                margin: 8px 0;
                user-select: all;
            }
            .copy-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 6px;
                font-size: 16px;
                cursor: pointer;
                margin: 10px 5px;
                transition: all 0.3s;
            }
            .copy-btn:hover {
                background: #5568d3;
                transform: translateY(-2px);
            }
            .copy-btn:active {
                transform: translateY(0);
            }
            .loading {
                color: #667eea;
                font-size: 18px;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .instruction {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 12px;
                margin: 15px 0;
                border-radius: 4px;
                text-align: left;
                font-size: 14px;
                color: #856404;
            }
            .success {
                color: #10b981;
                font-size: 14px;
                margin-top: 10px;
                display: none;
            }
            .success.show {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="title">🌍 Tu Ubicación Real Detectada</div>
            <div id="status" class="loading">Detectando desde tu navegador...</div>
            <div id="content" style="display:none;">
                <div class="instruction">
                    ⚠️ <strong>IMPORTANTE:</strong> Copia estos datos y pégalos en los campos de abajo.
                </div>
                <div class="ip-display">
                    <div style="font-size: 12px; color: #999; margin-bottom: 5px;">IP PÚBLICA:</div>
                    <div id="ip" class="ip-value">-</div>
                    <button class="copy-btn" onclick="copyIP()">📋 Copiar IP</button>
                </div>
                <div class="ip-display">
                    <div style="font-size: 12px; color: #999; margin-bottom: 5px;">CIUDAD:</div>
                    <div id="city" class="location-value">-</div>
                    <button class="copy-btn" onclick="copyCity()">📋 Copiar Ciudad</button>
                </div>
                <div class="ip-display">
                    <div style="font-size: 12px; color: #999; margin-bottom: 5px;">PAÍS:</div>
                    <div id="country" class="location-value">-</div>
                    <button class="copy-btn" onclick="copyCountry()">📋 Copiar País</button>
                </div>
                <div id="successMsg" class="success">✓ Copiado al portapapeles</div>
            </div>
        </div>
        <script>
            let detectedData = { ip: '', city: '', country: '' };
            
            function showSuccess() {
                const msg = document.getElementById('successMsg');
                msg.classList.add('show');
                setTimeout(() => msg.classList.remove('show'), 2000);
            }
            
            function copyIP() {
                navigator.clipboard.writeText(detectedData.ip);
                showSuccess();
            }
            
            function copyCity() {
                navigator.clipboard.writeText(detectedData.city);
                showSuccess();
            }
            
            function copyCountry() {
                navigator.clipboard.writeText(detectedData.country);
                showSuccess();
            }
            
            (async function() {
                try {
                    const res = await fetch('https://ipapi.co/json/');
                    const data = await res.json();
                    
                    detectedData = {
                        ip: data.ip || 'No detectado',
                        city: data.city || 'Unknown',
                        country: data.country_name || data.country || 'Unknown'
                    };
                    
                    document.getElementById('status').style.display = 'none';
                    document.getElementById('content').style.display = 'block';
                    document.getElementById('ip').textContent = detectedData.ip;
                    document.getElementById('city').textContent = detectedData.city;
                    document.getElementById('country').textContent = detectedData.country;
                    
                } catch (e) {
                    document.getElementById('status').textContent = '❌ Error detectando IP';
                    document.getElementById('status').classList.remove('loading');
                }
            })();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=550)
    
    st.markdown("---")
    st.markdown("### 📝 Pega los Datos Aquí")
    
    # Campos para que usuario pegue manualmente
    col1, col2, col3 = st.columns(3)
    with col1:
        ip_input = st.text_input("🌐 IP Pública", placeholder="Pega aquí tu IP", key="manual_ip")
    with col2:
        city_input = st.text_input("🏙️ Ciudad", placeholder="Pega aquí tu ciudad", key="manual_city")
    with col3:
        country_input = st.text_input("🌍 País", placeholder="Pega aquí tu país", key="manual_country")
    
    # Botón para confirmar
    if st.button("✅ Confirmar Ubicación", type="primary", use_container_width=True):
        if ip_input and city_input and country_input:
            st.session_state.user_ip = ip_input
            st.session_state.user_city = city_input
            st.session_state.user_country = country_input
            st.session_state.real_ip_detected = True
            st.session_state.ip_needs_confirmation = False
            
            print(f"[INFO] ✅ IP REAL confirmada manualmente: {ip_input} | {city_input}, {country_input}")
            
            st.success(f"✅ Ubicación confirmada: {city_input}, {country_input} ({ip_input})")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Por favor completa todos los campos con los datos mostrados arriba.")
