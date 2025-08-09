#!/usr/bin/env python3
"""
Script para verificar la configuración de variables de entorno
Útil para debuggear problemas en Vercel
"""

import os
import sys

def verificar_variables():
    """Verifica que todas las variables de entorno estén configuradas"""
    
    print("🔍 Verificando configuración de variables de entorno...\n")
    
    variables_requeridas = {
        'QOBUZ_TOKEN': 'Token de API de Qobuz',
        'GENIUS_TOKEN': 'Token de API de Genius (para búsqueda por letras)'
    }
    
    variables_opcionales = {
        'FLASK_ENV': 'Entorno de Flask',
        'FLASK_DEBUG': 'Debug de Flask',
        'PORT': 'Puerto del servidor'
    }
    
    # Verificar variables requeridas
    print("📋 Variables REQUERIDAS:")
    todas_ok = True
    
    for var, descripcion in variables_requeridas.items():
        valor = os.environ.get(var)
        if valor:
            print(f"  ✅ {var}: {valor[:20]}... ({descripcion})")
        else:
            print(f"  ❌ {var}: NO CONFIGURADA ({descripcion})")
            todas_ok = False
    
    # Verificar variables opcionales
    print("\n🔧 Variables OPCIONALES:")
    for var, descripcion in variables_opcionales.items():
        valor = os.environ.get(var, 'No configurada')
        print(f"  ⚙️  {var}: {valor} ({descripcion})")
    
    # Resultado final
    print("\n" + "="*50)
    if todas_ok:
        print("✅ CONFIGURACIÓN CORRECTA: Todas las variables requeridas están configuradas")
        return True
    else:
        print("❌ CONFIGURACIÓN INCOMPLETA: Faltan variables requeridas")
        print("\n💡 Para configurar en Vercel:")
        print("   1. Ve a tu proyecto en Vercel Dashboard")
        print("   2. Settings → Environment Variables")
        print("   3. Agrega las variables faltantes")
        print("   4. Redespliega el proyecto")
        return False

if __name__ == "__main__":
    sys.exit(0 if verificar_variables() else 1)
