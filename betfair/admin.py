from django.contrib import admin
from .models import (
    BetfairEventType, BetfairEvent, BetfairMarket, 
    BetfairRunner, BetfairOrder, BetfairAccount
)


@admin.register(BetfairEventType)
class BetfairEventTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type_id', 'market_count', 'active', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('name', 'event_type_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BetfairEvent)
class BetfairEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type', 'country_code', 'open_date', 'market_count', 'created_at')
    list_filter = ('event_type', 'country_code', 'open_date', 'created_at')
    search_fields = ('name', 'event_id')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'open_date'


@admin.register(BetfairMarket)
class BetfairMarketAdmin(admin.ModelAdmin):
    list_display = ('market_name', 'event', 'market_start_time', 'status', 'total_matched', 'created_at')
    list_filter = ('status', 'market_start_time', 'created_at', 'event__event_type')
    search_fields = ('market_name', 'market_id', 'event__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'market_start_time'


@admin.register(BetfairRunner)
class BetfairRunnerAdmin(admin.ModelAdmin):
    list_display = ('runner_name', 'market', 'selection_id', 'status', 'last_price_traded', 'last_updated')
    list_filter = ('status', 'last_updated', 'market__event__event_type')
    search_fields = ('runner_name', 'selection_id', 'market__market_name')
    readonly_fields = ('last_updated', 'created_at')


@admin.register(BetfairOrder)
class BetfairOrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'market', 'runner', 'side', 'price', 'size', 'status', 'placed_at')
    list_filter = ('side', 'order_type', 'status', 'placed_at')
    search_fields = ('order_id', 'market__market_name', 'runner__runner_name')
    readonly_fields = ('placed_at', 'settled_at')
    date_hierarchy = 'placed_at'


@admin.register(BetfairAccount)
class BetfairAccountAdmin(admin.ModelAdmin):
    list_display = ('username', 'available_to_bet_balance', 'exposure', 'sandbox', 'active', 'last_updated')
    list_filter = ('sandbox', 'active', 'last_updated')
    search_fields = ('username',)
    readonly_fields = ('last_updated', 'created_at')
