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
    
    # Cargar la animación Lottie desde el archivo
    import json
    import os
    
    lottie_path = os.path.join(os.path.dirname(__file__), "assets", "Unlock.json")
    
    try:
        with open(lottie_path, 'r', encoding='utf-8') as f:
            lottie_animation_data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] No se encontró el archivo Unlock.json en: {lottie_path}")
        lottie_animation_data = {}
    except Exception as e:
        print(f"[ERROR] Error cargando animación Lottie: {e}")
        lottie_animation_data = {}
    
    st.markdown("""
    <h3 style="color: #FF00FF; margin-bottom: 20px;">
        🔑 CLAVE GENERADA PARA CONSULTA
    </h3>
    """, unsafe_allow_html=True)
    
    # Inyectar el overlay directamente en el DOM de la página principal
    lottie_injector_html = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/bodymovin/5.12.2/lottie.min.js"></script>
        <script>
            (function() {{
                const animationData = {json.dumps(lottie_animation_data)};
                let pageLottieAnimation = null;
                let pagePlayCount = 0;
                
                function injectOverlay() {{
                    if (typeof lottie === 'undefined') {{
                        setTimeout(injectOverlay, 100);
                        return;
                    }}
                    
                    const targetDoc = window.top.document;
                    
                    if (targetDoc.getElementById('lottie-page-overlay')) {{
                        setupAnimation();
                        return;
                    }}
                    
                    const overlay = targetDoc.createElement('div');
                    overlay.id = 'lottie-page-overlay';
                    overlay.style.cssText = `
                        display: none;
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100vw;
                        height: 100vh;
                        background: rgba(0, 0, 0, 0.5);
                        z-index: 999999;
                        justify-content: center;
                        align-items: center;
                        pointer-events: none;
                    `;
                    
                    const container = targetDoc.createElement('div');
                    container.id = 'lottie-page-container';
                    container.style.cssText = `
                        width: 400px;
                        height: 400px;
                        pointer-events: auto;
                    `;
                    
                    overlay.appendChild(container);
                    targetDoc.body.appendChild(overlay);
                    
                    setupAnimation();
                }}
                
                function setupAnimation() {{
                    const targetDoc = window.top.document;
                    const container = targetDoc.getElementById('lottie-page-container');
                    
                    if (!container) {{
                        console.error('[ERROR] No se encontró el contenedor de animación');
                        return;
                    }}
                    
                    try {{
                        pageLottieAnimation = lottie.loadAnimation({{
                            container: container,
                            renderer: 'svg',
                            loop: false,
                            autoplay: false,
                            animationData: animationData
                        }});
                        
                        pageLottieAnimation.addEventListener('complete', function() {{
                            pagePlayCount++;
                            if (pagePlayCount < 3) {{
                                pageLottieAnimation.goToAndPlay(0);
                            }} else {{
                                targetDoc.getElementById('lottie-page-overlay').style.display = 'none';
                                pagePlayCount = 0;
                            }}
                        }});
                        
                        window.top.showUnlockAnimation = function() {{
                            const overlay = targetDoc.getElementById('lottie-page-overlay');
                            if (overlay && pageLottieAnimation) {{
                                overlay.style.display = 'flex';
                                pagePlayCount = 0;
                                pageLottieAnimation.goToAndPlay(0);
                            }}
                        }};
                        
                    }} catch (error) {{
                        console.error('[ERROR] Error inicializando animación Lottie:', error);
                    }}
                }}
                
                setTimeout(injectOverlay, 100);
            }})();
        </script>
    </body>
    </html>
    """
    
    components.html(lottie_injector_html, height=0)
    
    
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
                word-break: break-all;
                overflow-wrap: break-word;
            }
            @media (max-width: 768px) {
                .ip-value {
                    font-size: 18px;
                }
                .ip-box {
                    padding: 15px;
                }
            }
            @media (max-width: 480px) {
                .ip-value {
                    font-size: 14px;
                }
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
                transition: all 0.3s ease;
            }
            .copy-btn:hover {
                background: #f0f0f0;
            }
            .copy-btn.copied {
                background: #00ff41;
                color: #000;
                box-shadow: 0 0 20px #00ff41;
            }
            .loading {
                color: #667eea;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        </style>
    </head>
    <body>
        <div id="loading" class="loading">Detectando tu IP...</div>
        <div id="content" style="display:none;">
            <div class="ip-box">
                <div id="ip" class="ip-value">-</div>
                <button class="copy-btn" onclick="copyIP()">📋 Copiar CLAVE</button>
            </div>
        </div>
        <script>
            let detectedData = { ip: '', city: '', country: '' };
            
            function copyIP() {
                const btn = document.querySelector('.copy-btn');
                const originalText = btn.innerHTML;
                
                navigator.clipboard.writeText(detectedData.ip);
                
                // Cambiar a verde neón
                btn.classList.add('copied');
                btn.innerHTML = 'COPIADO ✓';
                
                // Volver al estado original después de 2 segundos
                setTimeout(() => {
                    btn.classList.remove('copied');
                    btn.innerHTML = originalText;
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
                    
                    // Llamar a la animación Unlock
                    let attempts = 0;
                    const maxAttempts = 10;
                    
                    function tryShowAnimation() {
                        attempts++;
                        
                        if (window.top && window.top.showUnlockAnimation) {
                            window.top.showUnlockAnimation();
                        } else if (attempts < maxAttempts) {
                            setTimeout(tryShowAnimation, 100);
                        }
                    }
                    
                    setTimeout(tryShowAnimation, 300);
                    
                } catch (e) {
                    console.error('[ERROR] Error obteniendo IP:', e);
                    document.getElementById('loading').textContent = '❌ Error';
                }
            })();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=200)
    
    st.markdown("---")
    st.markdown("""
    <p style="color: #FFFF00; font-size: 20px; font-weight: bold; margin-bottom: 10px;">
        PEGA LA CLAVE DE ACCESO AQUÍ:
    </p>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        ip_input = st.text_input("IP", label_visibility="collapsed", placeholder="Pega tu CLAVE aquí", key="ip_paste_field")
    
    # JavaScript para cambiar el botón a verde neón al hacer click
    button_click_js = """
    <script>
        (function() {
            function findAndStyleButton() {
                const buttons = window.parent.document.querySelectorAll('button[kind="primary"]');
                buttons.forEach(btn => {
                    if (btn.textContent.includes('Confirmar')) {
                        btn.addEventListener('click', function() {
                            this.style.background = '#00ff41';
                            this.style.color = '#000';
                            this.style.boxShadow = '0 0 20px #00ff41';
                            this.style.border = 'none';
                            this.style.transition = 'all 0.2s ease';
                        });
                    }
                });
            }
            
            setTimeout(findAndStyleButton, 100);
            setInterval(findAndStyleButton, 500);
        })();
    </script>
    """
    components.html(button_click_js, height=0)
    
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
                
                st.rerun()
            else:
                st.error("❌ Por favor pega una IP válida")
