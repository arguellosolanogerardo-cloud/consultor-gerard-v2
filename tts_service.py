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
        
        # Opción 1: Streamlit secrets (buscar en vertex_ai o gcp_service_account)
        if hasattr(st, 'secrets'):
            # Prioridad a vertex_ai (proyecto midyear-node-436821-t3)
            if 'vertex_ai' in st.secrets:
                print("[TTS] Usando credenciales de Streamlit secrets [vertex_ai]")
                credentials_info = dict(st.secrets["vertex_ai"])
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                return texttospeech.TextToSpeechClient(credentials=credentials)
            elif 'gcp_service_account' in st.secrets:
                print("[TTS] Usando credenciales de Streamlit secrets [gcp_service_account]")
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
        return None, "Biblioteca google-cloud-texttospeech no instalada"
    
    if not text or not text.strip():
        return None, "El texto proporcionado está vacío"
    
    # Limitar longitud del texto (Google Cloud TTS tiene límite de 5000 bytes)
    if len(text) > 5000:
        text = text[:4900] + "... y más contenido."
    
    try:
        # Crear cliente con credenciales apropiadas
        client = _get_tts_client()
        
        # Configurar la entrada de texto
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Configurar la voz
        # Detectar el idioma base de la voz de forma más robusta
        # Voces pueden ser es-MX-..., es-US-..., o es-419-...
        parts = voice_name.split('-')
        if len(parts) >= 2:
            if parts[1].isdigit(): # Caso es-419
                language_code = f"{parts[0]}-{parts[1]}"
            else: # Caso es-MX, es-US, etc.
                language_code = f"{parts[0]}-{parts[1]}"
        else:
            language_code = "es-MX" # Default seguro
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        # Configurar el audio (MP3)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.9,  # Velocidad: 90% (ajustado por usuario)
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
        return response.audio_content, None
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"[TTS] Error al generar audio: {error_msg}")
        return None, error_msg


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
    <div class="neo-player-container">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
            
            .neo-player-container {{
                background: rgba(10, 10, 15, 0.85);
                backdrop-filter: blur(15px);
                -webkit-backdrop-filter: blur(15px);
                border: 1px solid rgba(0, 255, 65, 0.4);
                border-radius: 20px;
                padding: 15px;
                margin: 10px 0;
                font-family: 'Orbitron', sans-serif;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8), 
                            inset 0 0 15px rgba(0, 255, 65, 0.1);
                overflow: hidden;
                position: relative;
            }}

            .player-layout {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}

            .play-btn-wrapper {{
                position: relative;
                flex-shrink: 0;
            }}

            .play-btn {{
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: rgba(0, 255, 65, 0.1);
                border: 2px solid #00ff41;
                color: #00ff41 !important;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 0 15px rgba(0, 255, 65, 0.3);
                z-index: 2;
                font-size: 20px;
                user-select: none;
            }}

            .play-btn:hover {{
                background: rgba(0, 255, 65, 0.2);
                transform: scale(1.05);
                box-shadow: 0 0 25px rgba(0, 255, 65, 0.5);
            }}

            .play-btn.playing {{
                border-color: #ff00ff;
                color: #ff00ff !important;
                box-shadow: 0 0 15px rgba(255, 0, 255, 0.3);
            }}

            .info-waves-container {{
                flex-grow: 1;
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}

            .wave-container {{
                height: 30px;
                display: flex;
                align-items: center;
                gap: 3px;
                padding: 0 5px;
            }}

            .bar {{
                flex: 1;
                background: linear-gradient(to top, #00ff41, #00d4ff);
                border-radius: 10px;
                height: 20%;
                transition: height 0.2s ease;
            }}

            .neo-player-container.playing .bar {{
                animation: wave-animation 1.2s infinite ease-in-out;
            }}

            .bar:nth-child(2)  {{ animation-delay: 0.1s !important; }}
            .bar:nth-child(3)  {{ animation-delay: 0.2s !important; }}
            .bar:nth-child(4)  {{ animation-delay: 0.3s !important; }}
            .bar:nth-child(5)  {{ animation-delay: 0.4s !important; }}
            .bar:nth-child(6)  {{ animation-delay: 0.5s !important; }}
            .bar:nth-child(7)  {{ animation-delay: 0.6s !important; }}
            .bar:nth-child(8)  {{ animation-delay: 0.5s !important; }}
            .bar:nth-child(9)  {{ animation-delay: 0.4s !important; }}
            .bar:nth-child(10) {{ animation-delay: 0.3s !important; }}
            .bar:nth-child(11) {{ animation-delay: 0.2s !important; }}
            .bar:nth-child(12) {{ animation-delay: 0.1s !important; }}

            @keyframes wave-animation {{
                0%, 100% {{ height: 20%; }}
                50% {{ height: 90%; }}
            }}

            .progress-container {{
                width: 100%;
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
                margin-top: 5px;
                cursor: pointer;
                position: relative;
            }}

            .progress-bar {{
                height: 100%;
                background: linear-gradient(90deg, #00ff41, #ff00ff);
                width: 0%;
                border-radius: 2px;
                box-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
                position: relative;
            }}

            .status-text {{
                font-size: 9px;
                color: #aaa;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                display: flex;
                justify-content: space-between;
                font-weight: bold;
            }}
        </style>

        <div class="player-layout">
            <div class="play-btn-wrapper">
                <div id="play-btn" class="play-btn" onclick="togglePlay()">▶</div>
            </div>
            
            <div class="info-waves-container">
                <div class="status-text">
                    <span>Gerard Neo-Player v1.0</span>
                    <span id="time-display">0:00</span>
                </div>
                
                <div id="wave-box" class="wave-container">
                    <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                    <div class="bar"></div><div class="bar"></div><div class="bar)</div>
                    <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                    <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                </div>

                <div id="progress-wrapper" class="progress-container" onclick="seek(event)">
                    <div id="progress-bar" class="progress-bar"></div>
                </div>
            </div>
        </div>

        <audio id="main-audio">
            <source src="data:audio/mpeg;base64,{audio_b64}" type="audio/mpeg">
        </audio>

        <script>
            const audio = document.getElementById('main-audio');
            const playBtn = document.getElementById('play-btn');
            const container = document.querySelector('.neo-player-container');
            const progressBar = document.getElementById('progress-bar');
            const timeDisplay = document.getElementById('time-display');

            function togglePlay() {{
                if (audio.paused) {{
                    audio.play();
                    playBtn.innerHTML = '||';
                    playBtn.classList.add('playing');
                    container.classList.add('playing');
                }} else {{
                    audio.pause();
                    playBtn.innerHTML = '▶';
                    playBtn.classList.remove('playing');
                    container.classList.remove('playing');
                }}
            }}

            audio.ontimeupdate = function() {{
                const pct = (audio.currentTime / audio.duration) * 100;
                progressBar.style.width = pct + '%';
                
                const mins = Math.floor(audio.currentTime / 60);
                const secs = Math.floor(audio.currentTime % 60);
                timeDisplay.innerHTML = mins + ':' + (secs < 10 ? '0' : '') + secs;
            }};

            audio.onended = function() {{
                playBtn.innerHTML = '▶';
                playBtn.classList.remove('playing');
                container.classList.remove('playing');
                progressBar.style.width = '0%';
            }};

            function seek(e) {{
                const wrapper = document.getElementById('progress-wrapper');
                const rect = wrapper.getBoundingClientRect();
                const pos = (e.clientX - rect.left) / rect.width;
                audio.currentTime = pos * audio.duration;
            }}
        </script>
    </div>
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
