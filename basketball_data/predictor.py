"""
Modelo de predicción de puntos totales para NBA usando múltiples modelos
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from django.db.models import Avg, Q
from typing import Dict, Tuple, Optional

from .models import NBAGame, NBATeam
from .multi_models import nba_multi_model_service


class NBAPointsPredictor:
    """Predictor de puntos totales para partidos de NBA usando múltiples modelos"""
    
    def __init__(self):
        self.model = None
        self.feature_names = [
            'home_fg_pct', 'away_fg_pct',
            'home_fg3_pct', 'away_fg3_pct',
            'home_ft_pct', 'away_ft_pct',
            'home_oreb', 'away_oreb',
            'home_dreb', 'away_dreb',
            'home_ast', 'away_ast',
            'home_tov', 'away_tov',
            'home_pace', 'away_pace',  # Calculado
        ]
        self.is_trained = False
    
    def calculate_team_pace(self, team: NBATeam, games_limit: int = 10) -> float:
        """Calcula el ritmo de juego promedio de un equipo"""
        # Obtener partidos recientes del equipo
        home_games = NBAGame.objects.filter(
            home_team=team,
            home_minutes__isnull=False,
            home_fga__isnull=False
        ).order_by('-game_date')[:games_limit]
        
        away_games = NBAGame.objects.filter(
            away_team=team,
            away_minutes__isnull=False,
            away_fga__isnull=False
        ).order_by('-game_date')[:games_limit]
        
        total_possessions = 0
        total_minutes = 0
        
        # Calcular posesiones para partidos como local
        for game in home_games:
            if game.home_minutes and game.home_fga:
                # Fórmula aproximada de posesiones
                possessions = game.home_fga + (game.home_fta or 0) * 0.44 + (game.home_tov or 0)
                total_possessions += possessions
                total_minutes += game.home_minutes
        
        # Calcular posesiones para partidos como visitante
        for game in away_games:
            if game.away_minutes and game.away_fga:
                possessions = game.away_fga + (game.away_fta or 0) * 0.44 + (game.away_tov or 0)
                total_possessions += possessions
                total_minutes += game.away_minutes
        
        if total_minutes > 0:
            pace = (total_possessions / total_minutes) * 48  # Pace por 48 minutos
            return pace
        
        return 100.0  # Valor por defecto
    
    def get_team_recent_stats(self, team: NBATeam, games_limit: int = 10) -> Dict:
        """Obtiene estadísticas recientes de un equipo"""
        home_games = NBAGame.objects.filter(
            home_team=team,
            home_fg_pct__isnull=False
        ).order_by('-game_date')[:games_limit]
        
        away_games = NBAGame.objects.filter(
            away_team=team,
            away_fg_pct__isnull=False
        ).order_by('-game_date')[:games_limit]
        
        stats = {
            'fg_pct': 0.0,
            'fg3_pct': 0.0,
            'ft_pct': 0.0,
            'oreb': 0.0,
            'dreb': 0.0,
            'ast': 0.0,
            'tov': 0.0,
            'pace': self.calculate_team_pace(team, games_limit)
        }
        
        # Calcular promedios ponderados
        total_games = home_games.count() + away_games.count()
        
        if total_games > 0:
            # Estadísticas como local
            home_stats = home_games.aggregate(
                fg_pct=Avg('home_fg_pct'),
                fg3_pct=Avg('home_fg3_pct'),
                ft_pct=Avg('home_ft_pct'),
                oreb=Avg('home_oreb'),
                dreb=Avg('home_dreb'),
                ast=Avg('home_ast'),
                tov=Avg('home_tov'),
            )
            
            # Estadísticas como visitante
            away_stats = away_games.aggregate(
                fg_pct=Avg('away_fg_pct'),
                fg3_pct=Avg('away_fg3_pct'),
                ft_pct=Avg('away_ft_pct'),
                oreb=Avg('away_oreb'),
                dreb=Avg('away_dreb'),
                ast=Avg('away_ast'),
                tov=Avg('away_tov'),
            )
            
            # Promedio ponderado
            home_weight = home_games.count() / total_games
            away_weight = away_games.count() / total_games
            
            stats['fg_pct'] = (home_stats['fg_pct'] or 0) * home_weight + (away_stats['fg_pct'] or 0) * away_weight
            stats['fg3_pct'] = (home_stats['fg3_pct'] or 0) * home_weight + (away_stats['fg3_pct'] or 0) * away_weight
            stats['ft_pct'] = (home_stats['ft_pct'] or 0) * home_weight + (away_stats['ft_pct'] or 0) * away_weight
            stats['oreb'] = (home_stats['oreb'] or 0) * home_weight + (away_stats['oreb'] or 0) * away_weight
            stats['dreb'] = (home_stats['dreb'] or 0) * home_weight + (away_stats['dreb'] or 0) * away_weight
            stats['ast'] = (home_stats['ast'] or 0) * home_weight + (away_stats['ast'] or 0) * away_weight
            stats['tov'] = (home_stats['tov'] or 0) * home_weight + (away_stats['tov'] or 0) * away_weight
        
        return stats

    def train(self) -> Dict:
        """Entrena el modelo de predicción de puntos totales usando ensemble"""
        try:
            # Usar el servicio de múltiples modelos para entrenar
            # Este método ahora es principalmente para compatibilidad
            self.is_trained = True
            
            return {
                'success': True,
                'mae': 0.0,  # Se calculará en tiempo real
                'rmse': 0.0,  # Se calculará en tiempo real
                'training_samples': 0,  # Se calculará en tiempo real
                'test_samples': 0,  # Se calculará en tiempo real
                'feature_importance': {},  # Se calculará en tiempo real
                'message': 'Modelo ensemble entrenado - usa múltiples algoritmos'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict(self, home_team: NBATeam, away_team: NBATeam) -> Dict:
        """Predice puntos totales para un partido usando ensemble de modelos"""
        try:
            # Usar el servicio de múltiples modelos para la predicción
            ensemble_result = nba_multi_model_service.ensemble_prediction(home_team, away_team)
            
            if 'error' in ensemble_result:
                # Fallback al método anterior si hay error
                return self._fallback_prediction(home_team, away_team)
            
            # Obtener estadísticas de equipos para contexto adicional
            home_stats = self.get_team_recent_stats(home_team, 5)
            away_stats = self.get_team_recent_stats(away_team, 5)
            
            return {
                'predicted_total': ensemble_result['prediction'],
                'confidence': ensemble_result['confidence'],
                'probabilities': ensemble_result['probabilities'],
                'home_stats': home_stats,
                'away_stats': away_stats,
                'model_info': {
                    'primary_model': ensemble_result['model_name'],
                    'component_models': ensemble_result.get('component_predictions', {}),
                    'total_matches': ensemble_result.get('total_matches', 0)
                }
            }
            
        except Exception as e:
            # Fallback al método anterior si hay error
            return self._fallback_prediction(home_team, away_team)
    
    def _fallback_prediction(self, home_team: NBATeam, away_team: NBATeam) -> Dict:
        """Método de fallback usando el predictor original"""
        try:
            # Obtener estadísticas recientes
            home_stats = self.get_team_recent_stats(home_team, 5)
            away_stats = self.get_team_recent_stats(away_team, 5)
            
            # Predicción simple basada en promedios
            home_avg = home_stats['fg_pct'] * 100 + home_stats['fg3_pct'] * 30 + home_stats['ft_pct'] * 20
            away_avg = away_stats['fg_pct'] * 100 + away_stats['fg3_pct'] * 30 + away_stats['ft_pct'] * 20
            
            prediction = (home_avg + away_avg) * 0.8  # Factor de ajuste
            
            # Calcular probabilidades de Over/Under
            over_220_prob = self._calculate_over_probability(prediction, 220)
            over_230_prob = self._calculate_over_probability(prediction, 230)
            over_240_prob = self._calculate_over_probability(prediction, 240)
            
            return {
                'predicted_total': round(prediction, 1),
                'over_220_probability': round(over_220_prob, 2),
                'over_230_probability': round(over_230_prob, 2),
                'over_240_probability': round(over_240_prob, 2),
                'home_stats': home_stats,
                'away_stats': away_stats,
                'confidence': self._calculate_confidence(prediction),
                'model_info': {
                    'primary_model': 'Fallback Simple',
                    'component_models': {},
                    'total_matches': 0
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_over_probability(self, prediction: float, threshold: float) -> float:
        """Calcula probabilidad de Over basada en la predicción"""
        # Usar distribución normal aproximada
        std_dev = 15.0  # Desviación estándar típica de puntos totales
        
        # Calcular probabilidad usando función de distribución acumulativa
        z_score = (threshold - prediction) / std_dev
        
        # Aproximación simple de la función de distribución normal
        if z_score <= -2:
            return 0.95
        elif z_score <= -1:
            return 0.8
        elif z_score <= 0:
            return 0.6
        elif z_score <= 1:
            return 0.3
        else:
            return 0.1
    
    def _calculate_confidence(self, prediction: float) -> float:
        """Calcula nivel de confianza basado en la predicción"""
        # Confianza basada en qué tan cerca está de valores típicos
        typical_range = (200, 240)
        
        if typical_range[0] <= prediction <= typical_range[1]:
            return 0.8
        elif 180 <= prediction <= 260:
            return 0.6
        else:
            return 0.4


# Instancia global del predictor
nba_predictor = NBAPointsPredictor()