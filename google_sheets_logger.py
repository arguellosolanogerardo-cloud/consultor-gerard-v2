
"""
Google Sheets Logger para GERARD

Este modulo envia automaticamente cada interaccion a una hoja de Google Sheets
para que puedas ver todos los logs de usuarios en tiempo real desde cualquier lugar.

Caracteristicas:
- Registro automatico en Google Sheets
- Columnas: Fecha/Hora, Usuario, Pregunta, Respuesta, Dispositivo, Navegador, OS, Ciudad, Pais, IP, Tiempo
- Acceso desde cualquier dispositivo
- Actualizacion en tiempo real
- Sin limites de almacenamiento (hasta 10M celdas)

Configuracion:
1. Crear un proyecto en Google Cloud Console
2. Habilitar Google Sheets API
3. Crear credenciales (Service Account)
4. Descargar archivo JSON de credenciales
5. Compartir la hoja de Google Sheets con el email del service account
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from typing import Dict, Optional, List
import json
import os
import re


class GoogleSheetsLogger:
    """
    Logger que envia interacciones a Google Sheets en tiempo real.
    """
    
    def __init__(
        self,
        credentials_file: str = "google_credentials.json",
        spreadsheet_name: str = "GERARD - Logs de Usuarios",
        worksheet_name: str = "Interacciones_v2",
        spreadsheet_key: str = "1O92R7BmxXfIOBO-qA3T0XpF1M2ena19bxqn8OrsqB2E"
    ):
        """
        Inicializa el logger de Google Sheets.
        
        Args:
            credentials_file: Ruta al archivo JSON de credenciales
            spreadsheet_name: Nombre de la hoja de calculo
            worksheet_name: Nombre de la pestana/worksheet
            spreadsheet_key: ID único de la hoja de cálculo (opcional, prioridad sobre nombre)
        """
        self.credentials_file = credentials_file
        self.spreadsheet_name = spreadsheet_name
        self.worksheet_name = worksheet_name
        self.spreadsheet_key = spreadsheet_key
        self.client = None
        self.worksheet = None
        self.enabled = False
        
        # Intentar conectar
        self._connect()
    
    def _connect(self):
        """Conecta con Google Sheets."""
        try:
            # Definir el scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Intentar obtener credenciales desde Streamlit secrets primero
            # Si el usuario indica una clave preferente en st.secrets['SHEETS_SERVICE_ACCOUNT']
            # usaremos esa entrada directamente (por ejemplo, 'gcp_service_account' o 'GOOGLE_CREDENTIALS').
            creds = None
            try:
                import streamlit as st
                # ...existing code...
                preferred_key = None
                try:
                    preferred_key = st.secrets.get('SHEETS_SERVICE_ACCOUNT')
                    if preferred_key:
                        print(f"[DEBUG] Preferencia SHEETS_SERVICE_ACCOUNT: {preferred_key}")
                except Exception:
                    preferred_key = None
                if hasattr(st, 'secrets'):
                    # ...existing code...
                    # Si existe una preferencia, solo usarla
                    if preferred_key and preferred_key in st.secrets:
                        print(f"[DEBUG] Using preferred service account secret: {preferred_key}")
                        raw_val = st.secrets[preferred_key]
                        # Streamlit stores JSON secrets as strings in the web UI; detect and parse
                        if isinstance(raw_val, str):
                            try:
                                import json as _json
                                gcp_dict = _json.loads(raw_val)
                            except Exception:
                                # Try to unescape newlines then parse (common when JSON stored as string)
                                try:
                                    gcp_dict = _json.loads(raw_val.replace('\\n', '\n'))
                                except Exception:
                                    print("[WARN] No se pudo parsear JSON desde secret preferido; será ignorado y se usará fallback")
                                    gcp_dict = None
                        elif isinstance(raw_val, dict):
                            gcp_dict = dict(raw_val)
                        else:
                            gcp_dict = raw_val
                        if gcp_dict:
                            creds = ServiceAccountCredentials.from_json_keyfile_dict(gcp_dict, scope)
                        else:
                            creds = None
                        print(f"[DEBUG] Credenciales cargadas exitosamente desde {preferred_key}")
                    elif 'gcp_service_account' in st.secrets:
                        # ...existing code...
                        gcp_dict = dict(st.secrets['gcp_service_account'])
                        # ...existing code...
                        # Usar credenciales desde secrets
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(
                            gcp_dict,
                            scope
                        )
                        # Guardar correo del service account para debug/identificación
                        try:
                            self.client_email = gcp_dict.get('client_email')
                        except Exception:
                            self.client_email = None
                        print("[DEBUG] Credenciales cargadas exitosamente desde gcp_service_account")
                    elif 'GOOGLE_CREDENTIALS' in st.secrets:
                        # ...existing code...
                        # GOOGLE_CREDENTIALS puede ser un string JSON o un dict
                        google_creds = st.secrets['GOOGLE_CREDENTIALS']
                        if isinstance(google_creds, str):
                            import json
                            gcp_dict = json.loads(google_creds)
                        else:
                            gcp_dict = dict(google_creds)
                        # ...existing code...
                        # Usar credenciales desde secrets
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(
                            gcp_dict,
                            scope
                        )
                        print("[DEBUG] Credenciales cargadas exitosamente desde GOOGLE_CREDENTIALS")
                    # Nueva clave alternativa para compatibilidad con documentación
                    elif 'GOOGLE_SHEETS_CREDENTIALS' in st.secrets:
                        google_creds = st.secrets['GOOGLE_SHEETS_CREDENTIALS']
                        if isinstance(google_creds, str):
                            import json
                            gcp_dict = json.loads(google_creds)
                        else:
                            gcp_dict = dict(google_creds)
                        creds = ServiceAccountCredentials.from_json_keyfile_dict(
                            gcp_dict,
                            scope
                        )
                        print("[DEBUG] Credenciales cargadas exitosamente desde GOOGLE_SHEETS_CREDENTIALS")
                    else:
                        print("[DEBUG] 'gcp_service_account' ni 'GOOGLE_CREDENTIALS' encontrados en st.secrets")
                else:
                    print("[DEBUG] st.secrets NO está disponible")
                    
            except Exception as e:
                print(f"[ERROR] Error cargando credenciales desde Streamlit secrets: {e}")
                import traceback
                traceback.print_exc()
            
            # Si no hay credenciales desde secrets, intentar archivo local
            if creds is None:
                # 1. Intentar variable de entorno (configurada por app_gerard.py en Cloud)
                env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                if env_creds and os.path.exists(env_creds):
                    print(f"[INFO] Usando credenciales desde variable de entorno: {env_creds}")
                    try:
                        creds = ServiceAccountCredentials.from_json_keyfile_name(env_creds, scope)
                        try:
                            import json as _json
                            with open(env_creds, 'r', encoding='utf-8') as _f:
                                _data = _json.load(_f)
                            self.client_email = _data.get('client_email')
                        except Exception:
                            self.client_email = None
                    except Exception as e:
                        print(f"[WARN] Falló carga desde variable de entorno: {e}")

                # 2. Si aun no hay creds, intentar archivo local por defecto
                if creds is None:
                    if not os.path.exists(self.credentials_file):
                        print(f"[!] Google Sheets Logger: Archivo de credenciales no encontrado: {self.credentials_file}")
                        print("    Para activar Google Sheets, sigue las instrucciones en GOOGLE_SHEETS_SETUP.md")
                        return
                    
                    print(f"[INFO] Usando credenciales desde archivo local: {self.credentials_file}")
                    # Autenticar desde archivo
                    creds = ServiceAccountCredentials.from_json_keyfile_name(
                        self.credentials_file,
                        scope
                    )
                    try:
                        import json as _json
                        with open(self.credentials_file, 'r', encoding='utf-8') as _f:
                            _data = _json.load(_f)
                        self.client_email = _data.get('client_email')
                    except Exception:
                        self.client_email = None

            # Soporte adicional: si hay un secret SHEET_ID definido para Streamlit Cloud,
            # preferimos usarlo como spreadsheet key en lugar del valor por defecto.
            try:
                if hasattr(st, 'secrets') and 'SHEET_ID' in st.secrets:
                    sheet_secret = st.secrets['SHEET_ID']
                    if sheet_secret and isinstance(sheet_secret, str) and len(sheet_secret) > 10:
                        print(f"[DEBUG] Usando SHEET_ID desde st.secrets: {sheet_secret}")
                        self.spreadsheet_key = sheet_secret
            except Exception:
                # Ignorar si st no está disponible o la clave no es válida
                pass
            
            # Mostrar correo del service account (solo para debug no sensible)
            try:
                if creds:
                    creds_dict_for_debug = getattr(creds, 'json_key', None)
                    if not creds_dict_for_debug:
                        # Algunos tipos de credenciales ponen el diccionario en ._service_account_email o en la variable original
                        creds_dict_for_debug = None
                    if creds_dict_for_debug:
                        print(f"[DEBUG] Service Account: {creds_dict_for_debug.get('client_email')}")
            except Exception:
                pass

            self.client = gspread.authorize(creds)
            
            # Abrir o crear la hoja de calculo
            spreadsheet = None
            
            # 1. Intentar por ID (Key) si existe
            if self.spreadsheet_key:
                try:
                    print(f"[INFO] Intentando abrir hoja por ID: {self.spreadsheet_key}")
                    spreadsheet = self.client.open_by_key(self.spreadsheet_key)
                    print(f"[OK] Hoja abierta por ID: {spreadsheet.title}")
                except Exception as e:
                    print(f"[WARN] No se pudo abrir por ID: {e}")
                    # Si no se pudo abrir por ID, intentar usar SHEET_NAME desde secrets si existe
                    try:
                        if hasattr(st, 'secrets') and 'SHEET_NAME' in st.secrets:
                            alt_name = st.secrets['SHEET_NAME']
                            print(f"[DEBUG] Intentando abrir hoja por nombre desde SHEET_NAME: {alt_name}")
                            spreadsheet = self.client.open(alt_name)
                            print(f"[OK] Hoja abierta por nombre: {spreadsheet.title}")
                    except Exception:
                        pass
            
            # 2. Si falló o no hay ID, intentar por nombre
            if spreadsheet is None:
                try:
                    print(f"[INFO] Intentando abrir hoja por nombre: {self.spreadsheet_name}")
                    spreadsheet = self.client.open(self.spreadsheet_name)
                except gspread.SpreadsheetNotFound:
                    print(f"[!] Hoja '{self.spreadsheet_name}' no encontrada. Creala y compartela con el service account.")
                    return
            
            # Abrir o crear el worksheet
            try:
                self.worksheet = spreadsheet.worksheet(self.worksheet_name)
            except gspread.WorksheetNotFound:
                # Crear nuevo worksheet con encabezados
                self.worksheet = spreadsheet.add_worksheet(
                    title=self.worksheet_name,
                    rows=1000,
                    cols=15
                )
                self._setup_headers()
            
            self.enabled = True
            print(f"[OK] Google Sheets Logger conectado exitosamente: {self.spreadsheet_name}")
            
        except Exception as e:
            print(f"[!] Error conectando con Google Sheets: {e}")
            print("    El logging continuara localmente sin Google Sheets")
    
    def _setup_headers(self):
        """Configura los encabezados de la hoja."""
        headers = [
            "ID",
            "Fecha/Hora",
            "Usuario",
            "Pregunta",
            "Respuesta",
            "Dispositivo",
            "Navegador",
            "Sistema Operativo",
            "Ciudad",
            "Pais",
            "IP",
            "Tiempo Respuesta (s)",
            "Estado",
            "Error",
            "Email"
        ]
        
        self.worksheet.update('A1:O1', [headers])
        
        # Formatear encabezados (negrita, fondo gris)
        self.worksheet.format('A1:O1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
    
    def _hex_to_rgb(self, hex_color: str) -> Dict[str, float]:
        """Convierte color hex a RGB normalizado para Google Sheets (0.0-1.0)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return {
                'red': r / 255.0,
                'green': g / 255.0,
                'blue': b / 255.0
            }
        return {'red': 0, 'green': 0, 'blue': 0}  # Negro por defecto
    
    def _parse_html_to_rich_text(self, plain_text: str) -> List[Dict]:
        """
        Detecta patrones en texto plano y aplica formato rico.
        
        Patrones detectados:
        - **[VIDEO / AUDIO: archivo.srt |  → Verde oscuro
        - Minuto: 00:00:00 --> 00:00:00]** → Rojo
        - "texto entre comillas" → Azul
        - ### Encabezados → Amarillo
        
        Args:
            plain_text: Texto plano de la respuesta
        
        Returns:
            Lista de segmentos con formato para Google Sheets API
        """
        if not plain_text:
            return [{"text": "", "format": {}}]
        
        # Definir colores
        COLOR_GREEN = self._hex_to_rgb("#2E7D32")  # Verde oscuro: VIDEO / AUDIO
        COLOR_RED = self._hex_to_rgb("#FF0000")    # Rojo: Minutos/timestamps
        COLOR_BLUE = self._hex_to_rgb("#61AFEF")   # Azul: Citas textuales
        COLOR_YELLOW = self._hex_to_rgb("#E5C07B") # Amarillo: Encabezados
        
        segments = []
        current_pos = 0
        
        # Patrones a detectar (en orden de prioridad)
        patterns = [
            # 1. VIDEO / AUDIO con archivo (verde)
            (r'\*\*\[VIDEO / AUDIO:[^\]]+\|', COLOR_GREEN),
            
            # 2. Timestamps/Minutos (rojo)
            (r'Minuto:\s*\d{2}:\d{2}:\d{2}\s*-->\s*\d{2}:\d{2}:\d{2}\]\*\*', COLOR_RED),
            
            # 3. Encabezados con ### o #### (amarillo)
            (r'^#{3,4}\s+\*\*[^\*]+\*\*', COLOR_YELLOW),
            
            # 4. Texto entre comillas (azul) - solo si tiene más de 10 caracteres
            (r'"[^"]{10,}"', COLOR_BLUE),
        ]
        
        # Encontrar todas las coincidencias con sus posiciones
        matches = []
        for pattern, color in patterns:
            for match in re.finditer(pattern, plain_text, re.MULTILINE):
                matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(),
                    'color': color
                })
        
        # Ordenar por posición
        matches.sort(key=lambda x: x['start'])
        
        # Construir segmentos
        for match in matches:
            # Texto antes del match (sin formato)
            if current_pos < match['start']:
                before_text = plain_text[current_pos:match['start']]
                if before_text:
                    segments.append({
                        "text": before_text,
                        "format": {}
                    })
            
            # Texto del match (con color)
            segments.append({
                "text": match['text'],
                "format": {
                    "foregroundColor": match['color']
                }
            })
            
            current_pos = match['end']
        
        # Texto final (sin formato)
        if current_pos < len(plain_text):
            final_text = plain_text[current_pos:]
            if final_text:
                segments.append({
                    "text": final_text,
                    "format": {}
                })
        
        # Si no hay matches, devolver todo sin formato
        if not segments:
            segments = [{"text": plain_text, "format": {}}]
        
        return segments
    
    def _apply_rich_text_format(self, row_index: int, col_index: int, rich_text_segments: List[Dict]):
        """
        Aplica formato de texto enriquecido a una celda específica usando batch_update.
        
        Args:
            row_index: Índice de la fila (0-indexed)
            col_index: Índice de la columna (0-indexed, ej: 5 para columna F)
            rich_text_segments: Lista de segmentos con formato
        """
        if not rich_text_segments or not self.worksheet:
            return
        
        try:
            # Construir textFormatRuns para la API
            runs = []
            start_index = 0
            
            for segment in rich_text_segments:
                text = segment.get("text", "")
                fmt = segment.get("format", {})
                
                if text:
                    run = {"startIndex": start_index}
                    
                    if fmt and "foregroundColor" in fmt:
                        run["format"] = {"foregroundColor": fmt["foregroundColor"]}
                    
                    runs.append(run)
                    start_index += len(text)
            
            # Si no hay runs con formato, no hacer nada
            if not runs:
                return
            
            # Obtener el spreadsheet ID
            spreadsheet_id = self.worksheet.spreadsheet.id
            sheet_id = self.worksheet.id
            
            # Preparar el batch update
            requests = [{
                "updateCells": {
                    "rows": [{
                        "values": [{
                            "userEnteredValue": {
                                "stringValue": "".join([seg["text"] for seg in rich_text_segments])
                            },
                            "textFormatRuns": runs
                        }]
                    }],
                    "fields": "userEnteredValue,textFormatRuns",
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1
                    }
                }
            }]
            
            # Ejecutar batch update
            self.worksheet.spreadsheet.batch_update({"requests": requests})
            
        except Exception as e:
            print(f"[WARNING] No se pudo aplicar formato rico: {e}")
    
    def log_interaction(
        self,
        interaction_id: str,
        user: str,
        question: str,
        answer: str,
        device_info: Optional[Dict] = None,
        location_info: Optional[Dict] = None,
        timing: Optional[Dict] = None,
        success: bool = True,
        error: Optional[str] = None,
        user_email: Optional[str] = None
    ):
        """
        Registra una interaccion en Google Sheets.
        
        Args:
            interaction_id: ID unico de la interaccion
            user: Nombre del usuario
            question: Pregunta realizada
            answer: Respuesta generada
            device_info: Informacion del dispositivo
            location_info: Informacion de ubicacion
            timing: Informacion de tiempos
            success: Si fue exitosa
            error: Mensaje de error si aplica
            user_email: Email del usuario (opcional)
        """
        if not self.enabled:
            return
        
        try:
            # Preparar datos
            timestamp = datetime.now()
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # Informacion del dispositivo
            device_type = "Desconocido"
            browser = "Desconocido"
            os_type = "Desconocido"
            
            if device_info:
                device_type = device_info.get("device_type", "Desconocido")
                browser = device_info.get("browser", "Desconocido")
                os_type = device_info.get("os", "Desconocido")
            
            # Informacion de ubicacion
            city = "Desconocida"
            country = "Desconocido"
            ip = "No disponible"
            
            if location_info:
                city = location_info.get("city", "Desconocida")
                country = location_info.get("country", "Desconocido")
                ip = location_info.get("ip", "No disponible")
            
            # Tiempo de respuesta
            response_time = 0
            if timing:
                response_time = timing.get("total_time", 0)
            
            # Guardar la respuesta completa (sin límite de caracteres)
            answer_full = answer
            
            # Estado
            status = "[OK] Exitoso" if success else "[ERROR] Error"
            error_msg = error if error else ""
            
            # Crear fila
            row = [
                interaction_id,
                timestamp_str,
                user,
                question,
                answer_full,  # Respuesta completa
                device_type,
                browser,
                os_type,
                city,
                country,
                ip,
                f"{response_time:.2f}",
                status,
                error_msg,
                user_email if user_email else "No disponible"
            ]
            
            # Agregar fila a la hoja
            self.worksheet.append_row(row)
            
            # Aplicar formato rico a la respuesta basándose en patrones de texto
            try:
                # Siempre intentar aplicar formato rico si hay respuesta
                if answer_full and len(answer_full) > 10:
                    # Obtener el número de fila recién agregada
                    # Las filas empiezan en 1, y la primera fila es el header
                    all_rows = self.worksheet.get_all_values()
                    row_index = len(all_rows) - 1  # 0-indexed, última fila agregada
                    
                    # Parsear texto plano a segmentos con formato
                    rich_segments = self._parse_html_to_rich_text(answer_full)
                    
                    # Aplicar formato a la columna de respuesta (columna E, índice 4)
                    col_index = 4  # 0-indexed: A=0, B=1, C=2, D=3, E=4
                    self._apply_rich_text_format(row_index, col_index, rich_segments)
                    
                    print(f"[OK] Formato rico aplicado a la respuesta ({len(rich_segments)} segmentos)")
            except Exception as e:
                # Si falla el formato rico, continuar (ya tenemos el texto guardado)
                print(f"[WARNING] No se pudo aplicar formato rico: {e}")
            
            print(f"[OK] Interaccion registrada en Google Sheets: {user} - {question[:50]}...")
            
        except Exception as e:
            print(f"[!] Error registrando en Google Sheets: {e}")
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadisticas de la hoja.
        
        Returns:
            Diccionario con estadisticas
        """
        if not self.enabled:
            return {}
        
        try:
            # Obtener todas las filas
            all_rows = self.worksheet.get_all_values()
            
            if len(all_rows) <= 1:  # Solo headers
                return {
                    "total_interactions": 0,
                    "unique_users": 0
                }
            
            # Contar (excluyendo header)
            data_rows = all_rows[1:]
            
            users = set()
            for row in data_rows:
                if len(row) > 2:
                    users.add(row[2])  # Columna de usuario
            
            return {
                "total_interactions": len(data_rows),
                "unique_users": len(users)
            }
            
        except Exception as e:
            print(f"[!] Error obteniendo estadisticas: {e}")
            return {}


# Funcion de ayuda para integracion facil
def create_sheets_logger() -> Optional[GoogleSheetsLogger]:
    """
    Crea y retorna un logger de Google Sheets.
    
    Returns:
        GoogleSheetsLogger o None si no esta configurado
    """
    logger = GoogleSheetsLogger()
    return logger if logger.enabled else None