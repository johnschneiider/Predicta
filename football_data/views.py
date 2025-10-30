"""
Vistas para mostrar datos históricos de fútbol
"""

import os
from datetime import datetime, timedelta, timezone as tz
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Max, Min
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from .models import League, Match, ExcelFile
from .services import ExcelImportService
from .forms import ExcelUploadForm, LeagueFilterForm, MatchFilterForm
from django.core.paginator import Paginator
import json


@method_decorator(login_required, name='dispatch')
class FootballDataDashboardView(View):
    """Dashboard principal de datos de fútbol"""
    
    def get(self, request):
        service = ExcelImportService()
        
        # Obtener estadísticas
        stats = service.get_import_statistics()
        
        # Obtener ligas con estadísticas
        leagues = League.objects.annotate(
            match_count=Count('matches'),
            latest_match=Max('matches__date')
        ).order_by('-match_count')
        
        # Obtener partidos recientes
        recent_matches = Match.objects.select_related('league').order_by('-date')[:10]
        
        # Obtener archivos disponibles
        available_files = service.get_available_files()
        
        context = {
            'stats': stats,
            'leagues': leagues,
            'recent_matches': recent_matches,
            'available_files': available_files,
        }
        
        return render(request, 'football_data/dashboard.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class LeaguesListView(View):
    """Lista de ligas"""
    
    def get(self, request):
        leagues = League.objects.annotate(
            match_count=Count('matches'),
            latest_match=Max('matches__date'),
            avg_goals=Avg('matches__fthg') + Avg('matches__ftag')
        ).order_by('-match_count')
        
        context = {
            'leagues': leagues,
        }
        
        return render(request, 'football_data/leagues_list.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class LeagueDetailView(View):
    """Detalle de una liga específica"""
    
    def get(self, request, league_id):
        league = get_object_or_404(League, id=league_id)
        service = ExcelImportService()
        
        # Obtener estadísticas de la liga
        stats = service.get_league_statistics(league_id)
        
        # Obtener partidos con paginación
        matches = Match.objects.filter(league=league).order_by('-date')
        
        # Filtros
        search = request.GET.get('search', '')
        season_filter = request.GET.get('season', '')
        result_filter = request.GET.get('result', '')
        
        if search:
            matches = matches.filter(
                Q(home_team__icontains=search) | 
                Q(away_team__icontains=search)
            )
        
        if season_filter:
            matches = matches.filter(league__season=season_filter)
        
        if result_filter:
            matches = matches.filter(ftr=result_filter)
        
        # Paginación
        paginator = Paginator(matches, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'league': league,
            'stats': stats,
            'page_obj': page_obj,
            'search_query': search,
            'season_filter': season_filter,
            'result_filter': result_filter,
        }
        
        return render(request, 'football_data/league_detail.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class MatchesListView(View):
    """Lista de partidos"""
    
    def get(self, request):
        matches = Match.objects.select_related('league').order_by('-date')
        
        # Filtros
        league_filter = request.GET.get('league', '')
        search = request.GET.get('search', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        result_filter = request.GET.get('result', '')
        
        if league_filter:
            matches = matches.filter(league_id=league_filter)
        
        if search:
            matches = matches.filter(
                Q(home_team__icontains=search) | 
                Q(away_team__icontains=search)
            )
        
        if date_from:
            matches = matches.filter(date__gte=date_from)
        
        if date_to:
            matches = matches.filter(date__lte=date_to)
        
        if result_filter:
            matches = matches.filter(ftr=result_filter)
        
        # Paginación
        paginator = Paginator(matches, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Obtener ligas para el filtro
        leagues = League.objects.annotate(match_count=Count('matches')).order_by('name')
        
        context = {
            'page_obj': page_obj,
            'leagues': leagues,
            'current_league': league_filter,
            'search_query': search,
            'date_from': date_from,
            'date_to': date_to,
            'result_filter': result_filter,
        }
        
        return render(request, 'football_data/matches_list.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class MatchDetailView(View):
    """Detalle de un partido específico"""
    
    def get(self, request, match_id):
        match = get_object_or_404(Match, id=match_id)
        
        # Obtener estadísticas del partido
        match_stats = {
            'total_goals': match.total_goals,
            'is_over_25': match.is_over_25,
            'best_home_odds': match.best_home_odds,
            'best_draw_odds': match.best_draw_odds,
            'best_away_odds': match.best_away_odds,
        }
        
        # Obtener partidos similares (mismo equipo local)
        similar_matches = Match.objects.filter(
            home_team=match.home_team,
            league=match.league
        ).exclude(id=match.id).order_by('-date')[:5]
        
        context = {
            'match': match,
            'match_stats': match_stats,
            'similar_matches': similar_matches,
        }
        
        return render(request, 'football_data/match_detail.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class ImportView(View):
    """Vista para importar archivos Excel"""
    
    def get(self, request):
        form = ExcelUploadForm()
        
        # Obtener información de equipos y fechas por liga
        leagues_data = []
        leagues = League.objects.all().order_by('name')
        
        for league in leagues:
            # Obtener todos los equipos únicos (como local y visitante)
            home_teams = Match.objects.filter(league=league).values_list('home_team', flat=True).distinct()
            away_teams = Match.objects.filter(league=league).values_list('away_team', flat=True).distinct()
            all_teams = sorted(set(list(home_teams)) | set(list(away_teams)))
            
            teams_info = []
            for team_name in all_teams:
                # Obtener fechas de partidos de este equipo
                team_matches = Match.objects.filter(
                    Q(home_team=team_name) | Q(away_team=team_name),
                    league=league
                ).aggregate(
                    first_date=Min('date'),
                    last_date=Max('date'),
                    total_matches=Count('id')
                )
                
                if team_matches['first_date']:
                    teams_info.append({
                        'name': team_name,
                        'first_date': team_matches['first_date'],
                        'last_date': team_matches['last_date'],
                        'total_matches': team_matches['total_matches']
                    })
            
            # Ordenar equipos por fecha más reciente (último partido) de forma descendente
            teams_info.sort(key=lambda x: x['last_date'], reverse=True)
            
            if teams_info:
                leagues_data.append({
                    'league': league,
                    'teams': teams_info
                })
        
        context = {
            'form': form,
            'leagues_data': leagues_data,
        }
        
        return render(request, 'football_data/import.html', context)
    
    def post(self, request):
        form = ExcelUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Obtener el archivo validado del formulario
                uploaded_file = form.cleaned_data['file']
                league_name = form.cleaned_data['league_name']
                season = form.cleaned_data['season']
                
                # Convertir a lista para mantener compatibilidad con el código existente
                uploaded_files = [uploaded_file]
                
                # Crear directorio de media si no existe
                media_dir = os.path.join(settings.MEDIA_ROOT, 'excel_files')
                os.makedirs(media_dir, exist_ok=True)
                
                # Procesar los archivos
                service = ExcelImportService()
                total_imported = 0
                total_failed = 0
                successful_files = []
                failed_files = []
                
                for uploaded_file in uploaded_files:
                    try:
                        # Guardar archivo temporalmente
                        temp_file_path = os.path.join(media_dir, uploaded_file.name)
                        with open(temp_file_path, 'wb+') as destination:
                            for chunk in uploaded_file.chunks():
                                destination.write(chunk)
                        
                        # Importar archivo
                        result = service.import_data_file(temp_file_path, league_name, season)
                        
                        if result['success']:
                            # Crear registro de ExcelFile
                            league = League.objects.get(name=result['league'])
                            ExcelFile.objects.create(
                                name=uploaded_file.name,
                                file=uploaded_file,
                                file_path=temp_file_path,
                                league=league,
                                total_rows=result['imported_count'] + result['failed_count'],
                                imported_rows=result['imported_count'],
                                failed_rows=result['failed_count'],
                                file_size=uploaded_file.size
                            )
                            
                            total_imported += result['imported_count']
                            total_failed += result['failed_count']
                            successful_files.append(uploaded_file.name)
                        else:
                            failed_files.append(f"{uploaded_file.name}: {result['error']}")
                            # Eliminar archivo temporal si falló
                            if os.path.exists(temp_file_path):
                                os.remove(temp_file_path)
                                
                    except Exception as e:
                        failed_files.append(f"{uploaded_file.name}: {str(e)}")
                        # Eliminar archivo temporal si falló
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                
                # Mostrar resultados
                if successful_files:
                    messages.success(
                        request, 
                        f"Archivos importados exitosamente: {len(successful_files)} archivos, "
                        f"{total_imported} partidos importados, {total_failed} fallos"
                    )
                
                if failed_files:
                    for failed_file in failed_files:
                        messages.error(request, f"Error: {failed_file}")
                
            except Exception as e:
                messages.error(request, f"Error procesando archivos: {str(e)}")
        else:
            # Si el formulario no es válido, mostrar errores específicos
            for field, errors in form.errors.items():
                for error in errors:
                    if field == 'file':
                        messages.error(request, f"❌ Archivo: {error}")
                    elif field == 'league':
                        messages.warning(request, f"⚠️ Liga: {error}")
                    elif field == 'league_name':
                        messages.warning(request, f"⚠️ Nombre de liga: {error}")
                    else:
                        messages.error(request, f"❌ {field}: {error}")
        
        # Pasar el formulario con errores para mostrarlos en el template
        # Obtener información de equipos y fechas por liga
        leagues_data = []
        leagues = League.objects.all().order_by('name')
        
        for league in leagues:
            # Obtener todos los equipos únicos (como local y visitante)
            home_teams = Match.objects.filter(league=league).values_list('home_team', flat=True).distinct()
            away_teams = Match.objects.filter(league=league).values_list('away_team', flat=True).distinct()
            all_teams = sorted(set(list(home_teams)) | set(list(away_teams)))
            
            teams_info = []
            for team_name in all_teams:
                # Obtener fechas de partidos de este equipo
                team_matches = Match.objects.filter(
                    Q(home_team=team_name) | Q(away_team=team_name),
                    league=league
                ).aggregate(
                    first_date=Min('date'),
                    last_date=Max('date'),
                    total_matches=Count('id')
                )
                
                if team_matches['first_date']:
                    teams_info.append({
                        'name': team_name,
                        'first_date': team_matches['first_date'],
                        'last_date': team_matches['last_date'],
                        'total_matches': team_matches['total_matches']
                    })
            
            # Ordenar equipos por fecha más reciente (último partido) de forma descendente
            teams_info.sort(key=lambda x: x['last_date'], reverse=True)
            
            if teams_info:
                leagues_data.append({
                    'league': league,
                    'teams': teams_info
                })
        
        context = {
            'form': form,
            'leagues_data': leagues_data,
        }
        
        return render(request, 'football_data/import.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class DeleteFileView(View):
    """Vista para eliminar archivos importados"""
    
    def post(self, request, file_id):
        try:
            # Obtener el archivo
            excel_file = ExcelFile.objects.get(id=file_id)
            
            # Obtener la liga asociada
            league = excel_file.league
            
            # Eliminar solamente los partidos vinculados a este archivo
            matches_qs = Match.objects.filter(source_file=excel_file)
            matches_deleted = matches_qs.count()
            matches_qs.delete()
            
            # Eliminar el archivo físico si existe
            if excel_file.file_path and os.path.exists(excel_file.file_path):
                os.remove(excel_file.file_path)
            
            # Eliminar el registro de la base de datos
            file_name = excel_file.name
            excel_file.delete()
            
            # Verificar si la liga quedó sin partidos y eliminarla si es necesario
            if Match.objects.filter(league=league).count() == 0:
                league.delete()
                league_deleted = True
            else:
                league_deleted = False
            
            messages.success(
                request, 
                f"✅ Archivo '{file_name}' eliminado exitosamente. "
                f"Se eliminaron {matches_deleted} partidos."
                + (f" La liga '{league.name}' también fue eliminada." if league_deleted else "")
            )
            
        except ExcelFile.DoesNotExist:
            messages.error(request, "❌ El archivo no existe.")
        except Exception as e:
            messages.error(request, f"❌ Error al eliminar el archivo: {str(e)}")
        
        return redirect('football_data:import')


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class DeleteAllFilesView(View):
    """Vista para eliminar todos los archivos y datos"""
    
    def post(self, request):
        try:
            # Contar archivos y partidos antes de eliminar
            total_files = ExcelFile.objects.count()
            total_matches = Match.objects.count()
            total_leagues = League.objects.count()
            
            # Eliminar todos los archivos físicos
            for excel_file in ExcelFile.objects.all():
                if excel_file.file_path and os.path.exists(excel_file.file_path):
                    os.remove(excel_file.file_path)
            
            # Eliminar todos los registros de la base de datos
            ExcelFile.objects.all().delete()
            Match.objects.all().delete()
            League.objects.all().delete()
            
            messages.success(
                request, 
                f"🗑️ Todos los datos eliminados exitosamente:\n"
                f"- {total_files} archivos eliminados\n"
                f"- {total_matches} partidos eliminados\n"
                f"- {total_leagues} ligas eliminadas"
            )
            
        except Exception as e:
            messages.error(request, f"❌ Error al eliminar todos los datos: {str(e)}")
        
        return redirect('football_data:import')


@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class ImportAjaxView(View):
    """Vista AJAX para importar archivos"""
    
    def post(self, request):
        service = ExcelImportService()
        
        file_name = request.POST.get('file_name')
        league_name = request.POST.get('league_name', '')
        season = request.POST.get('season', '')
        
        if not file_name:
            return JsonResponse({'success': False, 'error': 'Debe seleccionar un archivo'})
        
        file_path = os.path.join(service.data_dir, file_name)
        
        if not os.path.exists(file_path):
            return JsonResponse({'success': False, 'error': 'El archivo seleccionado no existe'})
        
        # Importar archivo
        result = service.import_excel_file(file_path, league_name, season)
        
        return JsonResponse(result)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class StatisticsView(View):
    """Vista de estadísticas"""
    
    def get(self, request):
        # Estadísticas generales
        total_matches = Match.objects.count()
        total_leagues = League.objects.count()
        
        # Análisis de resultados
        result_stats = Match.objects.values('ftr').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / total_matches
        ).exclude(ftr__isnull=True)
        
        # Análisis de goles
        goals_stats = Match.objects.exclude(
            fthg__isnull=True, ftag__isnull=True
        ).aggregate(
            avg_home_goals=Avg('fthg'),
            avg_away_goals=Avg('ftag'),
            avg_total_goals=Avg('fthg') + Avg('ftag'),
            max_goals=Max('fthg') + Max('ftag')
        )
        
        # Análisis de cuotas
        odds_stats = Match.objects.exclude(
            b365h__isnull=True, b365d__isnull=True, b365a__isnull=True
        ).aggregate(
            avg_home_odds=Avg('b365h'),
            avg_draw_odds=Avg('b365d'),
            avg_away_odds=Avg('b365a'),
            max_home_odds=Max('b365h'),
            max_draw_odds=Max('b365d'),
            max_away_odds=Max('b365a')
        )
        
        # Top equipos
        top_home_teams = Match.objects.values('home_team').annotate(
            wins=Count('id', filter=Q(ftr='H')),
            total=Count('id')
        ).order_by('-wins')[:10]
        
        top_away_teams = Match.objects.values('away_team').annotate(
            wins=Count('id', filter=Q(ftr='A')),
            total=Count('id')
        ).order_by('-wins')[:10]
        
        # Estadísticas adicionales
        leagues_stats = League.objects.annotate(
            match_count=Count('matches'),
            avg_goals=Avg('matches__fthg') + Avg('matches__ftag'),
            avg_shots=Avg('matches__hs') + Avg('matches__as_field'),
            latest_match=Max('matches__date')
        ).order_by('-match_count')[:10]
        
        # Estadísticas generales
        stats = {
            'total_matches': total_matches,
            'total_leagues': total_leagues,
            'total_files': ExcelFile.objects.count(),
            'date_range': f"{Match.objects.aggregate(min_date=Min('date'))['min_date']} - {Match.objects.aggregate(max_date=Max('date'))['max_date']}",
            'avg_goals_per_match': goals_stats['avg_total_goals'] or 0,
            'avg_home_goals': goals_stats['avg_home_goals'] or 0,
            'avg_away_goals': goals_stats['avg_away_goals'] or 0,
            'over_25_percentage': 0,  # Se calculará si hay datos
            'avg_shots_per_match': 0,  # Se calculará si hay datos
            'avg_shots_target': 0,  # Se calculará si hay datos
            'shots_effectiveness': 0,  # Se calculará si hay datos
            'avg_corners': 0,  # Se calculará si hay datos
        }
        
        # Calcular estadísticas de remates si hay datos
        shots_data = Match.objects.exclude(hs__isnull=True, as_field__isnull=True, hst__isnull=True, ast__isnull=True)
        if shots_data.exists():
            shots_stats = shots_data.aggregate(
                avg_home_shots=Avg('hs'),
                avg_away_shots=Avg('as_field'),
                avg_home_shots_target=Avg('hst'),
                avg_away_shots_target=Avg('ast')
            )
            stats['avg_shots_per_match'] = (shots_stats['avg_home_shots'] or 0) + (shots_stats['avg_away_shots'] or 0)
            stats['avg_shots_target'] = (shots_stats['avg_home_shots_target'] or 0) + (shots_stats['avg_away_shots_target'] or 0)
            
            if stats['avg_shots_per_match'] > 0:
                stats['shots_effectiveness'] = (stats['avg_shots_target'] / stats['avg_shots_per_match']) * 100
        
        # Calcular estadísticas de corners si hay datos
        corners_data = Match.objects.exclude(hc__isnull=True, ac__isnull=True)
        if corners_data.exists():
            corners_stats = corners_data.aggregate(
                avg_home_corners=Avg('hc'),
                avg_away_corners=Avg('ac')
            )
            stats['avg_corners'] = (corners_stats['avg_home_corners'] or 0) + (corners_stats['avg_away_corners'] or 0)
        
        # Calcular porcentaje Over 2.5 si hay datos
        goals_data = Match.objects.exclude(fthg__isnull=True, ftag__isnull=True)
        if goals_data.exists():
            over_25_count = goals_data.extra(where=['fthg + ftag > 2.5']).count()
            total_goals_matches = goals_data.count()
            if total_goals_matches > 0:
                stats['over_25_percentage'] = (over_25_count / total_goals_matches) * 100
        
        context = {
            'stats': stats,
            'leagues_stats': leagues_stats,
            'result_stats': result_stats,
            'goals_stats': goals_stats,
            'odds_stats': odds_stats,
            'top_home_teams': top_home_teams,
            'top_away_teams': top_away_teams,
        }
        
        return render(request, 'football_data/statistics.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class LeagueDataTableView(View):
    """Vista para mostrar tabla de datos de una liga específica"""
    
    def get(self, request):
        # Obtener parámetros
        league_id = request.GET.get('league')
        page = request.GET.get('page', 1)
        
        # Obtener todas las ligas para el selector
        leagues = League.objects.annotate(
            match_count=Count('matches')
        ).order_by('name')
        
        matches = None
        selected_league = None
        
        if league_id:
            try:
                selected_league = League.objects.get(id=league_id)
                matches = Match.objects.filter(league=selected_league).order_by('-date', '-time')
                
                # Paginación
                paginator = Paginator(matches, 50)  # 50 partidos por página
                matches = paginator.get_page(page)
                
            except League.DoesNotExist:
                messages.error(request, 'Liga no encontrada')
        
        context = {
            'leagues': leagues,
            'selected_league': selected_league,
            'matches': matches,
            'league_id': league_id,
        }
        
        return render(request, 'football_data/league_data_table.html', context)


# @method_decorator(login_required, name='dispatch')  # Temporalmente deshabilitado
@method_decorator(login_required, name='dispatch')
class MarketsView(View):
    """Vista de análisis de mercados con gráficas"""
    
    def get(self, request):
        # Obtener filtros
        league_filter = request.GET.get('league', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        # Construir consulta base
        matches = Match.objects.exclude(
            b365h__isnull=True, b365d__isnull=True, b365a__isnull=True
        )
        
        if league_filter:
            matches = matches.filter(league_id=league_filter)
        
        if date_from:
            matches = matches.filter(date__gte=date_from)
        
        if date_to:
            matches = matches.filter(date__lte=date_to)
        
        # Obtener ligas para el filtro
        leagues = League.objects.annotate(match_count=Count('matches')).order_by('name')
        
        # Análisis de mercados
        markets_data = self._analyze_markets(matches)
        
        context = {
            'leagues': leagues,
            'current_league': league_filter,
            'date_from': date_from,
            'date_to': date_to,
            'markets_data': json.dumps(markets_data, default=str),
        }
        
        return render(request, 'football_data/markets.html', context)
    
    def _analyze_markets(self, matches):
        """Analiza específicamente el mercado de remates"""
        markets = {}
        
        # Análisis de remates
        markets['shots'] = self._analyze_shots_market(matches)
        
        return markets
    
    def _analyze_shots_market(self, matches):
        """Analiza específicamente el mercado de remates"""
        data = {
            'title': 'Análisis de Remates',
            'description': 'Análisis detallado de tiros y tiros a puerta',
            'charts': {}
        }
        
        # Filtrar partidos que tengan datos de remates
        matches_with_shots = matches.exclude(
            hs__isnull=True, as_field__isnull=True, hst__isnull=True, ast__isnull=True
        )
        
        if not matches_with_shots.exists():
            data['charts']['no_data'] = {
                'type': 'info',
                'title': 'Sin Datos',
                'message': 'No hay datos de remates disponibles para el filtro seleccionado'
            }
            return data
        
        # Promedio de remates por partido
        shots_stats = matches_with_shots.aggregate(
            avg_home_shots=Avg('hs'),
            avg_away_shots=Avg('as_field'),
            avg_home_shots_target=Avg('hst'),
            avg_away_shots_target=Avg('ast')
        )
        
        # Gráfica 1: Promedio de remates totales
        data['charts']['shots_average'] = {
            'type': 'bar',
            'title': 'Promedio de Remates por Partido',
            'data': [
                {'label': 'Remates Local', 'value': round(shots_stats['avg_home_shots'] or 0, 2)},
                {'label': 'Remates Visitante', 'value': round(shots_stats['avg_away_shots'] or 0, 2)},
                {'label': 'Remates a Puerta Local', 'value': round(shots_stats['avg_home_shots_target'] or 0, 2)},
                {'label': 'Remates a Puerta Visitante', 'value': round(shots_stats['avg_away_shots_target'] or 0, 2)},
            ]
        }
        
        # Gráfica 2: Efectividad de remates (porcentaje de acierto)
        home_effectiveness = 0
        away_effectiveness = 0
        
        if shots_stats['avg_home_shots'] and shots_stats['avg_home_shots'] > 0:
            home_effectiveness = round((shots_stats['avg_home_shots_target'] or 0) / shots_stats['avg_home_shots'] * 100, 2)
        
        if shots_stats['avg_away_shots'] and shots_stats['avg_away_shots'] > 0:
            away_effectiveness = round((shots_stats['avg_away_shots_target'] or 0) / shots_stats['avg_away_shots'] * 100, 2)
        
        data['charts']['shots_effectiveness'] = {
            'type': 'bar',
            'title': 'Efectividad de Remates (%)',
            'data': [
                {'label': 'Local', 'value': home_effectiveness},
                {'label': 'Visitante', 'value': away_effectiveness},
            ]
        }
        
        # Gráfica 3: Distribución de remates totales por partido
        total_shots_dist = matches_with_shots.extra(
            select={'total_shots': 'hs + as_field'}
        ).values('total_shots').annotate(
            count=Count('id')
        ).order_by('total_shots')
        
        data['charts']['total_shots_distribution'] = {
            'type': 'line',
            'title': 'Distribución de Remates Totales por Partido',
            'data': [{'x': item['total_shots'], 'y': item['count']} for item in total_shots_dist]
        }
        
        # Gráfica 4: Distribución de remates a puerta por partido
        shots_target_dist = matches_with_shots.extra(
            select={'total_shots_target': 'hst + ast'}
        ).values('total_shots_target').annotate(
            count=Count('id')
        ).order_by('total_shots_target')
        
        data['charts']['shots_target_distribution'] = {
            'type': 'line',
            'title': 'Distribución de Remates a Puerta por Partido',
            'data': [{'x': item['total_shots_target'], 'y': item['count']} for item in shots_target_dist]
        }
        
        # Gráfica 5: Comparación Local vs Visitante (remates totales)
        data['charts']['home_vs_away_shots'] = {
            'type': 'pie',
            'title': 'Distribución de Remates: Local vs Visitante',
            'data': [
                {'label': 'Local', 'value': round(shots_stats['avg_home_shots'] or 0, 2)},
                {'label': 'Visitante', 'value': round(shots_stats['avg_away_shots'] or 0, 2)},
            ]
        }
        
        # Gráfica 6: Comparación Local vs Visitante (remates a puerta)
        data['charts']['home_vs_away_shots_target'] = {
            'type': 'pie',
            'title': 'Distribución de Remates a Puerta: Local vs Visitante',
            'data': [
                {'label': 'Local', 'value': round(shots_stats['avg_home_shots_target'] or 0, 2)},
                {'label': 'Visitante', 'value': round(shots_stats['avg_away_shots_target'] or 0, 2)},
            ]
        }
        
        return data
    
    def _analyze_over_under_market(self, matches):
        """Analiza el mercado Over/Under 2.5"""
        data = {
            'title': 'Mercado Over/Under 2.5',
            'description': 'Análisis de goles y cuotas Over/Under',
            'charts': {}
        }
        
        # Distribución Over/Under basada en goles reales
        matches_with_goals = matches.exclude(fthg__isnull=True, ftag__isnull=True)
        
        if matches_with_goals.exists():
            over_25_count = matches_with_goals.extra(
                where=['fthg + ftag > 2.5']
            ).count()
            under_25_count = matches_with_goals.extra(
                where=['fthg + ftag <= 2.5']
            ).count()
            
            data['charts']['over_under_distribution'] = {
                'type': 'pie',
                'title': 'Distribución Over/Under 2.5 (Basado en Goles Reales)',
                'data': [
                    {'label': 'Over 2.5', 'value': over_25_count},
                    {'label': 'Under 2.5', 'value': under_25_count},
                ]
            }
            
            # Promedio de goles por partido
            avg_goals = matches_with_goals.aggregate(
                avg_home=Avg('fthg'),
                avg_away=Avg('ftag')
            )
            
            avg_total = (avg_goals['avg_home'] or 0) + (avg_goals['avg_away'] or 0)
            
            data['charts']['goals_average'] = {
                'type': 'bar',
                'title': 'Promedio de Goles por Partido',
                'data': [
                    {'label': 'Local', 'value': round(avg_goals['avg_home'] or 0, 2)},
                    {'label': 'Visitante', 'value': round(avg_goals['avg_away'] or 0, 2)},
                    {'label': 'Total', 'value': round(avg_total, 2)},
                ]
            }
            
            # Distribución de goles por partido
            goals_dist = matches_with_goals.extra(
                select={'total_goals': 'fthg + ftag'}
            ).values('total_goals').annotate(
                count=Count('id')
            ).order_by('total_goals')
            
            data['charts']['goals_distribution'] = {
                'type': 'line',
                'title': 'Distribución de Goles por Partido',
                'data': [{'x': item['total_goals'], 'y': item['count']} for item in goals_dist]
            }
        
        # Análisis de cuotas Over/Under si están disponibles
        matches_with_ou_odds = matches.exclude(
            b365_over_25__isnull=True, b365_under_25__isnull=True
        )
        
        if matches_with_ou_odds.exists():
            ou_odds = matches_with_ou_odds.aggregate(
                b365_over=Avg('b365_over_25'),
                b365_under=Avg('b365_under_25'),
                p_over=Avg('p_over_25'),
                p_under=Avg('p_under_25'),
                max_over=Avg('max_over_25'),
                max_under=Avg('max_under_25'),
                avg_over=Avg('avg_over_25'),
                avg_under=Avg('avg_under_25'),
            )
            
            data['charts']['over_under_odds'] = {
                'type': 'bar',
                'title': 'Promedio de Cuotas Over/Under 2.5',
                'data': [
                    {'label': 'Bet365 Over', 'value': round(ou_odds['b365_over'] or 0, 2)},
                    {'label': 'Bet365 Under', 'value': round(ou_odds['b365_under'] or 0, 2)},
                    {'label': 'Pinnacle Over', 'value': round(ou_odds['p_over'] or 0, 2)},
                    {'label': 'Pinnacle Under', 'value': round(ou_odds['p_under'] or 0, 2)},
                    {'label': 'Max Over', 'value': round(ou_odds['max_over'] or 0, 2)},
                    {'label': 'Max Under', 'value': round(ou_odds['max_under'] or 0, 2)},
                ]
            }
        
        return data
    
    def _analyze_goals_market(self, matches):
        """Analiza el mercado de goles"""
        data = {
            'title': 'Mercado de Goles',
            'description': 'Análisis detallado de goles y estadísticas',
            'charts': {}
        }
        
        # Distribución de goles por partido
        goals_dist = matches.exclude(
            fthg__isnull=True, ftag__isnull=True
        ).extra(
            select={'total_goals': 'fthg + ftag'}
        ).values('total_goals').annotate(
            count=Count('id')
        ).order_by('total_goals')
        
        data['charts']['goals_distribution'] = {
            'type': 'line',
            'title': 'Distribución de Goles por Partido',
            'data': [{'x': item['total_goals'], 'y': item['count']} for item in goals_dist]
        }
        
        return data
    
    def _analyze_corners_market(self, matches):
        """Analiza el mercado de corners"""
        data = {
            'title': 'Mercado de Corners',
            'description': 'Análisis de corners y estadísticas',
            'charts': {}
        }
        
        # Promedio de corners
        corners_stats = matches.exclude(
            hc__isnull=True, ac__isnull=True
        ).aggregate(
            avg_home=Avg('hc'),
            avg_away=Avg('ac')
        )
        
        if corners_stats['avg_home'] is not None:
            avg_total = (corners_stats['avg_home'] or 0) + (corners_stats['avg_away'] or 0)
            
            data['charts']['corners_average'] = {
                'type': 'bar',
                'title': 'Promedio de Corners por Partido',
                'data': [
                    {'label': 'Local', 'value': round(corners_stats['avg_home'] or 0, 2)},
                    {'label': 'Visitante', 'value': round(corners_stats['avg_away'] or 0, 2)},
                    {'label': 'Total', 'value': round(avg_total, 2)},
                ]
            }
            
            # Distribución de corners totales
            corners_dist = matches.exclude(
                hc__isnull=True, ac__isnull=True
            ).extra(
                select={'total_corners': 'hc + ac'}
            ).values('total_corners').annotate(
                count=Count('id')
            ).order_by('total_corners')
            
            data['charts']['corners_distribution'] = {
                'type': 'line',
                'title': 'Distribución de Corners por Partido',
                'data': [{'x': item['total_corners'], 'y': item['count']} for item in corners_dist]
            }
        
        return data
    
    def _analyze_cards_market(self, matches):
        """Analiza el mercado de tarjetas"""
        data = {
            'title': 'Mercado de Tarjetas',
            'description': 'Análisis de tarjetas amarillas y rojas',
            'charts': {}
        }
        
        # Promedio de tarjetas amarillas
        yellow_cards_stats = matches.exclude(
            hy__isnull=True, ay__isnull=True
        ).aggregate(
            avg_home_yellow=Avg('hy'),
            avg_away_yellow=Avg('ay')
        )
        
        # Promedio de tarjetas rojas
        red_cards_stats = matches.exclude(
            hr__isnull=True, ar__isnull=True
        ).aggregate(
            avg_home_red=Avg('hr'),
            avg_away_red=Avg('ar')
        )
        
        if yellow_cards_stats['avg_home_yellow'] is not None:
            data['charts']['yellow_cards_average'] = {
                'type': 'bar',
                'title': 'Promedio de Tarjetas Amarillas',
                'data': [
                    {'label': 'Local', 'value': round(yellow_cards_stats['avg_home_yellow'] or 0, 2)},
                    {'label': 'Visitante', 'value': round(yellow_cards_stats['avg_away_yellow'] or 0, 2)},
                ]
            }
        
        if red_cards_stats['avg_home_red'] is not None:
            data['charts']['red_cards_average'] = {
                'type': 'bar',
                'title': 'Promedio de Tarjetas Rojas',
                'data': [
                    {'label': 'Local', 'value': round(red_cards_stats['avg_home_red'] or 0, 2)},
                    {'label': 'Visitante', 'value': round(red_cards_stats['avg_away_red'] or 0, 2)},
                ]
            }
        
        # Análisis de tiros y tiros a puerta
        shots_stats = matches.exclude(
            hs__isnull=True, as_field__isnull=True, hst__isnull=True, ast__isnull=True
        ).aggregate(
            avg_home_shots=Avg('hs'),
            avg_away_shots=Avg('as_field'),
            avg_home_shots_target=Avg('hst'),
            avg_away_shots_target=Avg('ast')
        )
        
        if shots_stats['avg_home_shots'] is not None:
            data['charts']['shots_average'] = {
                'type': 'bar',
                'title': 'Promedio de Tiros',
                'data': [
                    {'label': 'Tiros Local', 'value': round(shots_stats['avg_home_shots'] or 0, 2)},
                    {'label': 'Tiros Visitante', 'value': round(shots_stats['avg_away_shots'] or 0, 2)},
                    {'label': 'Tiros a Puerta Local', 'value': round(shots_stats['avg_home_shots_target'] or 0, 2)},
                    {'label': 'Tiros a Puerta Visitante', 'value': round(shots_stats['avg_away_shots_target'] or 0, 2)},
                ]
            }
        
        return data
    
    def _analyze_asian_handicap_market(self, matches):
        """Analiza el mercado de handicap asiático"""
        data = {
            'title': 'Mercado Handicap Asiático',
            'description': 'Análisis de handicap asiático',
            'charts': {}
        }
        
        # Promedio de handicap asiático
        handicap_stats = matches.exclude(
            ahh__isnull=True
        ).aggregate(
            avg_handicap=Avg('ahh'),
            b365_ah_home=Avg('b365ahh'),
            b365_ah_away=Avg('b365aha'),
            p_ah_home=Avg('pahh'),
            p_ah_away=Avg('paha'),
            max_ah_home=Avg('maxahh'),
            max_ah_away=Avg('maxaha'),
            avg_ah_home=Avg('avgahh'),
            avg_ah_away=Avg('avgaha'),
        )
        
        if handicap_stats['avg_handicap'] is not None:
            data['charts']['handicap_average'] = {
                'type': 'bar',
                'title': 'Promedio de Handicap Asiático',
                'data': [
                    {'label': 'Handicap Promedio', 'value': round(handicap_stats['avg_handicap'] or 0, 2)},
                    {'label': 'Bet365 AH Home', 'value': round(handicap_stats['b365_ah_home'] or 0, 2)},
                    {'label': 'Bet365 AH Away', 'value': round(handicap_stats['b365_ah_away'] or 0, 2)},
                    {'label': 'Pinnacle AH Home', 'value': round(handicap_stats['p_ah_home'] or 0, 2)},
                    {'label': 'Pinnacle AH Away', 'value': round(handicap_stats['p_ah_away'] or 0, 2)},
                ]
            }
        
        return data


@method_decorator(login_required, name='dispatch')
class AnalysisView(View):
    """Vista de análisis con predicciones de 'ambos marcan' para partidos próximos"""
    
    def get(self, request):
        from odds.services import OddsAPIService
        from ai_predictions.enhanced_both_teams_score import enhanced_both_teams_score_model
        from ai_predictions.simple_models import SimplePredictionService
        from ai_predictions.official_prediction_model import official_prediction_model
        from ai_predictions.shots_prediction_model import shots_prediction_model
        from ai_predictions.xg_shots_model import xg_shots_model
        from ai_predictions.simple_models import ModeloHibridoCorners, ModeloHibridoGeneral
        
        # Obtener partidos de las próximas 24 horas
        odds_service = OddsAPIService()
        # Compatibilidad con versiones antiguas de OddsAPIService que no aceptan
        # el parámetro include_multiple_sports en producción
        try:
            upcoming_matches = odds_service.get_upcoming_matches(
                sport_key='soccer_epl',
                include_multiple_sports=True
            )
        except TypeError:
            upcoming_matches = odds_service.get_upcoming_matches(
                sport_key='soccer_epl'
            )
        
        # Filtrar solo partidos de las próximas 24 horas
        # Asegurar que now esté en UTC para comparar correctamente
        from datetime import timezone as dt_timezone
        now = timezone.now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt_timezone.utc)
        else:
            # Convertir a UTC si tiene otro timezone
            now = now.astimezone(dt_timezone.utc)
        
        next_24h = now + timedelta(hours=24)
        
        import logging
        logger_init = logging.getLogger('football_data')
        logger_init.info(f"📅 Filtrando partidos: ahora={now} UTC, límite={next_24h} UTC ({len(upcoming_matches)} partidos obtenidos)")
        
        matches_with_predictions = []
        
        for match_data in upcoming_matches:
            # Parsear fecha del partido
            commence_time_str = match_data.get('commence_time', '')
            if not commence_time_str:
                continue
                
            try:
                # Convertir a datetime (UTC)
                commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                
                # Asegurar que commence_time tenga timezone (UTC) para comparar
                from datetime import timezone as dt_timezone
                if commence_time.tzinfo is None:
                    commence_time = commence_time.replace(tzinfo=dt_timezone.utc)
                else:
                    # Convertir a UTC si tiene otro timezone
                    commence_time = commence_time.astimezone(dt_timezone.utc)
                
                # Obtener equipos ANTES de filtrar (para logging)
                home_team = match_data.get('home_team', '')
                away_team = match_data.get('away_team', '')
                
                # Filtrar solo los próximos 24 horas (tolerancia ampliada a 36h en prod)
                # Permitir partidos futuros hasta 24 horas adelante
                # No filtrar partidos pasados, solo los que están muy lejos en el futuro
                time_diff = (commence_time - now).total_seconds() / 3600  # Diferencia en horas
                
                if time_diff < -2 or time_diff > 36:
                    # Partido muy pasado (>2h) o demasiado futuro (>36h)
                    import logging
                    logger_info = logging.getLogger('football_data')
                    logger_info.info(f"⏰ Fuera de rango (descartado): {home_team} vs {away_team} - diff {time_diff:.1f}h, kickoff {commence_time} UTC")
                    continue
                
                # Ya tenemos home_team y away_team, verificar que no estén vacíos
                if not home_team or not away_team:
                    continue
                
                # Convertir a hora colombiana (UTC-5)
                colombia_tz = tz(timedelta(hours=-5))
                colombia_time = commence_time.astimezone(colombia_tz)
                
                # Obtener liga desde sport_title o sport_key
                sport_title = match_data.get('sport_title', '')
                sport_key = match_data.get('sport_key', '')
                
                # Mapear sport_key a nombres de ligas más precisos
                league_mapping = {
                    'soccer_epl': 'Premier League',
                    'soccer_spain_la_liga': 'La Liga',
                    'soccer_italy_serie_a': 'Serie A',
                    'soccer_germany_bundesliga': 'Bundesliga',
                    'soccer_france_ligue_one': 'Ligue 1',
                    'soccer_netherlands_eredivisie': 'Eredivisie',
                    'soccer_portugal_primeira_liga': 'Primeira Liga',
                    'soccer_turkey_super_league': 'Super Lig',
                    'soccer_argentina_primera_division': 'Primera División',
                    'soccer_belgium_first_div': 'Pro League',
                    'soccer_china_superleague': 'Super League',
                    'soccer_australia_aleague': 'A-League',
                    'soccer_uefa_champs_league': 'Champions League',
                }
                
                # Buscar la liga en la base de datos
                league = None
                search_names = []
                
                if sport_key and sport_key in league_mapping:
                    search_names.append(league_mapping[sport_key])
                
                if sport_title:
                    search_names.append(sport_title)
                
                # Buscar liga por múltiples nombres posibles
                for search_name in search_names:
                    league = League.objects.filter(name__icontains=search_name).first()
                    if league:
                        break
                
                # Si no se encuentra una liga en BD, crear/usar una por defecto
                if not league:
                    from django.utils import timezone as dj_tz
                    default_season = str(dj_tz.now().year)
                    league, _ = League.objects.get_or_create(
                        name='Premier League',
                        defaults={'country': 'England', 'season': default_season, 'active': True}
                    )
                
                # Calcular TODAS las predicciones usando el MISMO sistema que predict
                import logging
                import numpy as np
                logger = logging.getLogger('football_data')
                
                logger.info(f"🎯 Procesando predicciones completas: {home_team} vs {away_team} en {league.name}")
                
                # Todos los tipos de predicción igual que en predict
                prediction_types = [
                    'shots_total', 'shots_home', 'shots_away',
                    'shots_on_target_total',
                    'goals_total', 'goals_home', 'goals_away',
                    'corners_total', 'corners_home', 'corners_away',
                    'both_teams_score'
                ]
                
                simple_service = SimplePredictionService()
                all_predictions_by_type = {}
                
                # Procesar cada tipo de predicción
                for pred_type in prediction_types:
                    try:
                        predictions = []
                        
                        # 1. Modelos simples (shots tiene manejo especial)
                        if 'shots' in pred_type:
                            try:
                                if pred_type == 'shots_total':
                                    pred1 = shots_prediction_model.predict_shots_total(home_team, away_team, league)
                                elif pred_type == 'shots_home':
                                    pred1 = shots_prediction_model.predict_shots_home(home_team, away_team, league)
                                elif pred_type == 'shots_away':
                                    pred1 = shots_prediction_model.predict_shots_away(home_team, away_team, league)
                                elif pred_type == 'shots_on_target_total':
                                    pred1 = shots_prediction_model.predict_shots_on_target_total(home_team, away_team, league)
                                else:
                                    pred1 = None
                                
                                if pred1:
                                    predictions.append(pred1)
                            except Exception as e:
                                logger.warning(f"⚠️ Error en shots_prediction_model para {pred_type}: {e}")
                            
                            try:
                                if pred_type == 'shots_total':
                                    pred2 = xg_shots_model.predict_shots_total(home_team, away_team, league)
                                elif pred_type == 'shots_home':
                                    pred2 = xg_shots_model.predict_shots_home(home_team, away_team, league)
                                elif pred_type == 'shots_away':
                                    pred2 = xg_shots_model.predict_shots_away(home_team, away_team, league)
                                elif pred_type == 'shots_on_target_total':
                                    pred2 = xg_shots_model.predict_shots_on_target_total(home_team, away_team, league)
                                else:
                                    pred2 = None
                                
                                if pred2:
                                    predictions.append(pred2)
                            except Exception as e:
                                logger.warning(f"⚠️ Error en xg_shots_model para {pred_type}: {e}")
                        else:
                            # Para otros tipos, usar modelos simples
                            try:
                                simple_predictions = simple_service.get_all_simple_predictions(
                                    home_team, away_team, league, pred_type
                                )
                                predictions.extend(simple_predictions)
                            except Exception as e:
                                logger.warning(f"⚠️ Error obteniendo modelos simples para {pred_type}: {e}")
                        
                        # 2. Manejo especial para both_teams_score (enhanced)
                        if pred_type == 'both_teams_score':
                            try:
                                enhanced_prob = enhanced_both_teams_score_model.predict(
                                    home_team, away_team, league
                                )
                                enhanced_prediction = {
                                    'model_name': 'Enhanced Both Teams Score',
                                    'prediction': enhanced_prob,
                                    'confidence': 0.80,
                                    'probabilities': {'both_score': enhanced_prob},
                                    'total_matches': 100
                                }
                                predictions.append(enhanced_prediction)
                            except Exception as e:
                                logger.warning(f"⚠️ Error en enhanced model para {pred_type}: {e}")
                        
                        # 3. Agregar modelos híbridos
                        if 'corners' in pred_type:
                            try:
                                hybrid_model = ModeloHibridoCorners()
                                hybrid_prediction = hybrid_model.predecir(home_team, away_team, league, pred_type)
                                predictions.append(hybrid_prediction)
                            except Exception as e:
                                logger.warning(f"⚠️ Error en modelo híbrido corners para {pred_type}: {e}")
                        elif 'shots' not in pred_type and 'both_teams_score' not in pred_type:
                            try:
                                hybrid_model = ModeloHibridoGeneral()
                                hybrid_prediction = hybrid_model.predecir(home_team, away_team, league, pred_type)
                                predictions.append(hybrid_prediction)
                            except Exception as e:
                                logger.warning(f"⚠️ Error en modelo híbrido general para {pred_type}: {e}")
                        
                        all_predictions_by_type[pred_type] = predictions
                        
                    except Exception as e:
                        logger.error(f"❌ Error procesando {pred_type}: {e}")
                        all_predictions_by_type[pred_type] = []
                
                # 4. Calcular predicción oficial (promedio ponderado) para cada tipo
                official_predictions = official_prediction_model.calculate_official_predictions(all_predictions_by_type)
                
                # Preparar resultados finales
                match_predictions = {}
                for pred_type, official_pred in official_predictions.items():
                    if official_pred and 'prediction' in official_pred:
                        match_predictions[pred_type] = {
                            'prediction': official_pred['prediction'],
                            'confidence': official_pred.get('confidence', 0.5),
                            'probabilities': official_pred.get('probabilities', {}),
                            'total_matches': official_pred.get('total_matches', 0),
                        }
                
                # Extraer valores específicos para la plantilla
                both_teams_score_pct = match_predictions.get('both_teams_score', {}).get('prediction', 0.5) * 100
                probability = match_predictions.get('both_teams_score', {}).get('prediction', 0.5)
                
                # Agregar partido con todas las predicciones
                matches_with_predictions.append({
                    'league': league.name,
                    'home_team': home_team,
                    'away_team': away_team,
                    'date': colombia_time.strftime('%d/%m/%Y'),
                    'time': colombia_time.strftime('%H:%M'),
                    # Ambos marcan (para compatibilidad)
                    'prediction': both_teams_score_pct,
                    'probability': probability,
                    # Todas las predicciones
                    'predictions': match_predictions,
                })
                
                import logging
                logger_success = logging.getLogger('football_data')
                logger_success.info(f"✅ Partido agregado: {home_team} vs {away_team} - Ambos Marcan: {both_teams_score_pct:.1f}%")
                
            except Exception as e:
                # Continuar con el siguiente partido si hay error
                import logging
                logger_error = logging.getLogger('football_data')
                logger_error.error(f"❌ Error procesando partido {match_data.get('home_team', '?')} vs {match_data.get('away_team', '?')}: {e}", exc_info=True)
                continue
        
        # Log final
        import logging
        logger_final = logging.getLogger('football_data')
        logger_final.info(f"📊 Total partidos procesados: {len(matches_with_predictions)} de {len(upcoming_matches)} obtenidos")
        
        # Ordenar por fecha y hora
        matches_with_predictions.sort(key=lambda x: (x['date'], x['time']))
        
        context = {
            'matches': matches_with_predictions,
            'total_matches': len(matches_with_predictions),
            'updated_at': timezone.now(),
        }
        
        return render(request, 'football_data/analysis.html', context)