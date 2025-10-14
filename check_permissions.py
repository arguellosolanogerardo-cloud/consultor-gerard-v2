"""
Diagnóstico rápido de permisos de Google Sheets
"""

import json
from pathlib import Path

def check_credentials():
    """Verifica que las credenciales sean válidas"""

    creds_file = Path("google_credentials.json")
    if not creds_file.exists():
        print("❌ No se encontró google_credentials.json")
        return None

    try:
        with open(creds_file, 'r', encoding='utf-8') as f:
            creds = json.load(f)

        print("✅ Archivo de credenciales encontrado")
        print(f"📧 Service Account: {creds.get('client_email')}")
        print(f"🏗️ Project ID: {creds.get('project_id')}")

        return creds

    except Exception as e:
        print(f"❌ Error leyendo credenciales: {e}")
        return None

def main():
    print("🔍 DIAGNÓSTICO DE PERMISOS DE GOOGLE SHEETS")
    print("="*60)

    creds = check_credentials()
    if not creds:
        return

    print("\n📋 VERIFICACIÓN DE PERMISOS")
    print("="*60)

    print("Para que funcione, necesitas:")
    print()
    print("1. ✅ IR A GOOGLE SHEETS:")
    print("   https://docs.google.com/spreadsheets/d/1O92R7BmxXfIOBO-qA3T0XpF1M2ena19bxqn8OrsqB2E/edit")
    print()
    print("2. ✅ HACER CLIC EN 'COMPARTIR'")
    print()
    print("3. ✅ AGREGAR ESTE EMAIL COMO EDITOR:")
    print(f"   📧 {creds['client_email']}")
    print()
    print("4. ✅ EN STREAMLIT CLOUD → SETTINGS → SECRETS, PEGAR:")
    print()
    print("GOOGLE_API_KEY = \"tu_clave_real_de_google_ai_studio\"")
    print()
    print("GOOGLE_CREDENTIALS = \"\"\"")
    print(json.dumps(creds, indent=2))
    print("\"\"\"")
    print()
    print("SHEET_ID = \"1O92R7BmxXfIOBO-qA3T0XpF1M2ena19bxqn8OrsqB2E\"")
    print()
    print("SHEET_NAME = \"Interacciones\"")
    print()
    print("="*60)
    print("🚨 IMPORTANTE:")
    print("- Asegúrate de que el service account tenga permisos de EDITOR")
    print("- La hoja debe tener una pestaña llamada 'Interacciones'")
    print("- Si no funciona, regenera las credenciales del service account")

if __name__ == "__main__":
    main()