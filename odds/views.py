"""
Vistas para mostrar cuotas de The Odds API
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
# from django.contrib.auth.decorators import login_required  # Temporalmente deshabilitado
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import Sport, Match, Odds, AverageOdds
from .services import OddsAPIService

logger = logging.getLogger('odds')


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
class OddsDashboardView(View):
    """Vista principal del dashboard de cuotas"""
    
    def get(self, request):
        # Obtener deportes disponibles
        sports = Sport.objects.filter(active=True).order_by('title')
        
        # Obtener partidos recientes con cuotas promedio
        recent_matches = Match.objects.filter(
            average_odds__calculated_at__gte=timezone.now() - timedelta(hours=24)
        ).distinct().order_by('-commence_time')[:20]
        
        # Estadísticas básicas
        total_matches = Match.objects.count()
        total_odds = Odds.objects.count()
        recent_opportunities = AverageOdds.objects.filter(
            calculated_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        context = {
            'sports': sports,
            'recent_matches': recent_matches,
            'total_matches': total_matches,
            'total_odds': total_odds,
            'recent_opportunities': recent_opportunities,
        }
        
        return render(request, 'odds/dashboard.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
class MatchesListView(View):
    """Lista de partidos con cuotas"""
    
    def get(self, request):
        # Parámetros de filtrado
        sport_key = request.GET.get('sport', '')
        search = request.GET.get('search', '')
        
        # Construir queryset
        matches = Match.objects.select_related('sport').prefetch_related('average_odds')
        
        if sport_key:
            matches = matches.filter(sport__key=sport_key)
        
        if search:
            matches = matches.filter(
                Q(home_team__icontains=search) | 
                Q(away_team__icontains=search)
            )
        
        # Ordenar por fecha de inicio
        matches = matches.order_by('-commence_time')
        
        # Paginación
        paginator = Paginator(matches, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Obtener deportes para el filtro
        sports = Sport.objects.filter(active=True).order_by('title')
        
        context = {
            'page_obj': page_obj,
            'sports': sports,
            'current_sport': sport_key,
            'search_query': search,
        }
        
        return render(request, 'odds/matches_list.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
class MatchDetailView(View):
    """Detalle de un partido con todas sus cuotas"""
    
    def get(self, request, match_id):
        try:
            match = Match.objects.select_related('sport').prefetch_related(
                'odds__bookmaker',
                'average_odds'
            ).get(match_id=match_id)
            
            # Obtener cuotas agrupadas por casa de apuestas
            odds_by_bookmaker = {}
            for odds in match.odds.all():
                bookmaker = odds.bookmaker.title
                if bookmaker not in odds_by_bookmaker:
                    odds_by_bookmaker[bookmaker] = {
                        'bookmaker': odds.bookmaker,
                        'odds': odds,
                        'timestamp': odds.odds_timestamp
                    }
            
            # Obtener cuotas promedio más recientes
            latest_average = match.average_odds.order_by('-calculated_at').first()
            
            # Obtener historial de cuotas promedio
            average_history = match.average_odds.order_by('-calculated_at')[:10]
            
            context = {
                'match': match,
                'odds_by_bookmaker': odds_by_bookmaker,
                'latest_average': latest_average,
                'average_history': average_history,
            }
            
            return render(request, 'odds/match_detail.html', context)
            
        except Match.DoesNotExist:
            from django.http import HttpResponse
            return HttpResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error - Partido no encontrado</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="text-center">
                        <h1>Partido no encontrado</h1>
                        <p>El partido que buscas no existe en nuestra base de datos.</p>
                        <a href="/odds/upcoming/" class="btn btn-primary">Volver a Próximos Partidos</a>
                    </div>
                </div>
            </body>
            </html>
            """)


