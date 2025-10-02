"""
Comando para limpiar archivos Excel duplicados
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from football_data.models import ExcelFile, Match

class Command(BaseCommand):
    help = 'Limpia archivos Excel duplicados y mantiene solo el más reciente'

    def handle(self, *args, **options):
        self.stdout.write("🧹 Iniciando limpieza de duplicados...")
        
        # Obtener todos los archivos agrupados por nombre y liga
        files_by_name_league = {}
        
        for file in ExcelFile.objects.all():
            key = f"{file.name}_{file.league.id}"
            if key not in files_by_name_league:
                files_by_name_league[key] = []
            files_by_name_league[key].append(file)
        
        duplicates_removed = 0
        
        with transaction.atomic():
            for key, files in files_by_name_league.items():
                if len(files) > 1:
                    self.stdout.write(f"📁 Encontrados {len(files)} duplicados para: {files[0].name}")
                    
                    # Ordenar por fecha de importación (más reciente primero)
                    files.sort(key=lambda x: x.imported_at, reverse=True)
                    
                    # Mantener el más reciente, eliminar el resto
                    keep_file = files[0]
                    files_to_delete = files[1:]
                    
                    self.stdout.write(f"  ✅ Manteniendo: {keep_file.name} (ID: {keep_file.id}, {keep_file.imported_at})")
                    
                    for file_to_delete in files_to_delete:
                        self.stdout.write(f"  🗑️  Eliminando: {file_to_delete.name} (ID: {file_to_delete.id}, {file_to_delete.imported_at})")
                        
                        # Eliminar el archivo físico si existe
                        if file_to_delete.file and file_to_delete.file.path:
                            try:
                                import os
                                if os.path.exists(file_to_delete.file.path):
                                    os.remove(file_to_delete.file.path)
                                    self.stdout.write(f"    📄 Archivo físico eliminado: {file_to_delete.file.path}")
                            except Exception as e:
                                self.stdout.write(f"    ⚠️  Error eliminando archivo físico: {e}")
                        
                        # Eliminar el registro de la base de datos
                        file_to_delete.delete()
                        duplicates_removed += 1
        
        self.stdout.write(f"\n✅ Limpieza completada!")
        self.stdout.write(f"📊 Archivos duplicados eliminados: {duplicates_removed}")
        
        # Mostrar estadísticas finales
        total_files = ExcelFile.objects.count()
        total_matches = Match.objects.count()
        
        self.stdout.write(f"\n📈 ESTADÍSTICAS FINALES:")
        self.stdout.write(f"  📁 Archivos Excel: {total_files}")
        self.stdout.write(f"  ⚽ Partidos: {total_matches}")
        
        # Mostrar archivos restantes
        self.stdout.write(f"\n📋 ARCHIVOS RESTANTES:")
        for file in ExcelFile.objects.all().order_by('-imported_at'):
            matches_count = Match.objects.filter(league=file.league).count()
            self.stdout.write(f"  {file.name} - {file.league.name} - {matches_count} partidos - {file.imported_at}")
