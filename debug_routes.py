#!/usr/bin/env python3
"""
Script para verificar las rutas disponibles en la aplicación Flask
"""

import sys
sys.path.insert(0, '.')

from app_modules.app_factory import create_app

app = create_app()

print("🔍 Verificando rutas disponibles en la aplicación Flask:\n")

for rule in app.url_map.iter_rules():
    methods = ','.join(rule.methods - {'OPTIONS', 'HEAD'})
    print(f"  {rule.rule:<30} [{methods}] -> {rule.endpoint}")

print(f"\n📊 Total de rutas: {len(list(app.url_map.iter_rules()))}")

# Verificar específicamente los endpoints de debug
debug_routes = [rule for rule in app.url_map.iter_rules() if 'debug' in rule.rule]
print(f"\n🔧 Rutas de debug encontradas: {len(debug_routes)}")
for route in debug_routes:
    print(f"  {route.rule} -> {route.endpoint}")
