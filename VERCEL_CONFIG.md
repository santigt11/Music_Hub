# Configuración de Variables de Entorno en Vercel

## Problema
La búsqueda por letras funciona en local pero no en Vercel porque falta la variable de entorno `GENIUS_TOKEN`.

## Solución

### 1. Acceder a la configuración de Vercel
1. Ve a tu dashboard de Vercel: https://vercel.com/dashboard
2. Selecciona tu proyecto
3. Ve a **Settings** → **Environment Variables**

### 2. Agregar las variables necesarias
Agrega estas variables de entorno:

```
QOBUZ_TOKEN=wGhVEBhBrpMHmQ1TnZ7njn0_WuGUUeujgHP-KBerx1DRiYeKcgO0Czm8_Us6W9WvxPWmJd0IEnEBi75FE0qE1w
GENIUS_TOKEN=bOb0AM7TteQJ9J2t1JjQtHfSw2qlhp_U5oyFRenLmshiQw0jgrowXLyurdbda6Rt
FLASK_ENV=production
```

### 3. Configurar el entorno
- **Name**: Nombre de la variable (ej: `GENIUS_TOKEN`)
- **Value**: El valor del token
- **Environment**: Selecciona `Production`, `Preview` y `Development` según necesites

### 4. Redesplegar
Después de agregar las variables:
1. Ve a **Deployments**
2. Haz clic en el botón de "Redeploy" en el último deployment
3. O haz un nuevo push al repositorio

## Variables Requeridas

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `QOBUZ_TOKEN` | Token de la API de Qobuz | ✅ Sí |
| `GENIUS_TOKEN` | Token de la API de Genius para búsqueda por letras | ✅ Sí |
| `FLASK_ENV` | Entorno de Flask (production/development) | ⚠️ Recomendada |
| `FLASK_DEBUG` | Habilitar debug (0 o 1) | ❌ Opcional |

## Verificación

### 1. Verificar variables de entorno
Accede a: `https://tu-dominio.vercel.app/api/debug/env`

Debería mostrar:
```json
{
  "genius_token_configured": true,
  "genius_token_preview": "bOb0AM7TteQJ9J2t1JjQ...",
  "qobuz_token_configured": true,
  "env_genius": true,
  "env_qobuz": true
}
```

### 2. Probar búsqueda por letras
Accede a: `https://tu-dominio.vercel.app/api/debug/lyrics-test`

Debería mostrar:
```json
{
  "success": true,
  "results_count": 1,
  "results": [{"title": "POV", "artist": "ROBLEIS", ...}]
}
```

### 3. Revisar logs
Puedes revisar los logs de Vercel en la sección **Functions** para ver si hay errores relacionados con el token de Genius.

## Troubleshooting

Si las pruebas fallan:

1. **Variables no configuradas**: Verifica que `env_genius: true` en `/api/debug/env`
2. **Token inválido**: Verifica que el token de Genius sea correcto
3. **Errores de red**: Revisa los logs de funciones en Vercel
4. **Cache**: Intenta hacer un redeploy completo

Una vez configurado correctamente, la búsqueda por letras debería funcionar igual que en local.
