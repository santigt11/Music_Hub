# Usa una imagen base oficial de Python
FROM python:3.10-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos de dependencias primero para aprovechar el cache de Docker
COPY requirements.txt ./

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos del proyecto
COPY . .

# Expone el puerto 80 (ajusta si tu app usa otro puerto)
EXPOSE 80

# Comando por defecto para ejecutar la aplicación (ajusta si usas otro archivo o framework)
CMD ["python", "app.py"]
