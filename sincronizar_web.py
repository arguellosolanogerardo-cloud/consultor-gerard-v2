#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SINCRONIZADOR AUTOMÁTICO LOCAL ↔ WEB
====================================

Script para sincronizar automáticamente los cambios locales con Streamlit Cloud.
Detecta cambios, hace commit y push automáticamente.

Uso:
    python sincronizar_web.py
    python sincronizar_web.py --mensaje "Mi mensaje personalizado"
    python sincronizar_web.py --force  # Sincronizar incluso sin cambios
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import json

def ejecutar_comando(comando, mostrar_output=True):
    """Ejecuta un comando y retorna el resultado."""
    try:
        result = subprocess.run(
            comando, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=os.getcwd()
        )
        
        if mostrar_output and result.stdout:
            print(result.stdout.strip())
            
        if result.stderr and "warning" not in result.stderr.lower():
            print(f"⚠️  {result.stderr.strip()}")
            
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        
    except Exception as e:
        print(f"❌ Error ejecutando comando: {e}")
        return False, "", str(e)

def verificar_git():
    """Verifica si estamos en un repositorio git."""
    exito, _, _ = ejecutar_comando("git status", False)
    if not exito:
        print("❌ Este directorio no es un repositorio Git")
        print("💡 Ejecuta: git init && git remote add origin <URL>")
        return False
    return True

def obtener_estado_git():
    """Obtiene el estado actual del repositorio."""
    print("🔍 Verificando estado del repositorio...")
    
    # Verificar archivos modificados
    exito, output, _ = ejecutar_comando("git status --porcelain", False)
    if not exito:
        return None
        
    archivos_modificados = []
    archivos_nuevos = []
    
    for linea in output.split('\n'):
        if linea.strip():
            estado = linea[:2]
            archivo = linea[3:].strip()
            
            if estado.startswith('M') or estado.startswith(' M'):
                archivos_modificados.append(archivo)
            elif estado.startswith('A') or estado.startswith('??'):
                archivos_nuevos.append(archivo)
    
    return {
        'modificados': archivos_modificados,
        'nuevos': archivos_nuevos,
        'hay_cambios': len(archivos_modificados) > 0 or len(archivos_nuevos) > 0
    }

