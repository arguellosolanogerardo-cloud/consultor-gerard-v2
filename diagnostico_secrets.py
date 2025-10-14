"""
Script de diagnóstico para verificar secrets en Streamlit Cloud
Ejecuta esto en Streamlit Cloud para ver qué secrets están disponibles
"""

import streamlit as st

st.title("🔍 Diagnóstico de Secrets en Streamlit Cloud")

st.header("📋 Secrets Disponibles")
try:
    if hasattr(st, 'secrets') and st.secrets:
        st.write("**Claves encontradas en st.secrets:**")
        for key in st.secrets.keys():
            st.write(f"- `{key}`")

        st.header("🔍 Detalles de GOOGLE_CREDENTIALS")
        if 'GOOGLE_CREDENTIALS' in st.secrets:
            google_creds = st.secrets['GOOGLE_CREDENTIALS']
            st.write(f"**Tipo:** {type(google_creds)}")

            if isinstance(google_creds, str):
                st.write("**Es un string JSON**")
                try:
                    import json
                    parsed = json.loads(google_creds)
                    st.write("**JSON válido ✅**")
                    st.write("**Claves en el JSON:**")
                    for key in parsed.keys():
                        st.write(f"  - `{key}`")
                except json.JSONDecodeError as e:
                    st.write(f"**JSON inválido ❌:** {e}")
            else:
                st.write("**Es un diccionario**")
                st.write("**Claves:**")
                for key in google_creds.keys():
                    st.write(f"  - `{key}`")
        else:
            st.error("❌ GOOGLE_CREDENTIALS no encontrado en secrets")

        st.header("🔍 Detalles de gcp_service_account")
        if 'gcp_service_account' in st.secrets:
            gcp_creds = st.secrets['gcp_service_account']
            st.write(f"**Tipo:** {type(gcp_creds)}")
            st.write("**Claves:**")
            for key in gcp_creds.keys():
                st.write(f"  - `{key}`")
        else:
            st.warning("⚠️ gcp_service_account no encontrado en secrets")

    else:
        st.error("❌ st.secrets no disponible o vacío")

except Exception as e:
    st.error(f"❌ Error accediendo a secrets: {e}")
    import traceback
    st.code(traceback.format_exc())

st.header("📝 Instrucciones para Configurar Secrets")

st.markdown("""
### Opción 1: Usar GOOGLE_CREDENTIALS (Recomendado)
En la configuración de tu app en Streamlit Cloud → Settings → Secrets, pega:

```toml
GOOGLE_CREDENTIALS = \"\"\"
{
  "type": "service_account",
  "project_id": "gerard-logger",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...",
  "client_email": "gerard-sheets-logger@gerard-logger.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
  "universe_domain": "googleapis.com"
}
\"\"\"
```

### Opción 2: Usar gcp_service_account
```toml
[gcp_service_account]
type = "service_account"
project_id = "gerard-logger"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n..."
client_email = "gerard-sheets-logger@gerard-logger.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
universe_domain = "googleapis.com"
```

### Opción 3: API Key de Google (Obligatoria)
```toml
GOOGLE_API_KEY = "tu_clave_real_de_google_ai_studio"
```
""")

st.header("🧪 Probar Google Sheets Logger")

if st.button("Probar Conexión con Google Sheets"):
    try:
        from google_sheets_logger import create_sheets_logger

        st.write("🔄 Creando logger...")
        logger = create_sheets_logger()

        if logger and logger.enabled:
            st.success("✅ Logger de Google Sheets creado exitosamente")

            # Intentar hacer un registro de prueba
            st.write("📝 Enviando registro de prueba...")
            logger.log_interaction(
                interaction_id="DIAGNOSTIC_TEST",
                user="DIAGNOSTIC_USER",
                question="Pregunta de diagnóstico",
                answer="Respuesta de diagnóstico",
                device_info={"device_type": "diagnostic", "browser": "diagnostic", "os": "diagnostic"},
                location_info={"city": "Test City", "country": "Test Country", "ip": "127.0.0.1"},
                timing={"total_time": 1.0},
                success=True
            )
            st.success("✅ Registro enviado exitosamente a Google Sheets")
        else:
            st.error("❌ Logger no se pudo crear o no está habilitado")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.code(str(e))