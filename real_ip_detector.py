"""
Detector de IP REAL usando componente HTML bidireccional.
Versión mejorada que funciona en Streamlit Cloud.
"""

import streamlit as st
import streamlit.components.v1 as components
import time


def detect_real_ip_enhanced():
    """
    Detecta la IP real del cliente usando un componente HTML con comunicación bidireccional.
    Funciona tanto en local como en Streamlit Cloud.
    """
    # Solo ejecutar si no se ha detectado aún
    if st.session_state.get('real_ip_detected', False):
        return True
    
    # Crear componente HTML que envía datos vía Streamlit setValue
    html_component = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { margin: 0; padding: 0; background: transparent; }
            #status { 
                position: fixed;
                bottom: 10px;
                right: 10px;
                background: #667eea;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 11px;
                font-family: monospace;
                z-index: 9999;
            }
        </style>
    </head>
    <body>
        <div id="status">🌐 Detectando IP...</div>
        <script>
            (async function() {
                const statusDiv = document.getElementById('status');
                
                try {
                    // Intentar ipapi.co primero (más completo)
                    statusDiv.textContent = '🌐 Detectando IP...';
                    const response = await fetch('https://ipapi.co/json/');
                    const data = await response.json();
                    
                    // Preparar datos
                    const ipData = {
                        ip: data.ip || 'Unknown',
                        city: data.city || 'Unknown',
                        country: data.country_name || data.country || 'Unknown',
                        detected: true
                    };
                    
                    // Enviar a Streamlit
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        data: ipData
                    }, '*');
                    
                    statusDiv.textContent = '✅ IP: ' + ipData.ip;
                    statusDiv.style.background = '#10b981';
                    
                    // Ocultar después de 2 segundos
                    setTimeout(() => {
                        statusDiv.style.display = 'none';
                    }, 2000);
                    
                } catch (error) {
                    console.error('Error detectando IP:', error);
                    statusDiv.textContent = '⚠️ Usando IP servidor';
                    statusDiv.style.background = '#f59e0b';
                    
                    // Enviar fallback
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        data: { detected: false }
                    }, '*');
                    
                    setTimeout(() => {
                        statusDiv.style.display = 'none';
                    }, 3000);
                }
            })();
        </script>
    </body>
    </html>
    """
    
    # Ejecutar componente y capturar resultado
    result = components.html(html_component, height=0)
    
    # Si recibimos datos, guardarlos
    if result and isinstance(result, dict) and result.get('detected'):
        st.session_state.user_ip = result.get('ip', 'No detectado')
        st.session_state.user_city = result.get('city', 'Unknown')
        st.session_state.user_country = result.get('country', 'Unknown')
        st.session_state.real_ip_detected = True
        
        print(f"[INFO] ✅ IP REAL detectada: {st.session_state.user_ip} | {st.session_state.user_city}, {st.session_state.user_country}")
        return True
    
    return False


def ensure_real_ip():
    """
    Asegura que la IP real esté detectada.
    Si no lo está, ejecuta la detección.
    """
    if not st.session_state.get('real_ip_detected', False):
        # Mostrar mensaje breve
        with st.spinner("🌐 Detectando tu ubicación real..."):
            detect_real_ip_enhanced()
            time.sleep(1)  # Dar tiempo al JavaScript
            st.rerun()
    
    return st.session_state.get('real_ip_detected', False)
