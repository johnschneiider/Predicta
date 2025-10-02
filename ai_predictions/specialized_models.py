"""
Modelos especializados por tipo de predicción para mayor precisión
"""

import numpy as np
import logging
from typing import Dict, List, Tuple
from datetime import timedelta
from django.utils import timezone
from django.db import models
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score
from football_data.models import Match, League
from .advanced_features import AdvancedFeatureExtractor

logger = logging.getLogger('ai_predictions')


class SpecializedPredictionModels:
    """Modelos especializados para diferentes tipos de predicción"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_extractor = AdvancedFeatureExtractor()
        self.trained_models = {}
    
    def get_specialized_model_config(self, prediction_type: str) -> Dict:
        """Configuración específica para cada tipo de predicción"""
        configs = {
            'goals_total': {
                'target_range': (1.0, 6.0),
                'expected_mean': 2.7,
                'expected_std': 1.2,
                'models': {
                    'Ridge': Ridge(alpha=0.5),
                    'ElasticNet': ElasticNet(alpha=0.1, l1_ratio=0.5),
                    'RandomForest': RandomForestRegressor(n_estimators=100, max_depth=8, min_samples_split=5),
                    'GradientBoosting': GradientBoostingRegressor(n_estimators=100, max_depth=6, learning_rate=0.1)
                },
                'validation_splits': 5
            },
            'goals_home': {
                'target_range': (0.5, 4.0),
                'expected_mean': 1.5,
                'expected_std': 0.8,
                'models': {
                    'Ridge': Ridge(alpha=0.3),
                    'ElasticNet': ElasticNet(alpha=0.05, l1_ratio=0.7),
                    'RandomForest': RandomForestRegressor(n_estimators=80, max_depth=6, min_samples_split=3),
                    'SVR': SVR(kernel='rbf', C=1.0, gamma='scale')
                },
                'validation_splits': 4
            },
            'goals_away': {
                'target_range': (0.3, 3.5),
                'expected_mean': 1.2,
                'expected_std': 0.7,
                'models': {
                    'Ridge': Ridge(alpha=0.4),
                    'ElasticNet': ElasticNet(alpha=0.08, l1_ratio=0.6),
                    'RandomForest': RandomForestRegressor(n_estimators=90, max_depth=7, min_samples_split=4),
                    'SVR': SVR(kernel='rbf', C=0.8, gamma='scale')
                },
                'validation_splits': 4
            },
            'shots_total': {
                'target_range': (8.0, 35.0),
                'expected_mean': 23.0,
                'expected_std': 6.0,
                'models': {
                    'Ridge': Ridge(alpha=1.0),
                    'ElasticNet': ElasticNet(alpha=0.2, l1_ratio=0.3),
                    'RandomForest': RandomForestRegressor(n_estimators=120, max_depth=10, min_samples_split=8),
                    'GradientBoosting': GradientBoostingRegressor(n_estimators=120, max_depth=8, learning_rate=0.08)
                },
                'validation_splits': 5
            },
            'shots_home': {
                'target_range': (4.0, 20.0),
                'expected_mean': 12.0,
                'expected_std': 3.5,
                'models': {
                    'Ridge': Ridge(alpha=0.8),
                    'ElasticNet': ElasticNet(alpha=0.15, l1_ratio=0.4),
                    'RandomForest': RandomForestRegressor(n_estimators=100, max_depth=8, min_samples_split=5),
                    'SVR': SVR(kernel='rbf', C=1.2, gamma='scale')
                },
                'validation_splits': 4
            },
            'shots_away': {
                'target_range': (3.5, 18.0),
                'expected_mean': 11.0,
                'expected_std': 3.2,
                'models': {
                    'Ridge': Ridge(alpha=1.0),
                    'ElasticNet': ElasticNet(alpha=0.18, l1_ratio=0.5),
                    'RandomForest': RandomForestRegressor(n_estimators=110, max_depth=9, min_samples_split=6),
                    'SVR': SVR(kernel='rbf', C=1.0, gamma='scale')
                },
                'validation_splits': 4
            }
        }
        
        return configs.get(prediction_type, configs['goals_total'])
    
    def prepare_training_data(self, league: League, prediction_type: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara datos de entrenamiento con características avanzadas"""
        try:
            # Obtener partidos históricos
            matches = Match.objects.filter(league=league).exclude(
                models.Q(fthg__isnull=True) | models.Q(ftag__isnull=True) |
                models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
            ).order_by('date')
            
            if len(matches) < 50:
                logger.warning(f"Datos insuficientes para entrenamiento especializado: {len(matches)} partidos")
                return np.array([]), np.array([])
            
            X = []
            y = []
            
            for match in matches:
                try:
                    # Obtener características avanzadas
                    features = self.feature_extractor.prepare_advanced_features(
                        match.home_team, match.away_team, league, prediction_type
                    )
                    
                    # Variable objetivo según tipo
                    if prediction_type == 'goals_total':
                        target = (match.fthg or 0) + (match.ftag or 0)
                    elif prediction_type == 'goals_home':
                        target = match.fthg or 0
                    elif prediction_type == 'goals_away':
                        target = match.ftag or 0
                    elif prediction_type == 'shots_total':
                        target = (match.hs or 0) + (match.as_field or 0)
                    elif prediction_type == 'shots_home':
                        target = match.hs or 0
                    elif prediction_type == 'shots_away':
                        target = match.as_field or 0
                    else:
                        target = (match.fthg or 0) + (match.ftag or 0)
                    
                    X.append(features)
                    y.append(target)
                    
                except Exception as e:
                    logger.error(f"Error procesando partido {match.id}: {e}")
                    continue
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento especializado: {e}")
            return np.array([]), np.array([])
    
    def train_specialized_model(self, league: League, prediction_type: str) -> Dict:
        """Entrena modelo especializado para el tipo de predicción"""
        try:
            # Preparar datos
            X, y = self.prepare_training_data(league, prediction_type)
            
            if len(X) < 30:
                return {'error': 'Datos insuficientes para entrenamiento especializado'}
            
            # Obtener configuración específica
            config = self.get_specialized_model_config(prediction_type)
            
            # Validación cruzada temporal
            tscv = TimeSeriesSplit(n_splits=min(config['validation_splits'], len(X) // 10))
            
            best_model = None
            best_score = -np.inf
            best_name = None
            model_scores = {}
            
            # Probar diferentes modelos
            for name, model in config['models'].items():
                scores = []
                mae_scores = []
                
                for train_idx, test_idx in tscv.split(X):
                    X_train, X_test = X[train_idx], X[test_idx]
                    y_train, y_test = y[train_idx], y[test_idx]
                    
                    # Normalizar datos
                    X_train_scaled = self.scaler.fit_transform(X_train)
                    X_test_scaled = self.scaler.transform(X_test)
                    
                    # Entrenar y evaluar
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                    
                    # Métricas
                    mae = mean_absolute_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    
                    # Accuracy con tolerancia (más relevante para fútbol)
                    tolerance = 0.5 if 'goals' in prediction_type else 2.0
                    accuracy = np.mean(np.abs(y_pred - y_test) <= tolerance)
                    
                    # Score compuesto
                    score = r2 * 0.4 + (1 - mae / np.mean(y_test)) * 0.3 + accuracy * 0.3
                    
                    scores.append(score)
                    mae_scores.append(mae)
                
                avg_score = np.mean(scores)
                avg_mae = np.mean(mae_scores)
                
                model_scores[name] = {'score': avg_score, 'mae': avg_mae}
                
                if avg_score > best_score:
                    best_score = avg_score
                    best_model = model
                    best_name = name
            
            # Entrenar el mejor modelo con todos los datos
            X_scaled = self.scaler.fit_transform(X)
            best_model.fit(X_scaled, y)
            
            # Guardar modelo entrenado
            model_key = f"{league.id}_{prediction_type}_specialized"
            self.trained_models[model_key] = {
                'model': best_model,
                'scaler': self.scaler,
                'config': config,
                'features_count': X.shape[1],
                'samples_count': len(X)
            }
            
            return {
                'model_name': f"Specialized {best_name}",
                'score': best_score,
                'model_scores': model_scores,
                'features_count': X.shape[1],
                'samples_count': len(X),
                'model_key': model_key,
                'prediction_type': prediction_type
            }
            
        except Exception as e:
            logger.error(f"Error entrenando modelo especializado: {e}")
            return {'error': str(e)}
    
    def predict_with_specialized_model(self, home_team: str, away_team: str, league: League, 
                                     prediction_type: str) -> Dict:
        """Hace predicción usando modelo especializado"""
        try:
            model_key = f"{league.id}_{prediction_type}_specialized"
            
            if model_key not in self.trained_models:
                # Entrenar modelo si no existe
                train_result = self.train_specialized_model(league, prediction_type)
                if 'error' in train_result:
                    return self._fallback_prediction(prediction_type, train_result['error'])
            
            # Obtener características avanzadas
            features = self.feature_extractor.prepare_advanced_features(
                home_team, away_team, league, prediction_type
            )
            
            # Normalizar y predecir
            X_scaled = self.trained_models[model_key]['scaler'].transform([features])
            prediction = self.trained_models[model_key]['model'].predict(X_scaled)[0]
            
            # Aplicar límites realistas según configuración
            config = self.trained_models[model_key]['config']
            min_val, max_val = config['target_range']
            prediction = max(min_val, min(max_val, prediction))
            
            # Calcular probabilidades con distribución realista
            std_dev = config['expected_std']
            probabilities = self._calculate_probabilities(prediction, std_dev, prediction_type)
            
            # Confianza basada en calidad del modelo
            model_info = self.trained_models[model_key]
            confidence = min(0.95, max(0.4, model_info['samples_count'] / 200))
            
            return {
                'model_name': f"Specialized Model ({prediction_type})",
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'total_matches': model_info['samples_count'],
                'features_used': model_info['features_count'],
                'model_type': 'specialized'
            }
            
        except Exception as e:
            logger.error(f"Error en predicción especializada: {e}")
            return self._fallback_prediction(prediction_type, str(e))
    
    def _calculate_probabilities(self, prediction: float, std_dev: float, prediction_type: str) -> Dict:
        """Calcula probabilidades con distribución normal"""
        from scipy.stats import norm
        
        probabilities = {}
        
        if 'goals' in prediction_type:
            thresholds = [1, 2, 3, 4, 5]
        else:
            thresholds = [10, 15, 20, 25, 30]
        
        for threshold in thresholds:
            prob = 1 - norm.cdf(threshold, prediction, std_dev)
            probabilities[f'over_{threshold}'] = max(0, min(1, prob))
        
        return probabilities
    
    def _fallback_prediction(self, prediction_type: str, error_msg: str) -> Dict:
        """Predicción de fallback para errores"""
        config = self.get_specialized_model_config(prediction_type)
        default_prediction = config['expected_mean']
        
        if 'goals' in prediction_type:
            probabilities = {'over_1': 0.8, 'over_2': 0.5, 'over_3': 0.2, 'over_4': 0.05, 'over_5': 0.01}
        else:
            probabilities = {'over_10': 0.6, 'over_15': 0.3, 'over_20': 0.1, 'over_25': 0.02, 'over_30': 0.005}
        
        return {
            'model_name': f"Fallback Model ({prediction_type})",
            'prediction': default_prediction,
            'confidence': 0.2,
            'probabilities': probabilities,
            'total_matches': 0,
            'features_used': 0,
            'model_type': 'fallback',
            'error': error_msg
        }
