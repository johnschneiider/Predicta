"""
Modelo Zero-Inflated Poisson (ZIP) para predicción de goles en fútbol.
Mejor manejo de partidos con 0 goles y distribuciones sesgadas.
"""

import numpy as np
import logging
from typing import Dict, Tuple
from datetime import timedelta
from django.utils import timezone
from football_data.models import Match, League
from .simple_models import get_league_realistic_limits, analyze_team_statistics

logger = logging.getLogger('ai_predictions')


class ZeroInflatedPoissonModel:
    """
    Modelo Zero-Inflated Poisson para predicción de goles.
    
    El modelo ZIP maneja mejor la alta frecuencia de partidos con 0 goles
    combinando una distribución de Poisson con un componente de "inflación de ceros".
    """
    
    def __init__(self):
        self.name = "Zero-Inflated Poisson"
    
    def predict_match(self, home_team: str, away_team: str, league: League,
                     prediction_type: str = 'goals_total') -> Dict:
        """
        Predice un partido usando el modelo ZIP.
        
        Args:
            home_team: Equipo local
            away_team: Equipo visitante
            league: Liga
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con la predicción y probabilidades
        """
        try:
            if 'goals' not in prediction_type:
                # Para no-goles, usar modelo Poisson simple
                return self._simple_poisson_prediction(home_team, away_team, league, prediction_type)
            
            # Obtener límites y estadísticas
            lambda_min, lambda_max = get_league_realistic_limits(league, 'goals')
            home_stats = analyze_team_statistics(home_team, league, 'goals')
            away_stats = analyze_team_statistics(away_team, league, 'goals')
            
            # Calcular parámetros ZIP
            zip_params = self._calculate_zip_parameters(home_team, away_team, league, 
                                                      home_stats, away_stats, lambda_min, lambda_max)
            
            # Calcular predicción
            if prediction_type == 'goals_total':
                prediction = zip_params['lambda_home'] + zip_params['lambda_away']
            elif prediction_type == 'goals_home':
                prediction = zip_params['lambda_home']
            elif prediction_type == 'goals_away':
                prediction = zip_params['lambda_away']
            elif prediction_type == 'both_teams_score':
                prediction = self._calculate_both_teams_score_zip(zip_params)
            else:
                prediction = zip_params['lambda_home'] + zip_params['lambda_away']
            
            # Calcular probabilidades
            probabilities = self._calculate_zip_probabilities(zip_params, prediction_type)
            
            # Confianza basada en datos
            total_matches = home_stats['total_matches'] + away_stats['total_matches']
            confidence = min(0.9, max(0.4, total_matches / 40))
            
            return {
                'model_name': self.name,
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'zip_params': zip_params,
                'total_matches': total_matches,
                'model_type': 'zip'
            }
            
        except Exception as e:
            logger.error(f"Error en predicción ZIP: {e}")
            return self._fallback_prediction(prediction_type)
    
    def _calculate_zip_parameters(self, home_team: str, away_team: str, league: League,
                                 home_stats: Dict, away_stats: Dict, 
                                 lambda_min: float, lambda_max: float) -> Dict:
        """
        Calcula los parámetros del modelo ZIP.
        
        Args:
            home_team: Equipo local
            away_team: Equipo visitante
            league: Liga
            home_stats: Estadísticas del equipo local
            away_stats: Estadísticas del equipo visitante
            lambda_min: Lambda mínimo
            lambda_max: Lambda máximo
        
        Returns:
            Diccionario con parámetros ZIP
        """
        try:
            # Calcular lambda base
            home_avg = home_stats['overall_avg'] if home_stats['overall_avg'] > 0 else 1.5
            away_avg = away_stats['overall_avg'] if away_stats['overall_avg'] > 0 else 1.2
            
            # Aplicar ventajas de local/visitante
            lambda_home = home_avg * 1.1
            lambda_away = away_avg * 0.9
            
            # Aplicar límites
            lambda_home = max(lambda_min, min(lambda_max, lambda_home))
            lambda_away = max(lambda_min, min(lambda_max, lambda_away))
            
            # Calcular probabilidades de "inflación de ceros"
            # Basado en la frecuencia de partidos con 0 goles en los datos históricos
            home_zero_freq = self._calculate_zero_frequency(home_stats['home_data'])
            away_zero_freq = self._calculate_zero_frequency(away_stats['away_data'])
            
            # Parámetros ZIP
            zip_params = {
                'lambda_home': lambda_home,
                'lambda_away': lambda_away,
                'pi_home': home_zero_freq,  # Probabilidad de "inflación de ceros"
                'pi_away': away_zero_freq,
                'lambda_min': lambda_min,
                'lambda_max': lambda_max
            }
            
            logger.info(f"ZIP Parámetros - {home_team}: λ={lambda_home:.2f}, π={home_zero_freq:.2f}")
            logger.info(f"ZIP Parámetros - {away_team}: λ={lambda_away:.2f}, π={away_zero_freq:.2f}")
            
            return zip_params
            
        except Exception as e:
            logger.error(f"Error calculando parámetros ZIP: {e}")
            return {
                'lambda_home': 1.5,
                'lambda_away': 1.2,
                'pi_home': 0.1,
                'pi_away': 0.1,
                'lambda_min': lambda_min,
                'lambda_max': lambda_max
            }
    
    def _calculate_zero_frequency(self, data: list) -> float:
        """
        Calcula la frecuencia de ceros en los datos.
        
        Args:
            data: Lista de valores
        
        Returns:
            Frecuencia de ceros (0.0 a 1.0)
        """
        if not data:
            return 0.1  # Valor por defecto
        
        zero_count = sum(1 for x in data if x == 0)
        total_count = len(data)
        
        frequency = zero_count / total_count
        return min(0.5, max(0.05, frequency))  # Limitar entre 5% y 50%
    
    def _calculate_both_teams_score_zip(self, zip_params: Dict) -> float:
        """
        Calcula la probabilidad de "ambos marcan" usando modelo ZIP.
        
        Args:
            zip_params: Parámetros del modelo ZIP
        
        Returns:
            Probabilidad de que ambos equipos marquen
        """
        try:
            lambda_home = zip_params['lambda_home']
            lambda_away = zip_params['lambda_away']
            pi_home = zip_params['pi_home']
            pi_away = zip_params['pi_away']
            
            # P(equipo no marca) en modelo ZIP
            # P(X=0) = π + (1-π) * e^(-λ)
            prob_home_no_score = pi_home + (1 - pi_home) * np.exp(-lambda_home)
            prob_away_no_score = pi_away + (1 - pi_away) * np.exp(-lambda_away)
            
            # P(ninguno marca) = P(local no marca) * P(visitante no marca)
            prob_none_score = prob_home_no_score * prob_away_no_score
            
            # P(ambos marcan) = 1 - P(local no marca) - P(visitante no marca) + P(ninguno marca)
            prob_both_score = 1.0 - prob_home_no_score - prob_away_no_score + prob_none_score
            
            return min(0.95, max(0.05, prob_both_score))
            
        except Exception as e:
            logger.error(f"Error calculando both_teams_score ZIP: {e}")
            return 0.5
    
    def _calculate_zip_probabilities(self, zip_params: Dict, prediction_type: str) -> Dict:
        """
        Calcula probabilidades usando el modelo ZIP.
        
        Args:
            zip_params: Parámetros del modelo ZIP
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con probabilidades
        """
        probabilities = {}
        
        if prediction_type == 'both_teams_score':
            prob_both = self._calculate_both_teams_score_zip(zip_params)
            probabilities['both_score'] = prob_both
            probabilities['over_1'] = prob_both  # Compatibilidad
            return probabilities
        
        # Para otros tipos, usar probabilidades Poisson simples
        lambda_home = zip_params['lambda_home']
        lambda_away = zip_params['lambda_away']
        
        if 'goals' in prediction_type:
            thresholds = [1, 2, 3, 4, 5]
            
            for threshold in thresholds:
                if 'total' in prediction_type:
                    # P(over X goles totales)
                    prob_over = 0.0
                    for home_goals in range(threshold + 1, 8):
                        for away_goals in range(8):
                            if home_goals + away_goals > threshold:
                                prob_over += self._zip_probability(home_goals, away_goals, zip_params)
                    probabilities[f'over_{threshold}'] = min(1.0, max(0.0, prob_over))
                    
                elif 'home' in prediction_type:
                    # P(equipo local marca más de X goles)
                    prob_over = 0.0
                    for home_goals in range(threshold + 1, 8):
                        prob_over += self._zip_probability(home_goals, 0, zip_params)
                    probabilities[f'over_{threshold}'] = min(1.0, max(0.0, prob_over))
                    
                elif 'away' in prediction_type:
                    # P(equipo visitante marca más de X goles)
                    prob_over = 0.0
                    for away_goals in range(threshold + 1, 8):
                        prob_over += self._zip_probability(0, away_goals, zip_params)
                    probabilities[f'over_{threshold}'] = min(1.0, max(0.0, prob_over))
        
        return probabilities
    
    def _zip_probability(self, home_goals: int, away_goals: int, zip_params: Dict) -> float:
        """
        Calcula la probabilidad de un marcador específico usando modelo ZIP.
        
        Args:
            home_goals: Goles del equipo local
            away_goals: Goles del equipo visitante
            zip_params: Parámetros del modelo ZIP
        
        Returns:
            Probabilidad del marcador
        """
        try:
            lambda_home = zip_params['lambda_home']
            lambda_away = zip_params['lambda_away']
            pi_home = zip_params['pi_home']
            pi_away = zip_params['pi_away']
            
            # Calcular probabilidades individuales
            if home_goals == 0:
                prob_home = pi_home + (1 - pi_home) * np.exp(-lambda_home)
            else:
                prob_home = (1 - pi_home) * (lambda_home ** home_goals) * np.exp(-lambda_home) / np.math.factorial(home_goals)
            
            if away_goals == 0:
                prob_away = pi_away + (1 - pi_away) * np.exp(-lambda_away)
            else:
                prob_away = (1 - pi_away) * (lambda_away ** away_goals) * np.exp(-lambda_away) / np.math.factorial(away_goals)
            
            return prob_home * prob_away
            
        except Exception as e:
            logger.error(f"Error calculando probabilidad ZIP: {e}")
            return 0.0
    
    def _simple_poisson_prediction(self, home_team: str, away_team: str, league: League,
                                  prediction_type: str) -> Dict:
        """
        Predicción simple para tipos que no son goles.
        
        Args:
            home_team: Equipo local
            away_team: Equipo visitante
            league: Liga
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con predicción
        """
        try:
            # Usar función de límites para no-goles
            prediction_type_clean = 'shots' if 'shots' in prediction_type else 'corners'
            lambda_min, lambda_max = get_league_realistic_limits(league, prediction_type_clean)
            
            home_stats = analyze_team_statistics(home_team, league, prediction_type_clean)
            away_stats = analyze_team_statistics(away_team, league, prediction_type_clean)
            
            # Calcular lambda
            home_avg = home_stats['overall_avg'] if home_stats['overall_avg'] > 0 else 12.0
            away_avg = away_stats['overall_avg'] if away_stats['overall_avg'] > 0 else 11.0
            
            lambda_home = max(lambda_min, min(lambda_max, home_avg * 1.1))
            lambda_away = max(lambda_min, min(lambda_max, away_avg * 0.9))
            
            # Predicción
            if 'total' in prediction_type:
                prediction = lambda_home + lambda_away
            elif 'home' in prediction_type:
                prediction = lambda_home
            elif 'away' in prediction_type:
                prediction = lambda_away
            else:
                prediction = lambda_home + lambda_away
            
            # Probabilidades simples
            probabilities = {}
            if 'corners' in prediction_type:
                thresholds = [8, 10, 12, 15, 20]
            else:
                thresholds = [10, 15, 20, 25, 30]
            
            for threshold in thresholds:
                prob = max(0, min(1, 1 - (threshold / prediction) if prediction > 0 else 0.5))
                probabilities[f'over_{threshold}'] = prob
            
            return {
                'model_name': self.name,
                'prediction': prediction,
                'confidence': 0.6,
                'probabilities': probabilities,
                'total_matches': home_stats['total_matches'] + away_stats['total_matches'],
                'model_type': 'zip_simple'
            }
            
        except Exception as e:
            logger.error(f"Error en predicción ZIP simple: {e}")
            return self._fallback_prediction(prediction_type)
    
    def _fallback_prediction(self, prediction_type: str) -> Dict:
        """
        Predicción de fallback para errores.
        
        Args:
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con predicción de fallback
        """
        if 'goals' in prediction_type:
            default_prediction = 2.7 if 'total' in prediction_type else 1.5
            probabilities = {'over_1': 0.75, 'over_2': 0.55, 'over_3': 0.3, 'over_4': 0.12, 'over_5': 0.04}
        else:
            default_prediction = 23.0 if 'total' in prediction_type else 12.0
            probabilities = {'over_10': 0.7, 'over_15': 0.5, 'over_20': 0.3, 'over_25': 0.12, 'over_30': 0.04}
        
        return {
            'model_name': f"{self.name} (Fallback)",
            'prediction': default_prediction,
            'confidence': 0.3,
            'probabilities': probabilities,
            'total_matches': 0,
            'model_type': 'zip_fallback',
            'error': 'Fallback debido a falta de datos'
        }
