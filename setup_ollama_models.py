#!/usr/bin/env python3
"""
Script para probar la disponibilidad de modelos Ollama y instalar si es necesario
"""
import subprocess
import sys
import time

def run_command(cmd, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n[INFO] {description}")
    print(f"[CMD] {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("[SUCCESS] Comando ejecutado correctamente")
            if result.stdout:
                print(f"[STDOUT] {result.stdout.strip()}")
        else:
            print(f"[ERROR] Código de salida: {result.returncode}")
            if result.stderr:
                print(f"[STDERR] {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("[ERROR] Comando timeout")
        return False
    except Exception as e:
        print(f"[ERROR] Excepción: {e}")
        return False

def check_ollama_running():
    """Verifica si Ollama está ejecutándose"""
    return run_command("ollama list", "Verificando si Ollama está ejecutándose")

def pull_model(model_name):
    """Descarga un modelo de Ollama"""
    return run_command(f"ollama pull {model_name}", f"Descargando modelo {model_name}")

def test_model(model_name):
    """Prueba si un modelo está disponible"""
    return run_command(f"ollama run {model_name} --format json 'echo test'", f"Probando modelo {model_name}")

def main():
    print("=== VERIFICACIÓN DE MODELOS OLLAMA ===")

    # Verificar si Ollama está corriendo
    if not check_ollama_running():
        print("\n[ERROR] Ollama no está ejecutándose. Por favor inicia Ollama primero.")
        print("Puedes descargarlo desde: https://ollama.ai/download")
        sys.exit(1)

    # Modelos a probar en orden de preferencia
    models_to_try = [
        "mistral:7b",      # Modelo principal que queremos usar
        "llama2:7b",       # Alternativa
        "phi3:3.8b",       # Modelo pequeño
        "gemma:2b"         # Muy pequeño
    ]

    available_models = []

    for model in models_to_try:
        print(f"\n--- Probando modelo: {model} ---")
        if pull_model(model):
            available_models.append(model)
            print(f"[SUCCESS] Modelo {model} disponible")
        else:
            print(f"[WARNING] Modelo {model} no disponible")

    if available_models:
        print("\n[INFO] Modelos disponibles:")
        for model in available_models:
            print(f"  - {model}")

        # Usar el primer modelo disponible
        best_model = available_models[0]
        print(f"\n[RECOMMENDATION] Usar modelo: {best_model}")

        # Actualizar el archivo de configuración si es necesario
        update_config(best_model)
    else:
        print("\n[ERROR] No se pudo descargar ningún modelo")
        sys.exit(1)

def update_config(model_name):
    """Actualiza la configuración en consultar_web.py"""
    print(f"\n[INFO] Actualizando configuración para usar modelo: {model_name}")

    # Leer el archivo actual
    try:
        with open("consultar_web.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Reemplazar los modelos
        content = content.replace('model="mistral:7b"', f'model="{model_name}"')
        content = content.replace('model="llama2:7b"', f'model="{model_name}"')

        # Escribir de vuelta
        with open("consultar_web.py", "w", encoding="utf-8") as f:
            f.write(content)

        print("[SUCCESS] Configuración actualizada")

    except Exception as e:
        print(f"[ERROR] No se pudo actualizar la configuración: {e}")

if __name__ == "__main__":
    main()