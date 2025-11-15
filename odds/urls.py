"""
URLs para la aplicación odds
"""

from django.urls import path
from . import views

app_name = 'odds'

urlpatterns = [
    path('', views.OddsDashboardView.as_view(), name='dashboard'),
    path('matches/', views.UpcomingMatchesView.as_view(), name='matches_list'),
    path('matches-local/', views.MatchesListView.as_view(), name='matches_local'),
    path('matches/<str:match_id>/', views.MatchDetailView.as_view(), name='match_detail'),
    path('live/', views.LiveOddsView.as_view(), name='live_odds'),
    path('upcoming/', views.UpcomingMatchesView.as_view(), name='upcoming_matches'),
    path('sports/', views.SportsListView.as_view(), name='sports_list'),
    path('sync/', views.SyncOddsView.as_view(), name='sync_odds'),
]
