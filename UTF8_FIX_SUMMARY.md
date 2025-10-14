# Corrección UTF-8 Streamlit Cloud

## Problema Solucionado
Los caracteres especiales (tildes, eñes, comillas) se veían distorsionados en Streamlit Cloud pero perfectos en local.

## Cambios Realizados

### 1. Nueva función `fix_utf8_encoding()`
- Normaliza caracteres Unicode
- Corrige caracteres mal codificados comunes
- Reemplaza automáticamente: â€™→', Ã±→ñ, Ã¡→á, etc.

### 2. Configuración Sistema
- Variables entorno: PYTHONIOENCODING, LANG, LC_ALL
- Reconfiguración stdout/stderr UTF-8
- Meta tags HTML UTF-8

### 3. Aplicaciones Específicas
- Textos del expander "Cómo Hacer Preguntas"
- Texto de introducción principal  
- Todos los emojis problemáticos corregidos
- Procesamiento JSON de respuestas

### 4. Archivos Configuración
- `.streamlit/config.toml`: Configuración optimizada
- `requirements.txt`: Agregadas librerías chardet, unicodedata2
- `runtime.txt`: Python 3.9.19 específico

## Resultado Esperado
Después del deploy: caracteres idénticos en local y Streamlit Cloud.

## Archivos Modificados
- consultar_web.py (función fix_utf8_encoding + aplicaciones)
- .streamlit/config.toml (configuración server)
- requirements.txt (nuevas dependencias)
- runtime.txt (versión Python)