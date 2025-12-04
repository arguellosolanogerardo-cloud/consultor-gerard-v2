"""
Módulo MEJORADO para detectar IP REAL del cliente.

Usa un enfoque híbrido:
1. Muestra un iframe invisible que carga una API externa
2. La API retorna la IP en formato JSONP
3. Capturamos la IP y la mostramos al usuario para que la copie
"""

import streamlit as st
import streamlit.components.v1 as components


def show_ip_detector_widget():
    """
    Muestra un widget que detecta y MUESTRA la IP real del cliente.
    El usuario puede copiar la IP manualmente.
    """
    
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .ip-container {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 500px;
                margin: 0 auto;
            }
            .ip-label {
                font-size: 14px;
                color: #666;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .ip-address {
                font-size: 32px;
                font-weight: bold;
                color: #667eea;
                margin: 15px 0;
                font-family: 'Courier New', monospace;
            }
            .location {
                font-size: 18px;
                color: #333;
                margin: 10px 0;
            }
            .isp {
                font-size: 14px;
                color: #999;
                margin-top: 10px;
            }
            .loading {
                font-size: 18px;
                color: #667eea;
                animation: pulse 1.5s ease-in-out infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .copy-btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 15px;
                transition: all 0.3s;
            }
            .copy-btn:hover {
                background: #5568d3;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }
            .success-msg {
                color: #10b981;
                font-size: 14px;
                margin-top: 10px;
                opacity: 0;
                transition: opacity 0.3s;
            }
            .success-msg.show {
                opacity: 1;
            }
        </style>
    </head>
    <body>
        <div class="ip-container">
            <div class="ip-label">🌐 Tu Dirección IP Real</div>
            <div id="ipDisplay" class="loading">Detectando...</div>
            <div id="locationDisplay" class="location" style="display:none;"></div>
            <div id="ispDisplay" class="isp" style="display:none;"></div>
            <button id="copyBtn" class="copy-btn" style="display:none;" onclick="copyIP()">
                📋 Copiar IP
            </button>
            <div id="successMsg" class="success-msg">✓ IP copiada al portapapeles</div>
        </div>

        <script>
            let detectedIP = '';
            
            async function detectIP() {
                const apis = [
                    {
                        url: 'https://api.ipify.org?format=json',
                        parseIP: (data) => data.ip,
                        getDetails: async (ip) => {
                            const res = await fetch(`https://ipapi.co/${ip}/json/`);
                            return await res.json();
                        }
                    },
                    {
                        url: 'https://ipapi.co/json/',
                        parseIP: (data) => data.ip,
                        getDetails: async () => {
                            const res = await fetch('https://ipapi.co/json/');
                            return await res.json();
                        }
                    }
                ];

                for (const api of apis) {
                    try {
                        const response = await fetch(api.url);
                        const data = await response.json();
                        detectedIP = api.parseIP(data);
                        
                        // Mostrar IP
                        document.getElementById('ipDisplay').className = 'ip-address';
                        document.getElementById('ipDisplay').textContent = detectedIP;
                        
                        // Obtener detalles
                        const details = await api.getDetails(detectedIP);
                        
                        // Mostrar ubicación
                        const locationDiv = document.getElementById('locationDisplay');
                        locationDiv.textContent = `📍 ${details.city || 'Unknown'}, ${details.country_name || details.country || 'Unknown'}`;
                        locationDiv.style.display = 'block';
                        
                        // Mostrar ISP
                        const ispDiv = document.getElementById('ispDisplay');
                        ispDiv.textContent = `🏢 ${details.org || details.isp || 'Unknown ISP'}`;
                        ispDiv.style.display = 'block';
                        
                        // Mostrar botón de copiar
                        document.getElementById('copyBtn').style.display = 'inline-block';
                        
                        // Enviar a Streamlit via query params (intento)
                        try {
                            window.parent.postMessage({
                                type: 'streamlit:setComponentValue',
                                data: {
                                    ip: detectedIP,
                                    city: details.city,
                                    country: details.country_name || details.country,
                                    isp: details.org || details.isp
                                }
                            }, '*');
                        } catch(e) {
                            console.log('No se pudo enviar a Streamlit:', e);
                        }
                        
                        return; // Éxito
                    } catch (error) {
                        console.error('Error con API:', api.url, error);
                    }
                }
                
                // Si todas fallaron
                document.getElementById('ipDisplay').textContent = 'Error al detectar IP';
                document.getElementById('ipDisplay').className = 'ip-address';
            }
            
            function copyIP() {
                navigator.clipboard.writeText(detectedIP).then(() => {
                    const msg = document.getElementById('successMsg');
                    msg.classList.add('show');
                    setTimeout(() => msg.classList.remove('show'), 2000);
                });
            }
            
            // Ejecutar al cargar
            detectIP();
        </script>
    </body>
    </html>
    """
    
    # Mostrar el componente
    components.html(html_code, height=250)


def create_ip_input_form():
    """
    Crea un formulario simple para que el usuario ingrese manualmente su IP
    después de verla en el widget detector.
    """
    st.markdown("### 📝 Confirmar IP Detectada")
    st.info("👆 Copia la IP mostrada arriba y pégala aquí para confirmar")
    
    manual_ip = st.text_input(
        "IP Detectada:",
        placeholder="Pega aquí la IP que se mostró arriba",
        key="manual_ip_input"
    )
    
    if st.button("✅ Confirmar IP", type="primary"):
        if manual_ip and len(manual_ip) > 6:
            st.session_state.user_ip = manual_ip
            st.session_state.user_city = "Detectada manualmente"
            st.session_state.user_country = "Detectado manualmente"
            st.success(f"✅ IP guardada: {manual_ip}")
            return True
        else:
            st.error("❌ Por favor ingresa una IP válida")
            return False
    
    return False


if __name__ == "__main__":
    st.title("🌐 Detector de IP Real")
    st.write("Este widget detecta tu IP pública REAL directamente desde tu navegador.")
    st.write("---")
    
    show_ip_detector_widget()
    
    st.write("---")
    
    if create_ip_input_form():
        st.balloons()
        st.write(f"**IP guardada en session_state:** {st.session_state.user_ip}")
