"""
Detector INVISIBLE de IP Real del Cliente

Este módulo ejecuta JavaScript de forma invisible para detectar
la IP real del usuario sin mostrar ninguna interfaz.
"""

import streamlit as st
import streamlit.components.v1 as components


def detect_ip_silently():
    """
    Detecta la IP del cliente de forma invisible usando JavaScript.
    No muestra nada al usuario, todo sucede en segundo plano.
    
    Retorna la IP si está disponible en query_params, None si no.
    """
    # Verificar si la IP ya fue detectada en esta sesión
    if 'real_ip_detected' in st.session_state and st.session_state.real_ip_detected:
        return {
            'ip': st.session_state.get('user_ip'),
            'city': st.session_state.get('user_city'),
            'country': st.session_state.get('user_country')
        }
    
    # Verificar si está en query params (enviado por JavaScript)
    if 'detected_ip' in st.query_params:
        ip_data = {
            'ip': st.query_params.get('detected_ip', ''),
            'city': st.query_params.get('detected_city', 'Unknown'),
            'country': st.query_params.get('detected_country', 'Unknown')
        }
        
        # Guardar en session_state
        st.session_state.user_ip = ip_data['ip']
        st.session_state.user_city = ip_data['city']
        st.session_state.user_country = ip_data['country']
        st.session_state.real_ip_detected = True
        
        # Limpiar query params
        st.query_params.clear()
        
        print(f"[INFO] ✅ IP REAL detectada automáticamente: {ip_data['ip']} | {ip_data['city']}, {ip_data['country']}")
        
        return ip_data
    
    # Si no está detectada aún, mostrar iframe invisible
    html_code = """
    <iframe id="ipDetector" style="display:none; width:0; height:0; border:none;"></iframe>
    <script>
    (async function() {
        try {
            // Intentar detectar IP usando API externa
            const response = await fetch('https://ipapi.co/json/');
            const data = await response.json();
            
            // Enviar de vuelta a Streamlit via query params
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('detected_ip', data.ip);
            currentUrl.searchParams.set('detected_city', data.city || 'Unknown');
            currentUrl.searchParams.set('detected_country', data.country_name || data.country || 'Unknown');
            
            // Recargar con los nuevos parámetros
            window.location.href = currentUrl.toString();
        } catch (error) {
            console.error('[IP Detector] Error:', error);
            // Si falla, simplemente no hace nada (usará IP del proxy)
        }
    })();
    </script>
    """
    
    # Renderizar iframe invisible
    components.html(html_code, height=0)
    
    return None


def init_invisible_ip_detection():
    """
    Inicializa el sistema de detección invisible de IP.
    Debe llamarse una vez al inicio de la sesión.
    """
    if 'ip_detection_initialized' not in st.session_state:
        st.session_state.ip_detection_initialized = True
        st.session_state.real_ip_detected = False
        print("[INFO] Sistema de detección invisible de IP inicializado")
