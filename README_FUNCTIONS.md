# Azure Functions para Python

Este proyecto es una aplicación Flask convertida para ejecutarse en Azure Functions.

## Estructura del proyecto

- `function_app.py`: Punto de entrada para Azure Functions
- `app.py`: Aplicación Flask principal
- `host.json`: Configuración de Azure Functions
- `requirements.txt`: Dependencias de Python
- `local.settings.json`: Configuración local (no subir a producción)

## Despliegue

### Opción 1: Azure Functions Core Tools

1. Instalar Azure Functions Core Tools:
   ```bash
   npm install -g azure-functions-core-tools@4 --unsafe-perm true
   ```

2. Loguearse en Azure:
   ```bash
   az login
   ```

3. Crear Function App:
   ```bash
   az functionapp create --resource-group <resource-group> --consumption-plan-location <region> --runtime python --runtime-version 3.11 --functions-version 4 --name <function-app-name> --storage-account <storage-account>
   ```

4. Desplegar:
   ```bash
   func azure functionapp publish <function-app-name>
   ```

### Opción 2: Visual Studio Code

1. Instalar la extensión Azure Functions
2. Abrir la carpeta del proyecto
3. F1 > "Azure Functions: Deploy to Function App"

### Opción 3: ZIP Deploy

1. Crear ZIP del proyecto
2. Usar Azure Portal o Azure CLI para subir

## Configuración local

Para probar localmente:

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Ejecutar localmente:
   ```bash
   func start
   ```

La aplicación estará disponible en `http://localhost:7071`
