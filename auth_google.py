import os
import streamlit as st

# Importaciones con manejo defensivo de errores
try:
    import google_auth_oauthlib.flow
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Google Auth libraries not available: {e}")
    GOOGLE_LIBS_AVAILABLE = False

# Configuración
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]


def get_flow(redirect_uri):
    """Crea y retorna el flujo de OAuth 2.0"""
    if not GOOGLE_LIBS_AVAILABLE:
        return None
        
    # PRIORIDAD 1: Intentar cargar desde archivo (Local) - Para testing
    if os.path.exists(CLIENT_SECRETS_FILE):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES
        )
    # PRIORIDAD 2: Intentar cargar desde secrets (Cloud)
    elif "google_auth" in st.secrets:
        # Construir manualmente el client_config con la estructura correcta
        secrets_auth = st.secrets["google_auth"]
        client_config = {
            "web": {
                "client_id": secrets_auth["client_id"],
                "project_id": secrets_auth["project_id"],
                "auth_uri": secrets_auth["auth_uri"],
                "token_uri": secrets_auth["token_uri"],
                "auth_provider_x509_cert_url": secrets_auth["auth_provider_x509_cert_url"],
                "client_secret": secrets_auth["client_secret"],
                # Incluir redirect_uris explícitamente para que OAuth funcione
                "redirect_uris": [redirect_uri]
            }
        }
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=SCOPES
        )
    else:
        return None

    flow.redirect_uri = redirect_uri
    return flow

def get_login_url(redirect_uri):
    """Genera la URL de autorización de Google"""
    if not GOOGLE_LIBS_AVAILABLE:
        return None
        
    flow = get_flow(redirect_uri)
    if not flow:
        return None
        
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return authorization_url


def get_user_info(code, redirect_uri):
    """Intercambia el código por credenciales y obtiene info del usuario"""
    if not GOOGLE_LIBS_AVAILABLE:
        return None
        
    try:
        flow = get_flow(redirect_uri)
        if not flow:
            return None
            
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Obtener info del usuario usando la API de Google
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        
        return user_info
    except Exception as e:
        print(f"Error obteniendo info de usuario: {e}")
        return None
