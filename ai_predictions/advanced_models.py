"""
Modelos estadísticos avanzados para predicciones de fútbol
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from sklearn.linear_model import Ridge, LinearRegression, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, RobustScaler
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from django.utils import timezone
from django.db import models
from football_data.models import Match, League
from .models import PredictionModel, TeamStats, PredictionResult

logger = logging.getLogger('ai_predictions')


class AdvancedStatisticalModels:
    """Modelos estadísticos avanzados para predicciones de fútbol"""
    
    def __init__(self):
        self.scaler = RobustScaler()  # Más robusto que StandardScaler
        self.models_cache = {}
    
    def get_team_advanced_stats(self, team_name: str, league: League, is_home: bool = True) -> Dict:
        """Obtiene estadísticas avanzadas de un equipo"""
        try:
            # Ventana temporal más amplia para más datos
            cutoff_date = timezone.now().date() - timedelta(days=730)  # 2 años
            
            if is_home:
                matches = Match.objects.filter(
                    league=league,
                    home_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:50]  # Más partidos
                shots_data = [m.hs for m in matches if m.hs is not None]
                goals_data = [m.fthg for m in matches if m.fthg is not None]
                shots_on_target = [m.hst for m in matches if m.hst is not None]
            else:
                matches = Match.objects.filter(
                    league=league,
                    away_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:50]
                shots_data = [m.as_field for m in matches if m.as_field is not None]
                goals_data = [m.ftag for m in matches if m.ftag is not None]
                shots_on_target = [m.ast for m in matches if m.ast is not None]
            
            if not shots_data:
                return self._default_team_stats()
            
            # Estadísticas avanzadas
            shots_array = np.array(shots_data)
            goals_array = np.array(goals_data)
            sot_array = np.array(shots_on_target) if shots_on_target else np.array([])
            
            # Calcular métricas estadísticas avanzadas
            stats_dict = {
                'lambda_poisson': np.mean(shots_array),
                'lambda_goals': np.mean(goals_array),
                'std_shots': np.std(shots_array),
                'std_goals': np.std(goals_array),
                'skewness': stats.skew(shots_array),
                'kurtosis': stats.kurtosis(shots_array),
                'median_shots': np.median(shots_array),
                'q25_shots': np.percentile(shots_array, 25),
                'q75_shots': np.percentile(shots_array, 75),
                'iqr_shots': np.percentile(shots_array, 75) - np.percentile(shots_array, 25),
                'matches_count': len(shots_array),
                'recent_trend': self._calculate_trend(shots_array),
                'consistency': 1 / (1 + np.std(shots_array) / np.mean(shots_array)) if np.mean(shots_array) > 0 else 0,
                'efficiency': np.mean(goals_array) / np.mean(shots_array) if np.mean(shots_array) > 0 else 0,
                'sot_rate': np.mean(sot_array) / np.mean(shots_array) if len(sot_array) > 0 and np.mean(shots_array) > 0 else 0,
                'form_momentum': self._calculate_momentum(shots_array),
                'home_advantage_factor': 1.15 if is_home else 0.9
            }
            
            return stats_dict
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas avanzadas de {team_name}: {e}")
            return self._default_team_stats()
    
    def _default_team_stats(self) -> Dict:
        """Estadísticas por defecto cuando no hay datos"""
        return {
            'lambda_poisson': 12.0,
            'lambda_goals': 1.5,
            'std_shots': 3.0,
            'std_goals': 1.0,
            'skewness': 0.0,
            'kurtosis': 0.0,
            'median_shots': 12.0,
            'q25_shots': 9.0,
            'q75_shots': 15.0,
            'iqr_shots': 6.0,
            'matches_count': 0,
            'recent_trend': 0.0,
            'consistency': 0.5,
            'efficiency': 0.12,
            'sot_rate': 0.35,
            'form_momentum': 0.0,
            'home_advantage_factor': 1.0
        }
    
    def _calculate_trend(self, data: np.ndarray) -> float:
        """Calcula la tendencia reciente usando regresión lineal"""
        if len(data) < 3:
            return 0.0
        
        x = np.arange(len(data))
        slope, _, _, _, _ = stats.linregress(x, data)
        return slope
    
    def _calculate_momentum(self, data: np.ndarray) -> float:
        """Calcula el momentum basado en los últimos partidos"""
        if len(data) < 5:
            return 0.0
        
        recent = data[:5]  # Últimos 5 partidos
        older = data[5:10] if len(data) >= 10 else data[5:]
        
        if len(older) == 0:
            return 0.0
        
        return np.mean(recent) - np.mean(older)
    
    def enhanced_poisson_model(self, home_team: str, away_team: str, league: League, 
                              prediction_type: str = 'shots_total') -> Dict:
        """Modelo de Poisson mejorado con factores contextuales"""
        try:
            home_stats = self.get_team_advanced_stats(home_team, league, True)
            away_stats = self.get_team_advanced_stats(away_team, league, False)
            
            # Calcular lambda base
            if prediction_type == 'shots_total':
                lambda_home = home_stats['lambda_poisson'] * home_stats['home_advantage_factor']
                lambda_away = away_stats['lambda_poisson'] * away_stats['home_advantage_factor']
                lambda_combined = lambda_home + lambda_away
            elif prediction_type == 'shots_home':
                lambda_combined = home_stats['lambda_poisson'] * home_stats['home_advantage_factor']
            elif prediction_type == 'shots_away':
                lambda_combined = away_stats['lambda_poisson'] * away_stats['home_advantage_factor']
            else:
                lambda_combined = (home_stats['lambda_poisson'] + away_stats['lambda_poisson']) / 2
            
            # Aplicar factores de ajuste basados en estadísticas avanzadas
            consistency_factor = (home_stats['consistency'] + away_stats['consistency']) / 2
            momentum_factor = 1 + (home_stats['form_momentum'] + away_stats['form_momentum']) / 20
            trend_factor = 1 + (home_stats['recent_trend'] + away_stats['recent_trend']) / 10
            
            # Lambda ajustado
            lambda_adjusted = lambda_combined * consistency_factor * momentum_factor * trend_factor
            
            # Predicción principal
            prediction = lambda_adjusted
            
            # Calcular probabilidades usando distribución de Poisson
            probabilities = {}
            for threshold in [10, 15, 20, 25, 30]:
                prob = 1 - stats.poisson.cdf(threshold, lambda_adjusted)
                probabilities[f'over_{threshold}'] = max(0, min(1, prob))
            
            # Confianza basada en cantidad y calidad de datos
            total_matches = home_stats['matches_count'] + away_stats['matches_count']
            data_quality = min(1.0, total_matches / 30)  # Máximo con 30+ partidos
            consistency_score = (home_stats['consistency'] + away_stats['consistency']) / 2
            confidence = data_quality * consistency_score
            
            return {
                'model_name': 'Enhanced Poisson',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'lambda_home': home_stats['lambda_poisson'],
                'lambda_away': away_stats['lambda_poisson'],
                'total_matches': total_matches,
                'consistency_factor': consistency_factor,
                'momentum_factor': momentum_factor
            }
            
        except Exception as e:
            logger.error(f"Error en modelo Poisson mejorado: {e}")
            return self._fallback_prediction('Enhanced Poisson', 12.0, 0.1)
    
    def bayesian_model(self, home_team: str, away_team: str, league: League, 
                      prediction_type: str = 'shots_total') -> Dict:
        """Modelo bayesiano para predicciones más robustas"""
        try:
            home_stats = self.get_team_advanced_stats(home_team, league, True)
            away_stats = self.get_team_advanced_stats(away_team, league, False)
            
            # Prior bayesiano basado en estadísticas de la liga
            league_stats = self._get_league_stats(league)
            
            # Likelihood basado en estadísticas del equipo
            if prediction_type == 'shots_total':
                home_lambda = home_stats['lambda_poisson']
                away_lambda = away_stats['lambda_poisson']
                combined_lambda = home_lambda + away_lambda
            elif prediction_type == 'shots_home':
                combined_lambda = home_stats['lambda_poisson']
            elif prediction_type == 'shots_away':
                combined_lambda = away_stats['lambda_poisson']
            else:
                combined_lambda = (home_stats['lambda_poisson'] + away_stats['lambda_poisson']) / 2
            
            # Prior bayesiano (distribución gamma conjugada)
            alpha_prior = league_stats['alpha']
            beta_prior = league_stats['beta']
            
            # Posterior bayesiano
            alpha_posterior = alpha_prior + combined_lambda
            beta_posterior = beta_prior + 1
            
            # Predicción bayesiana (media de la distribución posterior)
            prediction = alpha_posterior / beta_posterior
            
            # Calcular probabilidades usando distribución gamma
            probabilities = {}
            for threshold in [10, 15, 20, 25, 30]:
                prob = 1 - stats.gamma.cdf(threshold, alpha_posterior, scale=1/beta_posterior)
                probabilities[f'over_{threshold}'] = max(0, min(1, prob))
            
            # Confianza basada en la varianza posterior
            posterior_variance = alpha_posterior / (beta_posterior ** 2)
            confidence = max(0.1, min(0.95, 1 - posterior_variance / prediction))
            
            return {
                'model_name': 'Bayesian',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'alpha_posterior': alpha_posterior,
                'beta_posterior': beta_posterior,
                'total_matches': home_stats['matches_count'] + away_stats['matches_count']
            }
            
        except Exception as e:
            logger.error(f"Error en modelo bayesiano: {e}")
            return self._fallback_prediction('Bayesian', 12.0, 0.1)
    
    def ensemble_model(self, home_team: str, away_team: str, league: League, 
                      prediction_type: str = 'shots_total') -> Dict:
        """Modelo ensemble que combina múltiples enfoques"""
        try:
            # Obtener predicciones de múltiples modelos
            poisson_pred = self.enhanced_poisson_model(home_team, away_team, league, prediction_type)
            bayesian_pred = self.bayesian_model(home_team, away_team, league, prediction_type)
            
            # Calcular pesos basados en confianza
            poisson_weight = poisson_pred['confidence']
            bayesian_weight = bayesian_pred['confidence']
            total_weight = poisson_weight + bayesian_weight
            
            if total_weight == 0:
                poisson_weight = bayesian_weight = 0.5
                total_weight = 1.0
            
            poisson_weight /= total_weight
            bayesian_weight /= total_weight
            
            # Predicción ensemble
            prediction = (poisson_pred['prediction'] * poisson_weight + 
                         bayesian_pred['prediction'] * bayesian_weight)
            
            # Confianza ensemble
            confidence = (poisson_pred['confidence'] + bayesian_pred['confidence']) / 2
            
            # Probabilidades ensemble
            probabilities = {}
            for threshold in [10, 15, 20, 25, 30]:
                poisson_prob = poisson_pred['probabilities'].get(f'over_{threshold}', 0.5)
                bayesian_prob = bayesian_pred['probabilities'].get(f'over_{threshold}', 0.5)
                ensemble_prob = (poisson_prob * poisson_weight + 
                               bayesian_prob * bayesian_weight)
                probabilities[f'over_{threshold}'] = ensemble_prob
            
            return {
                'model_name': 'Ensemble',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'poisson_weight': poisson_weight,
                'bayesian_weight': bayesian_weight,
                'total_matches': max(poisson_pred.get('total_matches', 0), 
                                   bayesian_pred.get('total_matches', 0))
            }
            
        except Exception as e:
            logger.error(f"Error en modelo ensemble: {e}")
            return self._fallback_prediction('Ensemble', 12.0, 0.1)
    
    def _get_league_stats(self, league: League) -> Dict:
        """Obtiene estadísticas de la liga para priors bayesianos"""
        try:
            matches = Match.objects.filter(league=league).exclude(
                models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
            ).order_by('-date')[:100]
            
            if not matches:
                return {'alpha': 2.0, 'beta': 0.2}
            
            shots_data = []
            for match in matches:
                shots_data.append((match.hs or 0) + (match.as_field or 0))
            
            shots_array = np.array(shots_data)
            mean_shots = np.mean(shots_array)
            var_shots = np.var(shots_array)
            
            # Parámetros de la distribución gamma
            alpha = (mean_shots ** 2) / var_shots if var_shots > 0 else 2.0
            beta = mean_shots / var_shots if var_shots > 0 else 0.2
            
            return {'alpha': alpha, 'beta': beta}
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de liga: {e}")
            return {'alpha': 2.0, 'beta': 0.2}
    
    def get_all_advanced_predictions(self, home_team: str, away_team: str, league: League, 
                                   prediction_type: str = 'shots_total') -> List[Dict]:
        """Obtiene predicciones de todos los modelos avanzados"""
        predictions = []
        
        # Modelo Poisson mejorado
        poisson_pred = self.enhanced_poisson_model(home_team, away_team, league, prediction_type)
        predictions.append(poisson_pred)
        
        # Modelo bayesiano
        bayesian_pred = self.bayesian_model(home_team, away_team, league, prediction_type)
        predictions.append(bayesian_pred)
        
        # Modelo ensemble
        ensemble_pred = self.ensemble_model(home_team, away_team, league, prediction_type)
        predictions.append(ensemble_pred)
        
        return predictions
    
    def _fallback_prediction(self, model_name: str, prediction: float, confidence: float) -> Dict:
        """Predicción de fallback para errores"""
        return {
            'model_name': model_name,
            'prediction': prediction,
            'confidence': confidence,
            'probabilities': {'over_10': 0.5, 'over_15': 0.3, 'over_20': 0.1, 'over_25': 0.05, 'over_30': 0.02},
            'error': 'Modelo no disponible'
        }
