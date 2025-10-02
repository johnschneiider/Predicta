"""
Servicios para importar y procesar datos de Excel
"""

import pandas as pd
import os
import logging
from datetime import datetime
from django.conf import settings
from django.db import transaction, models
from django.utils import timezone

from .models import League, Match, ExcelFile

logger = logging.getLogger('football_data')


class ExcelImportService:
    """Servicio para importar datos de Excel"""
    
    def __init__(self):
        self.data_dir = os.path.join(settings.BASE_DIR, 'data', 'excel_files')
        self.column_mapping = self._get_column_mapping()
    
    def _get_column_mapping(self):
        """Mapeo de columnas del Excel a campos del modelo"""
        return {
            # 'Div': 'league_name',  # Este campo se maneja por separado
            'Date': 'date',
            'Time': 'time',
            'HomeTeam': 'home_team',
            'AwayTeam': 'away_team',
            'FTHG': 'fthg',
            'FTAG': 'ftag',
            'FTR': 'ftr',
            'HTHG': 'hthg',
            'HTAG': 'htag',
            'HTR': 'htr',
            'HS': 'hs',
            'AS': 'as_field',
            'HST': 'hst',
            'AST': 'ast',
            'HF': 'hf',
            'AF': 'af',
            'HC': 'hc',
            'AC': 'ac',
            'HY': 'hy',
            'AY': 'ay',
            'HR': 'hr',
            'AR': 'ar',
            
            # Cuotas principales
            'B365H': 'b365h',
            'B365D': 'b365d',
            'B365A': 'b365a',
            'BFDH': 'bfdh',
            'BFDD': 'bfdd',
            'BFDA': 'bfda',
            'BMGMH': 'bmgmh',
            'BMGMD': 'bmgmd',
            'BMGMA': 'bmgma',
            'BVH': 'bvh',
            'BVD': 'bvd',
            'BVA': 'bva',
            'BWH': 'bwh',
            'BWD': 'bwd',
            'BWA': 'bwa',
            'CLH': 'clh',
            'CLD': 'cld',
            'CLA': 'cla',
            'LBH': 'lbh',
            'LBD': 'lbd',
            'LBA': 'lba',
            'PSH': 'psh',
            'PSD': 'psd',
            'PSA': 'psa',
            'MaxH': 'maxh',
            'MaxD': 'maxd',
            'MaxA': 'maxa',
            'AvgH': 'avgh',
            'AvgD': 'avgd',
            'AvgA': 'avga',
            'BFEH': 'bfeh',
            'BFED': 'bfed',
            'BFEA': 'bfea',
            
            # Mercados de goles
            'B365>2.5': 'b365_over_25',
            'B365<2.5': 'b365_under_25',
            'P>2.5': 'p_over_25',
            'P<2.5': 'p_under_25',
            'Max>2.5': 'max_over_25',
            'Max<2.5': 'max_under_25',
            'Avg>2.5': 'avg_over_25',
            'Avg<2.5': 'avg_under_25',
            'BFE>2.5': 'bfe_over_25',
            'BFE<2.5': 'bfe_under_25',
            
            # Handicap Asiático
            'AHh': 'ahh',
            'B365AHH': 'b365ahh',
            'B365AHA': 'b365aha',
            'PAHH': 'pahh',
            'PAHA': 'paha',
            'MaxAHH': 'maxahh',
            'MaxAHA': 'maxaha',
            'AvgAHH': 'avgahh',
            'AvgAHA': 'avgaha',
            'BFEAHH': 'bfeahh',
            'BFEAHA': 'bfeaha',
            
            # Cuotas de Corners
            'B365CH': 'b365ch',
            'B365CD': 'b365cd',
            'B365CA': 'b365ca',
            'BFDCH': 'bfdch',
            'BFDCD': 'bfdcd',
            'BFDCA': 'bfdca',
            'BMGMCH': 'bmgmch',
            'BMGMCD': 'bmgmcd',
            'BMGMCA': 'bmgmca',
            'BVCH': 'bvch',
            'BVCD': 'bvcd',
            'BVCA': 'bvca',
            'BWCH': 'bwch',
            'BWCD': 'bwcd',
            'BWCA': 'bwca',
            'CLCH': 'clch',
            'CLCD': 'clcd',
            'CLCA': 'clca',
            'LBCH': 'lbch',
            'LBCD': 'lbcd',
            'LBCA': 'lbca',
            'PSCH': 'psch',
            'PSCD': 'pscd',
            'PSCA': 'psca',
            'MaxCH': 'maxch',
            'MaxCD': 'maxcd',
            'MaxCA': 'maxca',
            'AvgCH': 'avgch',
            'AvgCD': 'avgcd',
            'AvgCA': 'avgca',
            'BFECH': 'bfech',
            'BFECD': 'bfecd',
            'BFECA': 'bfeca',
            
            # Mercados de corners Over/Under
            'B365C>2.5': 'b365c_over_25',
            'B365C<2.5': 'b365c_under_25',
            'PC>2.5': 'pc_over_25',
            'PC<2.5': 'pc_under_25',
            'MaxC>2.5': 'maxc_over_25',
            'MaxC<2.5': 'maxc_under_25',
            'AvgC>2.5': 'avgc_over_25',
            'AvgC<2.5': 'avgc_under_25',
            'BFEC>2.5': 'bfec_over_25',
            'BFEC<2.5': 'bfec_under_25',
            
            # Handicap Asiático de Corners
            'AHCh': 'ahch',
            'B365CAHH': 'b365cahh',
            'B365CAHA': 'b365caha',
            'PCAHH': 'pcahh',
            'PCAHA': 'pcaha',
            'MaxCAHH': 'maxcahh',
            'MaxCAHA': 'maxcaha',
            'AvgCAHH': 'avgcahh',
            'AvgCAHA': 'avgcaha',
            'BFECAHH': 'bfecahh',
            'BFECAHA': 'bfecaha',
        }
    
    def get_available_files(self):
        """Obtiene lista de archivos Excel disponibles"""
        if not os.path.exists(self.data_dir):
            return []
        
        files = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith(('.xlsx', '.xls')):
                file_path = os.path.join(self.data_dir, filename)
                file_size = os.path.getsize(file_path)
                files.append({
                    'name': filename,
                    'path': file_path,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
                })
        
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    def read_data_file(self, file_path):
        """Lee un archivo Excel o CSV y retorna DataFrame (tolerante a separadores/formatos)."""
        try:
            is_csv = file_path.lower().endswith('.csv')
            if is_csv:
                # Autodetectar separador y tolerar líneas dañadas
                df = pd.read_csv(
                    file_path,
                    encoding='utf-8',
                    sep=None,
                    engine='python',
                    on_bad_lines='skip'
                )
            else:
                df = pd.read_excel(file_path)

            # Limpiar nombres de columnas
            df.columns = df.columns.astype(str).str.strip()

            # No convertir Date/Time aquí; se hará por fila en _prepare_match_data con lógica robusta

            # Log de diagnóstico: columnas presentes vs esperadas
            expected_cols = set(self._get_column_mapping().keys())
            present_cols = set(df.columns)
            missing_cols = sorted(list(expected_cols - present_cols))
            logger.info(f"Archivo leído exitosamente: {file_path}")
            logger.info(f"Tipo: {'CSV' if is_csv else 'Excel'} dimensiones: {df.shape}")
            logger.info(f"Columnas presentes: {sorted(list(present_cols))}")
            if missing_cols:
                logger.info(f"Columnas faltantes detectadas (se ignorarán): {missing_cols}")

            return df

        except Exception as e:
            logger.error(f"Error leyendo archivo {file_path}: {e}")
            return None
    
    def detect_league(self, df):
        """Detecta la liga basándose en los datos"""
        if 'Div' in df.columns:
            # Obtener la división más común
            div_counts = df['Div'].value_counts()
            most_common_div = div_counts.index[0] if not div_counts.empty else 'Unknown'
            
            # Mapear códigos de división a nombres
            div_mapping = {
                'E0': 'Premier League',
                'E1': 'Championship',
                'E2': 'League One',
                'E3': 'League Two',
                'SP1': 'La Liga',
                'SP2': 'Segunda División',
                'D1': 'Bundesliga',
                'D2': '2. Bundesliga',
                'F1': 'Ligue 1',
                'F2': 'Ligue 2',
                'I1': 'Serie A',
                'I2': 'Serie B',
                'N1': 'Eredivisie',
                'B1': 'Jupiler Pro League',
                'P1': 'Primeira Liga',
                'T1': 'Süper Lig',
                'G1': 'Super League',
                'SC0': 'Scottish Premiership',
                'SC1': 'Scottish Championship',
                'SC2': 'Scottish League One',
                'SC3': 'Scottish League Two',
            }
            
            league_name = div_mapping.get(most_common_div, most_common_div)
            
            # Detectar temporada de forma más robusta
            try:
                if not df['Date'].empty and pd.notna(df['Date'].iloc[0]):
                    year = df['Date'].dt.year.iloc[0]
                    season = f"{year}-{year + 1}"
                else:
                    season = "2024-2025"  # Temporada por defecto
            except (IndexError, AttributeError, TypeError):
                season = "2024-2025"  # Temporada por defecto
            
            return league_name, season
        
        return 'Unknown League', '2024-2025'
    
    def import_data_file(self, file_path, league_name=None, season=None):
        """Importa un archivo Excel/CSV a la base de datos"""
        try:
            # Leer archivo
            df = self.read_data_file(file_path)
            if df is None or df.empty:
                return {'success': False, 'error': 'No se pudo leer el archivo o está vacío'}
            
            # Detectar liga si no se proporciona
            if not league_name:
                league_name, season = self.detect_league(df)
            
            # Asegurar que la temporada no esté vacía
            if not season or season.strip() == '':
                season = "2024-2025"
            
            # Crear o obtener liga
            league, created = League.objects.get_or_create(
                name=league_name,
                defaults={'season': season, 'country': 'Unknown'}
            )
            
            # Crear o actualizar registro de archivo Excel
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # Verificar si el archivo ya existe (manejar duplicados)
            existing_files = ExcelFile.objects.filter(name=file_name, league=league)
            
            if existing_files.exists():
                # Si hay duplicados, eliminar los antiguos y mantener solo el más reciente
                if existing_files.count() > 1:
                    logger.info(f"Encontrados {existing_files.count()} duplicados para {file_name}, limpiando...")
                    # Ordenar por fecha y eliminar todos excepto el más reciente
                    files_sorted = existing_files.order_by('-imported_at')
                    files_to_delete = files_sorted[1:]  # Todos excepto el primero (más reciente)
                    
                    for file_to_delete in files_to_delete:
                        logger.info(f"Eliminando archivo duplicado ID {file_to_delete.id}")
                        file_to_delete.delete()
                
                # Actualizar el archivo restante
                excel_file = existing_files.first()
                excel_file.file_path = file_path
                excel_file.total_rows = len(df)
                excel_file.file_size = file_size
                excel_file.imported_at = timezone.now()
                excel_file.save()
                file_created = False
                logger.info(f"Archivo {file_name} actualizado")
            else:
                # Crear nuevo archivo
                excel_file = ExcelFile.objects.create(
                    name=file_name,
                    file_path=file_path,
                    league=league,
                    total_rows=len(df),
                    file_size=file_size
                )
                file_created = True
                logger.info(f"Nuevo archivo {file_name} creado")
            
            # Importar partidos
            imported_count = 0
            failed_count = 0
            
            # Procesar cada fila individualmente para evitar que un error afecte a todas
            for index, row in df.iterrows():
                try:
                    match_data = self._prepare_match_data(row, league)
                    
                    # Verificar que tenemos los datos mínimos necesarios
                    if not all(key in match_data for key in ['date', 'home_team', 'away_team']):
                        logger.warning(f"Fila {index} no tiene datos mínimos necesarios, saltando...")
                        failed_count += 1
                        continue
                    
                    # Crear o actualizar el partido
                    with transaction.atomic():
                        match, created = Match.objects.update_or_create(
                            league=league,
                            date=match_data['date'],
                            home_team=match_data['home_team'],
                            away_team=match_data['away_team'],
                            defaults=match_data
                        )
                        # Vincular al archivo fuente si no está seteado
                        if match.source_file_id != excel_file.id:
                            match.source_file = excel_file
                            match.save(update_fields=['source_file'])
                        imported_count += 1
                        
                except Exception as e:
                    logger.error(f"Error importando fila {index}: {e}")
                    failed_count += 1
                    continue
            
            # Actualizar estadísticas del archivo
            excel_file.imported_rows = imported_count
            excel_file.failed_rows = failed_count
            excel_file.save()
            
            logger.info(f"Importación completada: {imported_count} partidos importados, {failed_count} fallos")
            
            return {
                'success': True,
                'imported_count': imported_count,
                'failed_count': failed_count,
                'league': league.name,
                'excel_file_id': excel_file.id
            }
            
        except Exception as e:
            logger.error(f"Error importando archivo {file_path}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _prepare_match_data(self, row, league):
        """Prepara los datos de un partido para la base de datos"""
        match_data = {}
        
        # Mapear columnas (tolerante a columnas ausentes)
        for excel_col, model_field in self.column_mapping.items():
            if excel_col in row and pd.notna(row[excel_col]):
                value = row[excel_col]
                
                # Conversiones especiales
                if model_field == 'date':
                    try:
                        if isinstance(value, str):
                            # Intentar diferentes formatos de fecha
                            if value.strip() == '' or value.lower() in ['nan', 'none', '']:
                                continue  # Saltar filas con fechas vacías
                            
                            # Intentar parsear con diferentes formatos
                            for date_format in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%m/%d/%y', '%d.%m.%Y']:
                                try:
                                    value = pd.to_datetime(value, format=date_format).date()
                                    break
                                except:
                                    continue
                            else:
                                # Si ningún formato funciona, intentar parsing automático
                                parsed = pd.to_datetime(value, dayfirst=True, infer_datetime_format=True, errors='coerce')
                                value = parsed.date() if pd.notna(parsed) else None
                                
                        elif hasattr(value, 'date'):
                            value = value.date()
                        elif pd.isna(value):
                            continue  # Saltar valores NaN
                            
                        # Validar que la fecha sea razonable
                        if value.year < 1900 or value.year > 2030:
                            continue  # Saltar fechas inválidas
                            
                    except Exception as date_error:
                        logger.warning(f"Error procesando fecha '{value}': {date_error}")
                        continue  # Saltar esta fila
                elif model_field == 'time':
                    if isinstance(value, str):
                        try:
                            value = pd.to_datetime(value, format='%H:%M', errors='coerce').time()
                        except Exception:
                            value = None
                    elif hasattr(value, 'time'):
                        value = value.time()
                elif model_field in ['fthg', 'ftag', 'hthg', 'htag', 'hs', 'as_field', 'hst', 'ast', 
                                   'hf', 'af', 'hc', 'ac', 'hy', 'ay', 'hr', 'ar']:
                    try:
                        value = int(float(value)) if pd.notna(value) else None
                    except (ValueError, TypeError):
                        value = None
                elif model_field.startswith(('b365', 'bw', 'iw', 'ps', 'wh', 'vc', 'max', 'avg', 'p_', 'ah')):
                    try:
                        value = float(value) if pd.notna(value) else None
                    except (ValueError, TypeError):
                        value = None
                
                # Normalizar nombres de equipos
                if model_field in ['home_team', 'away_team'] and isinstance(value, str):
                    value = value.strip()

                match_data[model_field] = value
        
        return match_data
    
    def get_import_statistics(self):
        """Obtiene estadísticas de importación"""
        total_files = ExcelFile.objects.count()
        total_matches = Match.objects.count()
        total_leagues = League.objects.count()
        
        recent_imports = ExcelFile.objects.order_by('-imported_at')[:5]
        
        return {
            'total_files': total_files,
            'total_matches': total_matches,
            'total_leagues': total_leagues,
            'recent_imports': recent_imports
        }
    
    def get_league_statistics(self, league_id):
        """Obtiene estadísticas de una liga específica"""
        try:
            league = League.objects.get(id=league_id)
            matches = Match.objects.filter(league=league)
            
            # Estadísticas básicas
            total_matches = matches.count()
            matches_with_odds = matches.exclude(b365h__isnull=True).count()
            matches_with_stats = matches.exclude(hs__isnull=True).count()
            
            # Análisis de resultados
            home_wins = matches.filter(ftr='H').count()
            draws = matches.filter(ftr='D').count()
            away_wins = matches.filter(ftr='A').count()
            
            # Análisis de goles
            over_25_matches = matches.exclude(fthg__isnull=True, ftag__isnull=True).filter(
                models.Q(fthg__gt=2) | models.Q(ftag__gt=2) | models.Q(fthg__gte=2, ftag__gte=1) | models.Q(fthg__gte=1, ftag__gte=2)
            ).count()
            
            return {
                'league': league,
                'total_matches': total_matches,
                'matches_with_odds': matches_with_odds,
                'matches_with_stats': matches_with_stats,
                'home_wins': home_wins,
                'draws': draws,
                'away_wins': away_wins,
                'over_25_matches': over_25_matches,
                'home_win_rate': (home_wins / total_matches * 100) if total_matches > 0 else 0,
                'draw_rate': (draws / total_matches * 100) if total_matches > 0 else 0,
                'away_win_rate': (away_wins / total_matches * 100) if total_matches > 0 else 0,
                'over_25_rate': (over_25_matches / total_matches * 100) if total_matches > 0 else 0,
            }
            
        except League.DoesNotExist:
            return None
