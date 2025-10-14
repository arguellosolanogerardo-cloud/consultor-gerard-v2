"""
Script para convertir credenciales JSON a formato TOML seguro
Ejecuta esto localmente para convertir tu archivo JSON
"""

import json
import sys

def convert_json_to_toml_format():
    """Convierte un archivo JSON a formato TOML seguro"""

    print("=== CONVERSOR JSON → TOML PARA STREAMLIT SECRETS ===\n")

    # Pedir la ruta del archivo JSON
    json_file = input("Ingresa la ruta completa de tu archivo JSON de credenciales (ej: C:\\Users\\tu_usuario\\Downloads\\gerard-logger-XXXXX.json): ").strip()

    if not json_file:
        print("❌ No se proporcionó una ruta")
        return

    try:
        # Leer el archivo JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print("✅ Archivo JSON leído correctamente")
        print(f"📧 Service Account: {data.get('client_email', 'N/A')}")
        print(f"🏗️ Project ID: {data.get('project_id', 'N/A')}")

        # Convertir a JSON string escapado para TOML
        json_string = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

        # Escapar comillas para TOML
        escaped_json = json_string.replace('"', '\\"')

        print("\n" + "="*60)
        print("COPIA Y PEGA ESTO EN STREAMLIT CLOUD SECRETS:")
        print("="*60)

        print(f'GOOGLE_API_KEY = "tu_clave_real_de_google_ai_studio"')
        print()
        print(f'GOOGLE_CREDENTIALS = "{escaped_json}"')
        print()
        print(f'SHEET_ID = "1O92R7BmxXfIOBO-qA3T0XpF1M2ena19bxqn8OrsqB2E"')
        print()
        print(f'SHEET_NAME = "Interacciones"')

        print("\n" + "="*60)
        print("INSTRUCCIONES:")
        print("1. Copia todo lo anterior")
        print("2. Ve a Streamlit Cloud → Tu app → Settings → Secrets")
        print("3. Pega el contenido")
        print("4. Reemplaza 'tu_clave_real_de_google_ai_studio' con tu clave real")
        print("5. Guarda y espera el redeploy")
        print("="*60)

    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {json_file}")
        print("Asegúrate de que la ruta sea correcta")
    except json.JSONDecodeError as e:
        print(f"❌ Error al parsear JSON: {e}")
        print("El archivo JSON podría estar corrupto")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    convert_json_to_toml_format()