"""
Configuración del admin para basketball_data
"""

from django.contrib import admin
from .models import NBATeam, NBAPlayer, NBAGame, NBAPrediction


@admin.register(NBATeam)
class NBATeamAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'abbreviation', 'city', 'state', 'year_founded']
    list_filter = ['state', 'year_founded']
    search_fields = ['full_name', 'abbreviation', 'city']
    ordering = ['full_name']


@admin.register(NBAPlayer)
class NBAPlayerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'first_name', 'last_name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['full_name', 'first_name', 'last_name']
    ordering = ['full_name']


@admin.register(NBAGame)
class NBAGameAdmin(admin.ModelAdmin):
    list_display = ['game_date', 'home_team', 'away_team', 'total_points', 'home_win']
    list_filter = ['game_date', 'season_type', 'home_team', 'away_team']
    search_fields = ['nba_game_id', 'home_team__full_name', 'away_team__full_name']
    ordering = ['-game_date']
    date_hierarchy = 'game_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nba_game_id', 'season_id', 'game_date', 'season_type', 'home_team', 'away_team')
        }),
        ('Resultado', {
            'fields': ('home_win', 'home_points', 'away_points', 'total_points')
        }),
        ('Estadísticas Local', {
            'fields': ('home_minutes', 'home_fgm', 'home_fga', 'home_fg_pct', 'home_fg3m', 'home_fg3a', 'home_fg3_pct', 'home_ftm', 'home_fta', 'home_ft_pct'),
            'classes': ('collapse',)
        }),
        ('Estadísticas Visitante', {
            'fields': ('away_minutes', 'away_fgm', 'away_fga', 'away_fg_pct', 'away_fg3m', 'away_fg3a', 'away_fg3_pct', 'away_ftm', 'away_fta', 'away_ft_pct'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NBAPrediction)
class NBAPredictionAdmin(admin.ModelAdmin):
    list_display = ['game', 'predicted_total_points', 'confidence', 'model_name', 'created_at']
    list_filter = ['model_name', 'created_at']
    search_fields = ['game__nba_game_id', 'model_name']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'