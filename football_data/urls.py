"""
URLs para la aplicación football_data
"""

from django.urls import path
from . import views
from .views_shots import ShotsAnalysisView

app_name = 'football_data'

urlpatterns = [
    path('', views.FootballDataDashboardView.as_view(), name='dashboard'),
    path('leagues/', views.LeaguesListView.as_view(), name='leagues_list'),
    path('leagues/<int:league_id>/', views.LeagueDetailView.as_view(), name='league_detail'),
    path('matches/', views.MatchesListView.as_view(), name='matches_list'),
    path('matches/<int:match_id>/', views.MatchDetailView.as_view(), name='match_detail'),
    path('import/', views.ImportView.as_view(), name='import'),
    path('import/delete/<int:file_id>/', views.DeleteFileView.as_view(), name='delete_file'),
    path('import/delete-all/', views.DeleteAllFilesView.as_view(), name='delete_all_files'),
    path('import/ajax/', views.ImportAjaxView.as_view(), name='import_ajax'),
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    path('markets/', views.MarketsView.as_view(), name='markets'),
    path('shots/', ShotsAnalysisView.as_view(), name='shots'),
    path('league-data/', views.LeagueDataTableView.as_view(), name='league_data_table'),
    path('analysis/', views.AnalysisView.as_view(), name='analysis'),
]
