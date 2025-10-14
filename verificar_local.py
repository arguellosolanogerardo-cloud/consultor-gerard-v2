"""
Script para verificar Google Sheets localmente
Ejecuta esto en tu máquina local para probar la conexión

INSTRUCCIONES:
1. Reemplaza las credenciales abajo con las tuyas reales
2. Ejecuta: python verificar_local.py
"""

# ⚠️ REEMPLAZA ESTO CON TUS CREDENCIALES REALES ⚠️
# Copia el JSON completo de tu archivo google_credentials.json
GOOGLE_CREDENTIALS_DICT = {
  "type": "service_account",
  "project_id": "TU_PROJECT_ID_AQUI",
  "private_key_id": "TU_PRIVATE_KEY_ID_AQUI",
  "private_key": "-----BEGIN PRIVATE KEY-----\nTU_PRIVATE_KEY_AQUI\n-----END PRIVATE KEY-----\n",
  "client_email": "TU_SERVICE_ACCOUNT_EMAIL_AQUI",
  "client_id": "TU_CLIENT_ID_AQUI",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/TU_SERVICE_ACCOUNT_EMAIL_AQUI",
  "universe_domain": "googleapis.com"
}

# ⚠️ REEMPLAZA ESTO CON TU SHEET_ID REAL ⚠️
SHEET_ID = "TU_SHEET_ID_AQUI"
SHEET_NAME = "Interacciones"

def verificar_conexion():
    try:
        print("🔍 Verificando conexión con Google Sheets...")

        # Verificar JSON de credenciales
        import json
        creds_dict = GOOGLE_CREDENTIALS_DICT
        print("✅ Credenciales JSON válidas")
        print(f"📧 Service Account: {creds_dict.get('client_email', 'N/A')}")

        # Verificar SHEET_ID
        if SHEET_ID:
            print(f"✅ SHEET_ID: {SHEET_ID}")
        else:
            print("❌ SHEET_ID vacío")
            return

        # Intentar conectar
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Abrir hoja por ID
        spreadsheet = client.open_by_key(SHEET_ID)
        print(f"✅ Hoja encontrada: {spreadsheet.title}")

        # Verificar worksheet
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
            print(f"✅ Worksheet '{SHEET_NAME}' encontrado")

            # Obtener datos existentes
            all_values = worksheet.get_all_values()
            print(f"✅ Datos obtenidos: {len(all_values)} filas")

            # Agregar una fila de prueba
            import datetime
            test_row = [
                str(datetime.datetime.now()),
                "TEST_LOCAL",
                "test_user",
                "¿Funciona el registro local?",
                "Sí, funciona correctamente",
                "Local",
                "Python",
                "Desktop",
                "Test City",
                "Test Country",
                "127.0.0.1",
                "0.0",
                "-999.0",
                "2.5",
                "True"
            ]

            worksheet.append_row(test_row)
            print("✅ Registro de prueba agregado exitosamente!")

        except Exception as e:
            print(f"❌ Error con worksheet '{SHEET_NAME}': {e}")
            print("📋 Worksheets disponibles:")
            worksheets = spreadsheet.worksheets()
            for ws in worksheets:
                print(f"  - '{ws.title}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_conexion()