"""
Módulo para detectar la IP REAL del cliente usando JavaScript.

Este módulo usa JavaScript que se ejecuta en el navegador del usuario
para obtener su IP pública real, saltando el proxy de Streamlit.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Optional, Dict

def detect_real_client_ip() -> Optional[Dict[str, str]]:
    """
    Detecta la IP real del cliente usando JavaScript en el navegador.
    
    Retorna un diccionario con:
        - ip: IP pública del cliente
        - city: Ciudad (si está disponible)
        - country: País (si está disponible)
        - isp: Proveedor de internet (si está disponible)
    
    Returns:
        Dict con información de IP o None si falla
    """
    # HTML + JavaScript que se ejecuta en el navegador del cliente
    html_code = """
    <script>
    (function() {
        // Función para enviar la IP a Streamlit
        function sendIPToStreamlit(data) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                data: data
            }, '*');
        }
        
        // Intentar múltiples APIs en caso de que alguna falle
        const apis = [
            // API 1: ipapi.co (gratuita, muy confiable)
            {
                url: 'https://ipapi.co/json/',
                parser: (data) => ({
                    ip: data.ip,
                    city: data.city,
                    country: data.country_name,
                    isp: data.org,
                    latitude: data.latitude,
                    longitude: data.longitude
                })
            },
            // API 2: ipify + ipapi.com (backup)
            {
                url: 'https://api.ipify.org?format=json',
                parser: async (data) => {
                    const ip = data.ip;
                    // Obtener más detalles con ip-api.com
                    try {
                        const detailsResponse = await fetch(`http://ip-api.com/json/${ip}`);
                        const details = await detailsResponse.json();
                        return {
                            ip: ip,
                            city: details.city,
                            country: details.country,
                            isp: details.isp,
                            latitude: details.lat,
                            longitude: details.lon
                        };
                    } catch (e) {
                        return { ip: ip, city: 'Unknown', country: 'Unknown', isp: 'Unknown' };
                    }
                }
            },
            // API 3: ipwhois (backup 2)
            {
                url: 'https://ipwhois.app/json/',
                parser: (data) => ({
                    ip: data.ip,
                    city: data.city,
                    country: data.country,
                    isp: data.isp,
                    latitude: data.latitude,
                    longitude: data.longitude
                })
            }
        ];
        
        // Intentar con la primera API
        async function detectIP() {
            for (const api of apis) {
                try {
                    console.log('[IP Detector] Intentando API:', api.url);
                    const response = await fetch(api.url);
                    const data = await response.json();
                    const parsed = await api.parser(data);
                    
                    console.log('[IP Detector] IP detectada:', parsed);
                    sendIPToStreamlit(parsed);
                    return; // Éxito, salir
                } catch (error) {
                    console.error('[IP Detector] Error con API:', api.url, error);
                    // Continuar con la siguiente API
                }
            }
            
            // Si todas las APIs fallaron
            console.error('[IP Detector] Todas las APIs fallaron');
            sendIPToStreamlit({ 
                ip: 'Error', 
                city: 'Error', 
                country: 'Error',
                isp: 'Error'
            });
        }
        
        // Ejecutar detección
        detectIP();
    })();
    </script>
    <div style="display: none;">IP Detection in progress...</div>
    """
    
    # Renderizar el componente JavaScript
    result = components.html(html_code, height=0)
    
    return result


def get_real_ip_with_timeout(timeout_seconds: int = 5) -> Optional[Dict[str, str]]:
    """
    Obtiene la IP real del cliente con timeout.
    
    Args:
        timeout_seconds: Tiempo máximo de espera
        
    Returns:
        Dict con información de IP o None si timeout
    """
    import time
    
    # Crear placeholder para el resultado
    if 'real_ip_data' not in st.session_state:
        st.session_state.real_ip_data = None
    
    # Detectar IP
    start_time = time.time()
    ip_data = detect_real_client_ip()
    
    if ip_data:
        st.session_state.real_ip_data = ip_data
        return ip_data
    
    # Esperar hasta timeout
    while (time.time() - start_time) < timeout_seconds:
        if st.session_state.real_ip_data:
            return st.session_state.real_ip_data
        time.sleep(0.1)
    
    return None


# Función de conveniencia
def initialize_real_ip_detector():
    """
    Inicializa el detector de IP real en el session_state.
    Debe llamarse una sola vez al inicio de la aplicación.
    """
    if 'real_ip_initialized' not in st.session_state:
        st.session_state.real_ip_initialized = True
        st.session_state.real_ip_data = None
        print("[INFO] Real IP Detector inicializado")


if __name__ == "__main__":
    # Prueba del módulo
    st.title("🌐 Detector de IP Real")
    st.write("Este componente detecta tu IP pública REAL usando JavaScript en tu navegador.")
    
    if st.button("🔍 Detectar Mi IP Real"):
        with st.spinner("Detectando IP desde tu navegador..."):
            ip_data = detect_real_client_ip()
            
            if ip_data:
                st.success("✅ IP detectada exitosamente")
                st.json(ip_data)
            else:
                st.error("❌ No se pudo detectar la IP")
