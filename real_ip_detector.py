"""
Detector de IP REAL - Solución con 1 SOLO CLIC

Widget detecta automáticamente, muestra, botón con texto del país.
1 clic → todo automático → IP REAL guardada.
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_one_click():
    """
    Widget minimalista: SOLO botón "Continuar desde [PAÍS]?"
    Sin mostrar IP, ciudad ni textos de verificación.
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
        
        st.rerun()
        return True
    
    # Widget MINIMALISTA: solo botón, sin textos
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 30px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 150px;
            }
            .confirm-btn {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 18px 40px;
                border-radius: 10px;
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
            .loading {
                color: #667eea;
                font-size: 16px;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        </style>
    </head>
    <body>
        <div id="loading" class="loading">Cargando...</div>
        <button id="confirmBtn" class="confirm-btn" onclick="confirmLocation()">
            -
        </button>
        <script>
            let detectedData = { ip: '', city: '', country: '' };
            
            function confirmLocation() {
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
                    
                    // Ocultar loading, mostrar solo botón
                    document.getElementById('loading').style.display = 'none';
                    
                    const btn = document.getElementById('confirmBtn');
                    btn.textContent = '✅ Continuar desde ' + detectedData.country + '?';
                    btn.classList.add('show');
                    
                } catch (e) {
                    document.getElementById('loading').textContent = 'Error';
                }
            })();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=150)
    
    return False
