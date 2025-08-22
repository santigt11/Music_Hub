# 📁 Estructura Final del Proyecto

## 🗂️ Archivos Principales

```
web/
├── 📄 .env.example              # Plantilla de variables de entorno
├── 📄 .gitignore               # Archivos a ignorar en Git
├── 📄 app.py                   # Aplicación Flask principal
├── 📄 index.py                 # Punto de entrada para Vercel
├── 📄 README.md                # Documentación principal
├── 📄 requirements.txt         # Dependencias Python
├── 📄 vercel.json             # Configuración de Vercel
└── 📄 RENOVACION_VERCEL.md  # Documentación del sistema de renovación
```

## 🔧 Módulos de la Aplicación

```
app_modules/
├── 📄 app_factory.py           # Factory pattern para Flask
├── 📄 config.py                # Configuración de la aplicación
├── routes/
│   └── 📄 api.py               # Rutas de la API
├── services/
│   ├── 📄 auto_renewal.py      # Sistema de renovación automática ⭐
│   ├── 📄 qobuz.py            # Servicio de Qobuz
│   ├── 📄 spotify.py          # Servicio de Spotify
│   └── 📄 vercel_adapter.py   # Adaptador para Vercel ⭐
└── utils/
    ├── 📄 metadata.py          # Utilidades de metadatos
    └── 📄 token.py            # Gestión de tokens
```

## 🎨 Frontend

```
static/
├── 📄 animations.js            # Animaciones JavaScript
├── 📄 script.js               # Lógica principal JS (incluye auto-renovación) ⭐
└── 📄 style.css               # Estilos CSS

templates/
└── 📄 index.html              # Plantilla principal HTML
```

## 🧪 Pruebas

```
tests/
├── 📄 test_lyrics_min.py             # Pruebas de letras
└── 📄 test_search_by_lyrics_genius.py # Pruebas de búsqueda
```

## 📡 API para Vercel

```
api/
└── 📄 index.py                # Endpoint principal para Vercel
```

---

## ⭐ Archivos Clave del Sistema de Renovación

1. **`app_modules/services/auto_renewal.py`** - Sistema principal de renovación
2. **`app_modules/services/vercel_adapter.py`** - Adaptador para entorno Vercel
3. **`static/script.js`** - Interfaz de usuario para renovación
4. **`VERCEL_AUTO_RENEWAL.md`** - Documentación del sistema

## 🚀 Para Desplegar en Vercel

Solo necesitas:
- Los archivos del proyecto (sin `.venv/`)
- Variables de entorno configuradas en el dashboard de Vercel
- El archivo `vercel.json` con la configuración

## 🧹 Archivos Eliminados

- ❌ `vercel_app.py` (redundante con index.py)
- ❌ `wsgi.py` (no necesario para Vercel)
- ❌ `package.json` (no necesario para Python)
- ❌ `DEPLOY.md` (información obsoleta)
- ❌ `verificar_config.py` (archivo temporal)
- ❌ `VERCEL_CONFIG.md` (redundante)
- ❌ `api/requirements.txt` (duplicado)
- ❌ `.pytest_cache/` (caché temporal)

¡Proyecto limpio y listo para producción! 🎉
