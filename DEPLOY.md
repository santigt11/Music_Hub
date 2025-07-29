# Despliegue en Vercel - Qobuz Music Downloader

## 📋 Pasos para desplegar

### 1. Preparar el repositorio
```bash
# Si no tienes git inicializado
git init
git add .
git commit -m "Initial commit for Vercel deployment"

# Subir a GitHub
git remote add origin https://github.com/tu-usuario/tu-repositorio.git
git push -u origin main
```

### 2. Configurar Vercel

1. Ve a [vercel.com](https://vercel.com) y conecta tu cuenta de GitHub
2. Haz clic en "New Project"
3. Selecciona tu repositorio
4. Configura el proyecto:

#### Framework Settings:
- **Framework Preset**: Other
- **Build Command**: `echo "No build step required"`
- **Output Directory**: `.` (punto)
- **Install Command**: `pip install -r requirements.txt`
- **Development Command**: `python app.py`

### 3. Variables de entorno

En Vercel → Settings → Environment Variables, agrega:

| Variable | Valor |
|----------|-------|
| `VERCEL` | `1` |
| `FLASK_ENV` | `production` |
| `FLASK_DEBUG` | `0` |
| `QOBUZ_TOKEN` | `tu_token_de_qobuz` |

### 4. Desplegar

1. Haz clic en "Deploy"
2. Espera a que termine el build
3. ¡Tu aplicación estará lista!

## 🔧 Estructura de archivos

```
web/
├── app.py              # Aplicación Flask principal
├── requirements.txt    # Dependencias Python
├── vercel.json        # Configuración de Vercel
├── package.json       # Configuración del proyecto
├── static/            # Archivos estáticos (CSS, JS, imágenes)
├── templates/         # Plantillas HTML
├── .env.example       # Ejemplo de variables de entorno
├── .gitignore         # Archivos a ignorar en git
└── DEPLOY.md          # Esta guía
```

## ⚠️ Limitaciones de Vercel

- **Tiempo límite**: 10 segundos por request
- **Memoria**: 1024MB máximo
- **Tamaño de respuesta**: 4.5MB máximo
- **No persistencia**: Los archivos no se guardan permanentemente

## 🐛 Troubleshooting

### Error: "Module not found"
- Verifica que todas las dependencias estén en `requirements.txt`
- Asegúrate de que no hay imports relativos problemáticos

### Error: "Function timeout"
- Las descargas grandes pueden exceder el límite de 10 segundos
- La aplicación devuelve URLs de descarga directa en lugar de archivos

### Error: "Build failed"
- Revisa los logs de build en Vercel
- Verifica que `vercel.json` esté configurado correctamente

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en Vercel Dashboard
2. Verifica que todas las variables de entorno estén configuradas
3. Asegúrate de que tu token de Qobuz sea válido