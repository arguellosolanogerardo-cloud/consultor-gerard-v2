#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 ASISTENTE INTERACTIVO PARA CLONAR GERARD
===========================================

Te guía paso a paso para crear una nueva instancia de GERARD
con preguntas simples y claras.

Uso:
    python clonar_gerard_facil.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

def print_header():
    """Muestra el header del asistente."""
    print("\n" + "=" * 70)
    print("🤖 ASISTENTE PARA CLONAR GERARD - MODO FÁCIL")
    print("=" * 70)
    print("Te ayudo a crear una nueva versión de GERARD para tus archivos .srt")
    print()

def print_step(step, title):
    """Imprime cada paso claramente."""
    print(f"\n🔄 PASO {step}: {title}")
    print("─" * 50)

def ask_question(question, default="", required=True):
    """Hace una pregunta al usuario con validación."""
    while True:
        if default:
            response = input(f"❓ {question} [{default}]: ").strip()
            if not response:
                response = default
        else:
            response = input(f"❓ {question}: ").strip()
        
        if response or not required:
            return response
        else:
            print("⚠️  Esta respuesta es obligatoria. Intenta de nuevo.")

def confirm_action(message):
    """Pide confirmación al usuario."""
    while True:
        response = input(f"🤔 {message} (s/n): ").strip().lower()
        if response in ['s', 'si', 'sí', 'y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("⚠️  Responde 's' para sí o 'n' para no")

def show_preview(config):
    """Muestra un preview de la configuración."""
    print("\n📋 RESUMEN DE TU CONFIGURACIÓN:")
    print("=" * 40)
    print(f"🤖 Nombre del asistente: {config['nombre']}")
    print(f"📁 Carpeta destino: {config['carpeta']}")
    print(f"🎯 Tema: {config['tema'] if config['tema'] else 'General'}")
    print(f"📄 Archivos .srt: {config['carpeta']}/documentos_srt/")
    print()

def run_command(cmd, cwd=None, show_output=True):
    """Ejecuta comando con manejo de errores."""
    try:
        if show_output:
            print(f"🔄 Ejecutando: {cmd}")
        
        result = subprocess.run(cmd, shell=True, cwd=cwd, 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            if show_output:
                print("✅ Comando exitoso")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return False

def collect_user_config():
    """Recolecta la configuración del usuario paso a paso."""
    print_header()
    
    config = {}
    
    # Paso 1: Nombre del asistente
    print_step(1, "NOMBRE DEL NUEVO ASISTENTE")
    print("💡 Ejemplos: GERARD_OVNIS, GERARD_HISTORIA, GERARD_CIENCIA")
    config['nombre'] = ask_question("¿Cómo quieres llamar al nuevo asistente?", "GERARD_TEMA2")
    
    # Paso 2: Carpeta destino
    print_step(2, "UBICACIÓN DEL NUEVO PROYECTO")
    print("💡 Ejemplo: E:/proyecto-ovnis, C:/mis-proyectos/historia")
    carpeta_sugerida = f"E:/proyecto-{config['nombre'].lower().replace('gerard_', '')}"
    config['carpeta'] = ask_question("¿Dónde quieres crear el nuevo proyecto?", carpeta_sugerida)
    
    # Paso 3: Tema/descripción (opcional)
    print_step(3, "TEMA DEL PROYECTO (OPCIONAL)")
    print("💡 Ejemplos: 'documentales sobre OVNIs', 'videos históricos', 'contenido científico'")
    config['tema'] = ask_question("¿Cuál es el tema de los archivos que vas a analizar?", "", required=False)
    
    return config

def create_clone(config):
    """Crea el clon con la configuración proporcionada."""
    
    # Paso 4: Crear directorio
    print_step(4, "CREANDO DIRECTORIO")
    try:
        os.makedirs(config['carpeta'], exist_ok=True)
        print(f"✅ Directorio creado: {config['carpeta']}")
    except Exception as e:
        print(f"❌ Error creando directorio: {e}")
        return False
    
    # Paso 5: Clonar repositorio
    print_step(5, "DESCARGANDO CÓDIGO FUENTE")
    print("⏳ Esto puede tardar 1-2 minutos...")
    
    clone_cmd = "git clone https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2.git ."
    if not run_command(clone_cmd, config['carpeta']):
        return False
    
    # Paso 6: Personalizar archivos
    print_step(6, "PERSONALIZANDO CONFIGURACIÓN")
    
    consultar_path = Path(config['carpeta']) / "consultar_web.py"
    
    try:
        with open(consultar_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Lista de reemplazos
        replacements = [
            ('Nombre: GERARD', f'Nombre: {config["nombre"]}'),
            ('<div class="title-style">GERARD</div>', 
             f'<div class="title-style">{config["nombre"]}</div>'),
            ('st.markdown("## GERARD")', 
             f'st.markdown("## {config["nombre"]}")'),
            ('page_title="GERARD"', 
             f'page_title="{config["nombre"]}"'),
            ('🔬 GERARD v3.01 - Sistema', 
             f'🔬 {config["nombre"]} v3.01 - Sistema'),
            ('Eres GERARD, un sistema', 
             f'Eres {config["nombre"]}, un sistema')
        ]
        
        # Aplicar reemplazos
        for old, new in replacements:
            content = content.replace(old, new)
            
        # Agregar descripción del tema
        if config['tema']:
            content = content.replace(
                'especializado en arqueología documental', 
                f'especializado en arqueología documental de {config["tema"]}'
            )
        
        # Guardar archivo
        with open(consultar_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Configuración personalizada para {config['nombre']}")
        
    except Exception as e:
        print(f"❌ Error personalizando: {e}")
        return False
    
    # Paso 7: Crear estructura
    print_step(7, "CREANDO ESTRUCTURA DE CARPETAS")
    
    carpetas = ['documentos_srt', 'faiss_index', 'logs', 'assets', '.streamlit']
    
    for carpeta in carpetas:
        try:
            carpeta_path = Path(config['carpeta']) / carpeta
            carpeta_path.mkdir(exist_ok=True)
            print(f"✅ Carpeta: {carpeta}")
        except Exception as e:
            print(f"⚠️ Error con {carpeta}: {e}")
    
    # Paso 8: Copiar configuración
    print_step(8, "COPIANDO CONFIGURACIÓN")
    
    # Copiar .env si existe
    env_original = Path.cwd() / ".env"
    env_destino = Path(config['carpeta']) / ".env"
    
    if env_original.exists():
        try:
            shutil.copy2(env_original, env_destino)
            print("✅ Configuración API copiada")
        except Exception as e:
            print(f"⚠️ No se pudo copiar configuración: {e}")
            print("💡 Deberás configurar tu API key manualmente")
    
    return True

def show_final_instructions(config):
    """Muestra las instrucciones finales."""
    print("\n" + "🎉" * 20)
    print("¡CLONACIÓN COMPLETADA EXITOSAMENTE!")
    print("🎉" * 20)
    
    print(f"\n📁 Tu nuevo proyecto está en: {config['carpeta']}")
    print(f"🤖 Nombre del asistente: {config['nombre']}")
    
    print("\n📋 PRÓXIMOS PASOS:")
    print("─" * 30)
    
    print("1️⃣ AGREGAR TUS ARCHIVOS:")
    print(f"   📄 Copia tus archivos .srt a:")
    print(f"   📁 {config['carpeta']}/documentos_srt/")
    
    print("\n2️⃣ INICIAR LA APLICACIÓN:")
    print(f"   💻 Abre terminal en: {config['carpeta']}")
    print("   ⚡ Ejecuta: python consultar_web.py")
    
    print("\n3️⃣ PRIMERA EJECUCIÓN:")
    print("   ⏳ La primera vez tardará 5-10 minutos")
    print("   🔄 Se procesarán automáticamente tus archivos")
    print("   📊 Se creará el índice de búsqueda")
    
    print("\n💡 CONSEJOS:")
    print("   🔑 Verifica que tu API key esté configurada")
    print("   📱 Puedes usar la app inmediatamente")
    print("   🌐 Para web: sube a GitHub + Streamlit Cloud")
    
    print(f"\n🚀 ¡Disfruta tu {config['nombre']} personalizado!")

def main():
    """Función principal del asistente."""
    try:
        # Recopilar configuración
        config = collect_user_config()
        
        # Mostrar resumen y confirmar
        show_preview(config)
        
        if not confirm_action("¿Proceder con esta configuración?"):
            print("❌ Operación cancelada por el usuario")
            return False
        
        # Crear el clon
        print("\n🚀 INICIANDO PROCESO DE CLONACIÓN...")
        
        if not create_clone(config):
            print("❌ Error durante la clonación")
            return False
        
        # Mostrar instrucciones finales
        show_final_instructions(config)
        
        return True
        
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    if success:
        print("✅ ¡Proceso completado exitosamente!")
    else:
        print("❌ Proceso terminado con errores")
    print("=" * 50)
    
    input("\n🔚 Presiona Enter para salir...")
    sys.exit(0 if success else 1)