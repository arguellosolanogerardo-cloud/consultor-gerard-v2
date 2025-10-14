# 💾 SOLUCIÓN DEFINITIVA: Persistencia de FAISS

## ❌ Problema Actual

**Cada vez que haces `git push`**:
1. Streamlit Cloud crea **contenedor nuevo**
2. Contenedor **NO tiene** `faiss_index/`
3. Auto-construcción detecta falta
4. **Reconstruye** (25-30 minutos) ❌

**Resultado**: Reconstrucción infinita en cada deploy 😤

---

## ✅ Soluciones Posibles

### Opción 1: ❌ Git LFS (NO funciona - ya probamos)
- Streamlit Cloud Community NO soporta Git LFS
- Requiere Streamlit Teams ($250/mes)

### Opción 2: ✅ Archivos normales en GitHub (limitado)
- GitHub permite archivos hasta **100 MB**
- Tu índice FAISS: **~182 MB** ❌ Muy grande

### Opción 3: ✅ Split del índice + GitHub (FUNCIONA)
Dividir `index.faiss` en partes < 100 MB cada una:
```python
# Al guardar:
split -b 90M index.faiss index.faiss.part_

# Al cargar:
cat index.faiss.part_* > index.faiss
```

### Opción 4: ✅✅ Storage Externo (MEJOR)
- **Google Drive** (gratuito, 15 GB)
- **Dropbox** (gratuito, 2 GB)
- **GitHub Releases** (gratuito, archivos grandes)
- **Azure Blob** ($0.02/GB/mes)

---

## 🚀 SOLUCIÓN RECOMENDADA: GitHub Releases

### Por qué GitHub Releases:
✅ **Gratuito** e ilimitado para archivos grandes  
✅ **CDN global** (descarga rápida)  
✅ **Versionado** automático  
✅ **Sin API keys** necesarias  
✅ **Integración nativa** con el repo

### Cómo funciona:
1. **Una vez**: Construir índice localmente
2. **Una vez**: Subir a GitHub Release
3. **Cada deploy**: Descargar desde Release (< 30 segundos)
4. **Nunca más**: Reconstruir

---

## 📝 Implementación

### Paso 1: Crear script de upload (local)
```python
# upload_faiss_to_release.py
import requests
import os

GITHUB_TOKEN = "tu_token_aqui"  # Personal Access Token
REPO = "arguellosolanogerardo-cloud/consultor-gerard-v2"
TAG = "faiss-index-v1"

# Crear release
url = f"https://api.github.com/repos/{REPO}/releases"
response = requests.post(url, json={
    "tag_name": TAG,
    "name": "FAISS Index v1",
    "body": "Índice FAISS pre-construido (41,109 chunks)"
}, headers={"Authorization": f"token {GITHUB_TOKEN}"})

release_id = response.json()["id"]

# Subir archivo
upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets"
with open("faiss_index/index.faiss", "rb") as f:
    requests.post(
        f"{upload_url}?name=index.faiss",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Content-Type": "application/octet-stream"
        },
        data=f
    )
```

### Paso 2: Modificar consultar_web.py
```python
import requests
import tarfile

def download_faiss_from_release():
    """Descarga índice desde GitHub Release"""
    RELEASE_URL = "https://github.com/arguellosolanogerardo-cloud/consultor-gerard-v2/releases/download/faiss-index-v1/index.faiss"
    
    if os.path.exists("faiss_index/index.faiss"):
        return True  # Ya existe
    
    st.info("📥 Descargando índice FAISS (~182 MB)...")
    response = requests.get(RELEASE_URL, stream=True)
    
    os.makedirs("faiss_index", exist_ok=True)
    with open("faiss_index/index.faiss", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    st.success("✅ Índice descargado")
    return True

# En load_resources():
download_faiss_from_release()  # Solo descarga, NO construye
faiss_vs = FAISS.load_local("faiss_index", embeddings)
```

---

## ⚡ Ventajas de esta Solución

### Construcción:
- ❌ Antes: 25-30 min en cada deploy
- ✅ Ahora: Una vez localmente, nunca más

### Deploy:
- ❌ Antes: 30 min hasta que app funcione
- ✅ Ahora: 30 segundos (solo descarga)

### Mantenimiento:
- ❌ Antes: Reconstruir en cada cambio de código
- ✅ Ahora: Solo reconstruir si cambias .srt

---

## 🔄 Flujo de Trabajo

### Primera vez (AHORA, mientras construye):
1. ✅ Dejar que termine construcción actual
2. ✅ Crear GitHub Personal Access Token
3. ✅ Ejecutar `upload_faiss_to_release.py` (local)
4. ✅ Modificar `consultar_web.py` para descargar
5. ✅ Push y deploy (30 seg, NO 30 min)

### Futuros deploys (cambios de código):
1. ✅ Cambiar código (geo_utils, etc.)
2. ✅ `git push`
3. ✅ Streamlit descarga índice (30 seg)
4. ✅ App lista inmediatamente

### Si actualizas .srt (raro):
1. Construir índice localmente
2. Subir nueva versión a Release
3. Cambiar TAG en código (v1 → v2)
4. Deploy

---

## 🎯 Implementación Inmediata

**MIENTRAS CONSTRUYE (los próximos 20 minutos)**:

### 1. Crear Personal Access Token
- GitHub → Settings → Developer settings
- Personal access tokens → Tokens (classic)
- Generate new token
- Scopes: `repo` (full control)
- Copiar token

### 2. Yo preparo el script
Te daré el script completo para:
- Subir índice a Release
- Modificar consultar_web.py
- Eliminar auto-construcción

### 3. Después de construcción
- Ejecutar script de upload
- Push del código modificado
- **NUNCA MÁS** reconstruir

---

## 📊 Comparación

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Primer deploy** | 30 min | 30 min (una vez) |
| **Deploys futuros** | 30 min cada uno | 30 seg |
| **Storage usado** | 0 MB (se borra) | 182 MB (en Release) |
| **Costo** | $0 | $0 |
| **Mantenimiento** | Reconstruir siempre | Solo si cambias .srt |

---

## ✅ Decisión

**¿Quieres que prepare esto AHORA** (mientras construye)?

En 20 minutos cuando termine la construcción:
1. Subes el índice a Release (1 minuto)
2. Push del código modificado (30 segundos)
3. **NUNCA MÁS** esperar 30 minutos

**¿Procedemos?** 🚀
