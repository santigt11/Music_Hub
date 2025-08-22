# 🔄 Sistema de Renovación Automática para Vercel

## ¿Cómo funciona en Vercel?

En Vercel, el sistema de renovación automática funciona de manera diferente que en un servidor tradicional:

### 🔍 **Detección Automática**
- Cada vez que usas la aplicación, verifica automáticamente si el token está próximo a vencer
- Cuando quedan ≤ 7 días, activa el proceso de renovación
- Busca nuevas credenciales en **arldeemix.com** automáticamente

### 📋 **Proceso de Renovación**

1. **Búsqueda Automática**: El sistema extrae credenciales de la página que especificaste
2. **Validación**: Verifica que las credenciales funcionen
3. **Instrucciones para Vercel**: Te muestra exactamente qué variables de entorno actualizar
4. **Modal Interactivo**: Interface para copiar las instrucciones y actualizar Vercel

### 🚀 **Pasos para Actualizar en Vercel**

Cuando el sistema encuentre nuevas credenciales:

1. **Aparecerá un modal** con las nuevas credenciales formateadas
2. **Copia las variables** usando el botón "📋 Copiar instrucciones"
3. **Ve a tu dashboard de Vercel**: https://vercel.com/dashboard
4. **Selecciona tu proyecto** Music Hub
5. **Ve a Settings → Environment Variables**
6. **Actualiza estas variables**:
   ```
   QOBUZ_TOKEN = [nuevo_token]
   QOBUZ_APP_ID = [nuevo_app_id]
   QOBUZ_APP_SECRET = [nuevo_app_secret]
   QOBUZ_USER_ID = [nuevo_user_id]
   QOBUZ_UPDATED_AT = [fecha_actual]
   ```
7. **Redeploy** tu aplicación

### ⚙️ **Variables de Entorno Requeridas**

Para que funcione correctamente en Vercel, asegúrate de tener:

```env
# Variables principales
QOBUZ_TOKEN=tu_token_actual
GENIUS_TOKEN=tu_token_de_genius

# Variables opcionales (para credenciales completas)
QOBUZ_APP_ID=app_id_si_disponible
QOBUZ_APP_SECRET=app_secret_si_disponible
QOBUZ_USER_ID=user_id_si_disponible
QOBUZ_UPDATED_AT=fecha_ultima_actualizacion
```

### 🔔 **Notificaciones Automáticas**

- **Verde**: Todo está funcionando, muchos días restantes
- **Amarillo**: ⚠️ Renovación necesaria (≤ 7 días)
- **Rojo**: Token expirado o error

### 💾 **Backup Local**

El sistema también guarda un respaldo en el navegador usando `localStorage`:
- Útil como referencia
- No afecta la aplicación
- Solo para consulta

### 🔧 **Testing Manual**

Puedes probar la renovación manualmente:
- **"Verificar renovación"**: Revisa si es necesario renovar
- **"Renovar ahora"**: Fuerza la búsqueda de nuevas credenciales

### ⏱️ **Limitaciones de Vercel**

- **No hay cron jobs**: La verificación solo ocurre cuando alguien usa la app
- **Sin persistencia**: Los archivos se reinician en cada deploy
- **Variables de entorno**: Es la única forma confiable de guardar datos
- **Timeouts**: Las funciones tienen límite de tiempo (generalmente suficiente)

### 🎯 **Ventajas del Sistema**

✅ **Totalmente automático**: Detecta y extrae credenciales sin intervención  
✅ **Interface intuitiva**: Modal con instrucciones claras  
✅ **Validación automática**: Verifica que las credenciales funcionen  
✅ **Multi-entorno**: Funciona tanto en desarrollo como en Vercel  
✅ **Backup automático**: Guarda respaldo en el navegador  
✅ **Zero downtime**: El token actual sigue funcionando mientras actualizas  

### 🔄 **Flujo Completo**

```
Token a 7 días de vencer
     ↓
Sistema busca en arldeemix.com
     ↓
Encuentra nuevas credenciales
     ↓
Las valida automáticamente
     ↓
Muestra modal con instrucciones
     ↓
Usuario copia y actualiza en Vercel
     ↓
Redeploy automático
     ↓
✅ Renovación completa
```