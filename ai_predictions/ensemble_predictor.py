"""
Sistema de ensemble learning avanzado para combinar múltiples modelos
"""

import numpy as np
import logging
from typing import Dict, List, Tuple
from sklearn.ensemble import VotingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from football_data.models import League
from .specialized_models import SpecializedPredictionModels
from .simple_models import SimplePredictionService
from .advanced_features import AdvancedFeatureExtractor

logger = logging.getLogger('ai_predictions')


class AdvancedEnsemblePredictor:
    """Ensemble predictor que combina múltiples modelos para mayor precisión"""
    
    def __init__(self):
        self.specialized_models = SpecializedPredictionModels()
        self.simple_models = SimplePredictionService()
        self.feature_extractor = AdvancedFeatureExtractor()
        self.ensemble_weights = {}
        self.performance_history = {}
    
    def get_all_model_predictions(self, home_team: str, away_team: str, league: League, 
                                 prediction_type: str) -> List[Dict]:
        """Obtiene predicciones de todos los modelos disponibles"""
        predictions = []
        
        try:
            # 1. Modelo especializado (más peso)
            specialized_pred = self.specialized_models.predict_with_specialized_model(
                home_team, away_team, league, prediction_type
            )
            specialized_pred['model_weight'] = 0.4  # 40% del peso
            specialized_pred['model_category'] = 'specialized'
            predictions.append(specialized_pred)
            
            # 2. Modelos simples (peso medio)
            simple_predictions = self.simple_models.get_all_simple_predictions(
                home_team, away_team, league, prediction_type
            )
            for pred in simple_predictions:
                pred['model_weight'] = 0.2  # 20% del peso cada uno
                pred['model_category'] = 'simple'
                predictions.append(pred)
            
            # 3. Modelo de características avanzadas (peso medio)
            advanced_pred = self._get_advanced_features_prediction(
                home_team, away_team, league, prediction_type
            )
            advanced_pred['model_weight'] = 0.2  # 20% del peso
            advanced_pred['model_category'] = 'advanced'
            predictions.append(advanced_pred)
            
        except Exception as e:
            logger.error(f"Error obteniendo predicciones de modelos: {e}")
            # Fallback a predicción básica
            predictions = [self._get_basic_fallback_prediction(prediction_type)]
        
        return predictions
    
    def _get_advanced_features_prediction(self, home_team: str, away_team: str, league: League, 
                                        prediction_type: str) -> Dict:
        """Predicción basada en características avanzadas"""
        try:
            # Obtener características avanzadas
            features = self.feature_extractor.prepare_advanced_features(
                home_team, away_team, league, prediction_type
            )
            
            # Análisis de forma de equipos
            home_form = self.feature_extractor.get_team_form_analysis(home_team, league, True)
            away_form = self.feature_extractor.get_team_form_analysis(away_team, league, False)
            
            # Análisis H2H
            h2h_data = self.feature_extractor.get_head_to_head_analysis(home_team, away_team, league)
            
            # Contexto de liga
            league_context = self.feature_extractor.get_league_context(league, prediction_type)
            
            # Predicción basada en características
            if 'goals' in prediction_type:
                # Predicción de goles
                home_goals = home_form['avg_goals'] * home_form['home_advantage']
                away_goals = away_form['avg_goals'] * away_form['home_advantage']
                
                # Ajustar por H2H si hay datos
                if h2h_data['matches_count'] > 0:
                    h2h_factor = 0.3  # 30% de peso al H2H
                    league_factor = 0.7  # 70% de peso a la liga
                    
                    home_goals = (home_goals * league_factor + 
                                h2h_data['avg_home_goals'] * h2h_factor)
                    away_goals = (away_goals * league_factor + 
                                h2h_data['avg_away_goals'] * h2h_factor)
                
                if prediction_type == 'goals_total':
                    prediction = home_goals + away_goals
                elif prediction_type == 'goals_home':
                    prediction = home_goals
                else:  # goals_away
                    prediction = away_goals
                    
                # Normalizar con contexto de liga
                if prediction_type == 'goals_total':
                    league_avg = league_context['league_avg_total_goals']
                elif prediction_type == 'goals_home':
                    league_avg = league_context['league_avg_home_goals']
                else:
                    league_avg = league_context['league_avg_away_goals']
                
                prediction = prediction * 0.8 + league_avg * 0.2
                
            else:
                # Predicción de remates
                home_shots = home_form['avg_shots'] * home_form['home_advantage']
                away_shots = away_form['avg_shots'] * away_form['home_advantage']
                
                # Ajustar por H2H si hay datos
                if h2h_data['matches_count'] > 0:
                    h2h_factor = 0.2  # 20% de peso al H2H
                    league_factor = 0.8  # 80% de peso a la liga
                    
                    home_shots = (home_shots * league_factor + 
                                h2h_data['avg_home_shots'] * h2h_factor)
                    away_shots = (away_shots * league_factor + 
                                h2h_data['avg_away_shots'] * h2h_factor)
                
                if prediction_type == 'shots_total':
                    prediction = home_shots + away_shots
                elif prediction_type == 'shots_home':
                    prediction = home_shots
                else:  # shots_away
                    prediction = away_shots
                
                # Normalizar con contexto de liga
                if prediction_type == 'shots_total':
                    league_avg = league_context['league_avg_total_shots']
                elif prediction_type == 'shots_home':
                    league_avg = league_context['league_avg_home_shots']
                else:
                    league_avg = league_context['league_avg_away_shots']
                
                prediction = prediction * 0.7 + league_avg * 0.3
            
            # Calcular confianza basada en calidad de datos
            confidence = min(0.8, max(0.3, 
                (home_form['total_matches'] + away_form['total_matches'] + h2h_data['matches_count']) / 100
            ))
            
            # Calcular probabilidades
            probabilities = self._calculate_advanced_probabilities(prediction, prediction_type)
            
            return {
                'model_name': 'Advanced Features',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'total_matches': home_form['total_matches'] + away_form['total_matches'],
                'features_used': len(features),
                'h2h_matches': h2h_data['matches_count']
            }
            
        except Exception as e:
            logger.error(f"Error en predicción avanzada: {e}")
            return self._get_basic_fallback_prediction(prediction_type)
    
    def create_ensemble_prediction(self, predictions: List[Dict]) -> Dict:
        """Crea predicción ensemble combinando múltiples modelos"""
        try:
            if not predictions:
                return self._get_basic_fallback_prediction('goals_total')
            
            # Filtrar predicciones válidas
            valid_predictions = [p for p in predictions if 'prediction' in p and p['prediction'] > 0]
            
            if not valid_predictions:
                return self._get_basic_fallback_prediction('goals_total')
            
            # Calcular pesos dinámicos basados en confianza
            total_confidence = sum(p['confidence'] for p in valid_predictions)
            dynamic_weights = []
            
            for pred in valid_predictions:
                # Peso base + peso por confianza
                base_weight = pred.get('model_weight', 0.25)
                confidence_weight = pred['confidence'] / total_confidence * 0.5
                final_weight = base_weight + confidence_weight
                dynamic_weights.append(final_weight)
            
            # Normalizar pesos
            total_weight = sum(dynamic_weights)
            dynamic_weights = [w / total_weight for w in dynamic_weights]
            
            # Predicción ponderada
            ensemble_prediction = sum(
                pred['prediction'] * weight 
                for pred, weight in zip(valid_predictions, dynamic_weights)
            )
            
            # Confianza del ensemble (promedio ponderado)
            ensemble_confidence = sum(
                pred['confidence'] * weight 
                for pred, weight in zip(valid_predictions, dynamic_weights)
            )
            
            # Probabilidades del ensemble (promedio ponderado)
            ensemble_probabilities = {}
            probability_keys = ['over_1', 'over_2', 'over_3', 'over_10', 'over_15', 'over_20']
            
            for key in probability_keys:
                if any(key in p.get('probabilities', {}) for p in valid_predictions):
                    ensemble_probabilities[key] = sum(
                        pred.get('probabilities', {}).get(key, 0.5) * weight
                        for pred, weight in zip(valid_predictions, dynamic_weights)
                    )
            
            # Total de partidos analizados
            total_matches = sum(p.get('total_matches', 0) for p in valid_predictions)
            
            return {
                'model_name': 'Advanced Ensemble',
                'prediction': ensemble_prediction,
                'confidence': ensemble_confidence,
                'probabilities': ensemble_probabilities,
                'total_matches': total_matches,
                'models_used': len(valid_predictions),
                'model_weights': dynamic_weights,
                'individual_predictions': valid_predictions
            }
            
        except Exception as e:
            logger.error(f"Error creando ensemble: {e}")
            return self._get_basic_fallback_prediction('goals_total')
    
    def predict_with_ensemble(self, home_team: str, away_team: str, league: League, 
                             prediction_type: str) -> Dict:
        """Predicción principal usando ensemble de modelos"""
        try:
            # Obtener predicciones de todos los modelos
            all_predictions = self.get_all_model_predictions(
                home_team, away_team, league, prediction_type
            )
            
            # Crear predicción ensemble
            ensemble_result = self.create_ensemble_prediction(all_predictions)
            
            # Agregar información adicional
            ensemble_result['prediction_type'] = prediction_type
            ensemble_result['home_team'] = home_team
            ensemble_result['away_team'] = away_team
            ensemble_result['league'] = league.name
            
            return ensemble_result
            
        except Exception as e:
            logger.error(f"Error en predicción ensemble: {e}")
            return self._get_basic_fallback_prediction(prediction_type)
    
    def _calculate_advanced_probabilities(self, prediction: float, prediction_type: str) -> Dict:
        """Calcula probabilidades avanzadas"""
        probabilities = {}
        
        if 'goals' in prediction_type:
            thresholds = [1, 2, 3, 4, 5]
            std_dev = 1.2 if prediction_type == 'goals_total' else 0.8
        else:
            thresholds = [10, 15, 20, 25, 30]
            std_dev = 6.0 if prediction_type == 'shots_total' else 3.5
        
        for threshold in thresholds:
            # Distribución normal
            z_score = (threshold - prediction) / std_dev
            prob = 1 - (0.5 * (1 + np.tanh(z_score / 1.414)))  # Aproximación de CDF normal
            probabilities[f'over_{threshold}'] = max(0, min(1, prob))
        
        return probabilities
    
    def _get_basic_fallback_prediction(self, prediction_type: str) -> Dict:
        """Predicción de fallback básica"""
        if 'goals' in prediction_type:
            default_prediction = 2.7 if prediction_type == 'goals_total' else 1.5
            probabilities = {'over_1': 0.8, 'over_2': 0.5, 'over_3': 0.2, 'over_4': 0.05, 'over_5': 0.01}
        else:
            default_prediction = 23.0 if prediction_type == 'shots_total' else 12.0
            probabilities = {'over_10': 0.6, 'over_15': 0.3, 'over_20': 0.1, 'over_25': 0.02, 'over_30': 0.005}
        
        return {
            'model_name': 'Fallback Model',
            'prediction': default_prediction,
            'confidence': 0.2,
            'probabilities': probabilities,
            'total_matches': 0,
            'features_used': 0,
            'models_used': 1,
            'prediction_type': prediction_type
        }
