"""
Servicios para interactuar con The Odds API
"""

import requests
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from django.conf import settings
from django.utils import timezone as django_timezone
from django.db import transaction

from .models import Sport, Bookmaker, Match, Odds, AverageOdds

logger = logging.getLogger('odds')


class OddsAPIService:
    """Servicio para interactuar con The Odds API"""
    
    def __init__(self):
        self.api_key = settings.ODDS_API_KEY
        self.base_url = settings.ODDS_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BettingBot/1.0'
        })
    
    def get_sports(self) -> List[Dict]:
        """
        Obtiene la lista de deportes disponibles
        
        Returns:
            List[Dict]: Lista de deportes con sus claves
        """
        try:
            url = f"{self.base_url}/sports"
            params = {'api_key': self.api_key}
            
            logger.info("Consultando deportes disponibles...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            sports_data = response.json()
            logger.info(f"Obtenidos {len(sports_data)} deportes")
            
            return sports_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo deportes: {e}")
            return []
    
    def sync_sports(self) -> int:
        """
        Sincroniza los deportes con la base de datos
        
        Returns:
            int: Número de deportes sincronizados
        """
        try:
            sports_data = self.get_sports()
            if not sports_data:
                return 0
            
            synced_count = 0
            with transaction.atomic():
                for sport_data in sports_data:
                    sport, created = Sport.objects.update_or_create(
                        key=sport_data['key'],
                        defaults={
                            'title': sport_data['title'],
                            'description': sport_data.get('description', ''),
                            'active': sport_data.get('active', True),
                            'has_outrights': sport_data.get('has_outrights', False),
                        }
                    )
                    if created:
                        synced_count += 1
                        logger.info(f"Nuevo deporte agregado: {sport.title}")
            
            logger.info(f"Sincronizados {synced_count} deportes nuevos")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error sincronizando deportes: {e}")
            return 0
    
    def get_odds(self, sport_key: str = None, regions: str = None, 
                 markets: str = None, odds_format: str = None) -> List[Dict]:
        """
        Obtiene las cuotas para un deporte específico
        
        Args:
            sport_key: Clave del deporte (ej: 'soccer_epl')
            regions: Regiones separadas por comas (ej: 'uk,us,eu')
            markets: Mercados separados por comas (ej: 'h2h')
            odds_format: Formato de cuotas ('decimal', 'american')
            
        Returns:
            List[Dict]: Lista de partidos con sus cuotas
        """
        try:
            # Usar valores por defecto de settings si no se especifican
            sport_key = sport_key or settings.SPORT_KEY
            regions = regions or settings.REGIONS
            markets = markets or settings.MARKETS
            odds_format = odds_format or settings.ODDS_FORMAT
            
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                'api_key': self.api_key,
                'regions': regions,
                'markets': markets,
                'oddsFormat': odds_format,
                'dateFormat': 'iso'
            }
            
            logger.info(f"Consultando cuotas para {sport_key}...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Obtenidas {len(data)} partidos con cuotas")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo cuotas: {e}")
            return []
    
    def normalize_odds_data(self, match_data: Dict) -> Dict:
        """
        Normaliza los datos de un partido para facilitar el procesamiento
        
        Args:
            match_data: Datos del partido de la API
            
        Returns:
            Dict: Datos normalizados del partido
        """
        try:
            bookmakers = match_data.get('bookmakers', [])
            
            # Recopilar todas las cuotas para el mercado h2h (ganador del partido)
            home_odds = []
            away_odds = []
            draw_odds = []
            
            for bookmaker in bookmakers:
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'h2h':
                        for outcome in market.get('outcomes', []):
                            name = outcome.get('name')
                            price = outcome.get('price')
                            
                            if name == match_data.get('home_team'):
                                home_odds.append({
                                    'price': price,
                                    'bookmaker': bookmaker.get('title')
                                })
                            elif name == match_data.get('away_team'):
                                away_odds.append({
                                    'price': price,
                                    'bookmaker': bookmaker.get('title')
                                })
                            elif name == 'Draw':
                                draw_odds.append({
                                    'price': price,
                                    'bookmaker': bookmaker.get('title')
                                })
            
            # Calcular promedios
            avg_home = sum(odd['price'] for odd in home_odds) / len(home_odds) if home_odds else 0
            avg_away = sum(odd['price'] for odd in away_odds) / len(away_odds) if away_odds else 0
            avg_draw = sum(odd['price'] for odd in draw_odds) / len(draw_odds) if draw_odds else 0
            
            return {
                'match_id': match_data.get('id'),
                'sport_key': match_data.get('sport_key'),
                'home_team': match_data.get('home_team'),
                'away_team': match_data.get('away_team'),
                'commence_time': match_data.get('commence_time'),
                'home_odds': home_odds,
                'away_odds': away_odds,
                'draw_odds': draw_odds,
                'avg_home_odds': avg_home,
                'avg_away_odds': avg_away,
                'avg_draw_odds': avg_draw,
                'bookmaker_count': len(bookmakers)
            }
            
        except Exception as e:
            logger.error(f"Error normalizando datos del partido: {e}")
            return {}
    
    def save_odds_to_database(self, match_data: Dict) -> Optional[Match]:
        """
        Guarda las cuotas de un partido en la base de datos
        
        Args:
            match_data: Datos del partido
            
        Returns:
            Optional[Match]: Objeto Match creado o actualizado
        """
        try:
            with transaction.atomic():
                # Obtener o crear el deporte
                sport, _ = Sport.objects.get_or_create(
                    key=match_data.get('sport_key', 'unknown'),
                    defaults={
                        'title': match_data.get('sport_key', 'Unknown Sport'),
                        'active': True
                    }
                )
                
                # Obtener o crear el partido
                commence_time = datetime.fromisoformat(
                    match_data.get('commence_time', '').replace('Z', '+00:00')
                )
                
                match, created = Match.objects.update_or_create(
                    match_id=match_data.get('id'),
                    defaults={
                        'sport': sport,
                        'home_team': match_data.get('home_team'),
                        'away_team': match_data.get('away_team'),
                        'commence_time': commence_time,
                    }
                )
                
                # Guardar cuotas de cada casa de apuestas
                bookmakers = match_data.get('bookmakers', [])
                for bookmaker_data in bookmakers:
                    bookmaker, _ = Bookmaker.objects.get_or_create(
                        key=bookmaker_data.get('title', '').lower().replace(' ', '_'),
                        defaults={
                            'title': bookmaker_data.get('title'),
                            'active': True
                        }
                    )
                    
                    # Buscar cuotas h2h
                    for market in bookmaker_data.get('markets', []):
                        if market.get('key') == 'h2h':
                            home_odds = None
                            away_odds = None
                            draw_odds = None
                            
                            for outcome in market.get('outcomes', []):
                                name = outcome.get('name')
                                price = outcome.get('price')
                                
                                if name == match.home_team:
                                    home_odds = price
                                elif name == match.away_team:
                                    away_odds = price
                                elif name == 'Draw':
                                    draw_odds = price
                            
                            # Crear o actualizar registro de cuotas
                            Odds.objects.update_or_create(
                                match=match,
                                bookmaker=bookmaker,
                                defaults={
                                    'home_odds': home_odds,
                                    'away_odds': away_odds,
                                    'draw_odds': draw_odds,
                                    'odds_timestamp': django_timezone.now()
                                }
                            )
                
                # Calcular y guardar cuotas promedio
                self.calculate_and_save_average_odds(match, match_data)
                
                return match
                
        except Exception as e:
            logger.error(f"Error guardando cuotas en base de datos: {e}")
            return None
    
    def calculate_and_save_average_odds(self, match: Match, match_data: Dict):
        """
        Calcula y guarda las cuotas promedio de un partido
        
        Args:
            match: Objeto Match
            match_data: Datos del partido
        """
        try:
            # Obtener todas las cuotas del partido
            odds_list = match.odds.all()
            
            if not odds_list:
                return
            
            # Calcular promedios
            home_odds = [odd.home_odds for odd in odds_list if odd.home_odds]
            away_odds = [odd.away_odds for odd in odds_list if odd.away_odds]
            draw_odds = [odd.draw_odds for odd in odds_list if odd.draw_odds]
            
            avg_home = sum(home_odds) / len(home_odds) if home_odds else 0
            avg_away = sum(away_odds) / len(away_odds) if away_odds else 0
            avg_draw = sum(draw_odds) / len(draw_odds) if draw_odds else 0
            
            # Calcular desviación estándar
            import statistics
            std_dev = 0
            if home_odds and len(home_odds) > 1:
                std_dev = statistics.stdev(home_odds)
            
            # Guardar cuotas promedio
            AverageOdds.objects.create(
                match=match,
                avg_home_odds=avg_home,
                avg_away_odds=avg_away,
                avg_draw_odds=avg_draw,
                bookmaker_count=len(odds_list),
                standard_deviation=std_dev,
                calculated_at=django_timezone.now()
            )
            
            logger.info(f"Cuotas promedio calculadas para {match}: "
                       f"H:{avg_home:.2f} D:{avg_draw:.2f} A:{avg_away:.2f}")
            
        except Exception as e:
            logger.error(f"Error calculando cuotas promedio: {e}")
    
    def sync_odds(self, sport_key: str = None) -> int:
        """
        Sincroniza las cuotas de un deporte con la base de datos
        
        Args:
            sport_key: Clave del deporte a sincronizar
            
        Returns:
            int: Número de partidos sincronizados
        """
        try:
            matches_data = self.get_odds(sport_key)
            if not matches_data:
                return 0
            
            synced_count = 0
            for match_data in matches_data:
                match = self.save_odds_to_database(match_data)
                if match:
                    synced_count += 1
            
            logger.info(f"Sincronizados {synced_count} partidos")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error sincronizando cuotas: {e}")
            return 0
    
    def get_upcoming_matches(self, sport_key: str = None) -> List[Dict]:
        """
        Obtiene los próximos partidos programados para un deporte específico
        
        Args:
            sport_key: Clave del deporte (ej: 'soccer_epl')
            
        Returns:
            List[Dict]: Lista de próximos partidos
        """
        try:
            sport_key = sport_key or settings.SPORT_KEY
            
            url = f"{self.base_url}/sports/{sport_key}/events"
            params = {
                'api_key': self.api_key,
                'dateFormat': 'iso'
            }
            
            logger.info(f"Consultando próximos partidos para {sport_key}...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Obtenidos {len(data)} próximos partidos")
            
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo próximos partidos: {e}")
            return []
    
    def get_latest_average_odds(self, sport_key: str = None) -> List[AverageOdds]:
        """
        Obtiene las cuotas promedio más recientes para un deporte
        
        Args:
            sport_key: Clave del deporte
            
        Returns:
            List[AverageOdds]: Lista de cuotas promedio
        """
        try:
            queryset = AverageOdds.objects.select_related('match__sport')
            
            if sport_key:
                queryset = queryset.filter(match__sport__key=sport_key)
            
            return queryset.order_by('-calculated_at')[:50]
            
        except Exception as e:
            logger.error(f"Error obteniendo cuotas promedio: {e}")
            return []
