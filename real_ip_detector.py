"""
Detector de IP REAL - Solución con 1 SOLO CLIC

Widget detecta automáticamente, muestra, botón con texto del país.
1 clic → todo automático → IP REAL guardada.
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_one_click():
    """
    Widget que detecta IP, muestra info, 1 botón: "Continuar desde [PAÍS]?"
    Al hacer clic, redirige con query params y Streamlit captura.
    """
    
    # Procesar query params si vienen del redirect
    if 'confirmed_ip' in st.query_params:
        st.session_state.user_ip = st.query_params.get('confirmed_ip', 'Proxy')
        st.session_state.user_city = st.query_params.get('confirmed_city', 'Unknown')
        st.session_state.user_country = st.query_params.get('confirmed_country', 'Unknown')
        st.session_state.real_ip_detected = True
        st.session_state.ip_needs_confirmation = False
        
        # Limpiar query params
        st.query_params.clear()
        
        print(f"[INFO] ✅ IP REAL confirmada: {st.session_state.user_ip} | {st.session_state.user_city}, {st.session_state.user_country}")
        
        st.success(f"✅ Ubicación confirmada: {st.session_state.user_city}, {st.session_state.user_country}")
        st.rerun()
        return True
    
    # Si no hay query params, mostrar widget de confirmación
    st.markdown("### 🌐 Verificación de Ubicación")
    st.info("📍 Detectando tu ubicación real...")
    
    # Widget con detección automática y botón de confirmación
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
                padding: 30px;
                text-align: center;
                box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            }
            .icon { font-size: 48px; margin-bottom: 15px; }
            .status {
                font-size: 16px;
                color: #667eea;
                margin: 15px 0;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .info-box {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
            }
            .label {
                font-size: 12px;
                color: #999;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }
            .value {
                font-size: 20px;
                font-weight: bold;
                color: #333;
                margin: 5px 0;
            }
            .ip-value {
                font-size: 24px;
                color: #667eea;
                font-family: 'Courier New', monospace;
            }
            .btn-container {
                margin-top: 25px;
            }
            .confirm-btn {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 16px 32px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                display: none;
            }
            .confirm-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
            }
            .confirm-btn:active {
                transform: translateY(0);
            }
            .confirm-btn.show {
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">🌍</div>
            <div id="status" class="status">Detectando tu ubicación...</div>
            <div id="content" style="display:none;">
                <div class="info-box">
                    <div class="label">IP Pública</div>
                    <div id="ip" class="value ip-value">-</div>
                </div>
                <div class="info-box">
                    <div class="label">Ubicación Detectada</div>
                    <div id="location" class="value">-</div>
                </div>
                <div class="btn-container">
                    <button id="confirmBtn" class="confirm-btn" onclick="confirmLocation()">
                        -
                    </button>
                </div>
            </div>
        </div>
        <script>
            let detectedData = { ip: '', city: '', country: '' };
            
            function confirmLocation() {
                // Redirigir con query params
                const url = new URL(window.location.href);
                url.searchParams.set('confirmed_ip', detectedData.ip);
                url.searchParams.set('confirmed_city', detectedData.city);
                url.searchParams.set('confirmed_country', detectedData.country);
                window.location.href = url.toString();
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
                    
                    // Ocultar loading
                    document.getElementById('status').style.display = 'none';
                    document.getElementById('content').style.display = 'block';
                    
                    // Mostrar datos
                    document.getElementById('ip').textContent = detectedData.ip;
                    document.getElementById('location').textContent = detectedData.city + ', ' + detectedData.country;
                    
                    // Mostrar botón con texto del país
                    const btn = document.getElementById('confirmBtn');
                    btn.textContent = '✅ Continuar desde ' + detectedData.country + '?';
                    btn.classList.add('show');
                    
                } catch (e) {
                    document.getElementById('status').textContent = '❌ Error detectando ubicación';
                    document.getElementById('status').classList.remove('status');
                }
            })();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=400)
    
    return False
