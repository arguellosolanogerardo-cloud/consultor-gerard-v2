"""
Servicio de Text-to-Speech usando Google Cloud TTS API
Genera audio MP3 del lado del servidor para evitar restricciones del iframe de Streamlit
"""
import os
import io
import base64
import json

# Intentar importar la biblioteca de Google Cloud TTS
TTS_AVAILABLE = False
try:
    from google.cloud import texttospeech
    from google.oauth2 import service_account
    TTS_AVAILABLE = True
except ImportError:
    print("[WARNING] google-cloud-texttospeech no disponible. Instala con: pip install google-cloud-texttospeech")


def _get_tts_client():
    """
    Crea un cliente de TTS usando credenciales de múltiples fuentes:
    1. Streamlit secrets (para Streamlit Cloud)
    2. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS
    3. Archivo JSON de credenciales local
    """
    try:
        import streamlit as st
        
        # Opción 1: Streamlit secrets
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            print("[TTS] Usando credenciales de Streamlit secrets")
            credentials_info = dict(st.secrets["gcp_service_account"])
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
            return texttospeech.TextToSpeechClient(credentials=credentials)
        
        # Opción 2: Variable de entorno o archivo local
        # Buscar archivo de credenciales
        possible_paths = [
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS', ''),
            'credencial json/midyear-node-436821-t3-525a146e96a0.json',
            'google_credentials.json',
            'credentials.json'
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                print(f"[TTS] Usando credenciales de archivo: {path}")
                credentials = service_account.Credentials.from_service_account_file(path)
                return texttospeech.TextToSpeechClient(credentials=credentials)
        
        # Opción 3: Credenciales por defecto de Google Cloud
        print("[TTS] Usando credenciales por defecto de Google Cloud")
        return texttospeech.TextToSpeechClient()
        
    except Exception as e:
        print(f"[TTS] Error al crear cliente: {type(e).__name__}: {e}")
        raise


def synthesize_text_to_mp3(text: str, voice_name: str = "es-ES-Standard-A") -> bytes | None:
    """
    Convierte texto a audio MP3 usando Google Cloud Text-to-Speech.
    
    Args:
        text: Texto a convertir (máximo 5000 caracteres)
        voice_name: Nombre de la voz. Opciones principales:
            - es-ES-Standard-A (Femenina, España)
            - es-ES-Standard-B (Masculina, España)
            - es-US-Standard-A (Femenina, Latinoamérica)
            - es-US-Standard-B (Masculina, Latinoamérica)
            - es-ES-Wavenet-B (Masculina de alta calidad, España)
            - es-US-Wavenet-A (Femenina de alta calidad, Latinoamérica)
    
    Returns:
        bytes: Audio en formato MP3, o None si hay error
    """
    if not TTS_AVAILABLE:
        print("[TTS] La biblioteca google-cloud-texttospeech no está disponible")
        return None
    
    if not text or not text.strip():
        print("[TTS] Texto vacío, no se puede generar audio")
        return None
    
    # Limitar longitud del texto (Google Cloud TTS tiene límite de 5000 bytes)
    if len(text) > 5000:
        text = text[:4900] + "... y más contenido."
    
    try:
        # Crear cliente con credenciales apropiadas
        client = _get_tts_client()
        
        # Configurar la entrada de texto
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Configurar la voz
        # Detectar el idioma base de la voz
        language_code = voice_name[:5]  # ej: "es-ES" o "es-US"
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        # Configurar el audio (MP3)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,  # Velocidad normal
            pitch=0.0  # Tono normal
        )
        
        # Realizar la síntesis
        print(f"[TTS] Generando audio con voz {voice_name}...")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        print(f"[TTS] Audio generado exitosamente ({len(response.audio_content)} bytes)")
        return response.audio_content
        
    except Exception as e:
        print(f"[TTS] Error al generar audio: {type(e).__name__}: {e}")
        return None


def get_audio_base64(audio_bytes: bytes) -> str:
    """
    Convierte bytes de audio a base64 para usar en HTML <audio>.
    """
    return base64.b64encode(audio_bytes).decode('utf-8')


def create_audio_html(audio_bytes: bytes, autoplay: bool = False) -> str:
    """
    Crea un elemento HTML <audio> con el audio embebido en base64.
    
    Args:
        audio_bytes: Audio en bytes (MP3)
        autoplay: Si True, reproduce automáticamente
    
    Returns:
        str: Código HTML del elemento audio
    """
    audio_b64 = get_audio_base64(audio_bytes)
    autoplay_attr = "autoplay" if autoplay else ""
    
    return f'''
    <audio controls {autoplay_attr} style="width: 100%; margin: 10px 0;">
        <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mpeg">
        Tu navegador no soporta el elemento de audio.
    </audio>
    '''


# Voces disponibles en español (las más usadas)
VOCES_ESPANOL = {
    "Femenina España": "es-ES-Standard-A",
    "Masculina España": "es-ES-Standard-B", 
    "Femenina Latinoamérica": "es-US-Standard-A",
    "Masculina Latinoamérica": "es-US-Standard-B",
    "Femenina España (Alta calidad)": "es-ES-Wavenet-C",
    "Masculina España (Alta calidad)": "es-ES-Wavenet-B",
    "Femenina Latinoamérica (Alta calidad)": "es-US-Wavenet-A",
    "Masculina Latinoamérica (Alta calidad)": "es-US-Wavenet-B",
}
