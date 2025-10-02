#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'betting_bot.settings')
django.setup()

from football_data.models import ExcelFile, Match, League
from django.db import transaction

def fix_duplicates():
    print("🧹 LIMPIANDO DUPLICADOS...\n")
    
    # Obtener todos los archivos
    all_files = ExcelFile.objects.all().order_by('-imported_at')
    print(f"📁 Total archivos encontrados: {all_files.count()}")
    
    # Agrupar por nombre y liga
    files_by_key = {}
    for file in all_files:
        key = f"{file.name}_{file.league.id}"
        if key not in files_by_key:
            files_by_key[key] = []
        files_by_key[key].append(file)
    
    duplicates_removed = 0
    
    with transaction.atomic():
        for key, files in files_by_key.items():
            if len(files) > 1:
                print(f"\n🔍 DUPLICADOS ENCONTRADOS: {files[0].name}")
                print(f"   Liga: {files[0].league.name}")
                print(f"   Cantidad: {len(files)}")
                
                # Ordenar por fecha (más reciente primero)
                files.sort(key=lambda x: x.imported_at, reverse=True)
                
                # Mantener el más reciente
                keep_file = files[0]
                print(f"   ✅ MANTENIENDO: ID {keep_file.id} ({keep_file.imported_at})")
                
                # Eliminar los duplicados
                for file_to_delete in files[1:]:
                    print(f"   🗑️  ELIMINANDO: ID {file_to_delete.id} ({file_to_delete.imported_at})")
                    file_to_delete.delete()
                    duplicates_removed += 1
    
    print(f"\n✅ LIMPIEZA COMPLETADA!")
    print(f"📊 Archivos duplicados eliminados: {duplicates_removed}")
    
    # Estadísticas finales
    total_files = ExcelFile.objects.count()
    total_matches = Match.objects.count()
    
    print(f"\n📈 ESTADÍSTICAS FINALES:")
    print(f"   📁 Archivos Excel: {total_files}")
    print(f"   ⚽ Partidos: {total_matches}")
    
    # Mostrar archivos restantes
    print(f"\n📋 ARCHIVOS RESTANTES:")
    for file in ExcelFile.objects.all().order_by('-imported_at'):
        matches_count = Match.objects.filter(league=file.league).count()
        print(f"   {file.name} - {file.league.name} - {matches_count} partidos")

if __name__ == "__main__":
    fix_duplicates()
