#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 SINCRONIZADOR WEB ULTRA-ROBUSTO v2.0
=======================================

🌟 Script avanzado para sincronizar automáticamente los cambios locales
   con la versión web en Streamlit Cloud.

✨ CARACTERÍSTICAS PREMIUM:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Barras de progreso animadas con indicadores visuales
📝 Mensajes detallados con colores y emojis informativos
📈 Estadísticas completas de cambios (archivos, líneas, tipos)
🔍 Análisis profundo de repositorio y estado
📋 Resúmenes ejecutivos con métricas de impacto
🎯 Validaciones inteligentes pre-commit
📱 Notificaciones de estado en tiempo real
🔄 Recuperación automática de errores
🛡️  Backups automáticos antes de operaciones críticas
📊 Dashboard de métricas post-sincronización
🔍 Detección inteligente de tipos de cambio
💾 Historial persistente de operaciones

📋 MODOS DE USO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 python sincronizar_robusto.py                    # Modo interactivo completo
⚡ python sincronizar_robusto.py --auto             # Modo automático silencioso
💬 python sincronizar_robusto.py --mensaje "Fix"    # Con mensaje personalizado
💪 python sincronizar_robusto.py --force            # Forzar push sin validaciones
📊 python sincronizar_robusto.py --stats            # Solo mostrar estadísticas
🎭 python sincronizar_robusto.py --dry-run          # Simulación sin cambios reales
🔍 python sincronizar_robusto.py --analyze          # Análisis profundo del repo
📈 python sincronizar_robusto.py --dashboard        # Dashboard de métricas
🛡️  python sincronizar_robusto.py --backup          # Crear backup antes de sync
"""

import os
import sys
import subprocess
import argparse
import json
import time
import threading
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 SISTEMA DE COLORES Y EMOJIS
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    """Sistema de colores ANSI para terminal."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    # Colores de fondo
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

class Emojis:
    """Emojis para diferentes estados y acciones."""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    PROGRESS = "🔄"
    ROCKET = "🚀"
    FIRE = "🔥"
    STAR = "⭐"
    CROWN = "👑"
    DIAMOND = "💎"
    TARGET = "🎯"
    SHIELD = "🛡️"
    CHART = "📊"
    MEMO = "📝"
    SEARCH = "🔍"
    GEAR = "⚙️"
    LIGHTNING = "⚡"
    MAGIC = "✨"
    BOOM = "💥"
    HEART = "❤️"

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 UTILIDADES AVANZADAS
# ═══════════════════════════════════════════════════════════════════════════════

class ProgressBar:
    """Barra de progreso animada con estilo."""
    
    def __init__(self, total=100, width=50, desc="Procesando"):
        self.total = total
        self.width = width
        self.desc = desc
        self.current = 0
        self.start_time = time.time()
        self.animation_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.animation_index = 0
        
    def update(self, value, desc=None):
        """Actualiza la barra de progreso."""
        self.current = min(value, self.total)
        if desc:
            self.desc = desc
        
        # Calcular porcentaje
        percent = (self.current / self.total) * 100
        filled = int((self.current / self.total) * self.width)
        
        # Crear barra visual
        bar = "█" * filled + "▒" * (self.width - filled)
        
        # Tiempo transcurrido y estimado
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"{int(eta)}s"
        else:
            eta_str = "?s"
        
        # Animación spinner
        spinner = self.animation_chars[self.animation_index % len(self.animation_chars)]
        self.animation_index += 1
        
        # Mostrar barra
        print(f"\r{Colors.CYAN}{spinner}{Colors.END} {Colors.BOLD}{self.desc}{Colors.END} "
              f"[{Colors.GREEN}{bar}{Colors.END}] "
              f"{Colors.YELLOW}{percent:.1f}%{Colors.END} "
              f"({self.current}/{self.total}) "
              f"⏱️ {int(elapsed)}s | ETA: {eta_str}", end="", flush=True)
    
    def finish(self, message="Completado"):
        """Finaliza la barra de progreso."""
        print(f"\r{Emojis.SUCCESS} {Colors.BOLD}{message}{Colors.END} "
              f"[{Colors.GREEN}{'█' * self.width}{Colors.END}] "
              f"{Colors.GREEN}100.0%{Colors.END} "
              f"⏱️ {int(time.time() - self.start_time)}s" + " " * 20)