@method_decorator(csrf_exempt, name='dispatch')
class SyncOddsView(View):
    """Vista para sincronizar cuotas desde la API"""
    
    def get(self, request):
        """Muestra el formulario de sincronización"""
        from .models import Sport
        sports = Sport.objects.filter(active=True).order_by('title')
        context = {
            'sports': sports,
            'current_sport': 'soccer_epl'
        }
        return render(request, 'odds/sync_odds.html', context)
    
    def post(self, request):
        try:
            odds_service = OddsAPIService()
            
            # Obtener parámetros
            sport_key = request.POST.get('sport', 'soccer_epl')
            sync_sports = request.POST.get('sync_sports') == 'on'
            
            # Sincronizar deportes si se solicita
            synced_sports = 0
            if sync_sports:
                synced_sports = odds_service.sync_sports()
                logger.info(f"Sincronizados {synced_sports} deportes")
            
            # Sincronizar cuotas
            synced_matches = odds_service.sync_odds(sport_key)
            logger.info(f"Sincronizados {synced_matches} partidos para {sport_key}")
            
            # Si es una petición AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'synced_sports': synced_sports,
                    'synced_matches': synced_matches,
                    'message': f'Sincronizados {synced_sports} deportes y {synced_matches} partidos'
                })
            
            # Si es un POST normal, redirigir con mensaje
            from django.contrib import messages
            messages.success(
                request, 
                f'¡Sincronización completada! {synced_sports} deportes y {synced_matches} partidos sincronizados.'
            )
            return redirect('odds:live_odds')
            
        except Exception as e:
            logger.error(f"Error en sincronización: {e}")
            
            # Si es una petición AJAX, devolver JSON con error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            
            # Si es un POST normal, redirigir con mensaje de error
            from django.contrib import messages
            messages.error(request, f'Error en la sincronización: {str(e)}')
            return redirect('odds:sync_odds')


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
class UpcomingMatchesView(View):
    """Vista para mostrar próximos partidos programados"""
    
    def get(self, request):
        try:
            odds_service = OddsAPIService()
            
            # Obtener parámetros
            sport_key = request.GET.get('sport', 'soccer_epl')
            
            # Obtener próximos partidos
            upcoming_matches = odds_service.get_upcoming_matches(sport_key)
            
            # Procesar fechas y convertir a hora colombiana
            from datetime import datetime, timezone, timedelta
            colombia_tz = timezone(timedelta(hours=-5))  # UTC-5
            
            # Importar servicios de predicción
            from ai_predictions.services import PredictionService
            from ai_predictions.models import League
            
            # OPTIMIZACIÓN: Generar predicciones solo si hay datos suficientes
            league_name = self._get_league_name(sport_key)
            league = League.objects.filter(name__icontains=league_name).first()
            
            # Verificar si hay datos suficientes para predicciones
            has_sufficient_data = False
            if league:
                match_count = Match.objects.filter(league=league).count()
                has_sufficient_data = match_count >= 50  # Mínimo 50 partidos
            
            for match in upcoming_matches:
                if 'commence_time' in match:
                    # Parsear la fecha UTC
                    utc_time = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
                    # Convertir a hora colombiana
                    colombia_time = utc_time.astimezone(colombia_tz)
                    # Agregar campos procesados
                    match['colombia_date'] = colombia_time.strftime('%d/%m/%Y')
                    match['colombia_time'] = colombia_time.strftime('%H:%M')
                    match['utc_timestamp'] = match['commence_time']
                    
                    # Generar predicciones simples basadas en valores por defecto
                    # Por ahora usamos valores fijos hasta que tengamos datos históricos
                    match['shots_total_prediction'] = "N/A"
                    match['shots_on_target_prediction'] = "N/A"
                    match['goals_total_prediction'] = "N/A"
            
            # Ordenar partidos por fecha y hora (más próximos primero)
            upcoming_matches.sort(key=lambda x: datetime.fromisoformat(x.get('commence_time', '').replace('Z', '+00:00')))
            
            # Agrupar partidos por fecha (para estadísticas)
            matches_by_date = {}
            for match in upcoming_matches:
                match_date = match.get('commence_time', '').split('T')[0]
                if match_date not in matches_by_date:
                    matches_by_date[match_date] = []
                matches_by_date[match_date].append(match)
            
            context = {
                'upcoming_matches': upcoming_matches,
                'matches_by_date': matches_by_date,
                'sport_key': sport_key,
                'total_matches': len(upcoming_matches)
            }
            
            return render(request, 'odds/upcoming_matches.html', context)
            
        except Exception as e:
            logger.error(f"Error obteniendo próximos partidos: {e}")
            return render(request, 'odds/error.html', {
                'error_message': f'Error obteniendo próximos partidos: {str(e)}'
            })
    
    def _get_league_name(self, sport_key):
        """Mapea sport_key a nombre de liga"""
        league_mapping = {
            'soccer_epl': 'Premier League',
            'soccer_spain_la_liga': 'La Liga',
            'soccer_germany_bundesliga': 'Bundesliga',
            'soccer_italy_serie_a': 'Serie A',
            'soccer_france_ligue_one': 'Ligue 1',
            'soccer_uefa_champs_league': 'Champions League',
        }
        return league_mapping.get(sport_key, 'Premier League')
    
    def _get_quick_prediction(self, home_team, away_team, league, prediction_type):
        """Predicción rápida basada en estadísticas simples sin entrenar modelos"""
        try:
            from football_data.models import Match
            import numpy as np
            
            # Obtener estadísticas recientes del equipo local (últimos 10 partidos)
            home_matches = Match.objects.filter(
                league=league,
                home_team=home_team
            ).exclude(hs__isnull=True).order_by('-date')[:10]
            
            # Obtener estadísticas recientes del equipo visitante (últimos 10 partidos)
            away_matches = Match.objects.filter(
                league=league,
                away_team=away_team
            ).exclude(as_field__isnull=True).order_by('-date')[:10]
            
            if not home_matches or not away_matches:
                return "N/A"
            
            # Calcular promedios según el tipo de predicción
            if prediction_type == 'shots_total':
                home_avg = np.mean([m.hs for m in home_matches if m.hs is not None])
                away_avg = np.mean([m.as_field for m in away_matches if m.as_field is not None])
                prediction = (home_avg + away_avg) * 1.05  # Factor de ajuste
                
            elif prediction_type == 'shots_on_target':
                home_avg = np.mean([m.hst for m in home_matches if m.hst is not None])
                away_avg = np.mean([m.ast for m in away_matches if m.ast is not None])
                prediction = (home_avg + away_avg) * 1.05
                
            elif prediction_type == 'goals_total':
                home_goals = np.mean([m.fthg for m in home_matches if m.fthg is not None])
                away_goals = np.mean([m.ftag for m in away_matches if m.ftag is not None])
                prediction = (home_goals + away_goals) * 1.05
                
            else:
                return "N/A"
            
            # Aplicar límites realistas
            if prediction_type in ['shots_total', 'shots_on_target']:
                prediction = max(3, min(prediction, 50))
            elif prediction_type == 'goals_total':
                prediction = max(0, min(prediction, 10))
            
            return round(prediction, 1)
            
        except Exception as e:
            logger.warning(f"Error en predicción rápida: {e}")
            return "N/A"
    


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
class LiveOddsView(View):
    """Vista para mostrar cuotas en tiempo real"""
    
    def get(self, request):
        # Obtener cuotas más recientes
        recent_odds = Odds.objects.select_related(
            'match__sport', 'bookmaker'
        ).filter(
            odds_timestamp__gte=timezone.now() - timedelta(minutes=30)
        ).order_by('-odds_timestamp')[:50]
        
        # Agrupar por partido
        matches_data = {}
        for odds in recent_odds:
            match_key = f"{odds.match.match_id}"
            if match_key not in matches_data:
                matches_data[match_key] = {
                    'match': odds.match,
                    'bookmakers': {}
                }
            
            matches_data[match_key]['bookmakers'][odds.bookmaker.title] = {
                'home_odds': odds.home_odds,
                'draw_odds': odds.draw_odds,
                'away_odds': odds.away_odds,
                'timestamp': odds.odds_timestamp
            }
        
        context = {
            'matches_data': matches_data,
        }
        
        return render(request, 'odds/live_odds.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
class SportsListView(View):
    """Lista de deportes disponibles"""
    
    def get(self, request):
        sports = Sport.objects.all().order_by('title')
        
        # Estadísticas por deporte
        sports_with_stats = []
        for sport in sports:
            match_count = Match.objects.filter(sport=sport).count()
            odds_count = Odds.objects.filter(match__sport=sport).count()
            
            sports_with_stats.append({
                'sport': sport,
                'match_count': match_count,
                'odds_count': odds_count,
            })
        
        context = {
            'sports_with_stats': sports_with_stats,
        }
        
        return render(request, 'odds/sports_list.html', context)