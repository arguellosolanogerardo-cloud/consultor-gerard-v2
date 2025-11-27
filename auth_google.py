import os
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import streamlit as st

# Configuración
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

def get_flow(redirect_uri):
    """Crea y retorna el flujo de OAuth 2.0"""
    # 1. Intentar cargar desde secrets (Prioridad para Cloud)
    if "google_auth" in st.secrets:
        # google-auth-oauthlib espera una estructura {"web": {...}}
        client_config = {"web": dict(st.secrets["google_auth"])}
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=SCOPES
        )
    # 2. Intentar cargar desde archivo (Local)
    elif os.path.exists(CLIENT_SECRETS_FILE):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES
        )
    else:
        return None

    flow.redirect_uri = redirect_uri
    return flow

def get_login_url(redirect_uri):
    """Genera la URL de autorización de Google"""
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
