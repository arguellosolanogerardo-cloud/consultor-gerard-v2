# RUNBOOK: Migración de LLM - Operaciones y Recuperación
# Versión: 1.0
# Fecha: 2024
# Autor: Sistema de Migración Automática

## 📋 ÍNDICE
1. [Monitoreo Normal](#monitoreo-normal)
2. [Alertas y Respuesta](#alertas-y-respuesta)
3. [Procedimientos de Recuperación](#procedimientos-de-recuperación)
4. [Degradado de Servicio](#degradado-de-servicio)
5. [Rollback](#rollback)
6. [Contactos de Emergencia](#contactos-de-emergencia)

---

## 🔍 MONITOREO NORMAL

### Métricas Principales
- **Latencia P95**: < 15 segundos
- **Tasa de éxito**: > 95%
- **Uso de cuota**: < 80%
- **Costo por hora**: < $5

### Comandos de Monitoreo
```bash
# Ver estadísticas actuales
python -c "from llm_monitor import get_monitoring_stats; import json; print(json.dumps(get_monitoring_stats(), indent=2))"

# Ver alertas activas
python -c "from llm_monitor import monitor; alerts = monitor.get_alerts(); print(f'Alertas: {len(alerts)}'); [print(f'{i+1}. {a[\"message\"]}') for i,a in enumerate(alerts)]"

# Ver estado de proveedores
python test_llm_integration.py
```

---

## 🚨 ALERTAS Y RESPUESTA

### Tipos de Alertas

#### 1. Alta Tasa de Error (>10%)
**Síntomas:**
- Múltiples errores 429 (Rate Limit)
- Errores 500/502/503 de APIs
- Timeouts frecuentes

**Respuesta Inmediata:**
1. Verificar estado de APIs en dashboards de proveedores
2. Revisar límites de cuota actuales
3. Cambiar prioridad de proveedores en .env:
   ```
   LLM_PROVIDER_PRIORITY=openai,claude,ollama
   ```
4. Reiniciar aplicación

#### 2. Alta Latencia (>20s P95)
**Síntomas:**
- Respuestas lentas
- Usuarios reportan delays
- Aumento en timeouts

**Respuesta Inmediata:**
1. Verificar conectividad de red
2. Cambiar a modelo más rápido:
   ```
   # En .env cambiar a GPT-4o-mini si usando Claude
   LLM_PROVIDER_PRIORITY=openai,ollama,claude
   ```
3. Reiniciar aplicación

#### 3. Cuota Excedida
**Síntomas:**
- Errores 429 persistentes
- Mensajes de "quota exceeded"
- Funcionalidad degradada

**Respuesta Inmediata:**
1. Verificar cuota restante en dashboard del proveedor
2. Cambiar a proveedor alternativo
3. Notificar al equipo para aumento de cuota

---

## 🔧 PROCEDIMIENTOS DE RECUPERACIÓN

### Recuperación Automática
La aplicación incluye fallback automático entre proveedores:
1. **Claude 3.5 Sonnet** (primario)
2. **GPT-4o Mini** (secundario)
3. **Ollama Llama2** (terciario/local)

### Recuperación Manual
```bash
# Forzar cambio de proveedor
export LLM_PROVIDER_PRIORITY="openai,ollama,claude"
streamlit run consultar_web.py

# Verificar recuperación
python test_llm_integration.py
```

### Escalada
Si la recuperación automática falla:
1. **Nivel 1**: Reinicio de aplicación
2. **Nivel 2**: Cambio manual de proveedor
3. **Nivel 3**: Rollback a versión anterior
4. **Nivel 4**: Contactar proveedores de API

---

## 📉 DEGRADADO DE SERVICIO

### Modo Degradado
Cuando todos los proveedores cloud fallan, la aplicación degrada a:

**Funcionalidad Limitada:**
- Solo búsqueda literal (sin LLM)
- Respuestas basadas únicamente en citas SRT
- Sin generación de nuevo contenido

**Activación:**
```bash
# Forzar modo degradado
export LLM_PROVIDER_PRIORITY="ollama"
export LLM_DEGRADED_MODE="true"
streamlit run consultar_web.py
```

**Mensaje al Usuario:**
> "Servicio funcionando en modo limitado. Las respuestas se basan únicamente en citas directas de fuentes SRT."

---

## 🔄 ROLLBACK

### Rollback Completo
```bash
# Detener aplicación actual
pkill -f streamlit

# Restaurar backup
cp backup_pre_migration_*/consultar_web.py .
cp backup_pre_migration_*/requirements.txt .

# Revertir dependencias
pip install -r requirements.txt

# Restaurar configuración
cp backup_pre_migration_*/.env .

# Reiniciar con configuración original
streamlit run consultar_web.py
```

### Rollback Parcial
Si solo se necesita cambiar configuración:
```bash
# Editar .env para volver a configuración anterior
# Cambiar LLM_PROVIDER_PRIORITY según necesidad
# Reiniciar aplicación
```

---

## 📞 CONTACTOS DE EMERGENCIA

### Proveedores de API
- **Anthropic Claude**: https://console.anthropic.com/ - Support 24/7
- **OpenAI**: https://platform.openai.com/account/billing - Support prioritario con pago
- **Ollama**: Comunidad Discord - https://discord.gg/ollama

### Equipo Técnico
- **Desarrollador Principal**: [Tu nombre/contacto]
- **DevOps/SysAdmin**: [Contacto infraestructura]
- **Producto**: [Contacto negocio]

### Procedimiento de Escalada
1. **0-15 min**: Intentar recuperación automática
2. **15-30 min**: Contactar desarrollador principal
3. **30-60 min**: Contactar DevOps
4. **>60 min**: Contactar proveedores de API directamente

---

## 📊 MÉTRICAS DE SEGUIMIENTO POST-MIGRACIÓN

### KPIs Principales (Primer mes)
- **Disponibilidad**: > 99.5%
- **Latencia P95**: < 10 segundos
- **Tasa de error**: < 2%
- **Costo mensual**: < $200

### Monitoreo Continuo
```bash
# Script de monitoreo continuo
while true; do
    python -c "from llm_monitor import get_monitoring_stats; stats = get_monitoring_stats(); print(f'{datetime.now()}: {stats}')" >> monitoring.log
    sleep 300  # 5 minutos
done
```

---

## ✅ CHECKLIST POST-MIGRACIÓN

### Día 1
- [ ] Verificar funcionamiento básico
- [ ] Probar consultas de usuario típicas
- [ ] Verificar logs sin errores
- [ ] Confirmar alertas configuradas

### Semana 1
- [ ] Monitorear uso de cuotas
- [ ] Verificar rendimiento vs Gemini
- [ ] Recopilar feedback de usuarios
- [ ] Ajustar umbrales de alerta si necesario

### Mes 1
- [ ] Análisis de costos
- [ ] Optimización de configuración
- [ ] Documentar lecciones aprendidas
- [ ] Planificar mejoras futuras

---

*Este runbook se actualiza automáticamente con cada despliegue. Última actualización: $(date)*