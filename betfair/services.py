"""
Servicios para interactuar con Betfair Exchange API
"""

import betfairlightweight
from betfairlightweight import APIClient
from betfairlightweight.filters import market_filter
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from django.conf import settings
from django.utils import timezone as django_timezone
from django.db import transaction

from .models import (
    BetfairEventType, BetfairEvent, BetfairMarket,
    BetfairRunner, BetfairOrder, BetfairAccount, BetfairTickSnapshot
)

logger = logging.getLogger('betfair')


class BetfairAPIService:
    """Servicio para interactuar con Betfair Exchange API"""
    
    def __init__(self):
        self.app_key = settings.BETFAIR_APP_KEY
        self.username = settings.BETFAIR_USERNAME
        self.password = settings.BETFAIR_PASSWORD
        self.sandbox = settings.BETFAIR_SANDBOX
        self.client = None
        self.session_token = None
        
    def login(self) -> bool:
        """
        Inicia sesión en Betfair
        
        Returns:
            bool: True si el login fue exitoso, False en caso contrario
        """
        try:
            # Configurar cliente
            self.client = APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                certs='',  # Certificados para producción
                locale='es',  # Idioma español
                light_weight=True
            )
            
            # Usar sandbox si está configurado
            if self.sandbox:
                # Para sandbox, usar endpoint de prueba
                self.client.login()
            else:
                self.client.login()
            
            logger.info("Login exitoso en Betfair")
            return True
            
        except Exception as e:
            logger.error(f"Error en login de Betfair: {e}")
            return False
    
    def get_event_types(self) -> List[Dict]:
        """
        Obtiene la lista de tipos de eventos (deportes) disponibles
        
        Returns:
            List[Dict]: Lista de tipos de eventos
        """
        try:
            if not self.client:
                if not self.login():
                    return []
            
            # Obtener tipos de eventos
            sports_response = self.client.betting.list_event_types()
            
            sports = []
            for sport in sports_response:
                sports.append({
                    'id': sport.event_type.id,
                    'name': sport.event_type.name,
                    'market_count': sport.market_count
                })
            
            logger.info(f"Deportes disponibles en Betfair: {len(sports)}")
            return sports
            
        except Exception as e:
            logger.error(f"Error obteniendo tipos de eventos de Betfair: {e}")
            return []
    
    def sync_event_types(self) -> int:
        """
        Sincroniza los tipos de eventos con la base de datos
        
        Returns:
            int: Número de tipos de eventos sincronizados
        """
        try:
            event_types_data = self.get_event_types()
            if not event_types_data:
                return 0
            
            synced_count = 0
            with transaction.atomic():
                for event_type_data in event_types_data:
                    event_type, created = BetfairEventType.objects.update_or_create(
                        event_type_id=str(event_type_data['id']),
                        defaults={
                            'name': event_type_data['name'],
                            'market_count': event_type_data['market_count'],
                            'active': True,
                        }
                    )
                    if created:
                        synced_count += 1
                        logger.info(f"Nuevo tipo de evento agregado: {event_type.name}")
            
            logger.info(f"Sincronizados {synced_count} tipos de eventos nuevos")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error sincronizando tipos de eventos: {e}")
            return 0
    
    def get_football_events(self) -> List[Dict]:
        """
        Obtiene eventos de fútbol (Premier League)
        
        Returns:
            List[Dict]: Lista de eventos de fútbol
        """
        try:
            if not self.client:
                if not self.login():
                    return []
            
            # Filtrar por fútbol (event_type_id = 1)
            events_response = self.client.betting.list_events(
                filter=market_filter(
                    event_type_ids=['1']  # Fútbol
                )
            )
            
            events = []
            for event in events_response:
                events.append({
                    'id': event.event.id,
                    'name': event.event.name,
                    'country_code': event.event.country_code,
                    'timezone': event.event.timezone,
                    'open_date': event.event.open_date,
                    'market_count': event.market_count
                })
            
            logger.info(f"Eventos de fútbol disponibles: {len(events)}")
            return events
            
        except Exception as e:
            logger.error(f"Error obteniendo eventos de fútbol: {e}")
            return []
    
    def sync_events(self, event_type_id: str = '1') -> int:
        """
        Sincroniza eventos de un tipo específico
        
        Args:
            event_type_id: ID del tipo de evento (1 para fútbol)
            
        Returns:
            int: Número de eventos sincronizados
        """
        try:
            if event_type_id == '1':
                events_data = self.get_football_events()
            else:
                return 0
            
            if not events_data:
                return 0
            
            synced_count = 0
            with transaction.atomic():
                for event_data in events_data:
                    # Obtener el tipo de evento
                    try:
                        event_type = BetfairEventType.objects.get(event_type_id=event_type_id)
                    except BetfairEventType.DoesNotExist:
                        logger.warning(f"Tipo de evento {event_type_id} no encontrado")
                        continue
                    
                    # Convertir fecha
                    open_date = datetime.fromisoformat(
                        event_data['open_date'].replace('Z', '+00:00')
                    )
                    
                    event, created = BetfairEvent.objects.update_or_create(
                        event_id=str(event_data['id']),
                        defaults={
                            'event_type': event_type,
                            'name': event_data['name'],
                            'country_code': event_data.get('country_code', ''),
                            'timezone': event_data.get('timezone', ''),
                            'open_date': open_date,
                            'market_count': event_data.get('market_count', 0),
                        }
                    )
                    if created:
                        synced_count += 1
                        logger.info(f"Nuevo evento agregado: {event.name}")
            
            logger.info(f"Sincronizados {synced_count} eventos nuevos")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error sincronizando eventos: {e}")
            return 0
    
    def get_match_odds_markets(self) -> List[Dict]:
        """
        Obtiene mercados de cuotas de partidos (Match Odds)
        
        Returns:
            List[Dict]: Lista de mercados de partidos
        """
        try:
            if not self.client:
                if not self.login():
                    return []
            
            # Buscar mercados de Match Odds de fútbol
            markets_response = self.client.betting.list_market_catalogue(
                filter=market_filter(
                    event_type_ids=['1'],  # Fútbol
                    market_type_codes=['MATCH_ODDS'],  # Cuotas de partido
                    in_play_only=False
                ),
                market_projection=['MARKET_DESCRIPTION', 'RUNNER_DESCRIPTION'],
                max_results=50
            )
            
            markets = []
            for market in markets_response:
                markets.append({
                    'market_id': market.market_id,
                    'market_name': market.market_name,
                    'event_name': market.event.name,
                    'event_id': market.event.id,
                    'market_start_time': market.market_start_time,
                    'total_matched': market.total_matched,
                    'runners': [
                        {
                            'selection_id': runner.selection_id,
                            'runner_name': runner.runner_name,
                            'sort_priority': runner.sort_priority
                        }
                        for runner in market.runners
                    ]
                })
            
            logger.info(f"Mercados de Match Odds encontrados: {len(markets)}")
            return markets
            
        except Exception as e:
            logger.error(f"Error obteniendo mercados de Match Odds: {e}")
            return []
    
    def get_market_book(self, market_ids: List[str]) -> List[Dict]:
        """
        Obtiene el libro de mercados (cuotas actuales)
        
        Args:
            market_ids: Lista de IDs de mercados
            
        Returns:
            List[Dict]: Datos del mercado con cuotas actuales
        """
        try:
            if not self.client:
                if not self.login():
                    return []
            
            # Obtener libro de mercados
            market_book = self.client.betting.list_market_book(
                market_ids=market_ids,
                price_projection=betfairlightweight.filters.price_projection(
                    price_data=betfairlightweight.filters.price_data(
                        ex_best_offers=True,  # Mejores ofertas
                        ex_all_offers=True,   # Todas las ofertas
                        ex_traded=True        # Apuestas ejecutadas
                    )
                )
            )
            
            markets_data = []
            for market in market_book:
                market_info = {
                    'market_id': market.market_id,
                    'market_definition': {
                        'market_name': market.market_definition.market_name,
                        'event_name': market.market_definition.event_name,
                        'event_id': market.market_definition.event_id,
                        'market_time': market.market_definition.market_time,
                        'status': market.market_definition.status
                    },
                    'runners': []
                }
                
                # Procesar corredores (opciones de apuesta)
                for runner in market.runners:
                    runner_info = {
                        'selection_id': runner.selection_id,
                        'status': runner.status,
                        'last_price_traded': runner.last_price_traded,
                        'total_matched': runner.total_matched,
                        'ex': {
                            'available_to_back': [],
                            'available_to_lay': []
                        }
                    }
                    
                    # Obtener precios de back (apostar a favor)
                    if runner.ex and runner.ex.available_to_back:
                        for price in runner.ex.available_to_back:
                            runner_info['ex']['available_to_back'].append({
                                'price': price.price,
                                'size': price.size
                            })
                    
                    # Obtener precios de lay (apostar en contra)
                    if runner.ex and runner.ex.available_to_lay:
                        for price in runner.ex.available_to_lay:
                            runner_info['ex']['available_to_lay'].append({
                                'price': price.price,
                                'size': price.size
                            })
                    
                    market_info['runners'].append(runner_info)
                
                markets_data.append(market_info)
            
            return markets_data
            
        except Exception as e:
            logger.error(f"Error obteniendo libro de mercados: {e}")
            return []
    
    def sync_markets(self) -> int:
        """
        Sincroniza mercados de Match Odds con la base de datos
        
        Returns:
            int: Número de mercados sincronizados
        """
        try:
            markets_data = self.get_match_odds_markets()
            if not markets_data:
                return 0
            
            synced_count = 0
            with transaction.atomic():
                for market_data in markets_data:
                    # Obtener el evento
                    try:
                        event = BetfairEvent.objects.get(event_id=str(market_data['event_id']))
                    except BetfairEvent.DoesNotExist:
                        logger.warning(f"Evento {market_data['event_id']} no encontrado")
                        continue
                    
                    # Convertir fecha
                    market_start_time = datetime.fromisoformat(
                        market_data['market_start_time'].replace('Z', '+00:00')
                    )
                    
                    market, created = BetfairMarket.objects.update_or_create(
                        market_id=str(market_data['market_id']),
                        defaults={
                            'event': event,
                            'market_name': market_data['market_name'],
                            'market_start_time': market_start_time,
                            'total_matched': market_data.get('total_matched', 0),
                            'status': 'OPEN'  # Asumir que está abierto
                        }
                    )
                    
                    if created:
                        synced_count += 1
                        logger.info(f"Nuevo mercado agregado: {market.market_name}")
                    
                    # Sincronizar corredores
                    for runner_data in market_data.get('runners', []):
                        BetfairRunner.objects.update_or_create(
                            market=market,
                            selection_id=runner_data['selection_id'],
                            defaults={
                                'runner_name': runner_data['runner_name'],
                                'sort_priority': runner_data.get('sort_priority', 0),
                                'status': 'ACTIVE',
                                'last_updated': django_timezone.now()
                            }
                        )
            
            logger.info(f"Sincronizados {synced_count} mercados nuevos")
            return synced_count
            
        except Exception as e:
            logger.error(f"Error sincronizando mercados: {e}")
            return 0
    
    def update_market_prices(self, market_ids: List[str]) -> int:
        """
        Actualiza los precios de mercados específicos
        
        Args:
            market_ids: Lista de IDs de mercados
            
        Returns:
            int: Número de mercados actualizados
        """
        try:
            markets_data = self.get_market_book(market_ids)
            if not markets_data:
                return 0
            
            updated_count = 0
            with transaction.atomic():
                for market_data in markets_data:
                    try:
                        market = BetfairMarket.objects.get(
                            market_id=str(market_data['market_id'])
                        )
                    except BetfairMarket.DoesNotExist:
                        continue
                    
                    # Actualizar estado del mercado
                    market.status = market_data['market_definition']['status']
                    market.save()
                    
                    # Actualizar corredores
                    for runner_data in market_data.get('runners', []):
                        try:
                            runner = BetfairRunner.objects.get(
                                market=market,
                                selection_id=runner_data['selection_id']
                            )
                            
                            runner.status = runner_data['status']
                            runner.last_price_traded = runner_data.get('last_price_traded')
                            runner.total_matched = runner_data.get('total_matched', 0)
                            runner.available_to_back = runner_data.get('ex', {}).get('available_to_back', [])
                            runner.available_to_lay = runner_data.get('ex', {}).get('available_to_lay', [])
                            runner.last_updated = django_timezone.now()
                            runner.save()
                            
                            # Persistir snapshot compacto (top-3 niveles back/lay)
                            best_back = (runner.available_to_back or [])[:3]
                            best_lay = (runner.available_to_lay or [])[:3]
                            BetfairTickSnapshot.objects.create(
                                market=market,
                                runner=runner,
                                best_back=best_back,
                                best_lay=best_lay,
                                last_price_traded=runner.last_price_traded,
                                total_matched=runner.total_matched,
                                captured_at=django_timezone.now()
                            )

                            updated_count += 1
                            
                        except BetfairRunner.DoesNotExist:
                            continue
            
            logger.info(f"Actualizados {updated_count} corredores")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error actualizando precios de mercados: {e}")
            return 0
    
    def place_order(self, market_id: str, selection_id: int, 
                   side: str, price: float, size: float, 
                   order_type: str = 'LIMIT') -> Dict:
        """
        Coloca una orden de apuesta
        
        Args:
            market_id: ID del mercado
            selection_id: ID de la selección
            side: 'BACK' (a favor) o 'LAY' (en contra)
            price: Precio de la apuesta
            size: Tamaño de la apuesta
            order_type: Tipo de orden ('LIMIT', 'MARKET_ON_CLOSE', etc.)
            
        Returns:
            Dict: Resultado de la orden
        """
        try:
            if not self.client:
                if not self.login():
                    return {'success': False, 'error': 'No se pudo conectar'}
            
            # Crear instrucción de orden
            instruction = betfairlightweight.filters.limit_order(
                size=size,
                price=price,
                persistence_type='LAPSE'  # Orden temporal
            )
            
            # Colocar orden
            order_response = self.client.betting.place_orders(
                market_id=market_id,
                instructions=[{
                    'selection_id': selection_id,
                    'handicap': 0,
                    'side': side,
                    'order_type': order_type,
                    'limit_order': instruction
                }]
            )
            
            result = {
                'success': True,
                'market_id': market_id,
                'selection_id': selection_id,
                'side': side,
                'price': price,
                'size': size,
                'response': order_response
            }
            
            logger.info(f"Orden colocada: {side} {size}€ @ {price} en selección {selection_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error colocando orden: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_account_funds(self) -> Dict:
        """
        Obtiene el saldo de la cuenta
        
        Returns:
            Dict: Información del saldo
        """
        try:
            if not self.client:
                if not self.login():
                    return {}
            
            account_funds = self.client.account.get_account_funds()
            
            funds_info = {
                'available_to_bet_balance': account_funds.available_to_bet_balance,
                'exposure': account_funds.exposure,
                'retained_commission': account_funds.retained_commission,
                'exposure_limit': account_funds.exposure_limit,
                'discount_rate': account_funds.discount_rate,
                'points_balance': account_funds.points_balance,
                'wallet': account_funds.wallet
            }
            
            # Actualizar información en base de datos
            BetfairAccount.objects.update_or_create(
                username=self.username,
                defaults={
                    **funds_info,
                    'sandbox': self.sandbox,
                    'last_updated': django_timezone.now()
                }
            )
            
            return funds_info
            
        except Exception as e:
            logger.error(f"Error obteniendo fondos de cuenta: {e}")
            return {}
    
    def logout(self):
        """Cierra la sesión"""
        if self.client:
            try:
                self.client.logout()
                logger.info("Sesión cerrada en Betfair")
            except Exception as e:
                logger.error(f"Error cerrando sesión: {e}")
