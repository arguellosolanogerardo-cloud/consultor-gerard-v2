# 🚀 Despliegue en Streamlit Cloud

## Requisitos Previos

1. **Repositorio en GitHub**: Asegúrate de que tu código esté subido a GitHub
2. **Cuenta en Streamlit Cloud**: Crea una cuenta en [share.streamlit.io](https://share.streamlit.io)
3. **API Key de Google**: Necesitas una API Key de Google AI Studio

## Pasos para el Despliegue

### 1. Accede a Streamlit Cloud
Ve a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con tu cuenta de GitHub.

### 2. Conecta tu Repositorio
- Haz clic en "New app"
- Selecciona tu repositorio: `arguellosolanogerardo-cloud/consultor-gerard-v2`
- Selecciona la rama: `main`
- Archivo principal: `consultar_web.py`

### 3. Configura las Secrets
En la configuración de la app (Settings → Secrets), añade:

```
GOOGLE_API_KEY = "tu_api_key_de_google_aqui"
```

**Importante**: Reemplaza `"tu_api_key_de_google_aqui"` con tu clave real de Google AI Studio.

### 4. Configuración Adicional (Opcional)
- **Python Version**: 3.11.9 (ya configurado en `runtime.txt`)
- **Main file path**: `consultar_web.py` (ya es el archivo principal)
- **App URL**: Se generará automáticamente

### 5. Deploy
Haz clic en "Deploy!" y espera a que se complete el proceso.

## Verificación del Despliegue

Una vez desplegado, deberías poder:
- Acceder a tu app desde la URL proporcionada por Streamlit Cloud
- Hacer preguntas sobre los archivos SRT indexados
- Ver los logs tanto localmente como en Google Sheets (si está configurado)

## Solución de Problemas

### Error de API Key
- Verifica que la `GOOGLE_API_KEY` esté configurada correctamente en Secrets
- Asegúrate de que la API key tenga permisos para Google AI Studio

### Error de Dependencias
- Verifica que `requirements.txt` incluya todas las dependencias necesarias
- Revisa los logs de construcción en Streamlit Cloud

### Error de Memoria
- Si la app se queda sin memoria, considera reducir el tamaño del índice FAISS
- O actualiza a un plan de pago en Streamlit Cloud

## Configuración de Google Sheets (Opcional)

Si quieres logging en Google Sheets:

1. Sigue las instrucciones en `GOOGLE_SHEETS_SETUP.md`
2. Sube el archivo `google_credentials.json` a Streamlit Cloud Secrets como un secret de tipo "file"
3. O configura las credenciales en el formato JSON en los secrets

## URLs Importantes

- **Streamlit Cloud**: https://share.streamlit.io
- **Documentación**: https://docs.streamlit.io/streamlit-cloud
- **Tu App**: [URL se generará después del despliegue]

¡Tu app GERARD estará lista para usar en la nube! 🎉