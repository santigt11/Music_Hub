#!/usr/bin/env python3
"""
Script para probar la aplicación localmente antes del despliegue
"""

import os
import sys
import subprocess

def test_dependencies():
    """Verificar que todas las dependencias estén instaladas"""
    print("🔍 Verificando dependencias...")
    
    try:
        import flask
        import flask_cors
        import requests
        import bs4
        print("✅ Todas las dependencias principales están instaladas")
        return True
    except ImportError as e:
        print(f"❌ Falta dependencia: {e}")
        print("💡 Ejecuta: pip install -r requirements.txt")
        return False

def test_token():
    """Verificar que el token esté configurado"""
    print("🔑 Verificando token...")
    
    # Importar después de verificar dependencias
    from app import QOBUZ_TOKEN
    
    if QOBUZ_TOKEN and len(QOBUZ_TOKEN) > 50:
        print("✅ Token configurado correctamente")
        return True
    else:
        print("❌ Token no configurado o inválido")
        print("💡 Verifica la variable QOBUZ_TOKEN en app.py o .env")
        return False

def test_app_startup():
    """Verificar que la aplicación inicie correctamente"""
    print("🚀 Probando inicio de aplicación...")
    
    try:
        from app import app
        
        # Verificar que las rutas principales existan
        with app.test_client() as client:
            # Probar ruta principal
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Ruta principal funciona")
            else:
                print(f"⚠️  Ruta principal devuelve código: {response.status_code}")
            
            # Probar ruta de API
            response = client.get('/api/test')
            print(f"📡 API test endpoint: {response.status_code}")
        
        print("✅ Aplicación inicia correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error al iniciar aplicación: {e}")
        return False

def run_local_server():
    """Ejecutar servidor local para pruebas"""
    print("🌐 Iniciando servidor local...")
    print("📍 La aplicación estará disponible en: http://localhost:5000")
    print("⏹️  Presiona Ctrl+C para detener")
    
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
    except Exception as e:
        print(f"❌ Error ejecutando servidor: {e}")

def main():
    print("🧪 PRUEBA LOCAL - Qobuz Music Downloader")
    print("=" * 50)
    
    # Ejecutar pruebas
    tests = [
        ("Dependencias", test_dependencies),
        ("Token", test_token),
        ("Aplicación", test_app_startup)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n🧪 Prueba: {test_name}")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 Resultado: {passed}/{len(tests)} pruebas pasaron")
    
    if passed == len(tests):
        print("🎉 ¡Todas las pruebas pasaron!")
        
        choice = input("\n¿Quieres iniciar el servidor local? (s/n): ").strip().lower()
        if choice in ['s', 'si', 'yes', 'y']:
            run_local_server()
    else:
        print("❌ Algunas pruebas fallaron. Revisa los errores antes de desplegar.")

if __name__ == "__main__":
    main()