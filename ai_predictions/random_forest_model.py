"""
Modelo Random Forest para predicción de shots y corners.
Captura relaciones no lineales y complejas entre variables.
"""

import numpy as np
import logging
from typing import Dict, List, Tuple
from datetime import timedelta
from django.utils import timezone
from football_data.models import Match, League
from .simple_models import get_league_realistic_limits, analyze_team_statistics

logger = logging.getLogger('ai_predictions')


class RandomForestModel:
    """
    Modelo Random Forest para predicción de shots y corners.
    
    Este modelo es especialmente útil para capturar relaciones no lineales
    y complejas entre variables que los modelos estadísticos simples no pueden manejar.
    """
    
    def __init__(self):
        self.name = "Random Forest"
        self.n_estimators = 50  # Número de árboles
        self.max_depth = 8  # Profundidad máxima
        self.min_samples_split = 5  # Mínimo de muestras para dividir
    
    def predict_match(self, home_team: str, away_team: str, league: League,
                     prediction_type: str = 'shots_total') -> Dict:
        """
        Predice un partido usando Random Forest.
        
        Args:
            home_team: Equipo local
            away_team: Equipo visitante
            league: Liga
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con la predicción y probabilidades
        """
        try:
            if 'goals' in prediction_type:
                # Para goles, usar modelo más simple (Random Forest no es ideal para goles)
                return self._simple_goals_prediction(home_team, away_team, league, prediction_type)
            
            # Obtener características del partido
            features = self._extract_features(home_team, away_team, league, prediction_type)
            
            if not features:
                return self._fallback_prediction(prediction_type)
            
            # Obtener datos históricos para entrenamiento
            training_data = self._get_training_data(league, prediction_type)
            
            if len(training_data['X']) < 20:
                logger.warning(f"Pocos datos para Random Forest ({len(training_data['X'])}), usando fallback")
                return self._fallback_prediction(prediction_type)
            
            # Entrenar modelo
            model = self._train_random_forest(training_data['X'], training_data['y'])
            
            # Hacer predicción
            prediction = model.predict([features])[0]
            
            # Calcular confianza basada en la varianza de los árboles
            predictions_trees = [tree.predict([features])[0] for tree in model.estimators_]
            confidence = max(0.3, min(0.9, 1.0 - (np.std(predictions_trees) / np.mean(predictions_trees))))
            
            # Calcular probabilidades
            probabilities = self._calculate_probabilities(model, features, prediction_type)
            
            return {
                'model_name': self.name,
                'prediction': float(prediction),
                'confidence': float(confidence),
                'probabilities': probabilities,
                'total_matches': len(training_data['X']),
                'model_type': 'random_forest',
                'feature_importance': self._get_feature_importance(model)
            }
            
        except Exception as e:
            logger.error(f"Error en predicción Random Forest: {e}")
            return self._fallback_prediction(prediction_type)
    
    def _extract_features(self, home_team: str, away_team: str, league: League, 
                         prediction_type: str) -> List[float]:
        """
        Extrae características del partido para el modelo.
        
        Args:
            home_team: Equipo local
            away_team: Equipo visitante
            league: Liga
            prediction_type: Tipo de predicción
        
        Returns:
            Lista de características
        """
        try:
            cutoff_date = timezone.now().date() - timedelta(days=365)
            
            # Estadísticas del equipo local
            home_matches = Match.objects.filter(
                league=league,
                home_team=home_team,
                date__gte=cutoff_date
            ).order_by('-date')[:20]
            
            # Estadísticas del equipo visitante
            away_matches = Match.objects.filter(
                league=league,
                away_team=away_team,
                date__gte=cutoff_date
            ).order_by('-date')[:20]
            
            # Estadísticas de la liga
            league_matches = Match.objects.filter(
                league=league,
                date__gte=cutoff_date
            ).order_by('-date')[:100]
            
            features = []
            
            if 'shots' in prediction_type:
                # Características para shots
                home_shots = [m.hs for m in home_matches if m.hs is not None]
                away_shots = [m.as_field for m in away_matches if m.as_field is not None]
                home_shots_against = [m.as_field for m in home_matches if m.as_field is not None]
                away_shots_against = [m.hs for m in away_matches if m.hs is not None]
                
                # Estadísticas básicas
                features.extend([
                    np.mean(home_shots) if home_shots else 12.0,  # Promedio shots local
                    np.mean(away_shots) if away_shots else 11.0,  # Promedio shots visitante
                    np.mean(home_shots_against) if home_shots_against else 11.0,  # Shots recibidos local
                    np.mean(away_shots_against) if away_shots_against else 12.0,  # Shots recibidos visitante
                    np.std(home_shots) if len(home_shots) > 1 else 3.0,  # Variabilidad local
                    np.std(away_shots) if len(away_shots) > 1 else 3.0,  # Variabilidad visitante
                ])
                
                # Estadísticas de la liga
                league_home_shots = [m.hs for m in league_matches if m.hs is not None]
                league_away_shots = [m.as_field for m in league_matches if m.as_field is not None]
                features.extend([
                    np.mean(league_home_shots) if league_home_shots else 12.0,  # Media liga local
                    np.mean(league_away_shots) if league_away_shots else 11.0,  # Media liga visitante
                ])
                
            elif 'corners' in prediction_type:
                # Características para corners
                home_corners = [m.hc for m in home_matches if m.hc is not None]
                away_corners = [m.ac for m in away_matches if m.ac is not None]
                home_corners_against = [m.ac for m in home_matches if m.ac is not None]
                away_corners_against = [m.hc for m in away_matches if m.hc is not None]
                
                # Estadísticas básicas
                features.extend([
                    np.mean(home_corners) if home_corners else 5.5,  # Promedio corners local
                    np.mean(away_corners) if away_corners else 4.5,  # Promedio corners visitante
                    np.mean(home_corners_against) if home_corners_against else 4.5,  # Corners recibidos local
                    np.mean(away_corners_against) if away_corners_against else 5.5,  # Corners recibidos visitante
                    np.std(home_corners) if len(home_corners) > 1 else 2.0,  # Variabilidad local
                    np.std(away_corners) if len(away_corners) > 1 else 2.0,  # Variabilidad visitante
                ])
                
                # Estadísticas de la liga
                league_home_corners = [m.hc for m in league_matches if m.hc is not None]
                league_away_corners = [m.ac for m in league_matches if m.ac is not None]
                features.extend([
                    np.mean(league_home_corners) if league_home_corners else 5.5,  # Media liga local
                    np.mean(league_away_corners) if league_away_corners else 4.5,  # Media liga visitante
                ])
            
            # Características adicionales
            features.extend([
                len(home_matches) / 20.0,  # Cantidad de datos local (normalizado)
                len(away_matches) / 20.0,  # Cantidad de datos visitante (normalizado)
                1.0,  # Ventaja de local (constante)
                0.0,  # Desventaja de visitante (constante)
            ])
            
            return features
            
        except Exception as e:
            logger.error(f"Error extrayendo características: {e}")
            return []
    
    def _get_training_data(self, league: League, prediction_type: str) -> Dict:
        """
        Obtiene datos de entrenamiento para el modelo.
        
        Args:
            league: Liga
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con características (X) y objetivos (y)
        """
        try:
            cutoff_date = timezone.now().date() - timedelta(days=730)  # 2 años
            
            # Obtener partidos históricos
            matches = Match.objects.filter(
                league=league,
                date__gte=cutoff_date
            ).order_by('-date')[:200]
            
            X = []  # Características
            y = []  # Objetivos
            
            for match in matches:
                try:
                    # Extraer características del partido
                    features = self._extract_features_from_match(match, prediction_type)
                    
                    if features is None:
                        continue
                    
                    X.append(features)
                    
                    # Extraer objetivo
                    if 'shots' in prediction_type:
                        if 'total' in prediction_type:
                            target = (match.hs or 0) + (match.as_field or 0)
                        elif 'home' in prediction_type:
                            target = match.hs or 0
                        elif 'away' in prediction_type:
                            target = match.as_field or 0
                        else:
                            target = (match.hs or 0) + (match.as_field or 0)
                    elif 'corners' in prediction_type:
                        if 'total' in prediction_type:
                            target = (match.hc or 0) + (match.ac or 0)
                        elif 'home' in prediction_type:
                            target = match.hc or 0
                        elif 'away' in prediction_type:
                            target = match.ac or 0
                        else:
                            target = (match.hc or 0) + (match.ac or 0)
                    else:
                        continue
                    
                    y.append(target)
                    
                except Exception as e:
                    continue
            
            return {'X': X, 'y': y}
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de entrenamiento: {e}")
            return {'X': [], 'y': []}
    
    def _extract_features_from_match(self, match: Match, prediction_type: str) -> List[float]:
        """
        Extrae características de un partido específico.
        
        Args:
            match: Partido
            prediction_type: Tipo de predicción
        
        Returns:
            Lista de características
        """
        try:
            cutoff_date = match.date - timedelta(days=365)
            
            # Estadísticas previas del equipo local
            home_prev_matches = Match.objects.filter(
                league=match.league,
                home_team=match.home_team,
                date__lt=match.date,
                date__gte=cutoff_date
            ).order_by('-date')[:10]
            
            # Estadísticas previas del equipo visitante
            away_prev_matches = Match.objects.filter(
                league=match.league,
                away_team=match.away_team,
                date__lt=match.date,
                date__gte=cutoff_date
            ).order_by('-date')[:10]
            
            features = []
            
            if 'shots' in prediction_type:
                # Características para shots
                home_shots = [m.hs for m in home_prev_matches if m.hs is not None]
                away_shots = [m.as_field for m in away_prev_matches if m.as_field is not None]
                
                features.extend([
                    np.mean(home_shots) if home_shots else 12.0,
                    np.mean(away_shots) if away_shots else 11.0,
                    np.std(home_shots) if len(home_shots) > 1 else 3.0,
                    np.std(away_shots) if len(away_shots) > 1 else 3.0,
                    len(home_shots) / 10.0,
                    len(away_shots) / 10.0,
                ])
                
            elif 'corners' in prediction_type:
                # Características para corners
                home_corners = [m.hc for m in home_prev_matches if m.hc is not None]
                away_corners = [m.ac for m in away_prev_matches if m.ac is not None]
                
                features.extend([
                    np.mean(home_corners) if home_corners else 5.5,
                    np.mean(away_corners) if away_corners else 4.5,
                    np.std(home_corners) if len(home_corners) > 1 else 2.0,
                    np.std(away_corners) if len(away_corners) > 1 else 2.0,
                    len(home_corners) / 10.0,
                    len(away_corners) / 10.0,
                ])
            
            # Características adicionales
            features.extend([
                1.0,  # Ventaja de local
                0.0,  # Desventaja de visitante
            ])
            
            return features
            
        except Exception as e:
            logger.error(f"Error extrayendo características del partido: {e}")
            return None
    
    def _train_random_forest(self, X: List[List[float]], y: List[float]):
        """
        Entrena un modelo Random Forest.
        
        Args:
            X: Características
            y: Objetivos
        
        Returns:
            Modelo entrenado
        """
        try:
            from sklearn.ensemble import RandomForestRegressor
            
            # Crear y entrenar modelo
            model = RandomForestRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                random_state=42,
                n_jobs=1  # Usar solo 1 core para evitar problemas
            )
            
            model.fit(X, y)
            return model
            
        except ImportError:
            logger.warning("sklearn no disponible, usando modelo simple")
            return self._simple_regression_model(X, y)
        except Exception as e:
            logger.error(f"Error entrenando Random Forest: {e}")
            return self._simple_regression_model(X, y)
    
    def _simple_regression_model(self, X: List[List[float]], y: List[float]):
        """
        Modelo de regresión simple como fallback.
        
        Args:
            X: Características
            y: Objetivos
        
        Returns:
            Modelo simple
        """
        class SimpleModel:
            def __init__(self, X, y):
                self.X = X
                self.y = y
                self.avg = np.mean(y) if y else 10.0
            
            def predict(self, features):
                # Predicción simple basada en promedio
                return [self.avg] * len(features)
            
            @property
            def estimators_(self):
                # Simular árboles para compatibilidad
                return [self] * 10
        
        return SimpleModel(X, y)
    
    def _calculate_probabilities(self, model, features: List[float], prediction_type: str) -> Dict:
        """
        Calcula probabilidades para diferentes umbrales.
        
        Args:
            model: Modelo entrenado
            features: Características del partido
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con probabilidades
        """
        try:
            probabilities = {}
            
            # Obtener predicciones de todos los árboles
            if hasattr(model, 'estimators_'):
                predictions_trees = [tree.predict([features])[0] for tree in model.estimators_]
                mean_prediction = np.mean(predictions_trees)
                std_prediction = np.std(predictions_trees)
            else:
                mean_prediction = model.predict([features])[0]
                std_prediction = mean_prediction * 0.2  # Estimación de desviación
            
            # Calcular probabilidades usando distribución normal
            if 'corners' in prediction_type:
                thresholds = [5, 7, 9, 12, 15]
            else:  # shots
                thresholds = [10, 15, 20, 25, 30]
            
            for threshold in thresholds:
                # P(X > threshold) usando distribución normal
                z_score = (threshold - mean_prediction) / max(std_prediction, 0.1)
                prob = 1 - self._normal_cdf(z_score)
                probabilities[f'over_{threshold}'] = max(0.0, min(1.0, prob))
            
            return probabilities
            
        except Exception as e:
            logger.error(f"Error calculando probabilidades: {e}")
            return {}
    
    def _normal_cdf(self, z: float) -> float:
        """
        Función de distribución acumulada normal aproximada.
        
        Args:
            z: Valor z
        
        Returns:
            Probabilidad acumulada
        """
        return 0.5 * (1 + np.sign(z) * np.sqrt(1 - np.exp(-2 * z**2 / np.pi)))
    
    def _get_feature_importance(self, model) -> Dict:
        """
        Obtiene la importancia de las características.
        
        Args:
            model: Modelo entrenado
        
        Returns:
            Diccionario con importancia de características
        """
        try:
            if hasattr(model, 'feature_importances_'):
                features = ['home_avg', 'away_avg', 'home_std', 'away_std', 'home_data', 'away_data', 
                           'league_home_avg', 'league_away_avg', 'home_advantage', 'away_disadvantage']
                importance = {}
                for i, feature in enumerate(features):
                    if i < len(model.feature_importances_):
                        importance[feature] = float(model.feature_importances_[i])
                return importance
            else:
                return {}
        except Exception as e:
            logger.error(f"Error obteniendo importancia de características: {e}")
            return {}
    
    def _simple_goals_prediction(self, home_team: str, away_team: str, league: League,
                                prediction_type: str) -> Dict:
        """
        Predicción simple para goles (Random Forest no es ideal para goles).
        
        Args:
            home_team: Equipo local
            away_team: Equipo visitante
            league: Liga
            prediction_type: Tipo de predicción
        
        Returns:
            Diccionario con predicción
        """
        try:
            # Usar límites y estadísticas
            lambda_min, lambda_max = get_league_realistic_limits(league, 'goals')
            home_stats = analyze_team_statistics(home_team, league, 'goals')
            away_stats = analyze_team_statistics(away_team, league, 'goals')
            
            # Calcular lambda
            home_avg = home_stats['overall_avg'] if home_stats['overall_avg'] > 0 else 1.5
            away_avg = away_stats['overall_avg'] if away_stats['overall_avg'] > 0 else 1.2
            
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
            thresholds = [1, 2, 3, 4, 5]
            for threshold in thresholds:
                prob = max(0, min(1, 1 - (threshold / prediction) if prediction > 0 else 0.5))
                probabilities[f'over_{threshold}'] = prob
            
            return {
                'model_name': f"{self.name} (Goals)",
                'prediction': prediction,
                'confidence': 0.6,
                'probabilities': probabilities,
                'total_matches': home_stats['total_matches'] + away_stats['total_matches'],
                'model_type': 'random_forest_goals'
            }
            
        except Exception as e:
            logger.error(f"Error en predicción Random Forest para goles: {e}")
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
            'model_type': 'random_forest_fallback',
            'error': 'Fallback debido a falta de datos'
        }
