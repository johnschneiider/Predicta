#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'betting_bot.settings')
django.setup()

from football_data.models import Match, League, ExcelFile

def clean_data():
    print("🧹 LIMPIANDO DATOS EXISTENTES...\n")
    
    # Eliminar todos los partidos
    matches_count = Match.objects.count()
    Match.objects.all().delete()
    print(f"✅ Eliminados {matches_count} partidos")
    
    # Eliminar todos los archivos Excel
    files_count = ExcelFile.objects.count()
    ExcelFile.objects.all().delete()
    print(f"✅ Eliminados {files_count} archivos Excel")
    
    # Mantener las ligas (no las eliminamos)
    leagues_count = League.objects.count()
    print(f"📊 Mantenidas {leagues_count} ligas")
    
    print(f"\n🎯 BASE DE DATOS LIMPIA - Lista para importar datos frescos")

if __name__ == "__main__":
    clean_data()
