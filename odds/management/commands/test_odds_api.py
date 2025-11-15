"""
Comando para probar la API de Odds y ver qué partidos devuelve
"""
from django.core.management.base import BaseCommand
from odds.services import OddsAPIService
import logging
from datetime import datetime, timezone

logger = logging.getLogger('odds')


class Command(BaseCommand):
    help = 'Prueba la API de Odds para ver qué partidos devuelve'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sport-key',
            type=str,
            default='soccer_epl',
            help='Clave del deporte (ej: soccer_epl)',
        )
        parser.add_argument(
            '--all-sports',
            action='store_true',
            help='Probar todos los deportes de fútbol principales',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('[TEST] Iniciando prueba de API de Odds...'))
        
        odds_service = OddsAPIService()
        
        if options['all_sports']:
            # Probar todos los deportes de fútbol principales
            football_sports = [
                ('soccer_epl', 'Premier League'),
                ('soccer_spain_la_liga', 'La Liga'),
                ('soccer_italy_serie_a', 'Serie A'),
                ('soccer_germany_bundesliga', 'Bundesliga'),
                ('soccer_france_ligue_one', 'Ligue 1'),
                ('soccer_netherlands_eredivisie', 'Eredivisie'),
                ('soccer_portugal_primeira_liga', 'Primeira Liga'),
                ('soccer_turkey_super_league', 'Super Lig'),
                ('soccer_china_superleague', 'Super League'),
                ('soccer_australia_aleague', 'A-League'),
                ('soccer_uefa_champs_league', 'Champions League'),
            ]
            
            total_matches = 0
            for sport_key, sport_name in football_sports:
                self.stdout.write(f'\n[TEST] Consultando {sport_name} ({sport_key})...')
                matches = odds_service.get_upcoming_matches(sport_key=sport_key)
                match_count = len(matches) if matches else 0
                total_matches += match_count
                self.stdout.write(f'  [RESULTADO] {match_count} partidos encontrados')
                
                if matches and match_count > 0:
                    # Mostrar algunos ejemplos
                    self.stdout.write(f'  [EJEMPLOS] Primeros 3 partidos:')
                    for i, match in enumerate(matches[:3]):
                        home = match.get('home_team', 'N/A')
                        away = match.get('away_team', 'N/A')
                        commence = match.get('commence_time', 'N/A')
                        self.stdout.write(f'    {i+1}. {home} vs {away} ({commence})')
            
            self.stdout.write(self.style.SUCCESS(f'\n[RESUMEN] Total partidos encontrados: {total_matches}'))
            
        else:
            # Probar un deporte específico
            sport_key = options['sport_key']
            self.stdout.write(f'\n[TEST] Consultando {sport_key}...')
            
            matches = odds_service.get_upcoming_matches(sport_key=sport_key)
            match_count = len(matches) if matches else 0
            
            self.stdout.write(self.style.SUCCESS(f'[RESULTADO] {match_count} partidos encontrados'))
            
            if matches and match_count > 0:
                self.stdout.write(f'\n[INFO] Detalles de los partidos:')
                
                # Analizar rangos de tiempo
                now = datetime.now(timezone.utc)
                matches_in_range = []
                matches_out_of_range = []
                
                for match in matches:
                    commence_time_str = match.get('commence_time', '')
                    if not commence_time_str:
                        continue
                    
                    try:
                        commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                        if commence_time.tzinfo is None:
                            commence_time = commence_time.replace(tzinfo=timezone.utc)
                        else:
                            commence_time = commence_time.astimezone(timezone.utc)
                        
                        time_diff = (commence_time - now).total_seconds() / 3600
                        
                        match_info = {
                            'home': match.get('home_team', 'N/A'),
                            'away': match.get('away_team', 'N/A'),
                            'time': commence_time_str,
                            'diff_hours': time_diff
                        }
                        
                        if -2 <= time_diff <= 36:
                            matches_in_range.append(match_info)
                        else:
                            matches_out_of_range.append(match_info)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  [WARNING] Error parseando tiempo: {e}'))
                
                self.stdout.write(f'\n[INFO] Partidos en rango (-2h a +36h): {len(matches_in_range)}')
                self.stdout.write(f'[INFO] Partidos fuera de rango: {len(matches_out_of_range)}')
                
                if matches_in_range:
                    self.stdout.write(f'\n[INFO] Partidos válidos (primeros 10):')
                    for i, match in enumerate(matches_in_range[:10]):
                        self.stdout.write(f'  {i+1}. {match["home"]} vs {match["away"]} '
                                         f'({match["diff_hours"]:.1f}h) - {match["time"]}')
                
                if matches_out_of_range:
                    self.stdout.write(f'\n[INFO] Partidos fuera de rango (primeros 5):')
                    for i, match in enumerate(matches_out_of_range[:5]):
                        self.stdout.write(f'  {i+1}. {match["home"]} vs {match["away"]} '
                                         f'({match["diff_hours"]:.1f}h) - {match["time"]}')
                
                # Mostrar algunos ejemplos completos
                self.stdout.write(f'\n[INFO] Datos completos de los primeros 3 partidos:')
                for i, match in enumerate(matches[:3]):
                    self.stdout.write(f'\n  Partido {i+1}:')
                    for key, value in match.items():
                        if isinstance(value, (dict, list)):
                            self.stdout.write(f'    {key}: {type(value).__name__} ({len(value) if isinstance(value, (list, dict)) else "N/A"} items)')
                        else:
                            self.stdout.write(f'    {key}: {value}')
            else:
                self.stdout.write(self.style.ERROR('[ERROR] No se encontraron partidos'))
                self.stdout.write('[INFO] Posibles causas:')
                self.stdout.write('  - La API key no está configurada correctamente')
                self.stdout.write('  - La API está temporalmente no disponible')
                self.stdout.write('  - No hay partidos programados para este deporte')
                self.stdout.write('  - El deporte especificado no existe')

