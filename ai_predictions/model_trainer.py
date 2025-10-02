"""
Sistema de entrenamiento y optimización de modelos basado en backtesting
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.ensemble import RandomForestRegressor
from scipy import stats
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from django.utils import timezone
from django.db import models
from football_data.models import Match, League
from .models import PredictionModel, TeamStats

logger = logging.getLogger('ai_predictions')


class ModelTrainer:
    """Sistema de entrenamiento y optimización de modelos"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.trained_models = {}
    
    def get_enhanced_team_features(self, team_name: str, league: League, is_home: bool = True) -> Dict:
        """Obtiene características mejoradas de un equipo"""
        try:
            # Ventana temporal más amplia para más datos
            cutoff_date = timezone.now().date() - timedelta(days=365)  # 1 año
            
            if is_home:
                matches = Match.objects.filter(
                    league=league,
                    home_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:50]
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
                return self._default_team_features()
            
            # Calcular características avanzadas
            shots_array = np.array(shots_data)
            goals_array = np.array(goals_data)
            sot_array = np.array(shots_on_target) if shots_on_target else np.array([])
            
            # Características básicas
            features = {
                'avg_shots': np.mean(shots_array),
                'std_shots': np.std(shots_array),
                'median_shots': np.median(shots_array),
                'q25_shots': np.percentile(shots_array, 25),
                'q75_shots': np.percentile(shots_array, 75),
                'avg_goals': np.mean(goals_array),
                'std_goals': np.std(goals_array),
                'matches_count': len(shots_array),
                'home_advantage': 1.15 if is_home else 0.9
            }
            
            # Características avanzadas
            if len(shots_array) >= 5:
                # Tendencia reciente (últimos 5 vs anteriores)
                recent_shots = shots_array[:5]
                older_shots = shots_array[5:10] if len(shots_array) >= 10 else shots_array[5:]
                
                if len(older_shots) > 0:
                    features['recent_trend'] = np.mean(recent_shots) - np.mean(older_shots)
                else:
                    features['recent_trend'] = 0
                
                # Consistencia (inverso del coeficiente de variación)
                features['consistency'] = 1 / (1 + np.std(shots_array) / np.mean(shots_array)) if np.mean(shots_array) > 0 else 0
                
                # Eficiencia (goles por remate)
                features['efficiency'] = np.mean(goals_array) / np.mean(shots_array) if np.mean(shots_array) > 0 else 0
                
                # Momentum (diferencia entre últimos 3 y anteriores 3)
                if len(shots_array) >= 6:
                    momentum_shots = shots_array[:3]
                    previous_shots = shots_array[3:6]
                    features['momentum'] = np.mean(momentum_shots) - np.mean(previous_shots)
                else:
                    features['momentum'] = 0
            else:
                features['recent_trend'] = 0
                features['consistency'] = 0.5
                features['efficiency'] = 0.1
                features['momentum'] = 0
            
            # Características de remates a puerta
            if len(sot_array) > 0:
                features['avg_sot'] = np.mean(sot_array)
                features['sot_rate'] = np.mean(sot_array) / np.mean(shots_array) if np.mean(shots_array) > 0 else 0.3
            else:
                features['avg_sot'] = features['avg_shots'] * 0.3  # Estimación
                features['sot_rate'] = 0.3
            
            return features
            
        except Exception as e:
            logger.error(f"Error obteniendo características de {team_name}: {e}")
            return self._default_team_features()
    
    def _default_team_features(self) -> Dict:
        """Características por defecto cuando no hay datos"""
        return {
            'avg_shots': 12.0, 'std_shots': 3.0, 'median_shots': 12.0,
            'q25_shots': 9.0, 'q75_shots': 15.0, 'avg_goals': 1.5,
            'std_goals': 1.0, 'matches_count': 0, 'home_advantage': 1.0,
            'recent_trend': 0, 'consistency': 0.5, 'efficiency': 0.1,
            'momentum': 0, 'avg_sot': 3.6, 'sot_rate': 0.3
        }
    
    def prepare_training_data(self, league: League, prediction_type: str = 'shots_total') -> Tuple[np.ndarray, np.ndarray]:
        """Prepara datos de entrenamiento para el modelo"""
        try:
            # Obtener partidos históricos
            matches = Match.objects.filter(league=league).exclude(
                models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
            ).order_by('date')
            
            if len(matches) < 20:
                logger.warning(f"Datos insuficientes para entrenamiento: {len(matches)} partidos")
                return np.array([]), np.array([])
            
            X = []
            y = []
            
            for match in matches:
                try:
                    # Obtener características de ambos equipos
                    home_features = self.get_enhanced_team_features(match.home_team, league, True)
                    away_features = self.get_enhanced_team_features(match.away_team, league, False)
                    
                    # Crear vector de características combinado
                    feature_vector = [
                        home_features['avg_shots'], home_features['std_shots'],
                        home_features['consistency'], home_features['efficiency'],
                        home_features['recent_trend'], home_features['momentum'],
                        home_features['sot_rate'], home_features['home_advantage'],
                        away_features['avg_shots'], away_features['std_shots'],
                        away_features['consistency'], away_features['efficiency'],
                        away_features['recent_trend'], away_features['momentum'],
                        away_features['sot_rate'], away_features['home_advantage']
                    ]
                    
                    # Variable objetivo
                    if prediction_type == 'shots_total':
                        target = (match.hs or 0) + (match.as_field or 0)
                    elif prediction_type == 'shots_home':
                        target = match.hs or 0
                    elif prediction_type == 'shots_away':
                        target = match.as_field or 0
                    elif prediction_type == 'goals_total':
                        target = (match.fthg or 0) + (match.ftag or 0)
                    elif prediction_type == 'goals_home':
                        target = match.fthg or 0
                    elif prediction_type == 'goals_away':
                        target = match.ftag or 0
                    else:
                        target = (match.hs or 0) + (match.as_field or 0)
                    
                    X.append(feature_vector)
                    y.append(target)
                    
                except Exception as e:
                    logger.error(f"Error procesando partido {match.id}: {e}")
                    continue
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento: {e}")
            return np.array([]), np.array([])
    
    def train_optimized_model(self, league: League, prediction_type: str = 'shots_total') -> Dict:
        """Entrena un modelo optimizado con backtesting"""
        try:
            # Preparar datos
            X, y = self.prepare_training_data(league, prediction_type)
            
            if len(X) < 20:
                return {'error': 'Datos insuficientes para entrenamiento'}
            
            # Validación cruzada temporal
            tscv = TimeSeriesSplit(n_splits=min(5, len(X) // 10))
            
            # Probar diferentes modelos
            models = {
                'Ridge': Ridge(alpha=1.0),
                'RandomForest': RandomForestRegressor(
                    n_estimators=50, max_depth=5, min_samples_split=5,
                    min_samples_leaf=2, random_state=42
                ),
                'LinearRegression': LinearRegression()
            }
            
            best_model = None
            best_score = -np.inf
            best_name = None
            model_scores = {}
            
            for name, model in models.items():
                scores = []
                mae_scores = []
                
                for train_idx, test_idx in tscv.split(X):
                    X_train, X_test = X[train_idx], X[test_idx]
                    y_train, y_test = y[train_idx], y[test_idx]
                    
                    # Normalizar datos
                    X_train_scaled = self.scaler.fit_transform(X_train)
                    X_test_scaled = self.scaler.transform(X_test)
                    
                    # Entrenar modelo
                    model.fit(X_train_scaled, y_train)
                    
                    # Predecir
                    y_pred = model.predict(X_test_scaled)
                    
                    # Calcular métricas
                    mae = mean_absolute_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    
                    # Score combinado (MAE + R²)
                    score = r2 - (mae / 10)  # Penalizar MAE alto
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
            model_key = f"{league.id}_{prediction_type}"
            self.trained_models[model_key] = {
                'model': best_model,
                'scaler': self.scaler,
                'features': X.shape[1],
                'samples': len(X)
            }
            
            return {
                'model_name': best_name,
                'score': best_score,
                'model_scores': model_scores,
                'features_count': X.shape[1],
                'samples_count': len(X),
                'model_key': model_key
            }
            
        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}")
            return {'error': str(e)}
    
    def predict_with_trained_model(self, home_team: str, away_team: str, league: League, 
                                 prediction_type: str = 'shots_total') -> Dict:
        """Hace predicción usando modelo entrenado"""
        try:
            model_key = f"{league.id}_{prediction_type}"
            
            if model_key not in self.trained_models:
                # Entrenar modelo si no existe
                train_result = self.train_optimized_model(league, prediction_type)
                if 'error' in train_result:
                    return self._fallback_prediction(train_result['error'])
            
            # Obtener características
            home_features = self.get_enhanced_team_features(home_team, league, True)
            away_features = self.get_enhanced_team_features(away_team, league, False)
            
            # Crear vector de características
            feature_vector = [
                home_features['avg_shots'], home_features['std_shots'],
                home_features['consistency'], home_features['efficiency'],
                home_features['recent_trend'], home_features['momentum'],
                home_features['sot_rate'], home_features['home_advantage'],
                away_features['avg_shots'], away_features['std_shots'],
                away_features['consistency'], away_features['efficiency'],
                away_features['recent_trend'], away_features['momentum'],
                away_features['sot_rate'], away_features['home_advantage']
            ]
            
            # Normalizar y predecir
            X_scaled = self.trained_models[model_key]['scaler'].transform([feature_vector])
            prediction = self.trained_models[model_key]['model'].predict(X_scaled)[0]
            
            # Asegurar predicción positiva
            prediction = max(0, prediction)
            
            # Calcular probabilidades usando distribución normal
            # Ajustar umbrales según el tipo de predicción
            if 'goals' in prediction_type:
                std_dev = 1.5  # Desviación estándar más realista para goles
                thresholds = [1, 2, 3, 4, 5]  # Umbrales realistas para goles
            else:
                std_dev = 3.0  # Desviación estándar para remates
                thresholds = [10, 15, 20, 25, 30]  # Umbrales para remates
            
            probabilities = {}
            for threshold in thresholds:
                prob = 1 - stats.norm.cdf(threshold, prediction, std_dev)
                probabilities[f'over_{threshold}'] = max(0, min(1, prob))
            
            # Confianza basada en calidad del modelo
            model_info = self.trained_models[model_key]
            confidence = min(0.9, max(0.3, model_info['samples'] / 100))
            
            return {
                'model_name': 'Trained Model',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'total_matches': model_info['samples'],
                'features_used': model_info['features']
            }
            
        except Exception as e:
            logger.error(f"Error en predicción con modelo entrenado: {e}")
            return self._fallback_prediction(str(e))
    
    def _fallback_prediction(self, error_msg: str) -> Dict:
        """Predicción de fallback para errores"""
        return {
            'model_name': 'Fallback Model',
            'prediction': 15.0,
            'confidence': 0.1,
            'probabilities': {'over_10': 0.5, 'over_15': 0.3, 'over_20': 0.1, 'over_25': 0.05, 'over_30': 0.02},
            'total_matches': 0,
            'error': error_msg
        }
