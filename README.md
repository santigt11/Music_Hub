# Music Downloader Web App

Una aplicación web moderna y minimalista para descargar música de Qobuz y Spotify.

## Características

- ✨ Interfaz moderna y responsiva
- 🎵 Descarga desde Qobuz (con token)
- 🎧 Búsqueda por enlaces de Spotify
- 🔒 Token seguro (solo en backend)
- 📱 Compatible con dispositivos móviles
- ⚡ Búsqueda rápida y descarga directa

## Instalación

### 1. Configurar el entorno Python

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
cd web
pip install -r requirements.txt
```

### 2. Configurar el token de Qobuz

Edita el archivo `config.py` en la raíz del proyecto y agrega tu token de Qobuz:

```python
QOBUZ_TOKEN = "tu_token_aqui"
```

### 3. Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

## Uso

### Búsqueda en Qobuz
1. Selecciona la pestaña "Qobuz"
2. Ingresa el nombre de la canción, artista o álbum
3. Presiona "Buscar"
4. Selecciona la calidad deseada
5. Haz clic en "Descargar"

### Búsqueda en Spotify
1. Selecciona la pestaña "Spotify"
2. Pega un enlace de Spotify (track, album, playlist)
3. Presiona "Buscar"
4. Las canciones se buscarán automáticamente en Qobuz
5. Descarga con la calidad disponible

## Calidades disponibles

### Qobuz
- MP3 320kbps
- FLAC 16-bit/44.1kHz (CD Quality)
- FLAC 24-bit/96kHz (Hi-Res)

### Spotify → Qobuz
- Automáticamente busca la mejor calidad disponible en Qobuz

## Estructura del proyecto

```
web/
├── app.py              # Backend Flask
├── requirements.txt    # Dependencias Python
├── templates/
│   └── index.html     # Frontend principal
└── static/
    ├── style.css      # Estilos CSS
    └── script.js      # Lógica JavaScript
```

## API Endpoints

### POST `/api/search`
Busca canciones en Qobuz o por enlace de Spotify.

**Body:**
```json
{
    "query": "nombre_cancion_o_enlace",
    "source": "qobuz" | "spotify"
}
```

### POST `/api/download`
Obtiene el enlace de descarga para una canción.

**Body:**
```json
{
    "song_data": {...},
    "quality": "27",
    "source": "qobuz"
}
```

### GET `/api/proxy-download`
Proxy para descargar archivos evitando CORS.

## Despliegue

### Opción 1: Solo Frontend (GitHub Pages)
Para usar solo el frontend con un backend externo:

1. Sube los archivos de `templates/` y `static/` a GitHub Pages
2. Modifica las URLs de la API en `script.js` para apuntar a tu backend
3. Despliega el backend en un servidor separado (Heroku, Railway, etc.)

### Opción 2: Aplicación completa
Despliega toda la aplicación en un servidor que soporte Python/Flask:

- Heroku
- Railway
- DigitalOcean App Platform
- Google Cloud Run
- AWS Elastic Beanstalk

## Seguridad

- ✅ El token de Qobuz nunca se expone al frontend
- ✅ Las búsquedas se procesan en el backend
- ✅ Los enlaces de descarga son temporales
- ✅ No se almacenan credenciales en el navegador

## Troubleshooting

### Error: "Error de conexión"
- Verifica que el backend esté funcionando en `http://localhost:5000`
- Revisa la consola del navegador para errores específicos

### Error: "Token inválido"
- Verifica que el token de Qobuz en `config.py` sea válido
- El token se obtiene automáticamente del navegador o apps de Qobuz

### No se encuentran resultados
- Verifica la ortografía del término de búsqueda
- Para Spotify, asegúrate de usar enlaces válidos
- Algunas canciones pueden no estar disponibles en Qobuz

## Contribuir

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -am 'Agregar nueva caracteristica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

## Licencia

Este proyecto es para uso educativo. Respeta los términos de servicio de Qobuz y Spotify.
