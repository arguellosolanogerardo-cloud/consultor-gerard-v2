"""
Script de diagnóstico para Google Sheets en Streamlit Cloud
Ejecuta esto en tu app de Streamlit Cloud para diagnosticar problemas
"""

import streamlit as st
import json

st.title("🔍 Diagnóstico de Google Sheets en Streamlit Cloud")

st.header("📋 Secrets Disponibles")
try:
    secrets = st.secrets
    st.write("**Claves encontradas en st.secrets:**")
    for key in secrets.keys():
        st.write(f"- `{key}`")

    # Verificar GOOGLE_API_KEY
    if 'GOOGLE_API_KEY' in secrets:
        api_key = secrets['GOOGLE_API_KEY']
        if api_key and len(str(api_key).strip()) > 10:
            st.success("✅ GOOGLE_API_KEY configurada correctamente")
        else:
            st.error("❌ GOOGLE_API_KEY está vacía o muy corta")
    else:
        st.error("❌ GOOGLE_API_KEY no encontrada en secrets")

    # Verificar GOOGLE_CREDENTIALS
    if 'GOOGLE_CREDENTIALS' in secrets:
        creds = secrets['GOOGLE_CREDENTIALS']
        st.write("**Tipo de GOOGLE_CREDENTIALS:**", type(creds))

        if isinstance(creds, str):
            st.write("Es un string JSON")
            try:
                parsed_creds = json.loads(creds)
                st.success("✅ GOOGLE_CREDENTIALS es un JSON válido")

                # Verificar campos requeridos
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                missing_fields = []
                for field in required_fields:
                    if field not in parsed_creds:
                        missing_fields.append(field)

                if missing_fields:
                    st.error(f"❌ Faltan campos en las credenciales: {missing_fields}")
                else:
                    st.success("✅ Todos los campos requeridos están presentes")

                    # Mostrar información del service account
                    st.write("**Información del Service Account:**")
                    st.write(f"- **Project ID:** {parsed_creds.get('project_id')}")
                    st.write(f"- **Client Email:** {parsed_creds.get('client_email')}")
                    st.write(f"- **Type:** {parsed_creds.get('type')}")

            except json.JSONDecodeError as e:
                st.error(f"❌ GOOGLE_CREDENTIALS no es un JSON válido: {e}")
                st.code(creds[:500] + "..." if len(creds) > 500 else creds)
        else:
            st.write("Es un diccionario")
            st.json(creds)
    else:
        st.error("❌ GOOGLE_CREDENTIALS no encontrada en secrets")

    # Verificar SHEET_ID
    if 'SHEET_ID' in secrets:
        sheet_id = secrets['SHEET_ID']
        if sheet_id and len(str(sheet_id).strip()) > 10:
            st.success(f"✅ SHEET_ID configurada: {sheet_id}")
        else:
            st.error("❌ SHEET_ID está vacía o inválida")
    else:
        st.warning("⚠️ SHEET_ID no encontrada (usará valor por defecto)")

    # Verificar SHEET_NAME
    if 'SHEET_NAME' in secrets:
        sheet_name = secrets['SHEET_NAME']
        st.info(f"ℹ️ SHEET_NAME: {sheet_name}")
    else:
        st.info("ℹ️ SHEET_NAME no configurada (usará 'Interacciones' por defecto)")

except Exception as e:
    st.error(f"❌ Error accediendo a secrets: {e}")
    st.code(str(e))

st.header("🧪 Probar Conexión con Google Sheets")