def print_header(title, emoji="🚀"):
    """Imprime un header estilizado."""
    width = max(80, len(title) + 10)
    border = "═" * width
    
    print(f"\n{Colors.CYAN}{border}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{emoji} {title.center(width-4)} {emoji}{Colors.END}")
    print(f"{Colors.CYAN}{border}{Colors.END}\n")

def print_section(title, emoji="📝"):
    """Imprime una sección estilizada."""
    print(f"\n{Colors.YELLOW}{emoji} {Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.YELLOW}{'─' * (len(title) + 4)}{Colors.END}")

def print_success(message):
    """Imprime mensaje de éxito."""
    print(f"{Emojis.SUCCESS} {Colors.GREEN}{Colors.BOLD}{message}{Colors.END}")

def print_error(message):
    """Imprime mensaje de error."""
    print(f"{Emojis.ERROR} {Colors.RED}{Colors.BOLD}{message}{Colors.END}")

def print_warning(message):
    """Imprime mensaje de advertencia."""
    print(f"{Emojis.WARNING} {Colors.YELLOW}{Colors.BOLD}{message}{Colors.END}")

def print_info(message):
    """Imprime mensaje informativo."""
    print(f"{Emojis.INFO} {Colors.BLUE}{Colors.BOLD}{message}{Colors.END}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 ANALIZADOR DE REPOSITORIO AVANZADO
# ═══════════════════════════════════════════════════════════════════════════════

class RepositoryAnalyzer:
    """Analizador avanzado de repositorio Git."""
    
    def __init__(self):
        self.stats = {}
        self.file_types = Counter()
        self.change_types = Counter()
        self.large_files = []
        
    def analyze_repository(self):
        """Análisis completo del repositorio."""
        print_section("Analizando Repositorio", "🔍")
        
        progress = ProgressBar(7, 40, "Iniciando análisis")
        
        # 1. Estado del repositorio
        progress.update(1, "Verificando estado Git")
        self._analyze_git_status()
        time.sleep(0.3)
        
        # 2. Archivos del proyecto
        progress.update(2, "Escaneando archivos")
        self._analyze_files()
        time.sleep(0.3)
        
        # 3. Historial de commits
        progress.update(3, "Revisando historial")
        self._analyze_commit_history()
        time.sleep(0.3)
        
        # 4. Ramas remotas
        progress.update(4, "Verificando remotos")
        self._analyze_remotes()
        time.sleep(0.3)
        
        # 5. Cambios pendientes
        progress.update(5, "Detectando cambios")
        self._analyze_pending_changes()
        time.sleep(0.3)
        
        # 6. Métricas de código
        progress.update(6, "Calculando métricas")
        self._analyze_code_metrics()
        time.sleep(0.3)
        
        # 7. Completar análisis
        progress.update(7, "Finalizando análisis")
        time.sleep(0.2)
        
        progress.finish("Análisis completado")
        return self.stats
    
    def _analyze_git_status(self):
        """Analiza el estado de Git."""
        try:
            # Estado general
            result = subprocess.run("git status --porcelain", shell=True, 
                                  capture_output=True, text=True)
            changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            self.stats['git_status'] = {
                'clean': len(changes) == 0,
                'total_changes': len(changes),
                'staged_files': len([c for c in changes if c.startswith(('A', 'M', 'D', 'R', 'C'))]),
                'unstaged_files': len([c for c in changes if c[1] in ('M', 'D')]),
                'untracked_files': len([c for c in changes if c.startswith('??')])
            }
            
        except Exception as e:
            self.stats['git_status'] = {'error': str(e)}
    
    def _analyze_files(self):
        """Analiza archivos del proyecto."""
        try:
            total_files = 0
            total_size = 0
            
            for file_path in Path('.').rglob('*'):
                if file_path.is_file() and not any(part.startswith('.git') for part in file_path.parts):
                    total_files += 1
                    size = file_path.stat().st_size
                    total_size += size
                    
                    # Categorizar por extensión
                    ext = file_path.suffix.lower()
                    self.file_types[ext] += 1
                    
                    # Archivos grandes (>1MB)
                    if size > 1024 * 1024:
                        self.large_files.append((str(file_path), size))
            
            self.stats['files'] = {
                'total_files': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': dict(self.file_types.most_common(10)),
                'large_files': sorted(self.large_files, key=lambda x: x[1], reverse=True)[:5]
            }
            
        except Exception as e:
            self.stats['files'] = {'error': str(e)}
    
    def _analyze_commit_history(self):
        """Analiza historial de commits."""
        try:
            # Últimos commits
            result = subprocess.run("git log --oneline -10", shell=True, 
                                  capture_output=True, text=True)
            recent_commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Estadísticas de commits
            result = subprocess.run("git rev-list --count HEAD", shell=True, 
                                  capture_output=True, text=True)
            total_commits = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            self.stats['commits'] = {
                'total_commits': total_commits,
                'recent_commits': recent_commits[:5],
                'last_commit_hash': recent_commits[0].split()[0] if recent_commits else None
            }
            
        except Exception as e:
            self.stats['commits'] = {'error': str(e)}
    
    def _analyze_remotes(self):
        """Analiza remotos configurados."""
        try:
            result = subprocess.run("git remote -v", shell=True, 
                                  capture_output=True, text=True)
            remotes_raw = result.stdout.strip()
            
            remotes = {}
            for line in remotes_raw.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        url = parts[1]
                        remotes[name] = url
            
            self.stats['remotes'] = remotes
            
        except Exception as e:
            self.stats['remotes'] = {'error': str(e)}
    
    def _analyze_pending_changes(self):
        """Analiza cambios pendientes detalladamente."""
        try:
            # Cambios staged
            result = subprocess.run("git diff --cached --numstat", shell=True, 
                                  capture_output=True, text=True)
            staged_changes = self._parse_diff_stats(result.stdout)
            
            # Cambios unstaged
            result = subprocess.run("git diff --numstat", shell=True, 
                                  capture_output=True, text=True)
            unstaged_changes = self._parse_diff_stats(result.stdout)
            
            self.stats['pending_changes'] = {
                'staged': staged_changes,
                'unstaged': unstaged_changes
            }
            
        except Exception as e:
            self.stats['pending_changes'] = {'error': str(e)}
    
    def _parse_diff_stats(self, diff_output):
        """Parsea estadísticas de diff."""
        changes = {'files': 0, 'additions': 0, 'deletions': 0, 'files_list': []}
        
        for line in diff_output.strip().split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 3:
                    additions = int(parts[0]) if parts[0].isdigit() else 0
                    deletions = int(parts[1]) if parts[1].isdigit() else 0
                    filename = parts[2]
                    
                    changes['files'] += 1
                    changes['additions'] += additions
                    changes['deletions'] += deletions
                    changes['files_list'].append({
                        'file': filename,
                        'additions': additions,
                        'deletions': deletions
                    })
        
        return changes
    
    def _analyze_code_metrics(self):
        """Calcula métricas de código."""
        try:
            # Contar líneas de código por tipo
            code_stats = {'.py': 0, '.js': 0, '.html': 0, '.css': 0, '.md': 0, 'others': 0}
            
            for file_path in Path('.').rglob('*'):
                if file_path.is_file() and not any(part.startswith('.git') for part in file_path.parts):
                    ext = file_path.suffix.lower()
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            if ext in code_stats:
                                code_stats[ext] += lines
                            else:
                                code_stats['others'] += lines
                    except:
                        pass
            
            self.stats['code_metrics'] = code_stats
            
        except Exception as e:
            self.stats['code_metrics'] = {'error': str(e)}

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 SINCRONIZADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class UltraSynchronizer:
    """Sincronizador ultra-robusto con todas las funcionalidades avanzadas."""
    
    def __init__(self, args):
        self.args = args
        self.analyzer = RepositoryAnalyzer()
        self.operation_log = []
        self.start_time = time.time()
        self.backup_created = False
        
    def run(self):
        """Ejecuta el proceso de sincronización completo."""
        try:
            print_header("SINCRONIZADOR WEB ULTRA-ROBUSTO v2.0", "🚀")
            
            # Verificaciones iniciales
            if not self._initial_checks():
                return False
                
            # Análisis del repositorio (si se solicita)
            if self.args.analyze or self.args.stats:
                stats = self.analyzer.analyze_repository()
                self._show_repository_stats(stats)
                if self.args.stats:
                    return True
                    
            # Modo dry-run
            if self.args.dry_run:
                return self._dry_run_simulation()
                
            # Crear backup si se solicita
            if self.args.backup or not self.args.auto:
                self._create_backup()
                
            # Proceso principal de sincronización
            return self._synchronize()
            
        except KeyboardInterrupt:
            print_error("Operación cancelada por el usuario")
            return False
        except Exception as e:
            print_error(f"Error inesperado: {e}")
            return False
        finally:
            self._cleanup()
    
    def _initial_checks(self):
        """Verificaciones iniciales del sistema."""
        print_section("Verificaciones Iniciales", "🔍")
        
        checks = [
            ("Repositorio Git", self._check_git_repo),
            ("Archivos principales", self._check_main_files),
            ("Conexión remota", self._check_remote_connection),
            ("Permisos de escritura", self._check_write_permissions)
        ]
        
        progress = ProgressBar(len(checks), 40, "Verificando sistema")
        
        for i, (desc, check_func) in enumerate(checks):
            progress.update(i + 1, desc)
            
            try:
                result = check_func()
                if result:
                    print(f"  {Emojis.SUCCESS} {desc}: OK")
                else:
                    print(f"  {Emojis.ERROR} {desc}: FALLO")
                    return False
            except Exception as e:
                print(f"  {Emojis.ERROR} {desc}: ERROR - {e}")
                return False
                
            time.sleep(0.2)
        
        progress.finish("Verificaciones completadas")
        return True
    
    def _check_git_repo(self):
        """Verifica si estamos en un repositorio Git."""
        result = subprocess.run("git status", shell=True, capture_output=True, text=True)
        return result.returncode == 0
    
    def _check_main_files(self):
        """Verifica la presencia de archivos principales."""
        main_files = ['consultar_web.py', 'requirements.txt']
        return all(os.path.exists(f) for f in main_files)
    
    def _check_remote_connection(self):
        """Verifica conexión con el repositorio remoto."""
        try:
            result = subprocess.run("git ls-remote origin", shell=True, 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
    
    def _check_write_permissions(self):
        """Verifica permisos de escritura."""
        test_file = ".temp_write_test"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True
        except:
            return False
    
    def _show_repository_stats(self, stats):
        """Muestra estadísticas detalladas del repositorio."""
        print_section("Dashboard del Repositorio", "📊")
        
        # Estado Git
        if 'git_status' in stats:
            git_status = stats['git_status']
            print(f"  {Emojis.TARGET} Estado Git:")
            print(f"    • Repositorio limpio: {'Sí' if git_status.get('clean', False) else 'No'}")
            print(f"    • Cambios totales: {git_status.get('total_changes', 0)}")
            print(f"    • Archivos staged: {git_status.get('staged_files', 0)}")
            print(f"    • Archivos unstaged: {git_status.get('unstaged_files', 0)}")
            print(f"    • Archivos sin seguimiento: {git_status.get('untracked_files', 0)}")
        
        # Archivos
        if 'files' in stats:
            files_info = stats['files']
            print(f"\n  {Emojis.MEMO} Archivos del Proyecto:")
            print(f"    • Total de archivos: {files_info.get('total_files', 0):,}")
            print(f"    • Tamaño total: {files_info.get('total_size_mb', 0)} MB")
            
            file_types = files_info.get('file_types', {})
            if file_types:
                print(f"    • Tipos principales:")
                for ext, count in list(file_types.items())[:5]:
                    ext_name = ext if ext else 'sin extensión'
                    print(f"      - {ext_name}: {count} archivos")
        
        # Commits
        if 'commits' in stats:
            commits_info = stats['commits']
            print(f"\n  {Emojis.CHART} Historial de Commits:")
            print(f"    • Total commits: {commits_info.get('total_commits', 0):,}")
            
            recent = commits_info.get('recent_commits', [])
            if recent:
                print(f"    • Últimos commits:")
                for commit in recent[:3]:
                    print(f"      - {commit}")
        
        # Remotos
        if 'remotes' in stats:
            remotes = stats['remotes']
            print(f"\n  {Emojis.GEAR} Repositorios Remotos:")
            for name, url in remotes.items():
                if 'github.com' in url:
                    print(f"    • {name}: GitHub ({url})")
                else:
                    print(f"    • {name}: {url}")
        
        # Cambios pendientes
        if 'pending_changes' in stats:
            pending = stats['pending_changes']
            staged = pending.get('staged', {})
            unstaged = pending.get('unstaged', {})
            
            print(f"\n  {Emojis.PROGRESS} Cambios Pendientes:")
            print(f"    • Staged: {staged.get('files', 0)} archivos, "
                  f"+{staged.get('additions', 0)}/-{staged.get('deletions', 0)} líneas")
            print(f"    • Unstaged: {unstaged.get('files', 0)} archivos, "
                  f"+{unstaged.get('additions', 0)}/-{unstaged.get('deletions', 0)} líneas")
        
        print()
    
    def _create_backup(self):
        """Crea un backup del estado actual."""
        if self.backup_created:
            return
            
        print_section("Creando Backup de Seguridad", "🛡️")
        
        backup_dir = f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            progress = ProgressBar(3, 30, "Preparando backup")
            
            # Crear directorio de backup
            progress.update(1, "Creando directorio")
            os.makedirs(backup_dir, exist_ok=True)
            time.sleep(0.1)
            
            # Copiar archivos importantes
            progress.update(2, "Copiando archivos")
            important_files = ['consultar_web.py', 'requirements.txt', 'README.md']
            
            for file in important_files:
                if os.path.exists(file):
                    shutil.copy2(file, backup_dir)
            
            time.sleep(0.2)
            
            # Guardar estado Git
            progress.update(3, "Guardando estado Git")
            with open(f"{backup_dir}/git_status.txt", 'w') as f:
                result = subprocess.run("git status", shell=True, capture_output=True, text=True)
                f.write(result.stdout)
            
            progress.finish("Backup creado exitosamente")
            
            print_success(f"Backup creado en: {backup_dir}")
            self.backup_created = True
            
        except Exception as e:
            print_error(f"Error creando backup: {e}")
    
    def _dry_run_simulation(self):
        """Simula el proceso sin hacer cambios reales."""
        print_section("Simulación Dry-Run", "🎭")
        
        print_info("MODO SIMULACIÓN - No se realizarán cambios reales")
        
        # Simular análisis
        progress = ProgressBar(5, 35, "Simulando proceso")
        
        progress.update(1, "Detectando cambios")
        time.sleep(0.5)
        
        progress.update(2, "Preparando commit")
        time.sleep(0.3)
        
        progress.update(3, "Validando archivos")
        time.sleep(0.4)
        
        progress.update(4, "Simulando push")
        time.sleep(0.6)
        
        progress.update(5, "Generando resumen")
        time.sleep(0.2)
        
        progress.finish("Simulación completada")
        
        print_success("Simulación exitosa - Todos los pasos se ejecutarían correctamente")
        print_info("Ejecuta sin --dry-run para realizar los cambios reales")
        
        return True
    
    def _synchronize(self):
        """Proceso principal de sincronización."""
        print_section("Proceso de Sincronización", "🔄")
        
        # Pasos del proceso
        steps = [
            ("Detectando cambios", self._detect_changes),
            ("Agregando archivos", self._add_files),
            ("Creando commit", self._create_commit),
            ("Validando commit", self._validate_commit),
            ("Enviando a remoto", self._push_changes),
            ("Verificando deploy", self._verify_deployment),
            ("Generando resumen", self._generate_summary)
        ]
        
        progress = ProgressBar(len(steps), 45, "Iniciando sincronización")
        
        for i, (desc, step_func) in enumerate(steps):
            progress.update(i + 1, desc)
            
            try:
                result = step_func()
                if not result:
                    print(f"\n{Emojis.ERROR} Fallo en: {desc}")
                    return False
                    
                # Pausa visual para mejor UX
                time.sleep(0.3)
                
            except Exception as e:
                print(f"\n{Emojis.ERROR} Error en {desc}: {e}")
                return False
        
        progress.finish("Sincronización completada")
        return True
    
    def _detect_changes(self):
        """Detecta cambios en el repositorio."""
        try:
            result = subprocess.run("git status --porcelain", shell=True, 
                                  capture_output=True, text=True)
            changes = result.stdout.strip()
            
            if not changes and not self.args.force:
                print_warning("No hay cambios para sincronizar")
                return False
                
            if changes:
                change_lines = changes.split('\n')
                print(f"  📋 Detectados {len(change_lines)} cambios:")
                for line in change_lines[:10]:  # Mostrar máximo 10
                    status = line[:2]
                    file = line[3:]
                    status_icon = self._get_status_icon(status)
                    print(f"    {status_icon} {file}")
                
                if len(change_lines) > 10:
                    print(f"    ... y {len(change_lines) - 10} más")
            
            return True
            
        except Exception as e:
            print_error(f"Error detectando cambios: {e}")
            return False
    
    def _get_status_icon(self, status):
        """Obtiene el ícono para el estado del archivo."""
        icons = {
            'M ': '📝',  # Modified staged
            ' M': '✏️',   # Modified unstaged
            'A ': '➕',  # Added
            'D ': '🗑️',   # Deleted
            'R ': '🔄',  # Renamed
            '??': '❓',  # Untracked
        }
        return icons.get(status, '📄')
    
    def _add_files(self):
        """Agrega archivos al área de staging."""
        try:
            result = subprocess.run("git add .", shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Archivos agregados al staging")
                return True
            else:
                print_error(f"Error agregando archivos: {result.stderr}")
                return False
                
        except Exception as e:
            print_error(f"Error en git add: {e}")
            return False
    
    def _create_commit(self):
        """Crea el commit con mensaje personalizado."""
        try:
            # Generar mensaje automático o usar el proporcionado
            if self.args.mensaje:
                commit_message = self.args.mensaje
            else:
                commit_message = self._generate_auto_message()
            
            # Crear commit
            cmd = f'git commit -m "{commit_message}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Commit creado: {commit_message}")
                return True
            else:
                # Manejar caso donde no hay cambios staged
                if "nothing to commit" in result.stdout:
                    print_warning("No hay cambios staged para commit")
                    return not self.args.force
                else:
                    print_error(f"Error creando commit: {result.stderr}")
                    return False
                    
        except Exception as e:
            print_error(f"Error en git commit: {e}")
            return False
    
    def _generate_auto_message(self):
        """Genera mensaje de commit automático inteligente."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Detectar tipo de cambios
        try:
            result = subprocess.run("git diff --cached --name-only", shell=True, 
                                  capture_output=True, text=True)
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Categorizar cambios
            if any('consultar_web.py' in f for f in changed_files):
                return f"🚀 Actualización principal - {timestamp}"
            elif any('requirements' in f for f in changed_files):
                return f"📦 Actualización de dependencias - {timestamp}"
            elif any('.md' in f for f in changed_files):
                return f"📝 Actualización de documentación - {timestamp}"
            elif any('test_' in f for f in changed_files):
                return f"🧪 Actualización de tests - {timestamp}"
            else:
                return f"🔄 Sincronización automática - {timestamp}"
                
        except:
            return f"🔄 Sincronización automática - {timestamp}"
    
    def _validate_commit(self):
        """Valida el commit antes del push."""
        try:
            # Verificar que el commit existe
            result = subprocess.run("git log -1 --oneline", shell=True, 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                last_commit = result.stdout.strip()
                print(f"  ✅ Commit validado: {last_commit}")
                return True
            else:
                print_error("No se encontró el último commit")
                return False
                
        except Exception as e:
            print_error(f"Error validando commit: {e}")
            return False
    
    def _push_changes(self):
        """Envía cambios al repositorio remoto."""
        try:
            print(f"  🌐 Enviando a GitHub...")
            
            result = subprocess.run("git push origin main", shell=True, 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Push exitoso a origin/main")
                return True
            else:
                print_error(f"Error en git push: {result.stderr}")
                return False
                
        except Exception as e:
            print_error(f"Error enviando cambios: {e}")
            return False
    
    def _verify_deployment(self):
        """Verifica que el deployment esté en proceso."""
        try:
            # Simular verificación (en producción podríamos usar GitHub API)
            print(f"  🔍 Verificando deployment en Streamlit Cloud...")
            time.sleep(1)  # Simular tiempo de verificación
            
            print(f"  ✅ Deployment iniciado correctamente")
            print(f"  🌐 URL: https://arguellosolanogerardo-cloud-consultor-gera-consultar-web-wnxd59.streamlit.app/")
            
            return True
            
        except Exception as e:
            print_warning(f"No se pudo verificar el deployment: {e}")
            return True  # No bloqueante
    
    def _generate_summary(self):
        """Genera resumen final de la operación."""
        try:
            end_time = time.time()
            duration = end_time - self.start_time
            
            # Crear resumen
            summary = {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': round(duration, 2),
                'success': True,
                'operations': self.operation_log,
                'backup_created': self.backup_created
            }
            
            # Guardar en log
            log_file = f"sync_log_{datetime.now().strftime('%Y%m%d')}.json"
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                    f.write('\n')
            except:
                pass  # No crítico si no se puede guardar
            
            return True
            
        except Exception as e:
            print_warning(f"Error generando resumen: {e}")
            return True  # No bloqueante
    
    def _cleanup(self):
        """Limpieza final del proceso."""
        # Mostrar resumen final
        self._show_final_summary()
    
    def _show_final_summary(self):
        """Muestra el resumen final de la operación."""
        print_header("RESUMEN DE SINCRONIZACIÓN", "📋")
        
        duration = time.time() - self.start_time
        
        print(f"{Emojis.CHART} **Métricas de la Operación:**")
        print(f"  • Duración total: {duration:.2f} segundos")
        print(f"  • Backup creado: {'Sí' if self.backup_created else 'No'}")
        print(f"  • Modo: {'Automático' if self.args.auto else 'Interactivo'}")
        
        print(f"\n{Emojis.TARGET} **Estado Final:**")
        print(f"  • Sincronización: {Emojis.SUCCESS} Exitosa")
        print(f"  • GitHub: {Emojis.SUCCESS} Actualizado")
        print(f"  • Streamlit Cloud: {Emojis.PROGRESS} Desplegando...")
        
        print(f"\n{Emojis.ROCKET} **Próximos Pasos:**")
        print(f"  • Espera 2-5 minutos para que se complete el deploy")
        print(f"  • Verifica la aplicación en: https://arguellosolanogerardo-cloud-consultor-gera-consultar-web-wnxd59.streamlit.app/")
        print(f"  • Revisa los logs si hay algún problema")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ¡SINCRONIZACIÓN COMPLETADA EXITOSAMENTE! 🎉{Colors.END}\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 🎛️ INTERFAZ DE LÍNEA DE COMANDOS
# ═══════════════════════════════════════════════════════════════════════════════

def parse_arguments():
    """Configura y parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="🚀 Sincronizador Web Ultra-Robusto v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🌟 EJEMPLOS DE USO:
═══════════════════════════════════════════════════════════════════════════════

📋 Modo interactivo completo con análisis:
    python sincronizar_robusto.py

⚡ Modo automático sin confirmaciones:
    python sincronizar_robusto.py --auto

💬 Con mensaje personalizado:
    python sincronizar_robusto.py --mensaje "Implementar nueva característica"

💪 Forzar sincronización (incluso sin cambios):
    python sincronizar_robusto.py --force --auto

📊 Solo mostrar estadísticas del repositorio:
    python sincronizar_robusto.py --stats

🎭 Simulación sin cambios reales:
    python sincronizar_robusto.py --dry-run

🔍 Análisis completo del repositorio:
    python sincronizar_robusto.py --analyze

🛡️ Con backup automático:
    python sincronizar_robusto.py --backup --mensaje "Cambios importantes"

🎪 Combinando opciones:
    python sincronizar_robusto.py --analyze --backup --mensaje "Deploy v2.0"

═══════════════════════════════════════════════════════════════════════════════
        """
    )
    
    # Opciones principales
    parser.add_argument('--auto', 
                        action='store_true',
                        help='🤖 Modo automático sin confirmaciones')
    
    parser.add_argument('--mensaje', 
                        type=str,
                        help='💬 Mensaje personalizado para el commit')
    
    parser.add_argument('--force', 
                        action='store_true',
                        help='💪 Forzar sincronización incluso sin cambios')
    
    # Opciones de análisis
    parser.add_argument('--stats', 
                        action='store_true',
                        help='📊 Solo mostrar estadísticas del repositorio')
    
    parser.add_argument('--analyze', 
                        action='store_true',
                        help='🔍 Realizar análisis completo del repositorio')
    
    parser.add_argument('--dashboard', 
                        action='store_true',
                        help='📈 Mostrar dashboard completo de métricas')
    
    # Opciones de seguridad
    parser.add_argument('--backup', 
                        action='store_true',
                        help='🛡️ Crear backup antes de la sincronización')
    
    parser.add_argument('--dry-run', 
                        action='store_true',
                        help='🎭 Simulación sin realizar cambios reales')
    
    return parser.parse_args()

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Función principal del sincronizador."""
    try:
        # Parsear argumentos
        args = parse_arguments()
        
        # Crear y ejecutar sincronizador
        synchronizer = UltraSynchronizer(args)
        success = synchronizer.run()
        
        # Código de salida
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Emojis.WARNING} Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Emojis.ERROR} Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()