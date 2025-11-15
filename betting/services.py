"""
Servicios para la lógica de apuestas y arbitraje
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone as django_timezone
from django.db import transaction
from django.utils import timezone as django_timezone
from decimal import Decimal
from typing import Callable, Dict, List, Tuple
from django.db.models import Q

from odds.models import Match, AverageOdds
from odds.services import OddsAPIService
from betfair.models import BetfairMarket, BetfairRunner, BetfairOrder
from betfair.services import BetfairAPIService
from .models import (
    ArbitrageOpportunity, BettingStrategy, BotSession, 
    BotCycle, BotConfiguration, Alert
)

logger = logging.getLogger('betting')


class ArbitrageService:
    """Servicio para detectar oportunidades de arbitraje"""
    
    def __init__(self):
        self.odds_service = OddsAPIService()
        self.betfair_service = BetfairAPIService()
        self.target_sport_keys = getattr(settings, 'TARGET_SPORT_KEYS', [])
        self.target_competition_names = [
            name.lower() for name in getattr(settings, 'BETFAIR_COMPETITION_NAMES', [])
        ]
    
    def find_matching_events(self, odds_matches: List[Match], 
                           betfair_markets: List[BetfairMarket]) -> List[Tuple[Match, BetfairMarket]]:
        """
        Encuentra eventos que coinciden entre las dos fuentes
        
        Args:
            odds_matches: Partidos de The Odds API
            betfair_markets: Mercados de Betfair
            
        Returns:
            List[Tuple[Match, BetfairMarket]]: Pares de eventos coincidentes
        """
        if self.target_sport_keys:
            odds_matches = [
                match for match in odds_matches
                if getattr(match, 'sport', None) and match.sport.key in self.target_sport_keys
            ]

        if self.target_competition_names:
            betfair_markets = [
                market for market in betfair_markets
                if any(
                    target in (market.event.competition_name or '').lower()
                    for target in self.target_competition_names
                )
            ]

        matches = []
        
        for odds_match in odds_matches:
            home_team = odds_match.home_team.lower()
            away_team = odds_match.away_team.lower()
            
            for betfair_market in betfair_markets:
                event_name = betfair_market.event.name.lower()
                
                # Buscar coincidencias por nombres de equipos
                if (home_team in event_name and away_team in event_name) or \
                   (self._team_name_match(home_team, event_name) and 
                    self._team_name_match(away_team, event_name)):
                    
                    matches.append((odds_match, betfair_market))
                    break
        
        logger.info(f"Encontrados {len(matches)} eventos coincidentes")
        return matches
    
    def _team_name_match(self, team_name: str, event_name: str) -> bool:
        """
        Verifica si un nombre de equipo coincide con un evento
        
        Args:
            team_name: Nombre del equipo
            event_name: Nombre del evento
            
        Returns:
            bool: True si hay coincidencia
        """
        # Limpiar nombres
        team_clean = team_name.replace('fc', '').replace('united', 'utd').strip()
        event_clean = event_name.replace('vs', ' v ').strip()
        
        # Buscar palabras clave del equipo
        team_words = team_clean.split()
        for word in team_words:
            if len(word) > 2 and word in event_clean:
                return True
        
        return False
    
    def calculate_arbitrage_opportunity(self, odds_match: Match, 
                                      betfair_market: BetfairMarket) -> List[ArbitrageOpportunity]:
        """
        Calcula oportunidades de arbitraje entre las dos fuentes
        
        Args:
            odds_match: Datos del partido de The Odds API
            betfair_market: Datos del mercado de Betfair
            
        Returns:
            List[ArbitrageOpportunity]: Lista de oportunidades de arbitraje
        """
        opportunities = []
        
        try:
            # Obtener cuotas promedio más recientes
            latest_average_odds = AverageOdds.objects.filter(
                match=odds_match
            ).order_by('-calculated_at').first()
            
            if not latest_average_odds:
                return opportunities
            
            # Obtener mejores cuotas de Betfair
            betfair_odds = self._extract_betfair_odds(betfair_market)
            
            if not betfair_odds:
                return opportunities
            
            # Comparar cada resultado posible
            outcomes = [
                ('home', latest_average_odds.avg_home_odds, betfair_odds.get('home')),
                ('draw', latest_average_odds.avg_draw_odds, betfair_odds.get('draw')),
                ('away', latest_average_odds.avg_away_odds, betfair_odds.get('away'))
            ]
            
            for outcome, odds_api_price, betfair_price in outcomes:
                if odds_api_price and betfair_price and betfair_price > odds_api_price:
                    # Calcular edge (ventaja)
                    edge = (betfair_price - odds_api_price) / odds_api_price
                    
                    # Si Betfair tiene mejor cuota (edge positivo)
                    if edge >= settings.MIN_EDGE:
                        # Calcular stake recomendado
                        recommended_stake = self._calculate_optimal_stake(
                            odds_api_price, betfair_price
                        )
                        
                        # Calcular puntuación de confianza
                        confidence = self._calculate_confidence_score(
                            odds_match, betfair_market, edge, latest_average_odds
                        )
                        
                        # Obtener el corredor correspondiente
                        betfair_runner = self._get_betfair_runner(betfair_market, outcome)
                        
                        if betfair_runner:
                            opportunity = ArbitrageOpportunity.objects.create(
                                match=odds_match,
                                betfair_market=betfair_market,
                                betfair_runner=betfair_runner,
                                selection=outcome,
                                odds_api_odds=odds_api_price,
                                betfair_odds=betfair_price,
                                edge=edge,
                                recommended_stake=recommended_stake,
                                confidence_score=confidence,
                                detected_at=django_timezone.now()
                            )
                            
                            opportunities.append(opportunity)
                            
                            logger.info(f"Oportunidad detectada: {outcome} - Edge {edge:.2%}, "
                                       f"Stake {recommended_stake:.2f}€, Confianza {confidence:.2f}")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error calculando arbitraje: {e}")
            return opportunities
    
    def _extract_betfair_odds(self, betfair_market: BetfairMarket) -> Dict:
        """
        Extrae las mejores cuotas de un mercado de Betfair
        
        Args:
            betfair_market: Datos del mercado
            
        Returns:
            Dict: Mejores cuotas por resultado
        """
        odds = {}
        
        try:
            runners = betfair_market.runners.all().order_by('sort_priority')
            
            for runner in runners:
                # Obtener mejor precio de back
                best_back = runner.get_best_back_price()
                
                if best_back:
                    price = best_back.get('price')
                    
                    # Mapear por posición (asumiendo orden: home, away, draw)
                    if runner.sort_priority == 1:
                        odds['home'] = price
                    elif runner.sort_priority == 3:
                        odds['away'] = price
                    elif runner.sort_priority == 2:
                        odds['draw'] = price
            
            return odds
            
        except Exception as e:
            logger.error(f"Error extrayendo cuotas de Betfair: {e}")
            return {}
    
    def _calculate_optimal_stake(self, odds_api_price: float, 
                               betfair_price: float) -> float:
        """
        Calcula el stake óptimo para una apuesta de arbitraje
        
        Args:
            odds_api_price: Precio de The Odds API
            betfair_price: Precio de Betfair
            
        Returns:
            float: Stake recomendado
        """
        # Fórmula de Kelly Criterion simplificada
        edge = (betfair_price - odds_api_price) / odds_api_price
        
        # Stake como porcentaje del bankroll (máximo 2%)
        max_stake_percentage = 0.02
        
        # Calcular stake óptimo
        optimal_stake = settings.MIN_STAKE * (1 + edge * 10)  # Escalar por edge
        
        # Limitar al máximo configurado
        optimal_stake = min(optimal_stake, settings.MAX_STAKE)
        
        return round(optimal_stake, 2)
    
    def _calculate_confidence_score(self, odds_match: Match, 
                                  betfair_market: BetfairMarket, 
                                  edge: float, average_odds: AverageOdds) -> float:
        """
        Calcula una puntuación de confianza para una oportunidad
        
        Args:
            odds_match: Datos del partido
            betfair_market: Datos del mercado
            edge: Edge calculado
            average_odds: Cuotas promedio
            
        Returns:
            float: Puntuación de confianza (0-1)
        """
        score = 0.0
        
        # Factor 1: Tamaño del edge
        score += min(edge * 2, 0.4)  # Máximo 0.4 puntos
        
        # Factor 2: Número de casas de apuestas en The Odds API
        bookmaker_count = average_odds.bookmaker_count
        score += min(bookmaker_count / 20, 0.3)  # Máximo 0.3 puntos
        
        # Factor 3: Liquidez del mercado en Betfair
        total_matched = betfair_market.total_matched
        if total_matched > 10000:
            score += 0.3
        elif total_matched > 1000:
            score += 0.2
        else:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_betfair_runner(self, betfair_market: BetfairMarket, 
                           selection: str) -> Optional[BetfairRunner]:
        """
        Obtiene el corredor de Betfair para un resultado
        
        Args:
            betfair_market: Datos del mercado
            selection: Resultado ('home', 'draw', 'away')
            
        Returns:
            Optional[BetfairRunner]: Corredor o None
        """
        try:
            runners = betfair_market.runners.all()
            
            for runner in runners:
                sort_priority = runner.sort_priority
                
                if selection == 'home' and sort_priority == 1:
                    return runner
                elif selection == 'away' and sort_priority == 3:
                    return runner
                elif selection == 'draw' and sort_priority == 2:
                    return runner
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo corredor: {e}")
            return None


class BettingService:
    """Servicio principal para la lógica de apuestas"""
    
    def __init__(self):
        self.arbitrage_service = ArbitrageService()
        self.betfair_service = BetfairAPIService()
    
    def execute_cycle(self, session: BotSession) -> BotCycle:
        """
        Ejecuta un ciclo completo del bot
        
        Args:
            session: Sesión del bot
            
        Returns:
            BotCycle: Resultado del ciclo
        """
        cycle_start = django_timezone.now()
        cycle_number = session.cycles_executed + 1
        
        # Crear registro del ciclo
        cycle = BotCycle.objects.create(
            session=session,
            cycle_number=cycle_number,
            started_at=cycle_start,
            completed_at=cycle_start,  # Se actualizará al final
            duration_seconds=0,
            success_status='SUCCESS'
        )
        
        try:
            logger.info(f"Ejecutando ciclo {cycle_number} de la sesión {session.session_id}")
            
            # Paso 1: Sincronizar cuotas de The Odds API
            logger.info("Paso 1: Sincronizando cuotas de The Odds API...")
            matches_synced = self.arbitrage_service.odds_service.sync_odds()
            cycle.matches_analyzed = matches_synced
            
            # Paso 2: Sincronizar mercados de Betfair
            logger.info("Paso 2: Sincronizando mercados de Betfair...")
            if not self.betfair_service.login():
                raise Exception("No se pudo conectar a Betfair")
            
            # Actualizar precios de mercados existentes
            existing_market_filters = Q(
                event__event_type__event_type_id='1',
                status='OPEN'
            )

            if self.arbitrage_service.target_competition_names:
                competition_query = Q()
                for target in self.arbitrage_service.target_competition_names:
                    competition_query |= Q(event__competition_name__icontains=target)
                existing_market_filters &= competition_query

            existing_markets = BetfairMarket.objects.filter(
                existing_market_filters
            ).select_related('event')[:self.betfair_service.max_markets]
            
            market_ids = [str(market.market_id) for market in existing_markets]
            if market_ids:
                updated_runners = self.betfair_service.update_market_prices(market_ids)
                logger.info(f"Actualizados {updated_runners} corredores")
            
            # Paso 3: Buscar oportunidades de arbitraje
            logger.info("Paso 3: Buscando oportunidades de arbitraje...")
            opportunities = self._find_arbitrage_opportunities()
            cycle.opportunities_found = len(opportunities)
            
            # Paso 4: Evaluar y ejecutar apuestas
            if opportunities:
                logger.info("Paso 4: Evaluando apuestas...")
                placed_bets = self._evaluate_and_place_bets(opportunities, session.strategy)
                cycle.bets_placed = len(placed_bets)
            else:
                logger.info("Paso 4: No se encontraron oportunidades")
                cycle.bets_placed = 0
            
            # Actualizar estadísticas de la sesión
            session.cycles_executed = cycle_number
            session.opportunities_found += cycle.opportunities_found
            session.bets_placed += cycle.bets_placed
            session.last_cycle_at = cycle_start
            session.save()
            
            # Completar ciclo
            cycle_end = django_timezone.now()
            cycle.completed_at = cycle_end
            cycle.duration_seconds = (cycle_end - cycle_start).total_seconds()
            cycle.success_status = 'SUCCESS'
            cycle.save()
            
            logger.info(f"Ciclo {cycle_number} completado en {cycle.duration_seconds:.1f} segundos")
            
            return cycle


class BacktesterService:
    """Servicio para ejecutar backtests y calcular métricas clave."""

    def __init__(self, price_source=None):
        # price_source should provide an iterator of ticks or a query interface
        # For example, it can read from BetfairTickSnapshot
        self.price_source = price_source

    def run_backtest(self, strategy, parameter_set, start_dt, end_dt, initial_bankroll: Decimal) -> Dict:
        bankroll = Decimal(initial_bankroll)
        peak_bankroll = bankroll
        total_bets = 0
        wins = 0
        pnl_series: List[Decimal] = []

        # Naive example loop: user should implement their own iteration over snapshots
        for decision in strategy.generate_signals(self.price_source, parameter_set, start_dt, end_dt):
            # decision: {market_id, selection_id, side, price, stake, outcome}
            stake = Decimal(decision['stake'])
            price = Decimal(decision['price'])
            side = decision['side']
            outcome = decision.get('outcome')  # +1 win, -1 lose for simplicity

            if side == 'BACK':
                potential_profit = stake * (price - Decimal('1'))
                pnl = potential_profit if outcome == 1 else -stake
            else:  # LAY
                liability = stake * (price - Decimal('1'))
                pnl = stake if outcome == 1 else -liability

            bankroll += pnl
            total_bets += 1
            wins += 1 if pnl > 0 else 0
            peak_bankroll = max(peak_bankroll, bankroll)
            drawdown = (peak_bankroll - bankroll) / peak_bankroll if peak_bankroll > 0 else Decimal('0')
            pnl_series.append(bankroll)

        roi = (bankroll - Decimal(initial_bankroll)) / Decimal(initial_bankroll) if initial_bankroll else Decimal('0')
        max_drawdown = max([
            (max(pnl_series[:i+1]) - pnl_series[i]) / max(pnl_series[:i+1])
            for i in range(len(pnl_series))
        ] or [Decimal('0')])
        hit_rate = Decimal(wins) / Decimal(total_bets) if total_bets else Decimal('0')

        return {
            'final_bankroll': bankroll,
            'roi': roi,
            'max_drawdown': max_drawdown,
            'hit_rate': hit_rate,
            'total_bets': total_bets,
        }

            
        except Exception as e:
            # Manejar errores
            cycle_end = django_timezone.now()
            cycle.completed_at = cycle_end
            cycle.duration_seconds = (cycle_end - cycle_start).total_seconds()
            cycle.success_status = 'FAILED'
            cycle.errors = [str(e)]
            cycle.save()
            
            # Crear alerta de error
            Alert.objects.create(
                title="Error en ciclo del bot",
                message=f"Error en ciclo {cycle_number}: {str(e)}",
                level='ERROR',
                session=session,
                cycle=cycle
            )
            
            logger.error(f"Error en ciclo {cycle_number}: {e}")
            return cycle
    
    def _find_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Busca oportunidades de arbitraje
        
        Returns:
            List[ArbitrageOpportunity]: Lista de oportunidades encontradas
        """
        try:
            # Obtener partidos recientes con cuotas promedio
            target_sports = self.arbitrage_service.target_sport_keys
            target_competitions = self.arbitrage_service.target_competition_names

            match_filters = Q(
                average_odds__calculated_at__gte=django_timezone.now() -
                django_timezone.timedelta(hours=1)
            )

            if target_sports:
                match_filters &= Q(sport__key__in=target_sports)

            limit = self.betfair_service.max_markets

            recent_matches = Match.objects.filter(match_filters).select_related('sport').distinct()[:limit]
            
            # Obtener mercados de Betfair activos
            market_filters = Q(
                status='OPEN',
                event__event_type__event_type_id='1'
            )

            if target_competitions:
                competition_query = Q()
                for target in target_competitions:
                    competition_query |= Q(event__competition_name__icontains=target)
                market_filters &= competition_query

            active_markets = BetfairMarket.objects.filter(market_filters).select_related('event')[:limit]
            
            opportunities = []
            
            # Buscar coincidencias
            matching_events = self.arbitrage_service.find_matching_events(
                list(recent_matches), list(active_markets)
            )
            
            # Calcular oportunidades de arbitraje
            for odds_match, betfair_market in matching_events:
                match_opportunities = self.arbitrage_service.calculate_arbitrage_opportunity(
                    odds_match, betfair_market
                )
                opportunities.extend(match_opportunities)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error buscando oportunidades de arbitraje: {e}")
            return []
    
    def _evaluate_and_place_bets(self, opportunities: List[ArbitrageOpportunity], 
                                strategy: BettingStrategy) -> List[BetfairOrder]:
        """
        Evalúa y coloca apuestas basadas en oportunidades
        
        Args:
            opportunities: Lista de oportunidades
            strategy: Estrategia de apuestas
            
        Returns:
            List[BetfairOrder]: Lista de apuestas colocadas
        """
        placed_bets = []
        
        try:
            # Filtrar oportunidades por estrategia
            high_confidence_opportunities = [
                opp for opp in opportunities 
                if (opp.confidence_score >= strategy.min_confidence and
                    opp.edge >= strategy.min_edge and
                    strategy.min_stake <= opp.recommended_stake <= strategy.max_stake)
            ]
            
            logger.info(f"Evaluando {len(high_confidence_opportunities)} oportunidades de alta confianza")
            
            # Verificar límite diario de apuestas
            today_bets = BetfairOrder.objects.filter(
                placed_at__date=django_timezone.now().date()
            ).count()
            
            if today_bets >= strategy.max_daily_bets:
                logger.warning(f"Límite diario de apuestas alcanzado: {today_bets}/{strategy.max_daily_bets}")
                return placed_bets
            
            # Verificar saldo disponible
            funds = self.betfair_service.get_account_funds()
            available_balance = funds.get('available_to_bet_balance', 0)
            
            for opportunity in high_confidence_opportunities:
                if available_balance < opportunity.recommended_stake:
                    logger.warning(f"Saldo insuficiente para apostar {opportunity.recommended_stake}€")
                    continue
                
                # Colocar apuesta
                bet_result = self.betfair_service.place_order(
                    market_id=str(opportunity.betfair_market.market_id),
                    selection_id=opportunity.betfair_runner.selection_id,
                    side='BACK',  # Apostar a favor
                    price=opportunity.betfair_odds,
                    size=opportunity.recommended_stake,
                    order_type='LIMIT'
                )
                
                if bet_result.get('success'):
                    # Crear registro de apuesta
                    bet_order = BetfairOrder.objects.create(
                        order_id=f"BOT_{opportunity.id}_{django_timezone.now().timestamp()}",
                        market=opportunity.betfair_market,
                        runner=opportunity.betfair_runner,
                        side='BACK',
                        order_type='LIMIT',
                        price=opportunity.betfair_odds,
                        size=opportunity.recommended_stake,
                        status='PENDING',
                        notes=f"Arbitraje: {opportunity.selection} - Edge: {opportunity.edge:.2%}"
                    )
                    
                    # Actualizar oportunidad
                    opportunity.acted_upon = True
                    opportunity.bet_order = bet_order
                    opportunity.save()
                    
                    placed_bets.append(bet_order)
                    available_balance -= opportunity.recommended_stake
                    
                    logger.info(f"Apuesta colocada: {opportunity.selection} "
                               f"por {opportunity.recommended_stake}€ @ {opportunity.betfair_odds}")
                    
                    # Crear alerta de éxito
                    Alert.objects.create(
                        title="Apuesta colocada",
                        message=f"Apuesta de {opportunity.recommended_stake}€ colocada en {opportunity.match}",
                        level='SUCCESS',
                        session=None  # Se puede asociar a la sesión si es necesario
                    )
                
                # Verificar límite diario
                today_bets += 1
                if today_bets >= strategy.max_daily_bets:
                    logger.info(f"Límite diario de apuestas alcanzado")
                    break
            
            return placed_bets
            
        except Exception as e:
            logger.error(f"Error evaluando y colocando apuestas: {e}")
            return placed_bets
