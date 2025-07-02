import azure.functions as func
import logging
import os
from app import app

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Crear la aplicación de Azure Functions
function_app = func.FunctionApp()

@function_app.route(route="{*route}", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def main(req: func.HttpRequest) -> func.HttpResponse:
    """Función HTTP que maneja todas las rutas de Flask"""
    logging.info(f'HTTP trigger function processed request: {req.method} {req.url}')
    
    try:
        # Obtener la ruta y parámetros
        route = req.route_params.get('route', '')
        if route is None:
            route = ''
        
        # Si la ruta está vacía, redirigir al index
        if not route or route == '':
            route = '/'
        elif not route.startswith('/'):
            route = '/' + route
            
        logging.info(f'Processing route: {route}')
        
        # Preparar headers para Flask
        headers = {}
        for key, value in req.headers.items():
            headers[key] = value
        
        # Crear el contexto de request para Flask
        with app.test_request_context(
            path=route,
            method=req.method,
            headers=headers,
            query_string=req.url.split('?', 1)[1] if '?' in req.url else '',
            data=req.get_body()
        ):
            # Procesar la request con Flask
            response = app.full_dispatch_request()
            
            # Preparar headers de respuesta
            response_headers = {}
            for key, value in response.headers:
                response_headers[key] = value
            
            # Crear la respuesta de Azure Functions
            return func.HttpResponse(
                body=response.get_data(),
                status_code=response.status_code,
                headers=response_headers,
                mimetype=response.content_type or 'text/html'
            )
            
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        logging.error(f"Route: {route}")
        logging.error(f"Method: {req.method}")
        logging.error(f"URL: {req.url}")
        import traceback
        logging.error(traceback.format_exc())
        
        return func.HttpResponse(
            body=f"Error interno del servidor: {str(e)}",
            status_code=500,
            mimetype='text/plain'
        )

# Función específica para la ruta raíz
@function_app.route(route="", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def root(req: func.HttpRequest) -> func.HttpResponse:
    """Función para manejar la ruta raíz específicamente"""
    logging.info('Root route accessed')
    
    try:
        with app.test_request_context(path='/', method='GET'):
            response = app.full_dispatch_request()
            
            response_headers = {}
            for key, value in response.headers:
                response_headers[key] = value
            
            return func.HttpResponse(
                body=response.get_data(),
                status_code=response.status_code,
                headers=response_headers,
                mimetype=response.content_type or 'text/html'
            )
    except Exception as e:
        logging.error(f"Error in root route: {str(e)}")
        return func.HttpResponse(
            body=f"Error: {str(e)}",
            status_code=500
        )
