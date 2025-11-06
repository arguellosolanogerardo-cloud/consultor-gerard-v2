# Sistema Consultor Gerard - 100% LOCAL (SIN COSTOS)

## 🎉 ¡FUNCIONAMIENTO COMPLETAMENTE GRATIS!

Este sistema está configurado para funcionar **EXCLUSIVAMENTE en local** usando Ollama, sin requerir ninguna API externa ni costos asociados.

## ✅ VENTAJAS

- 🚫 **SIN COSTOS** - No requiere suscripciones ni pagos
- 🔒 **100% PRIVADO** - Todo funciona en tu máquina local
- 📴 **OFFLINE** - Funciona sin conexión a internet (después de configuración inicial)
- 🏠 **LOCAL** - No envía datos a servidores externos

## 🛠️ CONFIGURACIÓN INICIAL

### Paso 1: Instalar Ollama

1. Ve a https://ollama.ai/download
2. Descarga e instala Ollama para tu sistema operativo
3. Reinicia tu computadora si es necesario

### Paso 2: Configurar el Sistema

Ejecuta el script de configuración automática:

```bash
# En Windows:
setup_local_only.bat

# O manualmente:
ollama pull deepseek-r1:8b  # ← MEJOR OPCIÓN (5.2GB)
ollama serve
```

### Paso 3: Verificar Instalación

```bash
# Verificar que Ollama funciona:
curl http://localhost:11434/api/tags
```

## 🚀 USO DEL SISTEMA

### Iniciar la Aplicación

```bash
streamlit run consultar_web.py
```

### Realizar Consultas

- Abre tu navegador en `http://localhost:8501`
- Escribe tus preguntas sobre Gerard en español
- El sistema responderá usando el modelo local

## 📋 REQUISITOS DEL SISTEMA

- **Memoria RAM**: Mínimo 8GB, recomendado 16GB+
- **Espacio Disco**: ~4GB para el modelo Llama3.2
- **Sistema Operativo**: Windows, macOS, Linux
- **Internet**: Solo para descarga inicial del modelo

## � MODELOS DISPONIBLES

1. **DeepSeek R1 8B** (⭐ RECOMENDADO - Mejor calidad para tu equipo)
   - Tamaño: ~5.2GB
   - Calidad: Excelente
   - Velocidad: Buena (45s primera respuesta)
   - Requisitos: RTX 3060 Ti + 32GB RAM

2. **Llama3.2 3B** (Buena alternativa)
   - Tamaño: ~3.3GB
   - Calidad: Muy buena
   - Velocidad: Rápida
   - Requisitos: RTX 3060 Ti + 16GB RAM

3. **Llama2 7B** (Fallback confiable)
   - Tamaño: ~3.8GB
   - Calidad: Buena
   - Velocidad: Rápida
   - Requisitos: RTX 3060 Ti + 16GB RAM

## 🆘 SOLUCIÓN DE PROBLEMAS

### "Ollama no está disponible"
```bash
# Verificar que Ollama esté ejecutándose:
ollama serve

# En otra terminal verificar:
curl http://localhost:11434/api/tags
```

### "Modelo no encontrado"
```bash
# Descargar el modelo:
ollama pull llama3.2:3b
```

### Aplicación no inicia
```bash
# Instalar dependencias:
pip install -r requirements.txt

# Verificar Python:
python --version
```

## 📊 CARACTERÍSTICAS TÉCNICAS

- **LLM**: Ollama con Llama3.2 3B parámetros
- **Base de Datos**: FAISS vectorial local
- **Interfaz**: Streamlit web local
- **Idioma**: Español (consultas y respuestas)
- **Búsqueda**: Híbrida (vectorial + keyword)

## 🔄 ACTUALIZACIONES

Para actualizar el modelo:
```bash
ollama pull llama3.2:3b  # Descarga la versión más reciente
```

## 📞 SOPORTE

Si tienes problemas:
1. Verifica que Ollama esté ejecutándose
2. Confirma que tienes suficiente RAM
3. Revisa los logs en la terminal

---

**¡Disfruta consultando a Gerard sin costos ni límites!** 🎯</content>
<parameter name="filePath">e:\proyecto-gemini-limpio\README_LOCAL_ONLY.md