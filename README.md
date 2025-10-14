# GERARD — asistente de búsqueda sobre archivos SRT

Pequeña app que indexa archivos `.srt` en FAISS y expone dos frontends:

- `consultar_terminal.py`: CLI interactiva.
- `consultar_web.py`: UI en Streamlit (archivo principal para deploy).

## Contenido del repositorio

- `ingestar.py` — carga `.srt` desde `documentos_srt/`, los divide en trozos y crea `./faiss_index`.
- `consultar_terminal.py` — cliente CLI que pregunta a GERARD y muestra salida JSON coloreada.
- `consultar_web.py` — interfaz Streamlit; espera la variable `GOOGLE_API_KEY` y usa `st.secrets` en despliegue.
- `documentos_srt/` — carpeta con los archivos SRT (datos). No recomendable subir si contienen material privado.
- `faiss_index/` — base vectorial persistida (NO se recomienda subir al repo).
- `.env.sample`, `.streamlit/secrets.toml`, `.github/copilot-instructions.md`, `.gitignore` y `requirements.txt`.

## Requisitos

- Python 3.10+ recomendado
- Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Configuración de la API Key (obligatorio)

La app usa la librería `langchain-google-genai` que requiere `GOOGLE_API_KEY`.

- Localmente: crea un archivo `.env` en la raíz (no comitear) copiando `.env.sample` y añadiendo tu clave:

```powershell
# En PowerShell (temporal para la sesión)
$env:GOOGLE_API_KEY = '<TU_API_KEY>'

# O crea un .env con:
## GOOGLE_API_KEY=<TU_API_KEY>
```

- En Streamlit Cloud: añade la clave desde la interfaz de la App → Settings → Secrets con la entrada exacta `GOOGLE_API_KEY`.

Nota: NO subas esa clave al repositorio. Usa `st.secrets` en Cloud o variables de entorno locales.

## Configuración de Google Sheets Logger (opcional pero recomendado)

Para registrar las interacciones de usuarios en Google Sheets:

### 1. Crear Service Account en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita las APIs: Google Sheets API y Google Drive API
4. Ve a "IAM & Admin" → "Service Accounts"
5. Crea una nueva Service Account (ej: "gerard-sheets-logger")
6. Genera una nueva clave JSON y descárgala

### 2. Configurar Google Sheets

1. Crea una nueva hoja de cálculo en Google Sheets
2. Comparte la hoja con el email de la Service Account (permiso Editor)
3. Copia el ID de la hoja de la URL (entre `/d/` y `/edit`)

### 3. Configurar Secrets en Streamlit Cloud

Ve a tu app en Streamlit Cloud → Settings → Secrets y añade:

```toml
# API Key de Google AI Studio (obligatorio)
GOOGLE_API_KEY = "tu_clave_real_aqui"

# Credenciales de Google Sheets (opcional)
GOOGLE_CREDENTIALS = """
{
  "type": "service_account",
  "project_id": "tu-proyecto-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "gerard-sheets-logger@tu-proyecto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
  "universe_domain": "googleapis.com"
}
"""

# Configuración del Logger (opcional)
SHEET_ID = "tu_sheet_id_aqui"
SHEET_NAME = "Interacciones"
```

### 4. Diagnosticar problemas en Streamlit Cloud

Si el logging no funciona en Streamlit Cloud, ejecuta el script de diagnóstico:

```powershell
streamlit run diagnostico_secrets.py
```

Este script mostrará qué secrets están disponibles y te ayudará a configurar correctamente las credenciales.

## Comandos habituales

- Generar/recrear la base vectorial (ejecutar cuando añadas/actualices SRTs):

```powershell
python ingestar.py
```

- Ejecutar la UI local (Streamlit):

```powershell
streamlit run consultar_web.py
```

- Ejecutar la CLI interactiva:

```powershell
python consultar_terminal.py
```

## Formato de salida (importante)

El modelo debe responder estrictamente con un array JSON de objetos. Cada objeto tiene dos claves:

- `type`: `normal` o `emphasis`.
- `content`: string. Las citas de fuente deben ir dentro del `content`, por ejemplo:

```json
[
  {"type":"normal","content":"Resumen: ... "},
  {"type":"emphasis","content":"concepto clave"},
  {"type":"normal","content":" (Fuente: archivo.srt, Timestamp: 00:01:23 --> 00:01:25)"}
]
```

Los scripts extraen el JSON mediante `re.search(r'\[.*\]')` y luego `json.loads(...)`. Evita que el modelo añada texto fuera del array.

## Seguridad y limpieza de claves expuestas

- Si tu API key estuvo expuesta en commits anteriores, revoca/regenera la clave en Google Cloud inmediatamente.
- Puedo ayudarte a preparar pasos para eliminar la clave del historial Git (BFG o git filter-repo) si lo solicitas.

## Qué subir al repositorio

- Subir: `*.py` (código), `requirements.txt`, `.env.sample`, `.streamlit/secrets.toml` (plantilla), `README.md`, `.github/*`, `.gitignore`.
- No subir: `chroma_db/`, `chroma_db.zip`, `gerard_log.txt`, `.env` con claves, `venv/`, `documentos_srt/` (opcional; subir solo si corresponde).

## Troubleshooting rápido

- Error "GOOGLE_API_KEY no está configurada": asegúrate de que la variable esté en el entorno o añadida en Streamlit Secrets con la clave EXACTA `GOOGLE_API_KEY`.
- Error con Google Sheets logging: ejecuta `streamlit run diagnostico_secrets.py` para verificar que las credenciales estén configuradas correctamente en Streamlit Cloud.
- Si Chroma devuelve poco o nada: borra `./chroma_db` y ejecuta `python ingestar.py` para regenerarla.
- Problemas de conexión en Streamlit Cloud: verifica que las secrets estén en formato TOML válido y que las credenciales de Google Sheets sean un JSON válido.

## Próximos pasos sugeridos

- Añadir `README.md` (hecho).
- (Opcional) Crear GitHub Action que bloquee commits con `.env` o `.streamlit/secrets.toml` con claves reales.
- (Opcional) Ayuda para limpiar el historial Git si la clave fue expuesta.

Si quieres que genere la GitHub Action preventiva o que limpie el historial de Git automáticamente, dime y lo preparo.

<!-- Last updated: 2025-10-13 10:30:02 -->
