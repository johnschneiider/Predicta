"""
Configuración del admin para football_data
"""

from django.contrib import admin
from .models import League, Match, ExcelFile


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'season', 'active', 'created_at']
    list_filter = ['country', 'season', 'active', 'created_at']
    search_fields = ['name', 'country', 'season']
    ordering = ['name', 'season']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'country', 'season', 'active')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['home_team', 'away_team', 'league', 'date', 'ftr', 'total_goals_display']
    list_filter = ['league', 'date', 'ftr', 'league__season']
    search_fields = ['home_team', 'away_team', 'league__name']
    ordering = ['-date', 'home_team']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Información del Partido', {
            'fields': ('league', 'date', 'time', 'home_team', 'away_team')
        }),
        ('Resultados', {
            'fields': ('fthg', 'ftag', 'ftr', 'hthg', 'htag', 'htr')
        }),
        ('Estadísticas', {
            'fields': ('hs', 'as_field', 'hst', 'ast', 'hf', 'af', 'hc', 'ac', 'hy', 'ay', 'hr', 'ar'),
            'classes': ('collapse',)
        }),
        ('Cuotas Bet365', {
            'fields': ('b365h', 'b365d', 'b365a'),
            'classes': ('collapse',)
        }),
        ('Cuotas Blue Square', {
            'fields': ('bwh', 'bwd', 'bwa'),
            'classes': ('collapse',)
        }),
        ('Cuotas Interwetten', {
            'fields': ('iwh', 'iwd', 'iwa'),
            'classes': ('collapse',)
        }),
        ('Cuotas Pinnacle', {
            'fields': ('psh', 'psd', 'psa'),
            'classes': ('collapse',)
        }),
        ('Cuotas William Hill', {
            'fields': ('whh', 'whd', 'wha'),
            'classes': ('collapse',)
        }),
        ('Cuotas VC Bet', {
            'fields': ('vch', 'vcd', 'vca'),
            'classes': ('collapse',)
        }),
        ('Análisis de Cuotas', {
            'fields': ('maxh', 'maxd', 'maxa', 'avgh', 'avgd', 'avga'),
            'classes': ('collapse',)
        }),
        ('Mercados de Goles', {
            'fields': ('b365_over_25', 'b365_under_25', 'p_over_25', 'p_under_25', 
                      'max_over_25', 'max_under_25', 'avg_over_25', 'avg_under_25'),
            'classes': ('collapse',)
        }),
        ('Handicap Asiático', {
            'fields': ('ahh', 'b365ahh', 'b365aha', 'pahh', 'paha', 
                      'maxahh', 'maxaha', 'avgahh', 'avgaha'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def total_goals_display(self, obj):
        """Mostrar total de goles"""
        if obj.fthg is not None and obj.ftag is not None:
            return f"{obj.fthg}-{obj.ftag}"
        return "-"
    total_goals_display.short_description = "Goles"


@admin.register(ExcelFile)
class ExcelFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'league', 'imported_rows', 'failed_rows', 'success_rate_display', 'imported_at']
    list_filter = ['league', 'imported_at']
    search_fields = ['name', 'league__name']
    ordering = ['-imported_at']
    date_hierarchy = 'imported_at'
    
    fieldsets = (
        ('Archivo', {
            'fields': ('name', 'file', 'file_path', 'league')
        }),
        ('Estadísticas de Importación', {
            'fields': ('total_rows', 'imported_rows', 'failed_rows', 'file_size')
        }),
        ('Metadatos', {
            'fields': ('imported_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['imported_at', 'file_size']
    
    def success_rate_display(self, obj):
        """Mostrar tasa de éxito"""
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = "Tasa de Éxito"