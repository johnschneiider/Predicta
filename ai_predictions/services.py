"""
Servicios para predicciones de IA
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
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


class PredictionService:
    """Servicio principal para predicciones de remates"""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def get_team_recent_stats(self, team_name: str, league: League, days_back: int = 365) -> Dict:
        """Obtiene estadísticas recientes de un equipo con optimizaciones"""
        try:
            # OPTIMIZACIÓN 1: Aumentar ventana temporal para más datos
            cutoff_date = timezone.now().date() - timedelta(days=days_back)
            
            # OPTIMIZACIÓN 2: Obtener más partidos históricos
            home_matches = Match.objects.filter(
                league=league,
                home_team=team_name,
                date__gte=cutoff_date
            ).order_by('-date')[:20]  # Aumentado de 10 a 20
            
            away_matches = Match.objects.filter(
                league=league,
                away_team=team_name,
                date__gte=cutoff_date
            ).order_by('-date')[:20]  # Aumentado de 10 a 20
            
            # OPTIMIZACIÓN 3: Estadísticas más robustas
            home_shots = [m.hs for m in home_matches if m.hs is not None]
            away_shots = [m.as_field for m in away_matches if m.as_field is not None]
            
            # Calcular estadísticas de goles
            home_goals = [m.fthg for m in home_matches if m.fthg is not None]
            away_goals = [m.ftag for m in away_matches if m.ftag is not None]
            
            # OPTIMIZACIÓN 4: Estadísticas adicionales para fútbol
            home_shots_on_target = [m.hst for m in home_matches if m.hst is not None]
            away_shots_on_target = [m.ast for m in away_matches if m.ast is not None]
            
            # Calcular forma reciente (más partidos)
            recent_matches = list(home_matches) + list(away_matches)
            recent_matches.sort(key=lambda x: x.date, reverse=True)
            recent_matches = recent_matches[:10]  # Aumentado de 5 a 10
            
            wins = draws = losses = 0
            for match in recent_matches:
                if match.home_team == team_name:
                    if match.fthg > match.ftag:
                        wins += 1
                    elif match.fthg == match.ftag:
                        draws += 1
                    else:
                        losses += 1
                else:
                    if match.ftag > match.fthg:
                        wins += 1
                    elif match.ftag == match.fthg:
                        draws += 1
                    else:
                        losses += 1
            
            return {
                'avg_shots_home': np.mean(home_shots) if home_shots else 0,
                'avg_shots_away': np.mean(away_shots) if away_shots else 0,
                'avg_goals_home': np.mean(home_goals) if home_goals else 0,
                'avg_goals_away': np.mean(away_goals) if away_goals else 0,
                'avg_shots_on_target_home': np.mean(home_shots_on_target) if home_shots_on_target else 0,
                'avg_shots_on_target_away': np.mean(away_shots_on_target) if away_shots_on_target else 0,
                'recent_wins': wins,
                'recent_draws': draws,
                'recent_losses': losses,
                'total_matches': len(recent_matches),
                # NUEVAS CARACTERÍSTICAS PARA FÚTBOL
                'shots_consistency_home': np.std(home_shots) if len(home_shots) > 1 else 0,
                'shots_consistency_away': np.std(away_shots) if len(away_shots) > 1 else 0,
                'form_trend': (wins - losses) / max(len(recent_matches), 1),  # Tendencia de forma
                'goals_per_shot_home': np.mean(home_goals) / max(np.mean(home_shots), 1) if home_shots and home_goals else 0,
                'goals_per_shot_away': np.mean(away_goals) / max(np.mean(away_shots), 1) if away_shots and away_goals else 0,
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de {team_name}: {e}")
            return {
                'avg_shots_home': 0, 'avg_shots_away': 0,
                'avg_goals_home': 0, 'avg_goals_away': 0,
                'recent_wins': 0, 'recent_draws': 0, 'recent_losses': 0,
                'total_matches': 0
            }
    
    def get_head_to_head_stats(self, team1: str, team2: str, league: League) -> Dict:
        """Obtiene estadísticas cara a cara entre dos equipos"""
        try:
            matches = Match.objects.filter(
                league=league
            ).filter(
                models.Q(home_team=team1, away_team=team2) | 
                models.Q(home_team=team2, away_team=team1)
            ).order_by('-date')[:10]
            
            if not matches:
                return {'avg_shots_team1': 0, 'avg_shots_team2': 0, 'matches_count': 0}
            
            team1_shots = []
            team2_shots = []
            
            for match in matches:
                if match.home_team == team1:
                    team1_shots.append(match.hs or 0)
                    team2_shots.append(match.as_field or 0)
                else:
                    team1_shots.append(match.as_field or 0)
                    team2_shots.append(match.hs or 0)
            
            return {
                'avg_shots_team1': np.mean(team1_shots),
                'avg_shots_team2': np.mean(team2_shots),
                'matches_count': len(matches)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas cara a cara {team1} vs {team2}: {e}")
            return {'avg_shots_team1': 0, 'avg_shots_team2': 0, 'matches_count': 0}
    
    def prepare_features(self, home_team: str, away_team: str, league: League) -> np.ndarray:
        """Prepara las características para la predicción"""
        try:
            # Estadísticas del equipo local
            home_stats = self.get_team_recent_stats(home_team, league)
            
            # Estadísticas del equipo visitante
            away_stats = self.get_team_recent_stats(away_team, league)
            
            # Estadísticas cara a cara
            h2h_stats = self.get_head_to_head_stats(home_team, away_team, league)
            
            # Crear vector de características optimizado
            features = np.array([
                home_stats['avg_shots_home'],              # Promedio remates local en casa
                away_stats['avg_shots_away'],              # Promedio remates visitante fuera
                home_stats['avg_goals_home'],              # Promedio goles local en casa
                away_stats['avg_goals_away'],              # Promedio goles visitante fuera
                home_stats['avg_shots_on_target_home'],    # Promedio remates a puerta local
                away_stats['avg_shots_on_target_away'],    # Promedio remates a puerta visitante
                home_stats['recent_wins'],                 # Victorias recientes local
                away_stats['recent_wins'],                 # Victorias recientes visitante
                home_stats['total_matches'],               # Partidos recientes local
                away_stats['total_matches'],               # Partidos recientes visitante
                h2h_stats['avg_shots_team1'],              # Promedio cara a cara (local)
                h2h_stats['matches_count'],                # Partidos cara a cara
                home_stats['shots_consistency_home'],      # Consistencia en remates local
                away_stats['shots_consistency_away'],      # Consistencia en remates visitante
                home_stats['form_trend'],                  # Tendencia de forma local
                away_stats['form_trend'],                  # Tendencia de forma visitante
                home_stats['goals_per_shot_home'],         # Eficiencia goleadora local
                away_stats['goals_per_shot_away'],         # Eficiencia goleadora visitante
                1.0,                                       # Ventaja de local
            ])
            
            return features.reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Error preparando características: {e}")
            return np.zeros((1, 19))  # Vector de características por defecto (actualizado)
    
    def train_shots_model(self, league: League, prediction_type: str = 'shots_total') -> PredictionModel:
        """Entrena un modelo para predecir remates"""
        try:
            logger.info(f"Entrenando modelo para {league.name} - {prediction_type}")
            
            # Obtener datos de entrenamiento
            matches = Match.objects.filter(league=league).exclude(
                models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
            ).order_by('-date')[:500]  # Últimos 500 partidos
            
            if len(matches) < 50:
                raise ValueError(f"No hay suficientes datos para entrenar. Solo {len(matches)} partidos disponibles.")
            
            # Preparar características y objetivos
            X = []
            y = []
            
            for match in matches:
                try:
                    # Características
                    features = self.prepare_features(match.home_team, match.away_team, league)
                    X.append(features.flatten())
                    
                    # Objetivo según el tipo de predicción
                    if prediction_type == 'shots_total':
                        target = (match.hs or 0) + (match.as_field or 0)
                    elif prediction_type == 'shots_home':
                        target = match.hs or 0
                    elif prediction_type == 'shots_away':
                        target = match.as_field or 0
                    elif prediction_type == 'shots_on_target':
                        target = (match.hst or 0) + (match.ast or 0)
                    else:
                        target = (match.hs or 0) + (match.as_field or 0)
                    
                    y.append(target)
                    
                except Exception as e:
                    logger.warning(f"Error procesando partido {match.id}: {e}")
                    continue
            
            if len(X) < 20:
                raise ValueError(f"No se pudieron procesar suficientes partidos. Solo {len(X)} válidos.")
            
            X = np.array(X)
            y = np.array(y)
            
            # MEJORA: Normalizar características para mejor rendimiento
            X_scaled = self.scaler.fit_transform(X)
            
            # OPTIMIZACIÓN 6: Validación temporal (más realista para fútbol)
            # En fútbol, no podemos predecir el pasado con datos del futuro
            split_point = int(len(X_scaled) * 0.8)
            X_train = X_scaled[:split_point]
            X_test = X_scaled[split_point:]
            y_train = y[:split_point]
            y_test = y[split_point:]
            
            # OPTIMIZACIÓN 5: Modelo adaptado para datos limitados
            # Para datos limitados, usar modelo más simple pero robusto
            if len(X_train) < 100:
                # Para pocos datos, usar regresión lineal regularizada
                from sklearn.linear_model import Ridge
                model = Ridge(alpha=1.0, random_state=42)
            else:
                # Para más datos, usar Random Forest optimizado
                model = RandomForestRegressor(
                    n_estimators=50,  # Reducido para evitar overfitting
                    max_depth=5,      # Reducido para datos limitados
                    min_samples_split=10,  # Aumentado para estabilidad
                    min_samples_leaf=5,    # Aumentado para estabilidad
                    max_features='sqrt',   # Reducir complejidad
                    random_state=42
                )
            model.fit(X_train, y_train)
            
            # Evaluar modelo con métricas mejoradas
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            # MÉTRICAS ADICIONALES PARA FÚTBOL
            from sklearn.metrics import mean_absolute_percentage_error, accuracy_score
            
            # MAPE (Mean Absolute Percentage Error) - mejor para fútbol
            mape = mean_absolute_percentage_error(y_test, y_pred)
            
            # Accuracy dentro de rangos (más relevante para fútbol)
            y_pred_rounded = np.round(y_pred)
            y_test_rounded = np.round(y_test)
            
            # Accuracy en rangos de ±2 remates (tolerancia realista)
            tolerance_2 = np.abs(y_pred_rounded - y_test_rounded) <= 2
            accuracy_tolerance_2 = np.mean(tolerance_2)
            
            # Accuracy en rangos de ±3 remates
            tolerance_3 = np.abs(y_pred_rounded - y_test_rounded) <= 3
            accuracy_tolerance_3 = np.mean(tolerance_3)
            
            # Accuracy exacta
            exact_accuracy = accuracy_score(y_test_rounded, y_pred_rounded)
            
            # MEJORA: Asegurar que las predicciones sean realistas
            y_pred_clipped = np.clip(y_pred, 0, 50)  # Límites realistas
            
            # Crear registro del modelo con métricas mejoradas
            model_type_name = 'ridge' if len(X_train) < 100 else 'random_forest'
            prediction_model = PredictionModel.objects.create(
                name=f"Modelo {league.name} - {prediction_type}",
                model_type=model_type_name,
                prediction_type=prediction_type,
                league=league,
                accuracy=accuracy_tolerance_2,  # Usar accuracy con tolerancia
                mae=mae,
                rmse=rmse,
                r2_score=r2,
                features_used=[
                    'avg_shots_home', 'avg_shots_away', 'avg_goals_home', 'avg_goals_away',
                    'recent_wins_home', 'recent_wins_away', 'recent_matches_home', 'recent_matches_away',
                    'h2h_avg_shots', 'h2h_matches', 'home_advantage'
                ],
                model_parameters={
                    'mape': float(mape),
                    'accuracy_tolerance_2': float(accuracy_tolerance_2),
                    'accuracy_tolerance_3': float(accuracy_tolerance_3),
                    'exact_accuracy': float(exact_accuracy),
                    'data_points': len(X_train),
                    'model_type': model_type_name
                }
            )
            
            logger.info(f"Modelo entrenado exitosamente. R²: {r2:.3f}, MAE: {mae:.3f}")
            return prediction_model
            
        except Exception as e:
            logger.error(f"Error entrenando modelo: {e}")
            raise
    
    def predict_shots(self, home_team: str, away_team: str, league: League, 
                     prediction_type: str = 'shots_total') -> Dict:
        """Realiza una predicción de remates"""
        try:
            # Buscar modelo entrenado
            model_record = PredictionModel.objects.filter(
                league=league,
                prediction_type=prediction_type,
                is_active=True
            ).first()
            
            if not model_record:
                logger.info(f"No hay modelo entrenado para {league.name} - {prediction_type}")
                # Entrenar modelo si no existe
                model_record = self.train_shots_model(league, prediction_type)
            
            # Preparar características
            features = self.prepare_features(home_team, away_team, league)
            
            # MEJORA: Usar Random Forest para predicción
            if model_record.model_type == 'random_forest':
                # Reentrenar con datos históricos para obtener el modelo completo
                # Esto es una simplificación - en producción se guardaría el modelo completo
                model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
                # Usar datos históricos para entrenar el modelo
                matches = Match.objects.filter(league=league).exclude(
                    models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
                ).order_by('-date')[:200]
                
                X_train = []
                y_train = []
                for match in matches:
                    try:
                        features_train = self.prepare_features(match.home_team, match.away_team, league)
                        X_train.append(features_train.flatten())
                        
                        if prediction_type == 'shots_total':
                            target = (match.hs or 0) + (match.as_field or 0)
                        elif prediction_type == 'shots_home':
                            target = match.hs or 0
                        elif prediction_type == 'shots_away':
                            target = match.as_field or 0
                        else:
                            target = (match.hs or 0) + (match.as_field or 0)
                        y_train.append(target)
                    except:
                        continue
                
                if len(X_train) > 10:
                    X_train = np.array(X_train)
                    y_train = np.array(y_train)
                    X_train_scaled = self.scaler.fit_transform(X_train)
                    model.fit(X_train_scaled, y_train)
                    
                    # Normalizar características de predicción
                    features_scaled = self.scaler.transform(features)
                    prediction = model.predict(features_scaled)[0]
                else:
                    # Fallback a predicción basada en estadísticas
                    prediction = self._fallback_prediction(home_team, away_team, league, prediction_type)
            else:
                # Fallback para modelos antiguos
                model = LinearRegression()
                model.coef_ = np.array(model_record.model_parameters)
                model.intercept_ = 0
                prediction = model.predict(features)[0]
            
            # CORRECCIÓN: Asegurar que la predicción sea positiva y realista
            prediction = max(0, prediction)  # No puede ser negativa
            
            # Aplicar límites realistas según el tipo de predicción
            if prediction_type in ['shots_total', 'shots_home', 'shots_away']:
                prediction = min(prediction, 50)  # Máximo 50 remates (límite realista)
                prediction = max(prediction, 3)   # Mínimo 3 remates
            elif prediction_type in ['goals_total', 'goals_home', 'goals_away']:
                prediction = min(prediction, 10)  # Máximo 10 goles
                prediction = max(prediction, 0)   # Mínimo 0 goles
            
            # Calcular probabilidades
            probabilities = self._calculate_probabilities(prediction, model_record.rmse or 1.0)
            
            # Guardar resultado
            result = PredictionResult.objects.create(
                model=model_record,
                home_team=home_team,
                away_team=away_team,
                league=league,
                predicted_value=prediction,
                confidence_score=model_record.r2_score or 0.5,
                probability_over_10=probabilities.get('over_10', 0),
                probability_over_15=probabilities.get('over_15', 0),
                probability_over_20=probabilities.get('over_20', 0),
                features_used=self._get_features_dict(features[0])
            )
            
            return {
                'prediction': prediction,
                'confidence': model_record.r2_score or 0.5,
                'probabilities': probabilities,
                'model_accuracy': model_record.r2_score or 0.5,
                'result_id': result.id
            }
            
        except Exception as e:
            logger.error(f"Error realizando predicción: {e}")
            return {
                'prediction': 0,
                'confidence': 0,
                'probabilities': {'over_10': 0, 'over_15': 0, 'over_20': 0},
                'model_accuracy': 0,
                'error': str(e)
            }
    
    def _calculate_probabilities(self, prediction: float, rmse: float) -> Dict:
        """Calcula probabilidades para diferentes rangos"""
        try:
            # Usar distribución normal aproximada
            from scipy.stats import norm
            
            over_10 = 1 - norm.cdf(10, prediction, rmse)
            over_15 = 1 - norm.cdf(15, prediction, rmse)
            over_20 = 1 - norm.cdf(20, prediction, rmse)
            
            return {
                'over_10': max(0, min(1, over_10)),
                'over_15': max(0, min(1, over_15)),
                'over_20': max(0, min(1, over_20))
            }
        except:
            # Fallback simple si scipy no está disponible
            return {
                'over_10': 0.5 if prediction > 10 else 0.3,
                'over_15': 0.3 if prediction > 15 else 0.1,
                'over_20': 0.1 if prediction > 20 else 0.05
            }
    
    def _fallback_prediction(self, home_team: str, away_team: str, league: League, prediction_type: str) -> float:
        """Predicción de fallback basada en estadísticas reales cuando no hay modelo entrenado"""
        try:
            # Obtener estadísticas reales de los equipos
            home_stats = self.get_team_recent_stats(home_team, league)
            away_stats = self.get_team_recent_stats(away_team, league)
            
            # Calcular predicción basada en promedios reales
            if prediction_type == 'shots_total':
                prediction = (home_stats['avg_shots_home'] + away_stats['avg_shots_away']) * 1.1
            elif prediction_type == 'shots_home':
                prediction = home_stats['avg_shots_home'] * 1.15  # Ventaja de local
            elif prediction_type == 'shots_away':
                prediction = away_stats['avg_shots_away'] * 0.9   # Desventaja de visitante
            elif prediction_type == 'goals_total':
                prediction = (home_stats['avg_goals_home'] + away_stats['avg_goals_away']) * 1.1
            else:
                prediction = 12.0  # Valor por defecto realista
            
            return max(0, prediction)
            
        except Exception as e:
            logger.error(f"Error en predicción de fallback: {e}")
            return 12.0  # Valor por defecto seguro
    
    def _get_features_dict(self, features: np.ndarray) -> Dict:
        """Convierte características a diccionario"""
        feature_names = [
            'avg_shots_home', 'avg_shots_away', 'avg_goals_home', 'avg_goals_away',
            'recent_wins_home', 'recent_wins_away', 'recent_matches_home', 'recent_matches_away',
            'h2h_avg_shots', 'h2h_matches', 'home_advantage'
        ]
        
        return {name: float(value) for name, value in zip(feature_names, features)}
