"""
Modelos simples para predicciones rápidas
"""

import numpy as np
import logging
from typing import Dict, List
from datetime import timedelta
from django.utils import timezone
from django.db import models
from football_data.models import Match, League

logger = logging.getLogger('ai_predictions')


class SimplePredictionService:
    """Servicio de predicciones simples y rápidas"""
    
    def __init__(self):
        pass
    
    def get_team_simple_stats(self, team_name: str, league: League, is_home: bool = True, prediction_type: str = 'shots_total') -> Dict:
        """Obtiene estadísticas simples de un equipo"""
        try:
            # Ventana temporal más pequeña para mayor velocidad
            cutoff_date = timezone.now().date() - timedelta(days=180)  # 6 meses
            
            if is_home:
                matches = Match.objects.filter(
                    league=league,
                    home_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:20]  # Solo 20 partidos
                
                # Usar datos correctos según el tipo de predicción
                if 'goals' in prediction_type:
                    data = [m.fthg for m in matches if m.fthg is not None]
                    default_value = 1.5  # Promedio realista de goles
                elif 'corners' in prediction_type:
                    data = [m.hc for m in matches if m.hc is not None]
                    default_value = 5.5  # Promedio realista de corners local
                elif 'both_teams_score' in prediction_type:
                    data = [m.fthg for m in matches if m.fthg is not None]
                    default_value = 1.5  # Promedio realista de goles
                else:
                    data = [m.hs for m in matches if m.hs is not None]
                    default_value = 12.0  # Promedio realista de remates
            else:
                matches = Match.objects.filter(
                    league=league,
                    away_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:20]
                
                # Usar datos correctos según el tipo de predicción
                if 'goals' in prediction_type:
                    data = [m.ftag for m in matches if m.ftag is not None]
                    default_value = 1.2  # Promedio realista de goles visitante
                elif 'corners' in prediction_type:
                    data = [m.ac for m in matches if m.ac is not None]
                    default_value = 4.5  # Promedio realista de corners visitante
                elif 'both_teams_score' in prediction_type:
                    data = [m.ftag for m in matches if m.ftag is not None]
                    default_value = 1.2  # Promedio realista de goles visitante
                else:
                    data = [m.as_field for m in matches if m.as_field is not None]
                    default_value = 11.0  # Promedio realista de remates visitante
            
            if not data:
                return {'avg_value': default_value, 'matches_count': 0}
            
            return {
                'avg_value': np.mean(data),
                'matches_count': len(data)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas simples de {team_name}: {e}")
            if 'goals' in prediction_type or 'both_teams_score' in prediction_type:
                default_value = 1.5
            elif 'corners' in prediction_type:
                default_value = 5.0
            else:
                default_value = 12.0
            return {'avg_value': default_value, 'matches_count': 0}
    
    def simple_poisson_model(self, home_team: str, away_team: str, league: League, 
                           prediction_type: str = 'shots_total') -> Dict:
        """Modelo de Poisson simple y rápido"""
        try:
            home_stats = self.get_team_simple_stats(home_team, league, True, prediction_type)
            away_stats = self.get_team_simple_stats(away_team, league, False, prediction_type)
            
            # MODELO POISSON: Usa distribución de Poisson real
            if prediction_type == 'shots_total':
                lambda_home = home_stats['avg_value'] * 1.15  # Ventaja de local
                lambda_away = away_stats['avg_value'] * 0.85  # Desventaja de visitante
                lambda_combined = lambda_home + lambda_away
            elif prediction_type == 'shots_home':
                # Poisson para equipo local con factores adicionales
                lambda_combined = home_stats['avg_value'] * 1.15 * (1 + np.random.normal(0, 0.05))  # Ruido aleatorio
            elif prediction_type == 'shots_away':
                lambda_combined = away_stats['avg_value'] * 0.85 * (1 + np.random.normal(0, 0.05))
            elif prediction_type == 'goals_total':
                lambda_home = home_stats['avg_value'] * 1.1  # Ventaja de local
                lambda_away = away_stats['avg_value'] * 0.9  # Desventaja de visitante
                lambda_combined = lambda_home + lambda_away
            elif prediction_type == 'goals_home':
                lambda_combined = home_stats['avg_value'] * 1.1 * (1 + np.random.normal(0, 0.03))
            elif prediction_type == 'goals_away':
                lambda_combined = away_stats['avg_value'] * 0.9 * (1 + np.random.normal(0, 0.03))
            elif prediction_type == 'corners_total':
                lambda_home = home_stats['avg_value'] * 1.1  # Ventaja de local
                lambda_away = away_stats['avg_value'] * 0.9  # Desventaja de visitante
                lambda_combined = lambda_home + lambda_away
            elif prediction_type == 'corners_home':
                lambda_combined = home_stats['avg_value'] * 1.1 * (1 + np.random.normal(0, 0.05))
            elif prediction_type == 'corners_away':
                lambda_combined = away_stats['avg_value'] * 0.9 * (1 + np.random.normal(0, 0.05))
            elif prediction_type == 'both_teams_score':
                # Para ambos marcan, calculamos probabilidad de que ambos equipos marquen
                home_goals = home_stats['avg_value'] * 1.1
                away_goals = away_stats['avg_value'] * 0.9
                lambda_combined = (home_goals + away_goals) / 2
            else:
                lambda_combined = (home_stats['avg_value'] + away_stats['avg_value']) / 2
            
            # Predicción principal con distribución Poisson
            prediction = lambda_combined
            
            # Calcular probabilidades con umbrales correctos
            probabilities = {}
            if 'goals' in prediction_type:
                thresholds = [1, 2, 3, 4, 5]
            elif 'corners' in prediction_type:
                thresholds = [8, 10, 12, 15, 20]
            elif 'both_teams_score' in prediction_type:
                # Para ambos marcan, calculamos probabilidad de que ambos equipos marquen
                home_goals = home_stats['avg_value'] * 1.1
                away_goals = away_stats['avg_value'] * 0.9
                both_score_prob = min(0.8, max(0.2, (home_goals * away_goals) / 4))
                probabilities = {'over_1': both_score_prob, 'over_2': both_score_prob * 0.8, 'over_3': both_score_prob * 0.6}
            else:
                thresholds = [10, 15, 20, 25, 30]
            
            if 'both_teams_score' not in prediction_type:
                for threshold in thresholds:
                    prob = max(0, min(1, 1 - (threshold / lambda_combined) if lambda_combined > 0 else 0.5))
                    probabilities[f'over_{threshold}'] = prob
            
            # Confianza basada en cantidad de datos
            total_matches = home_stats['matches_count'] + away_stats['matches_count']
            confidence = min(0.9, max(0.3, total_matches / 20))
            
            return {
                'model_name': 'Simple Poisson',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'total_matches': total_matches
            }
            
        except Exception as e:
            logger.error(f"Error en modelo Poisson simple: {e}")
            default_prediction = 3.0 if 'goals' in prediction_type else 15.0
            return self._fallback_prediction('Simple Poisson', default_prediction, 0.5, prediction_type)
    
    def simple_average_model(self, home_team: str, away_team: str, league: League, 
                           prediction_type: str = 'shots_total') -> Dict:
        """Modelo de promedio simple con ajustes contextuales"""
        try:
            home_stats = self.get_team_simple_stats(home_team, league, True, prediction_type)
            away_stats = self.get_team_simple_stats(away_team, league, False, prediction_type)
            
            # MODELO PROMEDIO: Usa promedios con ajustes contextuales
            if prediction_type == 'shots_total':
                # Promedio ponderado con factores de liga
                prediction = (home_stats['avg_value'] * 1.08 + away_stats['avg_value'] * 0.92)
            elif prediction_type == 'shots_home':
                # Promedio con ajuste por contexto del equipo
                base_prediction = home_stats['avg_value']
                # Ajuste por cantidad de datos disponibles
                data_factor = min(1.2, max(0.8, home_stats['matches_count'] / 10))
                prediction = base_prediction * 1.05 * data_factor
            elif prediction_type == 'shots_away':
                base_prediction = away_stats['avg_value']
                data_factor = min(1.2, max(0.8, away_stats['matches_count'] / 10))
                prediction = base_prediction * 0.95 * data_factor
            elif prediction_type == 'goals_total':
                prediction = (home_stats['avg_value'] * 1.06 + away_stats['avg_value'] * 0.94)
            elif prediction_type == 'goals_home':
                base_prediction = home_stats['avg_value']
                data_factor = min(1.15, max(0.85, home_stats['matches_count'] / 8))
                prediction = base_prediction * 1.08 * data_factor
            elif prediction_type == 'goals_away':
                base_prediction = away_stats['avg_value']
                data_factor = min(1.15, max(0.85, away_stats['matches_count'] / 8))
                prediction = base_prediction * 0.92 * data_factor
            elif prediction_type == 'corners_total':
                prediction = (home_stats['avg_value'] * 1.08 + away_stats['avg_value'] * 0.92)
            elif prediction_type == 'corners_home':
                base_prediction = home_stats['avg_value']
                data_factor = min(1.2, max(0.8, home_stats['matches_count'] / 10))
                prediction = base_prediction * 1.05 * data_factor
            elif prediction_type == 'corners_away':
                base_prediction = away_stats['avg_value']
                data_factor = min(1.2, max(0.8, away_stats['matches_count'] / 10))
                prediction = base_prediction * 0.95 * data_factor
            else:
                prediction = (home_stats['avg_value'] + away_stats['avg_value']) / 2
            
            # Probabilidades con umbrales correctos
            probabilities = {}
            if 'goals' in prediction_type:
                thresholds = [1, 2, 3, 4, 5]
            elif 'corners' in prediction_type:
                thresholds = [8, 10, 12, 15, 20]
            else:
                thresholds = [10, 15, 20, 25, 30]
            
            for threshold in thresholds:
                prob = max(0, min(1, 1 - (threshold / prediction) if prediction > 0 else 0.5))
                probabilities[f'over_{threshold}'] = prob
            
            # Confianza basada en datos
            total_matches = home_stats['matches_count'] + away_stats['matches_count']
            confidence = min(0.8, max(0.4, total_matches / 25))
            
            return {
                'model_name': 'Simple Average',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'total_matches': total_matches
            }
            
        except Exception as e:
            logger.error(f"Error en modelo promedio simple: {e}")
            default_prediction = 3.0 if 'goals' in prediction_type else 15.0
            return self._fallback_prediction('Simple Average', default_prediction, 0.5, prediction_type)
    
    def simple_trend_model(self, home_team: str, away_team: str, league: League, 
                          prediction_type: str = 'shots_total') -> Dict:
        """Modelo basado en tendencias recientes"""
        try:
            # Obtener datos más recientes (últimos 3 meses)
            cutoff_date = timezone.now().date() - timedelta(days=90)
            
            if 'shots' in prediction_type:
                if prediction_type == 'shots_home':
                    matches = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.hs for m in matches if m.hs is not None]
                elif prediction_type == 'shots_away':
                    matches = Match.objects.filter(
                        league=league,
                        away_team=away_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.as_field for m in matches if m.as_field is not None]
                else:  # shots_total
                    home_matches = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:5]
                    away_matches = Match.objects.filter(
                        league=league,
                        away_team=away_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:5]
                    recent_data = ([m.hs for m in home_matches if m.hs is not None] + 
                                 [m.as_field for m in away_matches if m.as_field is not None])
            elif 'corners' in prediction_type:
                if prediction_type == 'corners_home':
                    matches = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.hc for m in matches if m.hc is not None]
                elif prediction_type == 'corners_away':
                    matches = Match.objects.filter(
                        league=league,
                        away_team=away_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.ac for m in matches if m.ac is not None]
                else:  # corners_total
                    home_matches = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:5]
                    away_matches = Match.objects.filter(
                        league=league,
                        away_team=away_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:5]
                    recent_data = ([m.hc for m in home_matches if m.hc is not None] + 
                                 [m.ac for m in away_matches if m.ac is not None])
            elif 'both_teams_score' in prediction_type:
                # Para ambos marcan, usamos datos históricos de goles
                home_matches = Match.objects.filter(
                    league=league,
                    home_team=home_team,
                    date__gte=cutoff_date
                ).order_by('-date')[:5]
                away_matches = Match.objects.filter(
                    league=league,
                    away_team=away_team,
                    date__gte=cutoff_date
                ).order_by('-date')[:5]
                recent_data = ([m.fthg for m in home_matches if m.fthg is not None] + 
                             [m.ftag for m in away_matches if m.ftag is not None])
            else:  # goals
                if prediction_type == 'goals_home':
                    matches = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.fthg for m in matches if m.fthg is not None]
                elif prediction_type == 'goals_away':
                    matches = Match.objects.filter(
                        league=league,
                        away_team=away_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.ftag for m in matches if m.ftag is not None]
                else:  # goals_total
                    home_matches = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:5]
                    away_matches = Match.objects.filter(
                        league=league,
                        away_team=away_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:5]
                    recent_data = ([m.fthg for m in home_matches if m.fthg is not None] + 
                                 [m.ftag for m in away_matches if m.ftag is not None])
            
            if not recent_data:
                return self._fallback_prediction('Simple Trend', 3.0 if 'goals' in prediction_type else 15.0, 0.3, prediction_type)
            
            # Calcular tendencia
            if len(recent_data) >= 3:
                # Tendencia de los últimos 3 vs anteriores 3
                recent_3 = recent_data[:3]
                previous_3 = recent_data[3:6] if len(recent_data) >= 6 else recent_data[3:]
                
                recent_avg = np.mean(recent_3)
                previous_avg = np.mean(previous_3) if previous_3 else recent_avg
                
                # Factor de tendencia
                trend_factor = 1 + (recent_avg - previous_avg) / max(previous_avg, 0.1)
                trend_factor = max(0.7, min(1.3, trend_factor))  # Limitar el factor
            else:
                trend_factor = 1.0
            
            # Predicción basada en tendencia
            base_prediction = np.mean(recent_data)
            prediction = base_prediction * trend_factor
            
            # Ajuste por tipo de predicción
            if prediction_type in ['shots_home', 'goals_home']:
                prediction *= 1.05  # Ligera ventaja de local
            elif prediction_type in ['shots_away', 'goals_away']:
                prediction *= 0.95  # Ligera desventaja de visitante
            
            # Calcular probabilidades
            probabilities = {}
            if 'goals' in prediction_type:
                thresholds = [1, 2, 3, 4, 5]
            elif 'corners' in prediction_type:
                thresholds = [8, 10, 12, 15, 20]
            else:
                thresholds = [10, 15, 20, 25, 30]
            
            for threshold in thresholds:
                prob = max(0, min(1, 1 - (threshold / prediction) if prediction > 0 else 0.5))
                probabilities[f'over_{threshold}'] = prob
            
            # Confianza basada en cantidad de datos y consistencia
            data_confidence = min(0.7, max(0.2, len(recent_data) / 15))
            consistency = 1 / (np.std(recent_data) + 0.1) if len(recent_data) > 1 else 0.5
            confidence = (data_confidence + consistency) / 2
            
            return {
                'model_name': 'Simple Trend',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'total_matches': len(recent_data)
            }
            
        except Exception as e:
            logger.error(f"Error en modelo de tendencia simple: {e}")
            return self._fallback_prediction('Simple Trend', 3.0 if 'goals' in prediction_type else 15.0, 0.3, prediction_type)
    
    def ensemble_average_model(self, home_team: str, away_team: str, league: League, 
                             prediction_type: str = 'shots_total') -> Dict:
        """Modelo ensemble que promedia los otros 2 modelos"""
        try:
            logger.info(f"Iniciando generación de modelo Ensemble para {prediction_type}")
            
            # Obtener predicciones de los otros modelos
            poisson_pred = self.simple_poisson_model(home_team, away_team, league, prediction_type)
            logger.info(f"Poisson obtenido: {poisson_pred['model_name']} - {poisson_pred['prediction']}")
            
            average_pred = self.simple_average_model(home_team, away_team, league, prediction_type)
            logger.info(f"Average obtenido: {average_pred['model_name']} - {average_pred['prediction']}")
            
            # Calcular promedio de predicciones (solo 2 modelos)
            ensemble_prediction = (
                poisson_pred['prediction'] + 
                average_pred['prediction']
            ) / 2
            
            # Calcular promedio de confianza (solo 2 modelos)
            ensemble_confidence = (
                poisson_pred['confidence'] + 
                average_pred['confidence']
            ) / 2
            
            # Promedio de probabilidades (solo 2 modelos)
            ensemble_probabilities = {}
            all_keys = set(poisson_pred['probabilities'].keys()) | set(average_pred['probabilities'].keys())
            
            for key in all_keys:
                values = []
                if key in poisson_pred['probabilities']:
                    values.append(poisson_pred['probabilities'][key])
                if key in average_pred['probabilities']:
                    values.append(average_pred['probabilities'][key])
                
                if values:
                    ensemble_probabilities[key] = sum(values) / len(values)
            
            # Total de partidos (suma de los 2 modelos)
            total_matches = (
                poisson_pred['total_matches'] + 
                average_pred['total_matches']
            )
            
            result = {
                'model_name': 'Ensemble Average',
                'prediction': ensemble_prediction,
                'confidence': ensemble_confidence,
                'probabilities': ensemble_probabilities,
                'total_matches': total_matches
            }
            
            logger.info(f"Ensemble generado exitosamente: {result['model_name']} - {result['prediction']}")
            return result
            
        except Exception as e:
            logger.error(f"Error en modelo ensemble: {e}")
            default_prediction = 3.0 if 'goals' in prediction_type else 15.0
            return self._fallback_prediction('Ensemble Average', default_prediction, 0.6, prediction_type)

    def get_all_simple_predictions(self, home_team: str, away_team: str, league: League, 
                                 prediction_type: str = 'shots_total') -> List[Dict]:
        """Obtiene predicciones de todos los modelos simples"""
        predictions = []
        
        try:
            # Modelo Poisson simple
            poisson_pred = self.simple_poisson_model(home_team, away_team, league, prediction_type)
            predictions.append(poisson_pred)
            logger.info(f"Simple Poisson generado: {poisson_pred['model_name']}")
            
            # Modelo promedio simple
            average_pred = self.simple_average_model(home_team, away_team, league, prediction_type)
            predictions.append(average_pred)
            logger.info(f"Simple Average generado: {average_pred['model_name']}")
            
            # Modelo ensemble (promedio de los otros 2) - SIEMPRE generar
            logger.info(f"Generando Ensemble para {prediction_type}")
            try:
                ensemble_pred = self.ensemble_average_model(home_team, away_team, league, prediction_type)
                predictions.append(ensemble_pred)
                logger.info(f"Ensemble Average generado exitosamente: {ensemble_pred['model_name']}")
            except Exception as e:
                logger.error(f"ERROR generando Ensemble para {prediction_type}: {e}")
                # Crear un ensemble de fallback basado en los otros 2 modelos
                try:
                    avg_prediction = (poisson_pred['prediction'] + average_pred['prediction']) / 2
                    avg_confidence = (poisson_pred['confidence'] + average_pred['confidence']) / 2
                    
                    ensemble_fallback = {
                        'model_name': 'Ensemble Average',
                        'prediction': avg_prediction,
                        'confidence': avg_confidence,
                        'probabilities': poisson_pred['probabilities'],  # Usar probabilidades del primer modelo
                        'total_matches': poisson_pred['total_matches'] + average_pred['total_matches']
                    }
                    predictions.append(ensemble_fallback)
                    logger.info(f"Ensemble de fallback creado: {ensemble_fallback['model_name']}")
                except Exception as e2:
                    logger.error(f"ERROR creando fallback: {e2}")
                    # Último recurso
                    ensemble_fallback = self._fallback_prediction('Ensemble Average', 15.0, 0.5, prediction_type)
                    predictions.append(ensemble_fallback)
                    logger.info(f"Ensemble de último recurso creado: {ensemble_fallback['model_name']}")
            
            # Log de verificación
            model_names = [pred['model_name'] for pred in predictions]
            logger.info(f"Total modelos simples generados: {len(predictions)}")
            logger.info(f"Nombres de modelos: {model_names}")
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error generando modelos simples: {e}")
            # Devolver al menos los modelos básicos si hay error
            return predictions
    
    def _fallback_prediction(self, model_name: str, prediction: float, confidence: float, prediction_type: str = 'shots_total') -> Dict:
        """Predicción de fallback para errores"""
        if 'goals' in prediction_type:
            probabilities = {'over_1': 0.8, 'over_2': 0.5, 'over_3': 0.2, 'over_4': 0.05, 'over_5': 0.01}
        else:
            if 'corners' in prediction_type:
                probabilities = {'over_8': 0.7, 'over_10': 0.5, 'over_12': 0.3, 'over_15': 0.1, 'over_20': 0.02}
            else:
                probabilities = {'over_10': 0.5, 'over_15': 0.3, 'over_20': 0.1, 'over_25': 0.05, 'over_30': 0.02}
        
        return {
            'model_name': model_name,
            'prediction': prediction,
            'confidence': confidence,
            'probabilities': probabilities,
            'total_matches': 0
        }
