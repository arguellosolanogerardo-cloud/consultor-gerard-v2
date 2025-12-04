"""
Detector de IP REAL - Solución SIMPLE que SÍ funciona

Muestra IP, botón copiar, campo pegar, confirmar.
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_simple_copy():
    """
    Solución simple: muestra IP con botón copiar, usuario pega y confirma.
    5 segundos, 100% funcional.
    """
    
    st.markdown("### 🔑 CLAVE GENERADA PARA CONSULTA")
    
    # Widget que detecta y muestra IP con botón copiar
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 15px;
                text-align: center;
            }
            .ip-box {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
            }
            .ip-value {
                font-size: 28px;
                font-weight: bold;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
                user-select: all;
            }
            .location {
                font-size: 14px;
                opacity: 0.9;
            }
            .copy-btn {
                background: white;
                color: #667eea;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 10px;
            }
            .copy-btn:hover {
                background: #f0f0f0;
            }
            .loading {
                color: #667eea;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .success {
                color: #10b981;
                font-size: 12px;
                margin-top: 5px;
                display: none;
            }
        </style>
    </head>
    <body>
        <div id="loading" class="loading">Detectando tu IP...</div>
        <div id="content" style="display:none;">
            <div class="ip-box">
                <div style="font-size: 14px; margin-bottom: 5px;">TU IP REAL:</div>
                <div id="ip" class="ip-value">-</div>
                <div id="location" class="location">-</div>
                <button class="copy-btn" onclick="copyIP()">📋 Copiar IP</button>
                <div id="success" class="success">✓ Copiado!</div>
            </div>
        </div>
        <script>
            let detectedData = { ip: '', city: '', country: '' };
            
            function copyIP() {
                navigator.clipboard.writeText(detectedData.ip);
                document.getElementById('success').style.display = 'block';
                setTimeout(() => {
                    document.getElementById('success').style.display = 'none';
                }, 2000);
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
                    
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('content').style.display = 'block';
                    document.getElementById('ip').textContent = detectedData.ip;
                    document.getElementById('location').textContent = detectedData.city + ', ' + detectedData.country;
                    
                } catch (e) {
                    document.getElementById('loading').textContent = '❌ Error';
                }
            })();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=200)
    
    st.markdown("---")
    st.markdown("**Pega la IP aquí:**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ip_input = st.text_input("IP", label_visibility="collapsed", placeholder="Pega tu IP aquí", key="ip_paste_field")
    
    with col2:
        if st.button("✅ Confirmar", type="primary", use_container_width=True):
            if ip_input and len(ip_input) > 5:
                # Buscar ciudad y país de esta IP usando múltiples APIs
                import requests
                city = "Unknown"
                country = "Unknown"
                
                # Intentar API 1: ipapi.co
                try:
                    response = requests.get(f'https://ipapi.co/{ip_input}/json/', timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        city = data.get('city', 'Unknown')
                        country = data.get('country_name', data.get('country', 'Unknown'))
                        print(f"[INFO] ipapi.co: {city}, {country}")
                except Exception as e:
                    print(f"[WARNING] ipapi.co falló: {e}")
                
                # Si ipapi.co falló, intentar API 2: ip-api.com
                if city == "Unknown" or country == "Unknown":
                    try:
                        response = requests.get(f'http://ip-api.com/json/{ip_input}', timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('status') == 'success':
                                city = data.get('city', 'Unknown')
                                country = data.get('country', 'Unknown')
                                print(f"[INFO] ip-api.com: {city}, {country}")
                    except Exception as e:
                        print(f"[WARNING] ip-api.com falló: {e}")
                
                # Guardar datos
                st.session_state.user_ip = ip_input
                st.session_state.user_city = city
                st.session_state.user_country = country
                st.session_state.real_ip_detected = True
                st.session_state.ip_needs_confirmation = False
                
                print(f"[INFO] ✅ IP REAL confirmada: {ip_input} | {city}, {country}")
                
                st.success(f"✅ IP confirmada: {ip_input} | {city}, {country}")
                st.rerun()
            else:
                st.error("❌ Por favor pega una IP válida")
