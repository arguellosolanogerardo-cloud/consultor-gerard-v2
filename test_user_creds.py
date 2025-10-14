"""
Verificación de credenciales con el JSON proporcionado por el usuario
"""

import json
import os
from pathlib import Path

def test_user_credentials():
    """Probar las credenciales que el usuario configuró"""

    # ⚠️ REEMPLAZA ESTO CON TUS CREDENCIALES REALES ⚠️
    # Copia el JSON completo de tu archivo google_credentials.json
    user_creds = {
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

    print("🔍 Verificando credenciales del usuario...")
    print(f"📧 Service Account: {user_creds['client_email']}")
    print(f"🏗️ Project ID: {user_creds['project_id']}")

    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        # Configurar autenticación
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(user_creds, scope)

        print("✅ Autenticación configurada")

        # Conectar con gspread
        client = gspread.authorize(creds)
        print("✅ Cliente autorizado")

        # ID de la hoja del usuario (reemplaza con el tuyo)
        sheet_id = "TU_SHEET_ID_AQUI"

        # Abrir la hoja de cálculo
        spreadsheet = client.open_by_key(sheet_id)
        print(f"✅ Hoja de cálculo abierta: {spreadsheet.title}")

        # Verificar worksheet
        worksheet = spreadsheet.worksheet("Interacciones")
        print(f"✅ Worksheet 'Interacciones' encontrado")

        # Obtener datos existentes
        all_values = worksheet.get_all_values()
        print(f"✅ Datos obtenidos: {len(all_values)} filas")

        # Agregar una fila de prueba
        import datetime
        test_row = [
            str(datetime.datetime.now()),
            "TEST_USER_CREDS",
            "test_user",
            "¿Funciona la verificación de credenciales?",
            "Sí, las credenciales funcionan correctamente",
            "Local",
            "Python",
            "Test",
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
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_credentials()