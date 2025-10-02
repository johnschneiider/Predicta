from django.contrib import admin
from .models import (
    ArbitrageOpportunity, BettingStrategy, BotSession, 
    BotCycle, BotConfiguration, Alert
)


@admin.register(ArbitrageOpportunity)
class ArbitrageOpportunityAdmin(admin.ModelAdmin):
    list_display = ('match', 'selection', 'odds_api_odds', 'betfair_odds', 'edge', 'confidence_score', 'acted_upon', 'detected_at')
    list_filter = ('selection', 'acted_upon', 'detected_at', 'match__sport')
    search_fields = ('match__home_team', 'match__away_team')
    readonly_fields = ('detected_at',)
    date_hierarchy = 'detected_at'
    
    def edge(self, obj):
        return f"{obj.edge:.2%}"


@admin.register(BettingStrategy)
class BettingStrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_edge', 'min_confidence', 'min_stake', 'max_stake', 'max_daily_bets', 'active', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    def min_edge(self, obj):
        return f"{obj.min_edge:.2%}"


@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'strategy', 'status', 'cycles_executed', 'opportunities_found', 'bets_placed', 'total_profit_loss', 'started_at')
    list_filter = ('status', 'sandbox_mode', 'strategy', 'started_at')
    search_fields = ('session_id', 'strategy__name')
    readonly_fields = ('started_at', 'ended_at', 'last_cycle_at')
    date_hierarchy = 'started_at'


@admin.register(BotCycle)
class BotCycleAdmin(admin.ModelAdmin):
    list_display = ('session', 'cycle_number', 'matches_analyzed', 'opportunities_found', 'bets_placed', 'success_status', 'duration_seconds', 'started_at')
    list_filter = ('success_status', 'started_at', 'session__strategy')
    search_fields = ('session__session_id',)
    readonly_fields = ('started_at', 'completed_at')
    date_hierarchy = 'started_at'


@admin.register(BotConfiguration)
class BotConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'value_type', 'active', 'updated_at')
    list_filter = ('value_type', 'active', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'read', 'session', 'created_at')
    list_filter = ('level', 'read', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
