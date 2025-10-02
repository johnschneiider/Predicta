from django.contrib import admin
from .models import Sport, Bookmaker, Match, Odds, AverageOdds


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ('title', 'key', 'active', 'has_outrights', 'created_at')
    list_filter = ('active', 'has_outrights', 'created_at')
    search_fields = ('title', 'key')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Bookmaker)
class BookmakerAdmin(admin.ModelAdmin):
    list_display = ('title', 'key', 'active', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('title', 'key')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('home_team', 'away_team', 'sport', 'commence_time', 'created_at')
    list_filter = ('sport', 'commence_time', 'created_at')
    search_fields = ('home_team', 'away_team')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'commence_time'


@admin.register(Odds)
class OddsAdmin(admin.ModelAdmin):
    list_display = ('match', 'bookmaker', 'home_odds', 'draw_odds', 'away_odds', 'odds_timestamp')
    list_filter = ('bookmaker', 'odds_timestamp', 'match__sport')
    search_fields = ('match__home_team', 'match__away_team', 'bookmaker__title')
    readonly_fields = ('odds_timestamp', 'created_at')
    date_hierarchy = 'odds_timestamp'


@admin.register(AverageOdds)
class AverageOddsAdmin(admin.ModelAdmin):
    list_display = ('match', 'avg_home_odds', 'avg_draw_odds', 'avg_away_odds', 'bookmaker_count', 'calculated_at')
    list_filter = ('calculated_at', 'match__sport')
    search_fields = ('match__home_team', 'match__away_team')
    readonly_fields = ('calculated_at',)
    date_hierarchy = 'calculated_at'