def generar_mensaje_commit(estado):
    """Genera un mensaje de commit automático basado en los cambios."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Detectar tipo de cambios
    archivos_importantes = ['consultar_web.py', 'requirements.txt', 'runtime.txt', 'start_app.ps1']
    cambios_importantes = [f for f in estado['modificados'] + estado['nuevos'] 
                          if any(importante in f for importante in archivos_importantes)]
    
    if 'consultar_web.py' in str(cambios_importantes):
        categoria = "🔧 MEJORA APP"
    elif any('.md' in f for f in estado['modificados'] + estado['nuevos']):
        categoria = "📝 DOCS"
    elif 'requirements.txt' in str(cambios_importantes):
        categoria = "📦 DEPS"
    else:
        categoria = "🔄 SYNC"
    
    total_archivos = len(estado['modificados']) + len(estado['nuevos'])
    
    mensaje = f"{categoria}: Sincronización automática ({total_archivos} archivos) - {timestamp}"
    
    return mensaje

def sincronizar():
    """Ejecuta el proceso completo de sincronización."""
    print("🚀 SINCRONIZADOR LOCAL ↔ WEB")
    print("=" * 50)
    
    # Verificar git
    if not verificar_git():
        return False
    
    # Obtener estado
    estado = obtener_estado_git()
    if not estado:
        print("❌ No se pudo obtener el estado del repositorio")
        return False
    
    # Mostrar resumen
    print(f"📁 Archivos modificados: {len(estado['modificados'])}")
    print(f"📄 Archivos nuevos: {len(estado['nuevos'])}")
    
    if estado['modificados']:
        print("\n🔧 MODIFICADOS:")
        for archivo in estado['modificados'][:5]:  # Mostrar máximo 5
            print(f"   • {archivo}")
        if len(estado['modificados']) > 5:
            print(f"   • ... y {len(estado['modificados']) - 5} más")
    
    if estado['nuevos']:
        print("\n📄 NUEVOS:")
        for archivo in estado['nuevos'][:5]:  # Mostrar máximo 5
            print(f"   • {archivo}")
        if len(estado['nuevos']) > 5:
            print(f"   • ... y {len(estado['nuevos']) - 5} más")
    
    # Verificar si hay cambios
    if not estado['hay_cambios']:
        print("\n✅ No hay cambios para sincronizar")
        print("💡 Todo está actualizado con la web")
        return True
    
    return estado

def main():
    parser = argparse.ArgumentParser(description='Sincronizar cambios locales con Streamlit Cloud')
    parser.add_argument('--mensaje', '-m', help='Mensaje personalizado para el commit')
    parser.add_argument('--force', '-f', action='store_true', help='Forzar sincronización sin cambios')
    parser.add_argument('--auto', '-a', action='store_true', help='Modo automático sin confirmación')
    
    args = parser.parse_args()
    
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print(f"📂 Directorio de trabajo: {os.getcwd()}")
    
    # Ejecutar sincronización
    estado = sincronizar()
    
    if estado is True:  # No hay cambios
        if not args.force:
            return
        print("🔄 Forzando sincronización...")
    elif not estado:  # Error
        return
    
    # Generar mensaje de commit
    if args.mensaje:
        mensaje = args.mensaje
    else:
        mensaje = generar_mensaje_commit(estado)
    
    print(f"\n💬 Mensaje de commit: {mensaje}")
    
    # Confirmar acción (a menos que sea modo automático)
    if not args.auto:
        respuesta = input("\n¿Continuar con la sincronización? (S/n): ").strip().lower()
        if respuesta and respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
            print("❌ Sincronización cancelada")
            return
    
    print("\n🔄 Iniciando sincronización...")
    
    # 1. Agregar todos los cambios
    print("1️⃣ Agregando archivos...")
    exito, _, _ = ejecutar_comando("git add .")
    if not exito:
        print("❌ Error agregando archivos")
        return
    
    # 2. Hacer commit
    print("2️⃣ Creando commit...")
    comando_commit = f'git commit -m "{mensaje}"'
    exito, _, error = ejecutar_comando(comando_commit, False)
    
    if not exito and "nothing to commit" in error:
        print("✅ No hay cambios nuevos para commit")
    elif not exito:
        print(f"❌ Error en commit: {error}")
        return
    else:
        print("✅ Commit creado exitosamente")
    
    # 3. Push a origin main
    print("3️⃣ Subiendo cambios a GitHub...")
    exito, output, error = ejecutar_comando("git push origin main")
    
    if not exito:
        print(f"❌ Error en push: {error}")
        print("💡 Verifica tu conexión a internet y permisos del repositorio")
        return
    
    print("✅ ¡Cambios subidos exitosamente!")
    
    # 4. Información final
    print("\n🎉 SINCRONIZACIÓN COMPLETA")
    print("=" * 50)
    print("🌐 Streamlit Cloud se actualizará automáticamente en 2-5 minutos")
    print("🔗 URL: https://arguellosolanogerardo-cloud-consultor-gera-consultar-web-wnxd59.streamlit.app/")
    
    # Guardar log
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'mensaje': mensaje,
        'archivos_modificados': len(estado.get('modificados', [])) if isinstance(estado, dict) else 0,
        'archivos_nuevos': len(estado.get('nuevos', [])) if isinstance(estado, dict) else 0,
        'exito': True
    }
    
    try:
        log_file = "logs/sincronizacion_web.json"
        os.makedirs("logs", exist_ok=True)
        
        # Leer log existente
        logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        
        # Agregar nuevo entry
        logs.append(log_entry)
        
        # Mantener solo últimos 50 entries
        logs = logs[-50:]
        
        # Guardar
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
            
        print(f"📝 Log guardado en: {log_file}")
        
    except Exception as e:
        print(f"⚠️  No se pudo guardar el log: {e}")

if __name__ == "__main__":
    main()