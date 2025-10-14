"""
Script para verificar worksheets en Google Sheets
Ejecuta esto localmente para ver qué worksheets tiene tu hoja
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ⚠️ REEMPLAZA ESTO CON TU SHEET_ID REAL ⚠️
SHEET_ID = "TU_SHEET_ID_AQUI"

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

def verificar_hoja():
    try:
        # Parsear credenciales
        creds_dict = GOOGLE_CREDENTIALS_DICT

        # Autenticar
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Abrir por ID
        spreadsheet = client.open_by_key(SHEET_ID)

        print(f"✅ Hoja encontrada: {spreadsheet.title}")
        print(f"📄 ID: {SHEET_ID}")

        # Listar worksheets
        worksheets = spreadsheet.worksheets()
        print(f"\n📋 Worksheets encontrados ({len(worksheets)}):")

        for i, ws in enumerate(worksheets, 1):
            print(f"  {i}. '{ws.title}' - {ws.row_count} filas x {ws.col_count} columnas")

        # Verificar worksheet específico
        target_worksheet = "Interacciones"
        try:
            worksheet = spreadsheet.worksheet(target_worksheet)
            print(f"\n✅ Worksheet '{target_worksheet}' encontrado")
            print(f"📊 Dimensiones: {worksheet.row_count} filas x {worksheet.col_count} columnas")

            # Mostrar primeras filas
            all_values = worksheet.get_all_values()
            if all_values:
                print(f"📋 Datos encontrados: {len(all_values)} filas")
                if len(all_values) > 0:
                    print("📋 Cabeceras:")
                    print(f"    {all_values[0]}")
                if len(all_values) > 1:
                    print(f"📋 Primera fila de datos: {all_values[1]}")
            else:
                print("⚠️ La hoja está vacía")

        except Exception as e:
            print(f"❌ Error accediendo a worksheet '{target_worksheet}': {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_hoja()