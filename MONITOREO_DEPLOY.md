# 📊 MONITOREO DEL DEPLOY - Tiempo Real

**Fecha:** 13 de octubre de 2025  
**Hora inicio:** ___:___ (anota cuando hagas Reboot)  
**App URL:** https://share.streamlit.io/

---

## ⏱️ TIMELINE ESPERADO (25-30 minutos)

### **Fase 1: Inicio (Minutos 0-2)**

**En los logs verás:**
```
🖥 Provisioning machine...
🎛 Preparing system...
⛓ Spinning up manager process...
🚀 Starting up repository: 'consultor-gerard-v2'
🐙 Cloning repository...
```

**Checklist:**
- [ ] Clonación exitosa (sin error "Failed")
- [ ] Instalando dependencias
- [ ] Iniciando Streamlit

**Si falla aquí:** Hay problema con el repo o requirements.txt

---

### **Fase 2: Carga de App (Minutos 2-3)**

**En los logs verás:**
```
Collecting usage statistics...
You can now view your Streamlit app in your browser.
```

**Checklist:**
- [ ] App inicia sin errores de imports
- [ ] Carga página principal

**Si falla aquí:** Hay error de código Python o imports

---

### **Fase 3: Construcción del Índice (Minutos 3-30)**

**ESTO ES LO IMPORTANTE - En los logs verás:**

```
════════════════════════════════════════════════════════
🔨 CONSTRUYENDO ÍNDICE FAISS (Primera vez)
════════════════════════════════════════════════════════

📂 Cargando documentos desde: documentos_srt
📊 Archivos encontrados: 1973

✂️ Dividiendo documentos en chunks...
✅ Total de chunks: 41109

🤖 Creando embeddings y construyendo índice FAISS...
⚠️  NOTA: Este proceso tomará aproximadamente 20-30 minutos
📊 Progreso: Se mostrará cada 10 lotes

📦 Procesando lote 1/823 (50 chunks)...
✅ Lote 1/823 completado

📦 Procesando lote 2/823 (50 chunks)...
✅ Lote 2/823 completado

...

📦 Procesando lote 10/823 (50 chunks)...
✅ Lote 10/823 completado
🎯 PROGRESO GENERAL: 10/823 lotes completados (1.2%)

...

📦 Procesando lote 100/823 (50 chunks)...
✅ Lote 100/823 completado
🎯 PROGRESO GENERAL: 100/823 lotes completados (12.2%)

...

📦 Procesando lote 200/823 (50 chunks)...
✅ Lote 200/823 completado
🎯 PROGRESO GENERAL: 200/823 lotes completados (24.3%)

...

📦 Procesando lote 400/823 (50 chunks)...
✅ Lote 400/823 completado
🎯 PROGRESO GENERAL: 400/823 lotes completados (48.6%)

...

📦 Procesando lote 600/823 (50 chunks)...
✅ Lote 600/823 completado
🎯 PROGRESO GENERAL: 600/823 lotes completados (72.9%)

...

📦 Procesando lote 800/823 (50 chunks)...
✅ Lote 800/823 completado
🎯 PROGRESO GENERAL: 800/823 lotes completados (97.2%)

...

📦 Procesando lote 823/823 (9 chunks)...
✅ Lote 823/823 completado

💾 Índice FAISS guardado en faiss_index
✅ Construcción exitosa: 41109 chunks indexados
```

**Checklist de progreso (marca cada 100 lotes):**
- [ ] Lote 100/823 (12.2%) - ~3 min
- [ ] Lote 200/823 (24.3%) - ~6 min
- [ ] Lote 300/823 (36.5%) - ~9 min
- [ ] Lote 400/823 (48.6%) - ~12 min
- [ ] Lote 500/823 (60.8%) - ~15 min
- [ ] Lote 600/823 (72.9%) - ~18 min
- [ ] Lote 700/823 (85.1%) - ~21 min
- [ ] Lote 800/823 (97.2%) - ~24 min
- [ ] Lote 823/823 (100%) - ~25 min

**Si ves errores aquí:**
- `ResourceExhausted`: Rate limit de Google API (normal, tiene reintentos)
- `⚠️ Error en lote X, reintentando en 60s...`: Normal, sistema de reintentos
- Cualquier otro error: Copia y pégame el mensaje

---

### **Fase 4: Índice Listo (Minuto 30+)**

**En los logs verás:**
```
✅ Índice FAISS cargado exitosamente
📊 Vectorstore listo con 41109 documentos
```

**Checklist:**
- [ ] Mensaje "Índice FAISS cargado"
- [ ] No hay errores posteriores
- [ ] App responde

---

## 🧪 TESTS DE VERIFICACIÓN

### **Después de ver "✅ Construcción exitosa", haz estos tests:**

#### **Test 1: Consulta Básica**
```
Pregunta: QUIEN ES EL PADRE
```
- [ ] Respuesta aparece
- [ ] Incluye fuentes con timestamps
- [ ] No hay error "No such file"

#### **Test 2: Encoding UTF-8**
```
Pregunta: ¿Cómo fue que me creó el Amor?
```
- [ ] Caracteres españoles correctos (¿, ¡, ó, ñ)
- [ ] NO aparecen: Â¡, Ã³, â"

#### **Test 3: Botón PDF**
- [ ] Botón "📥 Descargar Guía Completa" visible
- [ ] Descarga archivo PDF (~26 KB)
- [ ] PDF abre correctamente

#### **Test 4: Google Sheets Logger**
- [ ] Abrir hoja: "GERARD - Logs de Usuarios"
- [ ] Consulta registrada con fecha/hora
- [ ] Columnas completas

---

## 🚨 PROBLEMAS COMUNES

### **Error: "ResourceExhausted" o "429"**
```
Causa: Rate limit de Google API
Solución: Normal, el sistema reintenta automáticamente
Espera: 60 segundos adicionales por reintento
```

### **Error: "ModuleNotFoundError"**
```
Causa: Falta alguna dependencia
Solución: Verificar requirements.txt
Acción: Cópiame el error completo
```

### **Error: "Out of memory"**
```
Causa: Lotes muy grandes
Solución: Poco probable (lotes de 50 chunks)
Acción: Cópiame el error completo
```

### **App se detiene en medio de construcción**
```
Causa: Timeout de Streamlit Cloud
Solución: Hacer Reboot y reintentar
Acción: El índice parcial se descarta, empieza de cero
```

---

## ✅ CONFIRMACIÓN FINAL

**Cuando TODO funcione, marca aquí:**

- [ ] ✅ Índice construido (41,109 chunks)
- [ ] ✅ Consultas funcionan
- [ ] ✅ Encoding correcto
- [ ] ✅ PDF descarga
- [ ] ✅ Google Sheets registra

**Hora de completación:** ___:___

**Tiempo total:** ___ minutos

---

## 📝 NOTAS ADICIONALES

Anota cualquier observación:

```
[Escribe aquí cualquier error, advertencia o comportamiento inesperado]




```

---

## 🎉 DESPUÉS DE LA VERIFICACIÓN

**Si todo funciona:**
1. ✅ Deployment completado 100%
2. ✅ Nunca más tendrás que esperar tanto
3. ✅ Próximos deploys: < 60 segundos

**Celebra con:** ☕🍕🎊

---

_Documento generado: 13 de octubre de 2025_
