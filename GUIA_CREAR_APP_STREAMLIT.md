# 🚀 GUÍA: Crear App en Streamlit Cloud

## ❌ PROBLEMA ACTUAL

**Error:** "You do not have access to this app or it does not exist"

**Causa:** La app `consultor-gerard-v2` no está creada/desplegada en Streamlit Cloud todavía.

---

## ✅ SOLUCIÓN: Crear la App Manualmente

### **PASO 1: Ir a Streamlit Cloud**

Abre tu navegador y ve a:
```
https://share.streamlit.io/
```

---

### **PASO 2: Iniciar Sesión**

- **Email:** arguellosolanogerardo@gmail.com
- **GitHub:** arguellosolanogerardo-cloud

Asegúrate de estar conectado con **ambas cuentas**.

---

### **PASO 3: Crear Nueva App**

1. **Click en "New app"** (botón naranja/morado en la esquina superior derecha)

2. **Configurar la app:**

   ```
   Repository: arguellosolanogerardo-cloud/consultor-gerard-v2
   Branch: main
   Main file path: consultar_web.py
   App URL (custom): consultor-gerard-v2
   ```

3. **Advanced settings** (click en "Advanced settings"):

   **Python version:**
   ```
   3.11
   ```

   **Secrets:** (pega esto en el campo de secrets)
   ```toml
   GOOGLE_API_KEY = "AIzaSyCDHkKF-KipEfMLU7PXJmtwEer3B2NL260"
   ```

4. **Click en "Deploy!"**

---

### **PASO 4: Esperar el Deploy**

- El deploy inicial tomará **1-2 minutos**
- Verás logs en tiempo real
- **Importante:** Esta vez el índice FAISS se cargará instantáneamente desde GitHub

**Logs esperados:**
```
✅ Clonando repositorio...
✅ Instalando dependencias...
✅ Iniciando aplicación...
💾 Índice FAISS cargado desde: faiss_index
✅ App lista!
```

---

### **PASO 5: Verificar URL Final**

Después del deploy, tu app estará en:
```
https://consultor-gerard-v2.streamlit.app/
```

O la URL personalizada que Streamlit asigne.

---

## 🔐 CONFIGURACIÓN DE SECRETS

Si no agregaste los secrets en el paso 3, puedes hacerlo después:

1. Ve a tu app en el dashboard
2. Click en **"⋮"** (tres puntos)
3. Click en **"Settings"**
4. Ve a la pestaña **"Secrets"**
5. Pega:
   ```toml
   GOOGLE_API_KEY = "AIzaSyCDHkKF-KipEfMLU7PXJmtwEer3B2NL260"
   ```
6. Click en **"Save"**
7. La app se reiniciará automáticamente

---

## 📋 CHECKLIST DE CREACIÓN

- [ ] Ir a https://share.streamlit.io/
- [ ] Click en "New app"
- [ ] Configurar repositorio: `consultor-gerard-v2`
- [ ] Configurar branch: `main`
- [ ] Configurar main file: `consultar_web.py`
- [ ] Agregar secrets: `GOOGLE_API_KEY`
- [ ] Click en "Deploy!"
- [ ] Esperar 1-2 minutos
- [ ] Verificar app funciona

---

## 🎯 DESPUÉS DEL DEPLOY

### **Verificar que todo funciona:**

1. **La app carga rápido** (< 10 seg)
2. **Consulta funciona:** "QUIEN ES EL PADRE"
3. **Encoding correcto:** Caracteres españoles bien
4. **PDF descarga:** Botón funciona
5. **Google Sheets:** Registra consultas

---

## 🐛 TROUBLESHOOTING

### **Error: "ModuleNotFoundError"**

**Causa:** Falta alguna dependencia en `requirements.txt`

**Solución:** Verificar que `requirements.txt` está en el repo:
```bash
streamlit
langchain-google-genai
langchain-chroma
langchain-community
python-dotenv
google-generativeai
faiss-cpu
```

### **Error: "No such file: faiss_index/index.faiss"**

**Causa:** Git LFS no está funcionando correctamente

**Solución:**
1. Verificar que los archivos están en GitHub
2. Ver tamaño de los archivos en GitHub (deben ser ~120 MB, no pointers)
3. Si son pointers, reinstalar Git LFS y volver a push

### **Error: "API Key not found"**

**Causa:** Los secrets no están configurados

**Solución:**
1. Ir a Settings → Secrets en Streamlit Cloud
2. Agregar `GOOGLE_API_KEY`
3. Guardar y reiniciar app

---

## 📞 ALTERNATIVA: Deploy desde CLI

Si prefieres, también puedes usar la CLI de Streamlit:

```bash
pip install streamlit
streamlit login
streamlit deploy consultar_web.py --repo arguellosolanogerardo-cloud/consultor-gerard-v2 --branch main
```

---

## ✅ CONFIRMACIÓN FINAL

Después de completar estos pasos, tu app estará en:

```
https://consultor-gerard-v2.streamlit.app/
```

O la URL que Streamlit te asigne.

---

_Sigue estos pasos y la app estará funcionando en menos de 5 minutos._ 🚀
