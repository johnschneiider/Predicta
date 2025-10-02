"""
Servicios para múltiples modelos estadísticos de predicción
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from django.utils import timezone
from django.db import models
from football_data.models import Match, League
from .models import PredictionModel, TeamStats, PredictionResult

logger = logging.getLogger('ai_predictions')


class MultiModelPredictionService:
    """Servicio para predicciones con múltiples modelos estadísticos"""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def get_team_stats_for_poisson(self, team_name: str, league: League, is_home: bool = True) -> Dict:
        """Obtiene estadísticas específicas para modelo de Poisson"""
        try:
            # Obtener partidos recientes (último año)
            cutoff_date = timezone.now().date() - timedelta(days=365)
            
            if is_home:
                matches = Match.objects.filter(
                    league=league,
                    home_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:30]
                shots_data = [m.hs for m in matches if m.hs is not None]
                goals_data = [m.fthg for m in matches if m.fthg is not None]
            else:
                matches = Match.objects.filter(
                    league=league,
                    away_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:30]
                shots_data = [m.as_field for m in matches if m.as_field is not None]
                goals_data = [m.ftag for m in matches if m.ftag is not None]
            
            if not shots_data:
                return {'lambda': 12.0, 'matches': 0}
            
            # Calcular lambda para distribución de Poisson
            lambda_value = np.mean(shots_data)
            
            return {
                'lambda': lambda_value,
                'matches': len(shots_data),
                'std': np.std(shots_data) if len(shots_data) > 1 else 0,
                'goals_avg': np.mean(goals_data) if goals_data else 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas Poisson para {team_name}: {e}")
            return {'lambda': 12.0, 'matches': 0, 'std': 0, 'goals_avg': 0}
    
    def poisson_model_prediction(self, home_team: str, away_team: str, league: League, 
                                prediction_type: str = 'shots_total') -> Dict:
        """Predicción usando modelo de Poisson"""
        try:
            home_stats = self.get_team_stats_for_poisson(home_team, league, is_home=True)
            away_stats = self.get_team_stats_for_poisson(away_team, league, is_home=False)
            
            # Calcular lambda combinado
            if prediction_type == 'shots_total':
                lambda_home = home_stats['lambda']
                lambda_away = away_stats['lambda']
                lambda_combined = lambda_home + lambda_away
            elif prediction_type == 'shots_home':
                lambda_combined = home_stats['lambda'] * 1.1  # Ventaja de local
            elif prediction_type == 'shots_away':
                lambda_combined = away_stats['lambda'] * 0.9  # Desventaja de visitante
            else:
                lambda_combined = (home_stats['lambda'] + away_stats['lambda']) / 2
            
            # Predicción principal
            prediction = lambda_combined
            
            # Calcular probabilidades para diferentes rangos
            probabilities = {}
            for threshold in [10, 15, 20, 25, 30]:
                prob = 1 - stats.poisson.cdf(threshold, lambda_combined)
                probabilities[f'over_{threshold}'] = max(0, min(1, prob))
            
            # Calcular confianza basada en cantidad de datos
            total_matches = home_stats['matches'] + away_stats['matches']
            confidence = min(0.95, total_matches / 50)  # Máximo 95% con 50+ partidos
            
            return {
                'model_name': 'Poisson',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'lambda_home': home_stats['lambda'],
                'lambda_away': away_stats['lambda'],
                'total_matches': total_matches
            }
            
        except Exception as e:
            logger.error(f"Error en modelo Poisson: {e}")
            return {
                'model_name': 'Poisson',
                'prediction': 12.0,
                'confidence': 0.1,
                'probabilities': {'over_10': 0.5, 'over_15': 0.3, 'over_20': 0.1, 'over_25': 0.05, 'over_30': 0.02},
                'error': str(e)
            }
    
    def linear_regression_model(self, home_team: str, away_team: str, league: League, 
                               prediction_type: str = 'shots_total') -> Dict:
        """Modelo de regresión lineal simple"""
        try:
            # Obtener datos históricos
            matches = Match.objects.filter(league=league).exclude(
                models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
            ).order_by('-date')[:200]
            
            if len(matches) < 20:
                return self._fallback_prediction('Linear Regression', 12.0, 0.1)
            
            # Preparar datos
            X = []
            y = []
            
            for match in matches:
                home_stats = self.get_team_stats_for_poisson(match.home_team, league, True)
                away_stats = self.get_team_stats_for_poisson(match.away_team, league, False)
                
                X.append([home_stats['lambda'], away_stats['lambda'], 1.0])  # 1.0 = ventaja local
                
                if prediction_type == 'shots_total':
                    target = (match.hs or 0) + (match.as_field or 0)
                elif prediction_type == 'shots_home':
                    target = match.hs or 0
                elif prediction_type == 'shots_away':
                    target = match.as_field or 0
                else:
                    target = (match.hs or 0) + (match.as_field or 0)
                
                y.append(target)
            
            X = np.array(X)
            y = np.array(y)
            
            # Entrenar modelo
            model = LinearRegression()
            model.fit(X, y)
            
            # Predicción
            home_stats = self.get_team_stats_for_poisson(home_team, league, True)
            away_stats = self.get_team_stats_for_poisson(away_team, league, False)
            features = np.array([[home_stats['lambda'], away_stats['lambda'], 1.0]])
            
            prediction = model.predict(features)[0]
            prediction = max(0, min(prediction, 50))  # Límites realistas
            
            # Calcular confianza
            r2 = model.score(X, y)
            confidence = max(0.1, min(0.9, r2))
            
            # Probabilidades simples
            probabilities = self._calculate_simple_probabilities(prediction)
            
            return {
                'model_name': 'Linear Regression',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'r2_score': r2,
                'total_matches': len(matches)
            }
            
        except Exception as e:
            logger.error(f"Error en modelo Linear Regression: {e}")
            return self._fallback_prediction('Linear Regression', 12.0, 0.1)
    
    def historical_average_model(self, home_team: str, away_team: str, league: League, 
                                prediction_type: str = 'shots_total') -> Dict:
        """Modelo basado en promedios históricos ponderados"""
        try:
            # Obtener estadísticas de equipos
            home_stats = self.get_team_stats_for_poisson(home_team, league, True)
            away_stats = self.get_team_stats_for_poisson(away_team, league, False)
            
            # Calcular predicción basada en promedios
            if prediction_type == 'shots_total':
                prediction = (home_stats['lambda'] + away_stats['lambda']) * 1.05  # Factor de ajuste
            elif prediction_type == 'shots_home':
                prediction = home_stats['lambda'] * 1.15  # Ventaja de local
            elif prediction_type == 'shots_away':
                prediction = away_stats['lambda'] * 0.9   # Desventaja de visitante
            else:
                prediction = (home_stats['lambda'] + away_stats['lambda']) / 2
            
            # Calcular confianza basada en cantidad de datos
            total_matches = home_stats['matches'] + away_stats['matches']
            confidence = min(0.8, total_matches / 40)
            
            # Probabilidades basadas en distribución normal
            probabilities = self._calculate_normal_probabilities(prediction, 3.0)
            
            return {
                'model_name': 'Historical Average',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'home_avg': home_stats['lambda'],
                'away_avg': away_stats['lambda'],
                'total_matches': total_matches
            }
            
        except Exception as e:
            logger.error(f"Error en modelo Historical Average: {e}")
            return self._fallback_prediction('Historical Average', 12.0, 0.1)
    
    def backtest_models(self, league: League, prediction_type: str = 'shots_total') -> Dict:
        """Realiza backtesting de todos los modelos (versión optimizada)"""
        try:
            # Obtener datos históricos ordenados por fecha (limitado para evitar problemas de memoria)
            matches = Match.objects.filter(league=league).exclude(
                models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
            ).order_by('date')[:100]  # Limitar a 100 partidos para evitar problemas
            
            if len(matches) < 20:
                return {'error': 'Datos insuficientes para backtesting'}
            
            # Dividir en entrenamiento y prueba (80/20)
            split_point = int(len(matches) * 0.8)
            test_matches = matches[split_point:]
            
            results = {}
            
            # Backtest Poisson (simplificado)
            poisson_errors = []
            for match in test_matches[:10]:  # Limitar a 10 pruebas
                try:
                    pred = self.poisson_model_prediction(
                        match.home_team, match.away_team, league, prediction_type
                    )
                    actual = (match.hs or 0) + (match.as_field or 0) if prediction_type == 'shots_total' else (match.hs or 0)
                    error = abs(pred['prediction'] - actual)
                    poisson_errors.append(error)
                except:
                    continue
            
            if poisson_errors:
                results['Poisson'] = {
                    'mae': np.mean(poisson_errors),
                    'accuracy_2': np.mean([e <= 2 for e in poisson_errors]),
                    'accuracy_3': np.mean([e <= 3 for e in poisson_errors]),
                    'total_tests': len(poisson_errors)
                }
            
            # Backtest Linear Regression (simplificado)
            lr_errors = []
            for match in test_matches[:10]:  # Limitar a 10 pruebas
                try:
                    pred = self.linear_regression_model(
                        match.home_team, match.away_team, league, prediction_type
                    )
                    actual = (match.hs or 0) + (match.as_field or 0) if prediction_type == 'shots_total' else (match.hs or 0)
                    error = abs(pred['prediction'] - actual)
                    lr_errors.append(error)
                except:
                    continue
            
            if lr_errors:
                results['Linear Regression'] = {
                    'mae': np.mean(lr_errors),
                    'accuracy_2': np.mean([e <= 2 for e in lr_errors]),
                    'accuracy_3': np.mean([e <= 3 for e in lr_errors]),
                    'total_tests': len(lr_errors)
                }
            
            # Backtest Historical Average (simplificado)
            ha_errors = []
            for match in test_matches[:10]:  # Limitar a 10 pruebas
                try:
                    pred = self.historical_average_model(
                        match.home_team, match.away_team, league, prediction_type
                    )
                    actual = (match.hs or 0) + (match.as_field or 0) if prediction_type == 'shots_total' else (match.hs or 0)
                    error = abs(pred['prediction'] - actual)
                    ha_errors.append(error)
                except:
                    continue
            
            if ha_errors:
                results['Historical Average'] = {
                    'mae': np.mean(ha_errors),
                    'accuracy_2': np.mean([e <= 2 for e in ha_errors]),
                    'accuracy_3': np.mean([e <= 3 for e in ha_errors]),
                    'total_tests': len(ha_errors)
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error en backtesting: {e}")
            return {'error': str(e)}
    
    def get_all_predictions(self, home_team: str, away_team: str, league: League, 
                           prediction_type: str = 'shots_total') -> List[Dict]:
        """Obtiene predicciones de todos los modelos"""
        predictions = []
        
        # Modelo Poisson
        poisson_pred = self.poisson_model_prediction(home_team, away_team, league, prediction_type)
        predictions.append(poisson_pred)
        
        # Modelo Linear Regression
        lr_pred = self.linear_regression_model(home_team, away_team, league, prediction_type)
        predictions.append(lr_pred)
        
        # Modelo Historical Average
        ha_pred = self.historical_average_model(home_team, away_team, league, prediction_type)
        predictions.append(ha_pred)
        
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
    
    def _calculate_simple_probabilities(self, prediction: float) -> Dict:
        """Calcula probabilidades simples basadas en la predicción"""
        probabilities = {}
        for threshold in [10, 15, 20, 25, 30]:
            if prediction > threshold:
                prob = min(0.9, 0.5 + (prediction - threshold) * 0.1)
            else:
                prob = max(0.1, 0.5 - (threshold - prediction) * 0.1)
            probabilities[f'over_{threshold}'] = prob
        return probabilities
    
    def _calculate_normal_probabilities(self, prediction: float, std: float) -> Dict:
        """Calcula probabilidades usando distribución normal"""
        probabilities = {}
        for threshold in [10, 15, 20, 25, 30]:
            prob = 1 - stats.norm.cdf(threshold, prediction, std)
            probabilities[f'over_{threshold}'] = max(0, min(1, prob))
        return probabilities