if st.button("Probar Conexión con Google Sheets"):
    try:
        st.write("🔄 Importando módulos...")

        # Importar módulos necesarios
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        import json

        st.write("✅ Módulos importados correctamente")

        # Verificar que tenemos las secrets necesarias
        if 'GOOGLE_CREDENTIALS' not in st.secrets:
            st.error("❌ GOOGLE_CREDENTIALS no configurada")
            st.stop()

        if 'SHEET_ID' not in st.secrets:
            st.error("❌ SHEET_ID no configurada")
            st.stop()

        creds_str = st.secrets['GOOGLE_CREDENTIALS']
        sheet_id = st.secrets['SHEET_ID']

        st.write("🔄 Parseando credenciales...")

        # Parsear credenciales
        if isinstance(creds_str, str):
            creds_dict = json.loads(creds_str)
        else:
            creds_dict = creds_str

        st.write("🔄 Configurando autenticación...")

        # Configurar scope y credenciales
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

        st.write("🔄 Conectando con Google Sheets...")

        # Conectar con gspread
        client = gspread.authorize(creds)

        st.write("🔄 Abriendo hoja de cálculo...")

        # Abrir la hoja de cálculo
        spreadsheet = client.open_by_key(sheet_id)

        st.success("✅ Conexión exitosa con Google Sheets!")

        # Obtener información de la hoja
        worksheet_name = st.secrets.get('SHEET_NAME', 'Interacciones')
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            st.write(f"✅ Hoja '{worksheet_name}' encontrada")

            # Obtener algunas filas para verificar
            all_values = worksheet.get_all_values()
            if all_values:
                st.write(f"✅ La hoja tiene {len(all_values)} filas")
                if len(all_values) > 0:
                    st.write("**Encabezados encontrados:**")
                    st.write(all_values[0])
            else:
                st.warning("⚠️ La hoja está vacía")

        except Exception as e:
            st.error(f"❌ Error accediendo a la hoja '{worksheet_name}': {e}")

            # Listar hojas disponibles
            try:
                worksheets = spreadsheet.worksheets()
                st.write("**Hojas disponibles:**")
                for ws in worksheets:
                    st.write(f"- {ws.title}")
            except Exception as e2:
                st.error(f"❌ Error listando hojas: {e2}")

    except ImportError as e:
        st.error(f"❌ Error importando módulos: {e}")
        st.write("Asegúrate de que estas dependencias estén en requirements.txt:")
        st.code("gspread>=5.10.0\noauth2client>=4.1.3")
    except json.JSONDecodeError as e:
        st.error(f"❌ Error parseando credenciales JSON: {e}")
    except Exception as e:
        st.error(f"❌ Error en la conexión: {e}")
        st.code(str(e))

st.header("📝 Instrucciones para Configurar Secrets")

st.markdown("""
### 🔧 Configuración Correcta de Secrets en Streamlit Cloud:

Ve a tu app → **Settings** → **Secrets** y pega exactamente esto:

```toml
# API Key de Google AI Studio (OBLIGATORIO)
GOOGLE_API_KEY = "tu_clave_real_aqui"

# Credenciales del Service Account (OBLIGATORIO)
GOOGLE_CREDENTIALS = \"\"\"
{
  "type": "service_account",
  "project_id": "gerard-logger",
  "private_key_id": "tu_private_key_id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nTU_CLAVE_PRIVADA_AQUI\\n-----END PRIVATE KEY-----\\n",
  "client_email": "gerard-sheets-logger@gerard-logger.iam.gserviceaccount.com",
  "client_id": "tu_client_id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/TU_CLIENT_ID"
}
\"\"\"

# ID de la hoja de cálculo (OBLIGATORIO)
SHEET_ID = "1O92R7BmxXfIOBO-qA3T0XpF1M2ena19bxqn8OrsqB2E"

# Nombre de la hoja (OPCIONAL)
SHEET_NAME = "Interacciones"
```

### ⚠️ Errores Comunes:

1. **Credenciales mal formateadas:** Asegúrate de que el JSON esté completo y válido
2. **Service Account sin permisos:** Comparte la hoja con el email del service account
3. **SHEET_ID incorrecto:** Verifica que sea exactamente el ID de la URL
4. **Secrets no guardadas:** Después de pegar, haz clic en "Save"

### 🔍 Para verificar que funciona:

1. Ejecuta este diagnóstico
2. Haz clic en "Probar Conexión con Google Sheets"
3. Si todo está bien, deberías ver "✅ Conexión exitosa"
""")

st.header("🚨 Solución Rápida")

st.markdown("""
Si el diagnóstico muestra errores, **copia y pega exactamente** esta configuración en Secrets:

```toml
GOOGLE_API_KEY = "AIzaSyDUMMYKEYFORDEMO"
GOOGLE_CREDENTIALS = \"\"\"
{
  "type": "service_account",
  "project_id": "gerard-logger",
  "private_key_id": "dummy",
  "private_key": "-----BEGIN PRIVATE KEY-----\\ndummy\\n-----END PRIVATE KEY-----\\n",
  "client_email": "gerard-sheets-logger@gerard-logger.iam.gserviceaccount.com",
  "client_id": "dummy",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy"
}
\"\"\""
SHEET_ID = "1O92R7BmxXfIOBO-qA3T0XpF1M2ena19bxqn8OrsqB2E"
SHEET_NAME = "Interacciones"
```

**Luego reemplaza con tus valores reales.**
""")