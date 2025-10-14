#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SINCRONIZACIÓN RÁPIDA LOCAL ↔ WEB
=================================

Script ultra-simple para sincronizar cambios con Streamlit Cloud.
Un solo comando y listo.

Uso:
    python sync_rapido.py
"""

import os
import subprocess
from datetime import datetime

def run_command(cmd):
    """Ejecuta comando y muestra resultado."""
    print(f"🔄 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=os.getcwd())
    return result.returncode == 0

def main():
    print("🚀 SINCRONIZACIÓN RÁPIDA")
    print("=" * 40)
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("consultar_web.py"):
        print("❌ No se encontró consultar_web.py")
        print("💡 Ejecuta este script desde la carpeta del proyecto")
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    mensaje = f"🔄 Sync rápido - {timestamp}"
    
    print(f"💬 Mensaje: {mensaje}")
    print()
    
    # 1. Git add
    if not run_command("git add ."):
        print("❌ Error agregando archivos")
        return
    
    # 2. Git commit
    if not run_command(f'git commit -m "{mensaje}"'):
        print("⚠️  Posiblemente no hay cambios nuevos")
    
    # 3. Git push
    if not run_command("git push origin main"):
        print("❌ Error subiendo cambios")
        return
    
    print()
    print("✅ ¡SINCRONIZACIÓN COMPLETA!")
    print("🌐 Streamlit Cloud se actualizará en 2-5 minutos")
    print("🔗 https://arguellosolanogerardo-cloud-consultor-gera-consultar-web-wnxd59.streamlit.app/")

if __name__ == "__main__":
    main()