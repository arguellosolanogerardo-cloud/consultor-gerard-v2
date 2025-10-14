"""
Script simple para verificar credenciales de Google Sheets
Ejecuta esto en Streamlit Cloud para verificar rápidamente
"""

import streamlit as st

st.title("🔍 Verificación Rápida de Google Sheets")

st.header("📋 Estado de Secrets")

try:
    secrets = st.secrets
    st.write("🔑 Secrets disponibles:", list(secrets.keys()))

    # Verificar GOOGLE_API_KEY
    if 'GOOGLE_API_KEY' in secrets:
        api_key = str(secrets['GOOGLE_API_KEY']).strip()
        if api_key and len(api_key) > 10:
            st.success("✅ GOOGLE_API_KEY configurada")
            st.write(f"📏 Longitud: {len(api_key)} caracteres")
        else:
            st.error("❌ GOOGLE_API_KEY vacía o muy corta")
            st.write(f"Valor actual: '{api_key}'")
    else:
        st.error("❌ GOOGLE_API_KEY no encontrada")

    # Verificar GOOGLE_CREDENTIALS
    if 'GOOGLE_CREDENTIALS' in secrets:
        creds = secrets['GOOGLE_CREDENTIALS']
        st.write(f"📝 Tipo de GOOGLE_CREDENTIALS: {type(creds)}")
        if isinstance(creds, str):
            st.write("📄 Es un string, intentando parsear JSON...")
            try:
                import json
                parsed = json.loads(creds)
                st.success("✅ GOOGLE_CREDENTIALS es JSON válido")
                st.write(f"📧 Service Account: {parsed.get('client_email', 'N/A')}")
                st.write(f"📋 Tipo de cuenta: {parsed.get('type', 'N/A')}")
            except json.JSONDecodeError as e:
                st.error("❌ GOOGLE_CREDENTIALS no es JSON válido")
                st.write(f"Error: {e}")
                st.code(creds[:500] + "..." if len(creds) > 500 else creds)
        else:
            st.error("❌ GOOGLE_CREDENTIALS debe ser un string JSON")
            st.write(f"Valor actual: {creds}")
    else:
        st.error("❌ GOOGLE_CREDENTIALS no encontrada")

    # Verificar SHEET_ID
    if 'SHEET_ID' in secrets:
        sheet_id = str(secrets['SHEET_ID']).strip()
        if sheet_id:
            st.success(f"✅ SHEET_ID: {sheet_id}")
        else:
            st.error("❌ SHEET_ID vacío")
    else:
        st.error("❌ SHEET_ID no encontrada")

    # Verificar SHEET_NAME
    if 'SHEET_NAME' in secrets:
        sheet_name = str(secrets['SHEET_NAME']).strip()
        if sheet_name:
            st.success(f"✅ SHEET_NAME: {sheet_name}")
        else:
            st.error("❌ SHEET_NAME vacío")
    else:
        st.error("❌ SHEET_NAME no encontrada")

except Exception as e:
    st.error(f"❌ Error accediendo a secrets: {e}")
    st.code(str(e))
    import traceback
    st.code(traceback.format_exc())

st.header("🚨 Instrucciones para Configurar")

st.markdown("""
### Si las secrets no están configuradas:

1. **Ve a Streamlit Cloud** → Tu app → **Settings** → **Secrets**

2. **Copia y pega exactamente esto:**

```toml
GOOGLE_API_KEY = "tu_clave_real_de_google_ai_studio"

GOOGLE_CREDENTIALS = \"\"\"
[JSON_DE_TUS_CREDENCIALES_AQUI]
\"\"\"

SHEET_ID = "tu_sheet_id_aqui"
SHEET_NAME = "Interacciones"
```

### ⚠️ IMPORTANTE:
- **Reemplaza** `"tu_clave_real_de_google_ai_studio"` con tu clave real
- **Reemplaza** `[JSON_DE_TUS_CREDENCIALES_AQUI]` con el JSON completo de tus credenciales
- **Reemplaza** `"tu_sheet_id_aqui"` con el ID real de tu hoja
- **Asegúrate** de que el service account tenga permisos de EDITOR en la hoja
- **Guarda** los cambios y espera a que la app se redeploye

### 🔗 Verificar permisos del Service Account:
Ve a tu hoja de Google Sheets y comparte con el email del service account como **Editor**
""")

st.header("🧪 Probar Conexión")

if st.button("Probar Conexión con Google Sheets"):
    try:
        # Verificar que tenemos las secrets necesarias
        if 'GOOGLE_CREDENTIALS' not in st.secrets:
            st.error("❌ GOOGLE_CREDENTIALS no configurada")
            st.stop()

        if 'SHEET_ID' not in st.secrets:
            st.error("❌ SHEET_ID no configurada")
            st.stop()

        creds_str = st.secrets['GOOGLE_CREDENTIALS']
        sheet_id = st.secrets['SHEET_ID']

        # Parsear credenciales
        import json
        if isinstance(creds_str, str):
            creds_dict = json.loads(creds_str)
        else:
            creds_dict = creds_str

        # Intentar conectar
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Abrir hoja
        spreadsheet = client.open_by_key(sheet_id)
        worksheet_name = st.secrets.get('SHEET_NAME', 'Interacciones')
        worksheet = spreadsheet.worksheet(worksheet_name)

        # Obtener datos existentes
        all_values = worksheet.get_all_values()
        st.success(f"✅ Conexión exitosa! La hoja tiene {len(all_values)} filas")

        # Agregar una fila de prueba
        import datetime
        test_row = [
            str(datetime.datetime.now()),
            "TEST_CLOUD",
            "test_user",
            "¿Funciona el registro?",
            "Sí, funciona correctamente desde Streamlit Cloud",
            "Cloud",
            "Streamlit",
            "Web",
            "Test City",
            "Test Country",
            "127.0.0.1",
            "0.0",
            "-999.0",
            "2.5",
            "True"
        ]

        worksheet.append_row(test_row)
        st.success("✅ Registro de prueba agregado exitosamente!")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.code(str(e))