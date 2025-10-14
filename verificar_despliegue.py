"""
Script de verificación pre-despliegue para Streamlit Cloud
Ejecuta esto antes de desplegar para asegurar que todo esté correcto
"""

import os
import sys
import json

def check_file_exists(filepath, description):
    """Verifica si un archivo existe"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists

def check_requirements():
    """Verifica el archivo requirements.txt"""
    print("\n📦 Verificando requirements.txt...")
    if not check_file_exists("requirements.txt", "Archivo requirements.txt"):
        return False

    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"✅ Encontradas {len(requirements)} dependencias")
        return True
    except Exception as e:
        print(f"❌ Error leyendo requirements.txt: {e}")
        return False

def check_streamlit_config():
    """Verifica la configuración de Streamlit"""
    print("\n⚙️ Verificando configuración de Streamlit...")
    config_path = ".streamlit/config.toml"
    if not check_file_exists(config_path, "Archivo .streamlit/config.toml"):
        return False

    try:
        import tomllib
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        print("✅ Configuración TOML válida")

        # Verificar configuraciones importantes
        server_config = config.get("server", {})
        if server_config.get("headless") == True:
            print("✅ Modo headless activado")
        else:
            print("⚠️ Modo headless no activado")

        return True
    except ImportError:
        print("⚠️ tomllib no disponible, saltando validación TOML detallada")
        # Verificación básica: el archivo existe y tiene contenido
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "[server]" in content and "headless = true" in content:
                    print("✅ Configuración básica correcta (headless activado)")
                    return True
                else:
                    print("⚠️ Configuración básica podría tener problemas")
                    return False
        except Exception as e:
            print(f"❌ Error leyendo archivo de configuración: {e}")
            return False
    except Exception as e:
        print(f"⚠️ Error en validación TOML detallada: {e}")
        print("⚠️ Intentando validación básica...")
        # Verificación básica como fallback
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "[server]" in content and "headless = true" in content:
                    print("✅ Configuración básica correcta (headless activado)")
                    return True
                else:
                    print("❌ Configuración básica incorrecta")
                    return False
        except Exception as e2:
            print(f"❌ Error en validación básica: {e2}")
            return False

def check_main_app():
    """Verifica que la aplicación principal exista y sea ejecutable"""
    print("\n🚀 Verificando aplicación principal...")
    main_files = ["consultar_web.py", "app.py", "main.py"]

    main_app = None
    for filename in main_files:
        if os.path.exists(filename):
            main_app = filename
            break

    if main_app:
        print(f"✅ Aplicación principal encontrada: {main_app}")
        return True
    else:
        print("❌ No se encontró aplicación principal (consultar_web.py, app.py, o main.py)")
        return False

def check_secrets_template():
    """Verifica si existe plantilla de secrets"""
    print("\n🔐 Verificando plantilla de secrets...")
    secrets_path = ".streamlit/secrets.toml"
    if check_file_exists(secrets_path, "Plantilla .streamlit/secrets.toml"):
        print("✅ Plantilla de secrets disponible")
        return True
    else:
        print("⚠️ No hay plantilla de secrets (no es obligatorio)")
        return True

def check_git_status():
    """Verifica el estado de Git"""
    print("\n📊 Verificando estado de Git...")
    try:
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=".")
        if result.returncode == 0:
            if result.stdout.strip():
                print("⚠️ Hay cambios sin commitear:")
                print(result.stdout)
                return False
            else:
                print("✅ Repositorio limpio, todos los cambios commiteados")
                return True
        else:
            print("❌ Error ejecutando git status")
            return False
    except Exception as e:
        print(f"❌ Error verificando Git: {e}")
        return False

def main():
    """Función principal de verificación"""
    print("🔍 VERIFICACIÓN PRE-DESPLIEGUE PARA STREAMLIT CLOUD")
    print("=" * 60)

    checks = [
        check_requirements,
        check_streamlit_config,
        check_main_app,
        check_secrets_template,
        check_git_status
    ]

    results = []
    for check in checks:
        results.append(check())

    print("\n" + "=" * 60)
    print("📋 RESUMEN DE VERIFICACIÓN:")

    if all(results):
        print("✅ TODOS LOS CHECKS PASARON - Listo para desplegar en Streamlit Cloud!")
        print("\n📝 Próximos pasos:")
        print("1. Ve a https://share.streamlit.io/")
        print("2. Conecta tu cuenta de GitHub")
        print("3. Selecciona el repositorio: arguellosolanogerardo-cloud/consultor-gerard-v2")
        print("4. Archivo principal: consultar_web.py")
        print("5. Haz clic en 'Deploy'")
        print("\n🔗 URL esperada: https://arguellosolanogerardo-cloud-consultor-gerard-v2.streamlit.app/")
    else:
        print("❌ Algunos checks fallaron - Revisa los errores arriba")

    print("\n🔐 IMPORTANTE - Configurar Secrets en Streamlit Cloud:")
    print("- GOOGLE_API_KEY: Tu clave de Google AI Studio")
    print("- GOOGLE_CREDENTIALS: JSON de Service Account para Google Sheets")
    print("- SHEET_ID: ID de tu hoja de Google Sheets")

if __name__ == "__main__":
    main()