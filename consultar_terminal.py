import os
import json
import re
import colorama
import argparse
import threading
import itertools
import sys
import time
import getpass
import uuid
from dotenv import load_dotenv
import keyring
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime

# Inicializamos colorama para que los colores funcionen en todas las terminales
colorama.init(autoreset=True)

# Configurar credenciales de Vertex AI
# Detectar automáticamente la ruta de credenciales correcta
credential_paths = [
    "google_credentials.json",  # Render/producción sin espacios
    "credencial_json_midyear-node-436821-t3-525a146e96a0.json",  # Alternativa sin espacios
    "credencial json/midyear-node-436821-t3-525a146e96a0.json"  # Local con espacios
]

credentials_file = None
for path in credential_paths:
    if os.path.exists(path):
        credentials_file = path
        print(f"[INFO] Usando credenciales desde: {path}")
        break

if credentials_file:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
else:
    print("[ERROR] No se encontró archivo de credenciales. Por favor verifica la configuración.")
    sys.exit(1)

# --- Carga la configuración ---
def build_retrieval_chain():
    """Construye y devuelve el retrieval_chain usando Vertex AI.

    Carga el índice FAISS persistido en `faiss_index/`.
    """
    # Small helper to run blocking calls in a thread and show a spinner in console
    def run_with_spinner(func, *args, message="Procesando..."):
        result_holder = {}

        def target():
            try:
                result_holder['result'] = func(*args)
            except Exception as e:
                result_holder['error'] = e

        thread = threading.Thread(target=target)
        thread.start()

        spinner = itertools.cycle(['|', '/', '-', '\\'])
        sys.stdout.write(message + ' ')
        sys.stdout.flush()
        try:
            while thread.is_alive():
                sys.stdout.write(next(spinner))
                sys.stdout.flush()
                time.sleep(0.1)
                sys.stdout.write('\b')
        except KeyboardInterrupt:
            pass
        thread.join()

        sys.stdout.write('\r' + ' ' * (len(message) + 2) + '\r')

        if 'error' in result_holder:
            raise result_holder['error']
        return result_holder.get('result')

    # Load LLM and embeddings with spinner to give feedback for slow init
    llm = run_with_spinner(lambda: ChatVertexAI(model="gemini-2.5-pro", project="midyear-node-436821-t3"), message="Inicializando LLM...")
    embeddings = run_with_spinner(lambda: VertexAIEmbeddings(model_name="text-embedding-004", project="midyear-node-436821-t3"), message="Inicializando embeddings...")

    try:
        vectorstore = run_with_spinner(lambda: FAISS.load_local(folder_path="faiss_index", embeddings=embeddings, allow_dangerous_deserialization=True), message="Cargando índice FAISS (puede tardar)...")
    except Exception as e:
        print(f"Error cargando FAISS index: {e}")
        raise

    retriever = vectorstore.as_retriever()
    retrieval_chain = (
        {
            "context": (lambda x: x["input"]) | retriever | format_docs_with_metadata,
            "input": (lambda x: x["input"]) 
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return retrieval_chain


# --- Funciones auxiliares ---

# --- PERSONALIDAD DE "GERARD" - AGENTE ANALÍTICO FORENSE ---
prompt = ChatPromptTemplate.from_template(r"""
# IDENTIDAD Y PROPÓSITO DEL SISTEMA

Eres un Agente Analítico Forense especializado en la extracción de información de una base de datos vectorial compuesta por 3.442 archivos de subtítulos (.srt). Tu función es actuar como un motor de búsqueda semántica de precisión quirúrgica.

## ARQUITECTURA EPISTEMOLÓGICA

**ÚNICO UNIVERSO DE CONOCIMIENTO:**
- Tu conocimiento TOTAL está limitado EXCLUSIVAMENTE a los 3.442 archivos .srt indexados
- NO posees conocimiento previo, entrenamiento general, ni información externa
- Cada afirmación debe ser RASTREABLE a un fragmento específico de la base de datos
- Si algo NO existe en la base de datos, NO EXISTE para ti

---

## 🚨 PROTOCOLOS DE SEGURIDAD ANALÍTICA

### 🔴 PROHIBICIONES ABSOLUTAS (Nivel de Cumplimiento: 100%)

#### PROHIBICIÓN NIVEL 1: FABRICACIÓN DE DATOS
❌ NO inventar información bajo ninguna circunstancia
❌ NO usar conocimiento del modelo base (entrenamiento general)
❌ NO suponer o inferir más allá de lo textualmente disponible
❌ NO completar información faltante con lógica externa
❌ NO responder "probablemente" o "es posible que"
❌ NO hacer generalizaciones sin evidencia textual directa

#### PROHIBICIÓN NIVEL 2: CONTAMINACIÓN ANALÍTICA
❌ NO mezclar análisis con citas textuales
❌ NO parafrasear cuando se requiere texto literal
❌ NO interpretar sin declarar explícitamente que es interpretación
❌ NO omitir información contradictoria si existe
❌ NO presentar sinónimos como si fueran el texto original

#### PROHIBICIÓN NIVEL 3: IMPRECISIÓN METODOLÓGICA
❌ NO agrupar resultados sin especificar cada fuente
❌ NO usar términos vagos ("varios documentos mencionan...")
❌ NO omitir timestamps cuando están disponibles
❌ NO presentar resultados sin indicar la fuente

---

### 🟢 MANDATOS OBLIGATORIOS

#### ESTRUCTURA DE CITA VERIFICABLE (OBLIGATORIA)
Cada afirmación DEBE seguir este formato:

**[Documento: nombre_archivo.srt | Timestamp: HH:MM:SS,mmm --> HH:MM:SS,mmm]**
"TEXTO LITERAL EXACTO DEL SUBTÍTULO"

**Componentes obligatorios:**
1. **Nombre del archivo fuente** (sin ruta, solo nombre)
2. **Timestamp completo** (inicio --> fin) extraído del formato [HH:MM:SS,mmm --> HH:MM:SS,mmm] que aparece en el contexto
3. **Texto literal** (sin modificaciones)

#### PROTOCOLO DE RESPUESTA ESTRUCTURADA

**Estructura obligatoria:**

## 🔍 RESULTADOS DE BÚSQUEDA

### 🎯 EVIDENCIAS ENCONTRADAS

[Para cada resultado, usar formato de cita obligatorio con timestamp completo]

### 🧮 ANÁLISIS INFERENCIAL (Claramente Separado)

⚠️ ADVERTENCIA: Lo siguiente es interpretación analítica, NO citas directas

[Tu análisis basado en patrones identificados]

### 📈 MÉTRICAS DE CONFIANZA

- **Nivel de Confianza General:** [BAJO/MEDIO/ALTO/CRÍTICO]
- **Fuentes encontradas:** [X] documentos contienen información relacionada

### ⚠️ LIMITACIONES DETECTADAS

[Enumerar explícitamente:]
- Información NO encontrada en la base de datos
- Ambigüedades identificadas
- Contradicciones entre fuentes (si existen)

---

## CONTEXTO DISPONIBLE (Fragmentos de la base de datos):
{context}

## CONSULTA DEL USUARIO:
{input}

---

## INSTRUCCIONES FINALES:

1. Analiza el CONTEXTO proporcionado arriba
2. Extrae ÚNICAMENTE información que esté presente textualmente
3. Para cada afirmación, cita: [Documento: archivo.srt | Timestamp: HH:MM:SS,mmm --> HH:MM:SS,mmm] seguido del texto literal
4. Los timestamps están embebidos en el contexto en formato [HH:MM:SS,mmm --> HH:MM:SS,mmm] - SIEMPRE inclúyelos
5. Separa claramente EVIDENCIAS de ANÁLISIS
6. Declara explícitamente si algo NO se encuentra en el contexto
7. Mantén tono profesional y preciso

**Base de datos cargada. Listo para consultas forenses. Protocolo de evidencia estricta activado.**
""")

# --- FUNCIÓN PARA FORMATEAR DOCUMENTOS (CON LIMPIEZA REFORZADA) ---
def get_cleaning_pattern():
    """Crea un patrón de regex robusto para eliminar textos no deseados."""
    texts_to_remove = [
        '[Spanish (auto-generated)]',
        '[DownSub.com]',
        '[Música]',
        '[Aplausos]'
    ]
    # Este patrón es más robusto: busca el texto dentro de los corchetes,
    # permitiendo espacios en blanco opcionales alrededor.
    robust_patterns = [r'\[\s*' + re.escape(text[1:-1]) + r'\s*\]' for text in texts_to_remove]
    return re.compile(r'|'.join(robust_patterns), re.IGNORECASE)

cleaning_pattern = get_cleaning_pattern()

def format_docs_with_metadata(docs):
    """Prepara los documentos recuperados, preservando los timestamps SRT y limpiando el contenido."""
    formatted_strings = []
    for doc in docs:
        # Obtener nombre completo del archivo sin usar basename
        source_filename = doc.metadata.get('source', 'Fuente desconocida')
        if '/' in source_filename or '\\' in source_filename:
            source_filename = source_filename.replace('\\', '/').split('/')[-1]
        
        # Eliminar extensión .srt para fuentes más limpias
        if source_filename.endswith('.srt'):
            source_filename = source_filename[:-4]
        
        # 1. Limpieza SOLO de textos no deseados (preservamos timestamps)
        cleaned_content = cleaning_pattern.sub('', doc.page_content)
        
        # 2. Limpieza de líneas vacías múltiples (pero preservamos estructura)
        cleaned_content = "\n".join(line for line in cleaned_content.split('\n') if line.strip())
        
        if cleaned_content:
            formatted_strings.append(f"Fuente del Archivo: {source_filename}\nContenido:\n{cleaned_content}")
            
    return "\n\n---\n\n".join(formatted_strings)

# --- Cadena de recuperación (LCEL) ---
# ... el retrieval_chain se construye con `build_retrieval_chain(api_key)` cuando
# se ejecute el script como programa principal.

# --- FUNCIÓN para guardar la conversación en un archivo ---
def save_to_log(question, user, answer_text):
    """Guarda la pregunta y la respuesta en un archivo de registro."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open("gerard_log.txt", "a", encoding="utf-8") as f:
        f.write(f"--- Conversación del {timestamp} ---\n")
        f.write(f"Usuario: {user}\n")
        f.write(f"Pregunta: {question}\n")
        f.write(f"Respuesta de GERARD: {answer_text}\n")
        f.write("="*40 + "\n\n")

# --- FUNCIÓN PARA IMPRIMIR LA RESPUESTA ---
def print_answer(answer_text):
    """Imprime la respuesta de GERARD con formato básico."""
    # Limpiar cualquier ruido residual
    cleaned_answer = cleaning_pattern.sub('', answer_text)
    print(f"{colorama.Fore.CYAN}{cleaned_answer}{colorama.Style.RESET_ALL}")

# --- Bucle de Interacción ---
def main():
    """Función principal que lanza el loop interactivo. Protegida para que no se ejecute al importar."""
    load_dotenv()

    # Construir la cadena de recuperación con Vertex AI
    try:
        retrieval_chain = build_retrieval_chain()
    except Exception as e:
        print(f"Error inicializando el pipeline: {e}")
        return

    print("GERARD listo. Escribe tu pregunta o 'salir' para terminar.")
    user_name = input("Por favor, introduce tu nombre para comenzar: ")

    while True:
        prompt_text = f"\nTu pregunta {colorama.Fore.BLUE}{user_name.upper()}{colorama.Style.RESET_ALL}: "
        pregunta = input(prompt_text)

        if pregunta.lower() == 'salir':
            break

        print("Buscando...")
        try:
            answer = retrieval_chain.invoke({"input": pregunta})
            print("\nRespuesta de GERARD:")
            print_answer(answer)
            save_to_log(pregunta, user_name.upper(), answer)

        except Exception as e:
            print(f"\n{colorama.Fore.RED}Ocurrió un error al procesar tu pregunta: {e}")


if __name__ == "__main__":
    main()

