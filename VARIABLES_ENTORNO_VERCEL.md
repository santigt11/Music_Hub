# Configuración de Variables de Entorno en Vercel

Este proyecto requiere que configures las siguientes variables de entorno en Vercel para funcionar correctamente.

## Variables Requeridas

### 1. QOBUZ_TOKEN
- **Descripción**: Token de autenticación para la API de Qobuz
- **Cómo obtenerlo**: Obtén este token desde tu cuenta de desarrollador de Qobuz
- **Ejemplo**: `uvYlbmnFsM0l0NBV6WPk7ZWODJyP1-CNCOVxYSycocXurhfHuqrq29GbDkouItq8yaiwNropgKUJN8H0MYbjxg`

### 2. QOBUZ_USER_ID
- **Descripción**: ID de usuario de Qobuz
- **Cómo obtenerlo**: Desde tu perfil de Qobuz o API
- **Ejemplo**: `12345678`

### 3. QOBUZ_APP_ID
- **Descripción**: ID de aplicación de Qobuz
- **Cómo obtenerlo**: Registro de desarrollador en Qobuz
- **Ejemplo**: `285473059`

### 4. QOBUZ_APP_SECRET
- **Descripción**: Secreto de aplicación de Qobuz
- **Cómo obtenerlo**: Panel de desarrollador de Qobuz
- **Ejemplo**: `9efd1e3b2cf3480f8aafbc94d2127aa5`

### 5. GENIUS_TOKEN
- **Descripción**: Token de API de Genius para búsqueda de letras
- **Cómo obtenerlo**: Registrarse en https://genius.com/api-clients
- **Ejemplo**: `bOb0AM7TteQJ9J2t1JjQtHfSw2qlhp_U5oyFRenLmshiQw0jgrowXLyurdbda6Rt`

## Cómo Configurar en Vercel

### Opción 1: Dashboard de Vercel
1. Ve a tu proyecto en https://vercel.com/dashboard
2. Selecciona tu proyecto
3. Ve a la pestaña "Settings"
4. Selecciona "Environment Variables"
5. Agrega cada variable con su nombre y valor

### Opción 2: Vercel CLI
```bash
vercel env add QOBUZ_TOKEN
vercel env add QOBUZ_USER_ID
vercel env add QOBUZ_APP_ID
vercel env add QOBUZ_APP_SECRET
vercel env add GENIUS_TOKEN
```

### Opción 3: Archivo vercel.json (NO RECOMENDADO para secretos)
```json
{
  "env": {
    "QOBUZ_TOKEN": "@qobuz-token",
    "QOBUZ_USER_ID": "@qobuz-user-id",
    "QOBUZ_APP_ID": "@qobuz-app-id",
    "QOBUZ_APP_SECRET": "@qobuz-app-secret",
    "GENIUS_TOKEN": "@genius-token"
  }
}
```

## Entornos

Puedes configurar diferentes valores para:
- **Production**: Valores para el entorno de producción
- **Preview**: Valores para ramas de preview/desarrollo
- **Development**: Valores para desarrollo local

## Verificación

Para verificar que las variables están configuradas correctamente, puedes:

1. Revisar los logs de despliegue en Vercel
2. La aplicación mostrará un error claro si falta alguna variable
3. Usar el endpoint de health check (si existe) para verificar la configuración

## Seguridad

⚠️ **IMPORTANTE**: 
- Nunca commitees estos valores en tu código
- Usa siempre variables de entorno para información sensible
- Revisa regularmente tus tokens y renuévalos si es necesario

## Troubleshooting

Si encuentras errores:
1. Verifica que todas las variables estén configuradas
2. Asegúrate de que no haya espacios extra en los valores
3. Redespliega después de agregar/modificar variables
4. Revisa los logs de Vercel para errores específicos