# PARCHE URGENTE: Integrar auto-construcción en consultar_web.py

## Problema Identificado:
Línea 162 de consultar_web.py intenta cargar FAISS sin verificar si existe primero.

## Solución:
Agregar verificación y construcción automática antes de FAISS.load_local()

## Código a insertar ANTES de la línea 162:

```python
# === AUTO-CONSTRUCCIÓN DEL ÍNDICE FAISS ===
if not os.path.exists("faiss_index/index.faiss"):
    st.warning("🔨 Índice FAISS no encontrado. Construyendo automáticamente...")
    st.info("⏱️ Este proceso tomará aproximadamente 25-30 minutos. Por favor espera...")
    
    try:
        from auto_build_index import build_faiss_index
        success = build_faiss_index(api_key, force=True)
        
        if success:
            st.success("✅ Índice FAISS construido exitosamente!")
        else:
            st.error("❌ Error construyendo el índice FAISS")
            raise Exception("Failed to build FAISS index")
    except ImportError:
        st.error("❌ auto_build_index.py no encontrado")
        raise
    except Exception as e:
        st.error(f"❌ Error en construcción: {str(e)}")
        raise
# === FIN AUTO-CONSTRUCCIÓN ===
```

## Ubicación exacta:
INSERTAR ANTES de:
```python
faiss_vs = FAISS.load_local(folder_path="faiss_index",
                            embeddings=embeddings, 
                            allow_dangerous_deserialization=True)
```

DESPUÉS de:
```python
            embeddings = FakeEmbeddings()
            st.error("⚠️ ADVERTENCIA...")
```

## Implementar ahora:
Ver siguiente comando...
