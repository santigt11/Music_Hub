from flask import Flask, request
import os

# Configurar variables de entorno para Vercel
os.environ['VERCEL'] = '1'

# Importar la aplicación
from app import app

# Handler para Vercel - Formato correcto para serverless functions
def handler(event, context):
    """
    Handler para Vercel serverless functions
    """
    try:
        # Crear un contexto de aplicación Flask
        with app.app_context():
            # Usar el test client para procesar la request
            with app.test_client() as client:
                # Extraer información del evento
                method = event.get('httpMethod', 'GET')
                path = event.get('path', '/')
                headers = event.get('headers', {})
                body = event.get('body', '')
                query_params = event.get('queryStringParameters') or {}
                
                # Construir la URL con query parameters
                if query_params:
                    query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
                    path = f"{path}?{query_string}"
                
                # Hacer la request
                if method == 'GET':
                    response = client.get(path, headers=headers)
                elif method == 'POST':
                    response = client.post(path, data=body, headers=headers)
                elif method == 'PUT':
                    response = client.put(path, data=body, headers=headers)
                elif method == 'DELETE':
                    response = client.delete(path, headers=headers)
                else:
                    response = client.get(path, headers=headers)
                
                # Formatear respuesta para Vercel
                return {
                    'statusCode': response.status_code,
                    'headers': dict(response.headers),
                    'body': response.get_data(as_text=True)
                }
                
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "Internal server error: {str(e)}"}}'
        }

# Exportar la app también
app_instance = app

if __name__ == "__main__":
    app.run(debug=True)