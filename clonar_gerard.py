#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 CLONADOR AUTOMÁTICO DE GERARD
===============================

Script para clonar la aplicación GERARD y configurarla 
para usar diferentes archivos .srt automáticamente.

Uso:
    python clonar_gerard.py --nombre "TEMA2" --carpeta "E:/proyecto-tema2"
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

def print_step(step, message):
    """Imprime paso con formato."""
    print(f"\n🔄 PASO {step}: {message}")
    print("─" * 50)

def run_command(cmd, cwd=None):
    """Ejecuta comando y maneja errores."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        print(f"✅ Éxito: {cmd}")
        return True
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return False

def clone_gerard(nuevo_nombre, carpeta_destino, tema_descripcion=""):
    """Clona y configura una nueva instancia de GERARD."""
    
    print("🚀 CLONADOR AUTOMÁTICO DE GERARD")
    print("=" * 50)
    
    # Paso 1: Crear directorio
    print_step(1, f"Creando directorio {carpeta_destino}")
    
    try:
        os.makedirs(carpeta_destino, exist_ok=True)
        print(f"✅ Directorio creado: {carpeta_destino}")
    except Exception as e:
        print(f"❌ Error creando directorio: {e}")
        return False
    
    # Paso 2: Clonar repositorio
    print_step(2, "Clonando repositorio original")
    
    clone_cmd = f"git clone https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2.git ."
    if not run_command(clone_cmd, carpeta_destino):
        return False
    
    # Paso 3: Configurar archivos
    print_step(3, "Configurando archivos para nuevo tema")
    
    # Modificar consultar_web.py
    consultar_path = Path(carpeta_destino) / "consultar_web.py"
    
    try:
        with open(consultar_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Reemplazos principales
        replacements = [
            ('Nombre: GERARD', f'Nombre: {nuevo_nombre}'),
            ('<div class="title-style">GERARD</div>', 
             f'<div class="title-style">{nuevo_nombre}</div>'),
            ('st.markdown("## GERARD")', 
             f'st.markdown("## {nuevo_nombre}")'),
            ('page_title="GERARD"', 
             f'page_title="{nuevo_nombre}"'),
            ('🔬 GERARD v3.01 - Sistema de Análisis', 
             f'🔬 {nuevo_nombre} v3.01 - Sistema de Análisis'),
            ('Eres GERARD, un sistema', 
             f'Eres {nuevo_nombre}, un sistema')
        ]
        
        # Aplicar reemplazos
        for old, new in replacements:
            content = content.replace(old, new)
            
        # Agregar descripción del tema si se proporciona
        if tema_descripcion:
            content = content.replace(
                'especializado en arqueología documental', 
                f'especializado en arqueología documental de {tema_descripcion}'
            )
        
        # Guardar archivo modificado
        with open(consultar_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Archivo consultar_web.py configurado para {nuevo_nombre}")
        
    except Exception as e:
        print(f"❌ Error configurando consultar_web.py: {e}")
        return False
    
    # Paso 4: Crear estructura de carpetas
    print_step(4, "Creando estructura de carpetas")
    
    carpetas_necesarias = [
        'documentos_srt',
        'faiss_index', 
        'logs',
        'assets',
        '.streamlit'
    ]
    
    for carpeta in carpetas_necesarias:
        carpeta_path = Path(carpeta_destino) / carpeta
        try:
            carpeta_path.mkdir(exist_ok=True)
            print(f"✅ Carpeta creada: {carpeta}")
        except Exception as e:
            print(f"❌ Error creando {carpeta}: {e}")
    
    # Paso 5: Copiar archivo .env si existe
    print_step(5, "Configurando variables de entorno")
    
    env_original = Path.cwd() / ".env"
    env_destino = Path(carpeta_destino) / ".env"
    
    if env_original.exists():
        try:
            shutil.copy2(env_original, env_destino)
            print("✅ Archivo .env copiado")
        except Exception as e:
            print(f"⚠️ No se pudo copiar .env: {e}")
    else:
        print("⚠️ No se encontró archivo .env en el proyecto original")
        print("💡 Deberás configurar tu API key manualmente")
    
    # Paso 6: Limpiar archivos innecesarios
    print_step(6, "Limpiando archivos innecesarios")
    
    archivos_limpiar = [
        'faiss_index/.faiss_ready',
        'faiss_index/index.faiss',
        'faiss_index/index.pkl',
        'gerard_log.txt'
    ]
    
    for archivo in archivos_limpiar:
        archivo_path = Path(carpeta_destino) / archivo
        try:
            if archivo_path.exists():
                archivo_path.unlink()
                print(f"✅ Eliminado: {archivo}")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar {archivo}: {e}")
    
    # Paso 7: Crear archivo README personalizado
    print_step(7, "Creando documentación")
    
    readme_content = f"""# {nuevo_nombre} - Consultor Especializado

## 🎯 Descripción
Esta es una instancia personalizada de GERARD configurada para:
{tema_descripcion if tema_descripcion else "Análisis de documentos específicos"}

## 📁 Estructura
- `documentos_srt/` - Coloca aquí tus archivos .srt
- `faiss_index/` - Índice vectorial (se genera automáticamente)
- `logs/` - Registros de conversaciones

## 🚀 Uso
1. Coloca tus archivos .srt en `documentos_srt/`
2. Ejecuta `python consultar_web.py`
3. El sistema procesará automáticamente los archivos

## ⚙️ Configuración
- Configura tu API key de Google en archivo .env
- El primer arranque tardará más tiempo (procesamiento inicial)

Creado automáticamente el {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    try:
        readme_path = Path(carpeta_destino) / "README_PERSONALIZADO.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print("✅ README personalizado creado")
    except Exception as e:
        print(f"⚠️ No se pudo crear README: {e}")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("🎉 ¡CLONACIÓN COMPLETADA EXITOSAMENTE!")
    print("=" * 60)
    print(f"📁 Ubicación: {carpeta_destino}")
    print(f"🤖 Nombre: {nuevo_nombre}")
    print(f"📋 Tema: {tema_descripcion}")
    
    print("\n📋 PRÓXIMOS PASOS:")
    print("1. 📄 Coloca tus archivos .srt en documentos_srt/")
    print("2. 🔑 Configura tu API key en .env (si no se copió)")
    print("3. 🚀 Ejecuta: python consultar_web.py")
    print("4. ⏳ Espera que se procesen los archivos (primera vez)")
    
    print(f"\n🌐 Para desplegar en Streamlit Cloud:")
    print("1. 📤 Sube a un nuevo repositorio GitHub")
    print("2. 🔗 Conecta con Streamlit Cloud")
    print("3. 🎯 ¡Listo para usar!")
    
    return True

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Clonar y configurar GERARD para nuevos temas")
    
    parser.add_argument('--nombre', 
                        required=True,
                        help='Nombre del nuevo asistente (ej: GERARD_OVNIS)')
    
    parser.add_argument('--carpeta',
                        required=True, 
                        help='Carpeta destino (ej: E:/proyecto-ovnis)')
    
    parser.add_argument('--tema',
                        default="",
                        help='Descripción del tema (ej: "archivos sobre OVNIs")')
    
    args = parser.parse_args()
    
    # Validar argumentos
    if not args.nombre or not args.carpeta:
        print("❌ Error: Debes especificar --nombre y --carpeta")
        return False
    
    # Ejecutar clonación
    success = clone_gerard(args.nombre, args.carpeta, args.tema)
    
    if success:
        print("\n✅ ¡Proceso completado exitosamente!")
        return True
    else:
        print("\n❌ Error durante el proceso de clonación")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)