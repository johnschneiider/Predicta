#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'betting_bot.settings')
django.setup()

from football_data.models import ExcelFile, Match, League

def check_duplicates():
    print("=== VERIFICACIÓN DE DUPLICADOS ===\n")
    
    # 1. Verificar archivos Excel
    print("📁 ARCHIVOS EXCEL:")
    files = ExcelFile.objects.all().order_by('-imported_at')
    for file in files:
        print(f"  ID: {file.id}")
        print(f"  Nombre: {file.name}")
        print(f"  Liga: {file.league.name}")
        print(f"  Partidos: {file.imported_rows}")
        print(f"  Fecha: {file.imported_at}")
        print(f"  Ruta: {file.file_path}")
        print("  ---")
    
    print(f"\nTotal archivos: {files.count()}")
    
    # 2. Verificar partidos
    print(f"\n⚽ PARTIDOS:")
    matches = Match.objects.all()
    print(f"Total partidos: {matches.count()}")
    
    # 3. Verificar duplicados por archivo
    print(f"\n🔍 ANÁLISIS DE DUPLICADOS:")
    file_names = {}
    for file in files:
        if file.name in file_names:
            file_names[file.name] += 1
        else:
            file_names[file.name] = 1
    
    duplicates_found = False
    for name, count in file_names.items():
        if count > 1:
            print(f"  ⚠️  DUPLICADO: {name} aparece {count} veces")
            duplicates_found = True
    
    if not duplicates_found:
        print("  ✅ No se encontraron archivos duplicados")
    
    # 4. Verificar partidos duplicados
    print(f"\n⚽ VERIFICACIÓN DE PARTIDOS DUPLICADOS:")
    matches_by_key = {}
    for match in matches:
        key = f"{match.home_team} vs {match.away_team} - {match.date}"
        if key in matches_by_key:
            matches_by_key[key] += 1
        else:
            matches_by_key[key] = 1
    
    duplicate_matches = 0
    for key, count in matches_by_key.items():
        if count > 1:
            print(f"  ⚠️  PARTIDO DUPLICADO: {key} ({count} veces)")
            duplicate_matches += 1
    
    if duplicate_matches == 0:
        print("  ✅ No se encontraron partidos duplicados")
    else:
        print(f"  ⚠️  Total partidos duplicados: {duplicate_matches}")
    
    # 5. Verificar por liga
    print(f"\n🏆 PARTIDOS POR LIGA:")
    leagues = League.objects.all()
    for league in leagues:
        league_matches = Match.objects.filter(league=league).count()
        league_files = ExcelFile.objects.filter(league=league).count()
        print(f"  {league.name}: {league_matches} partidos, {league_files} archivos")

if __name__ == "__main__":
    check_duplicates()
