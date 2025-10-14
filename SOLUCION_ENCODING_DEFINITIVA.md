# 🎯 SOLUCIÓN DEFINITIVA DE ENCODING UTF-8

## ❌ Error Persistente
```
'utf-8' codec can't decode byte 0xd3 in position 6848: invalid continuation byte
```

## ✅ Archivos Corregidos (5 en total)

### 1. `auto_build_index.py` ✅
```python
loader_kwargs={'encoding': 'latin-1'}  # ✅ YA CORREGIDO
```

### 2. `scripts/build_faiss.py` ✅
```python
loader = TextLoader(path, encoding='latin-1')  # ✅ YA CORREGIDO
```

### 3. `ingestar.py` ✅
```python
loader = TextLoader(file_path, encoding='latin-1')  # ✅ YA CORREGIDO
```

### 4. `ingestar_robusto.py` ✅
```python
loader = TextLoader(filepath, encoding='latin-1')  # ✅ YA CORREGIDO
```

### 5. `test_builder.py` ✅
```python
loader = TextLoader(filepath, encoding='latin-1')  # ✅ YA CORREGIDO
```

---

## 🔴 PROBLEMA: Error persiste después de todos los fixes

### Posibles causas:

#### 1. ⚠️ Caché de Streamlit Cloud NO se limpió
**Solución**: Clear cache manualmente
- Ve a: https://share.streamlit.io/
- App: `consultor-gerard-v2`
- **⋮ → Clear cache** 
- Luego: **Reboot app**

#### 2. ⚠️ Langchain usa UTF-8 internamente
El `DirectoryLoader` de `langchain_community` puede tener **fallback a UTF-8** cuando:
- `loader_kwargs` no se pasa correctamente
- Hay un bug en la versión de langchain

**Solución**: Verificar versión de langchain
```python
import langchain_community
print(langchain_community.__version__)
```

#### 3. ⚠️ Archivo .srt específico causa el error
Algunos archivos .srt pueden tener **BOM (Byte Order Mark)** o bytes especiales.

**Solución**: Identificar archivo problemático
```python
import os
from langchain_community.document_loaders import TextLoader

for filename in os.listdir("documentos_srt"):
    if filename.endswith(".srt"):
        filepath = os.path.join("documentos_srt", filename)
        try:
            loader = TextLoader(filepath, encoding='latin-1')
            docs = loader.load()
            print(f"✅ {filename}")
        except Exception as e:
            print(f"❌ {filename}: {e}")
```

---

## 🔧 SOLUCIÓN ALTERNATIVA: Preprocessing

Si el error persiste incluso con `latin-1`, podemos **pre-procesar los archivos**:

### Opción A: Convertir todos los .srt a UTF-8 limpio
```python
import os
from pathlib import Path

def clean_srt_files(directory: str):
    """Convierte todos los .srt a UTF-8 limpio"""
    for filepath in Path(directory).glob("**/*.srt"):
        try:
            # Leer con latin-1 (acepta todo)
            content = filepath.read_bytes()
            
            # Decodificar con latin-1
            text = content.decode('latin-1', errors='ignore')
            
            # Escribir como UTF-8 limpio
            filepath.write_text(text, encoding='utf-8')
            print(f"✅ Limpiado: {filepath.name}")
        except Exception as e:
            print(f"❌ Error en {filepath.name}: {e}")

# Ejecutar ANTES de construir índice
clean_srt_files("documentos_srt")
```

### Opción B: Usar errors='ignore' en DirectoryLoader
```python
loader = DirectoryLoader(
    DATA_PATH,
    glob="**/*.srt",
    loader_cls=TextLoader,
    loader_kwargs={'encoding': 'latin-1', 'errors': 'ignore'}
)
```

### Opción C: Loader personalizado más robusto
```python
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document

def robust_load_srt(filepath: str) -> list[Document]:
    """Carga .srt con múltiples intentos de encoding"""
    encodings = ['latin-1', 'cp1252', 'iso-8859-1', 'utf-8']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            return [Document(page_content=content, metadata={"source": filepath})]
        except Exception as e:
            continue
    
    # Si ninguno funciona, leer como binario
    with open(filepath, 'rb') as f:
        content = f.read().decode('latin-1', errors='ignore')
    
    return [Document(page_content=content, metadata={"source": filepath})]
```

---

## 🚀 PASOS SIGUIENTES

### 1. **PRIMERO**: Clear cache en Streamlit Cloud
   - ⋮ → Clear cache
   - Reboot app
   - Esperar 2-3 minutos

### 2. **Si persiste**: Verificar que los cambios están en GitHub
```powershell
cd e:\proyecto-gemini-limpio
git log --oneline -5
```

Deberías ver:
```
9ff4a1a Fix crítico #3: Cambiar encoding a latin-1 en todos los archivos restantes
00cf055 Fix crítico #2: Cambiar encoding en scripts/build_faiss.py a latin-1
0d626cd Fix crítico: Cambiar a encoding latin-1 para archivos .srt
```

### 3. **Si TODAVÍA persiste**: Aplicar Opción A (preprocessing)
   - Agregar script de limpieza a `auto_build_index.py`
   - Ejecutar ANTES de `DirectoryLoader`

---

## 📊 Commits Realizados

| Commit | Archivo | Estado |
|--------|---------|--------|
| `0d626cd` | `auto_build_index.py` | ✅ Subido |
| `00cf055` | `scripts/build_faiss.py` | ✅ Subido |
| `9ff4a1a` | 3 archivos más | ✅ Subido |

**Total**: 5 archivos corregidos, 3 commits pusheados

---

## 💡 Recomendación

**Haz esto AHORA**:
1. Ve a Streamlit Cloud
2. **⋮ → Clear cache** (NO solo Reboot)
3. **Reboot app**
4. Espera 3-5 minutos
5. Reporta si el error persiste o si la construcción inicia

Si después de Clear cache + Reboot el error **TODAVÍA** aparece, entonces el problema es más profundo y necesitamos aplicar la **Opción A (preprocessing)**.
