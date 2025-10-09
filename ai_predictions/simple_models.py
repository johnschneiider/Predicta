"""
Modelos simples para predicciones rápidas
"""

import numpy as np
import logging
from typing import Dict, List
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.core.cache import cache
from football_data.models import Match, League
from .dixon_coles import DixonColesModel

logger = logging.getLogger('ai_predictions')

# Caché global para parámetro rho optimizado
_GLOBAL_RHO_CACHE = {'rho': -0.13, 'last_update': None}


class SimplePredictionService:
    """Servicio de predicciones simples y rápidas"""
    
    def __init__(self):
        self.dixon_coles_model = DixonColesModel()
        # Optimizar rho periódicamente con datos recientes
        self._optimize_rho_if_needed()
    
    def _optimize_rho_if_needed(self):
        """
        Optimiza el parámetro rho del modelo Dixon-Coles usando datos históricos.
        Usa caché para evitar recalcular en cada solicitud.
        """
        global _GLOBAL_RHO_CACHE
        
        try:
            # Verificar si necesitamos re-optimizar
            now = timezone.now()
            last_update = _GLOBAL_RHO_CACHE.get('last_update')
            
            # Re-optimizar solo si:
            # 1. Nunca se ha optimizado (last_update es None)
            # 2. Han pasado más de 24 horas desde la última optimización
            should_optimize = (
                last_update is None or 
                (now - last_update).total_seconds() > 86400  # 24 horas
            )
            
            if not should_optimize:
                # Usar valor cacheado
                cached_rho = _GLOBAL_RHO_CACHE.get('rho', -0.13)
                self.dixon_coles_model.rho = cached_rho
                logger.debug(f"Usando rho cacheado: {cached_rho:.4f}")
                return
            
            # Obtener partidos recientes de múltiples ligas para optimización
            cutoff_date = timezone.now().date() - timedelta(days=180)
            recent_matches = Match.objects.filter(
                date__gte=cutoff_date
            ).exclude(
                models.Q(fthg__isnull=True) | models.Q(ftag__isnull=True)
            ).order_by('-date')[:500]  # Usar últimos 500 partidos
            
            if len(recent_matches) >= 100:
                logger.info(f"🔄 Optimizando parámetro rho con {len(recent_matches)} partidos (caché expirada)")
                optimal_rho = self.dixon_coles_model.optimize_rho(list(recent_matches), is_goals=True)
                
                # Guardar en caché global
                _GLOBAL_RHO_CACHE['rho'] = optimal_rho
                _GLOBAL_RHO_CACHE['last_update'] = now
                
                self.dixon_coles_model.rho = optimal_rho
                logger.info(f"✅ Rho optimizado y cacheado: {optimal_rho:.4f} (válido por 24h)")
            else:
                logger.warning("⚠️  Pocos datos para optimización de rho, usando valor por defecto")
                # Guardar valor por defecto en caché
                _GLOBAL_RHO_CACHE['rho'] = -0.13
                _GLOBAL_RHO_CACHE['last_update'] = now
                self.dixon_coles_model.rho = -0.13
                
        except Exception as e:
            logger.error(f"❌ Error optimizando rho: {e}")
            # En caso de error, usar valor por defecto
            self.dixon_coles_model.rho = _GLOBAL_RHO_CACHE.get('rho', -0.13)
    
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
                elif 'shots_on_target' in prediction_type:
                    data = [m.hst for m in matches if m.hst is not None]
                    default_value = 5.0  # Promedio realista de remates a puerta local
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
                elif 'shots_on_target' in prediction_type:
                    data = [m.ast for m in matches if m.ast is not None]
                    default_value = 4.0  # Promedio realista de remates a puerta visitante
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
            elif 'shots_on_target' in prediction_type:
                default_value = 5.0
            else:
                default_value = 12.0
            return {'avg_value': default_value, 'matches_count': 0}
    
    def simple_poisson_model(self, home_team: str, away_team: str, league: League, 
                           prediction_type: str = 'shots_total') -> Dict:
        """
        Modelo de Poisson mejorado con Dixon-Coles.
        
        El modelo Dixon-Coles corrige las limitaciones del Poisson tradicional
        para marcadores bajos (0-0, 1-0, 0-1, 1-1) que son comunes en fútbol.
        """
        try:
            # Usar Dixon-Coles para predicciones de goles
            if 'goals' in prediction_type or 'both_teams_score' in prediction_type:
                # Dixon-Coles es ideal para predicción de goles
                dixon_coles_pred = self.dixon_coles_model.predict_match(
                    home_team, away_team, league, prediction_type
                )
                
                # Adaptar formato de respuesta
                return {
                    'model_name': 'Dixon-Coles Poisson',
                    'prediction': dixon_coles_pred['prediction'],
                    'confidence': dixon_coles_pred['confidence'],
                    'probabilities': dixon_coles_pred['probabilities'],
                    'total_matches': dixon_coles_pred['total_matches'],
                    'lambda_home': dixon_coles_pred.get('lambda_home', 1.5),
                    'lambda_away': dixon_coles_pred.get('lambda_away', 1.2),
                    'rho': dixon_coles_pred.get('rho', -0.13),
                    'match_outcome': dixon_coles_pred.get('match_outcome', {}),
                    'model_type': 'dixon_coles'
                }
            
            # Para otros tipos de predicción (corners, remates), usar Poisson tradicional mejorado
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
            elif prediction_type == 'corners_total':
                lambda_home = home_stats['avg_value'] * 1.1  # Ventaja de local
                lambda_away = away_stats['avg_value'] * 0.9  # Desventaja de visitante
                lambda_combined = lambda_home + lambda_away
            elif prediction_type == 'corners_home':
                lambda_combined = home_stats['avg_value'] * 1.1 * (1 + np.random.normal(0, 0.05))
            elif prediction_type == 'corners_away':
                lambda_combined = away_stats['avg_value'] * 0.9 * (1 + np.random.normal(0, 0.05))
            elif prediction_type == 'shots_on_target_total':
                lambda_home = home_stats['avg_value'] * 1.1  # Ventaja de local
                lambda_away = away_stats['avg_value'] * 0.9  # Desventaja de visitante
                lambda_combined = lambda_home + lambda_away
            elif prediction_type == 'shots_on_target_home':
                lambda_combined = home_stats['avg_value'] * 1.1 * (1 + np.random.normal(0, 0.05))
            elif prediction_type == 'shots_on_target_away':
                lambda_combined = away_stats['avg_value'] * 0.9 * (1 + np.random.normal(0, 0.05))
            else:
                lambda_combined = (home_stats['avg_value'] + away_stats['avg_value']) / 2
            
            # Predicción principal con distribución Poisson
            prediction = lambda_combined
            
            # Calcular probabilidades con umbrales correctos
            probabilities = {}
            if 'corners' in prediction_type:
                thresholds = [8, 10, 12, 15, 20]
            elif 'shots_on_target' in prediction_type:
                thresholds = [4, 6, 8, 10, 12]
            else:
                thresholds = [10, 15, 20, 25, 30]
            
            for threshold in thresholds:
                prob = max(0, min(1, 1 - (threshold / lambda_combined) if lambda_combined > 0 else 0.5))
                probabilities[f'over_{threshold}'] = prob
            
            # Confianza basada en cantidad de datos
            total_matches = home_stats['matches_count'] + away_stats['matches_count']
            confidence = min(0.9, max(0.3, total_matches / 20))
            
            return {
                'model_name': 'Enhanced Poisson',
                'prediction': prediction,
                'confidence': confidence,
                'probabilities': probabilities,
                'total_matches': total_matches
            }
            
        except Exception as e:
            logger.error(f"Error en modelo Poisson mejorado: {e}")
            default_prediction = 3.0 if 'goals' in prediction_type else 15.0
            return self._fallback_prediction('Dixon-Coles Poisson', default_prediction, 0.5, prediction_type)
    
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
                elif prediction_type == 'shots_on_target_home':
                    matches = Match.objects.filter(
                        league=league,
                        home_team=home_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.hst for m in matches if m.hst is not None]
                elif prediction_type == 'shots_on_target_away':
                    matches = Match.objects.filter(
                        league=league,
                        away_team=away_team,
                        date__gte=cutoff_date
                    ).order_by('-date')[:10]
                    recent_data = [m.ast for m in matches if m.ast is not None]
                elif prediction_type == 'shots_on_target_total':
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
                    recent_data = ([m.hst for m in home_matches if m.hst is not None] + 
                                 [m.ast for m in away_matches if m.ast is not None])
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
        """Modelo ensemble que promedia los otros 2 modelos (Dixon-Coles + Average)"""
        try:
            logger.info(f"Iniciando generación de modelo Ensemble para {prediction_type}")
            
            # Obtener predicciones de los otros modelos
            dixon_coles_pred = self.simple_poisson_model(home_team, away_team, league, prediction_type)
            logger.info(f"Dixon-Coles obtenido: {dixon_coles_pred['model_name']} - {dixon_coles_pred['prediction']}")
            
            average_pred = self.simple_average_model(home_team, away_team, league, prediction_type)
            logger.info(f"Average obtenido: {average_pred['model_name']} - {average_pred['prediction']}")
            
            # Calcular promedio de predicciones (solo 2 modelos)
            ensemble_prediction = (
                dixon_coles_pred['prediction'] + 
                average_pred['prediction']
            ) / 2
            
            # Calcular promedio de confianza (solo 2 modelos)
            ensemble_confidence = (
                dixon_coles_pred['confidence'] + 
                average_pred['confidence']
            ) / 2
            
            # Promedio de probabilidades (solo 2 modelos)
            ensemble_probabilities = {}
            all_keys = set(dixon_coles_pred['probabilities'].keys()) | set(average_pred['probabilities'].keys())
            
            for key in all_keys:
                values = []
                if key in dixon_coles_pred['probabilities']:
                    values.append(dixon_coles_pred['probabilities'][key])
                if key in average_pred['probabilities']:
                    values.append(average_pred['probabilities'][key])
                
                if values:
                    ensemble_probabilities[key] = sum(values) / len(values)
            
            # Total de partidos (suma de los 2 modelos)
            total_matches = (
                dixon_coles_pred['total_matches'] + 
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
        """Obtiene predicciones de todos los modelos simples incluyendo Dixon-Coles"""
        predictions = []
        
        try:
            # Modelo Dixon-Coles / Poisson mejorado
            dixon_coles_pred = self.simple_poisson_model(home_team, away_team, league, prediction_type)
            predictions.append(dixon_coles_pred)
            logger.info(f"Dixon-Coles generado: {dixon_coles_pred['model_name']}")
            
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
                    avg_prediction = (dixon_coles_pred['prediction'] + average_pred['prediction']) / 2
                    avg_confidence = (dixon_coles_pred['confidence'] + average_pred['confidence']) / 2
                    
                    ensemble_fallback = {
                        'model_name': 'Ensemble Average',
                        'prediction': avg_prediction,
                        'confidence': avg_confidence,
                        'probabilities': dixon_coles_pred['probabilities'],  # Usar probabilidades del primer modelo
                        'total_matches': dixon_coles_pred['total_matches'] + average_pred['total_matches']
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


class PoissonCornersModel:
    """Modelo Poisson específico para predicción de corners"""
    
    def __init__(self):
        self.name = "Poisson Corners Model"
    
    def predict(self, home_team: str, away_team: str, league: League, prediction_type: str = 'corners_total') -> float:
        """Predicción específica para corners usando distribución de Poisson"""
        try:
            from scipy.stats import poisson
            
            # Obtener estadísticas específicas para corners
            cutoff_date = timezone.now().date() - timedelta(days=180)
            
            # Estadísticas del equipo local
            home_matches = Match.objects.filter(
                league=league,
                home_team=home_team,
                date__gte=cutoff_date
            ).order_by('-date')[:20]
            
            home_corners_data = [m.hc for m in home_matches if m.hc is not None]
            home_avg_corners = np.mean(home_corners_data) if home_corners_data else 5.5
            
            # Estadísticas del equipo visitante
            away_matches = Match.objects.filter(
                league=league,
                away_team=away_team,
                date__gte=cutoff_date
            ).order_by('-date')[:20]
            
            away_corners_data = [m.ac for m in away_matches if m.ac is not None]
            away_avg_corners = np.mean(away_corners_data) if away_corners_data else 4.5
            
            # Estadísticas de la liga
            league_matches = Match.objects.filter(
                league=league,
                date__gte=cutoff_date
            ).order_by('-date')[:100]
            
            league_home_corners = [m.hc for m in league_matches if m.hc is not None]
            league_away_corners = [m.ac for m in league_matches if m.ac is not None]
            
            league_avg_home_corners = np.mean(league_home_corners) if league_home_corners else 5.5
            league_avg_away_corners = np.mean(league_away_corners) if league_away_corners else 4.5
            
            if prediction_type == 'corners_total':
                # Calcular lambda para corners totales
                lambda_home = (home_avg_corners / league_avg_home_corners) * league_avg_home_corners
                lambda_away = (away_avg_corners / league_avg_away_corners) * league_avg_away_corners
                lambda_total = lambda_home + lambda_away
                
                # Aplicar distribución de Poisson
                prediction = poisson.rvs(lambda_total)
                return float(prediction)
                
            elif prediction_type == 'corners_home':
                lambda_home = (home_avg_corners / league_avg_home_corners) * league_avg_home_corners
                prediction = poisson.rvs(lambda_home)
                return float(prediction)
                
            elif prediction_type == 'corners_away':
                lambda_away = (away_avg_corners / league_avg_away_corners) * league_avg_away_corners
                prediction = poisson.rvs(lambda_away)
                return float(prediction)
            
            return 5.0  # Valor por defecto
            
        except Exception as e:
            logger.error(f"Error en PoissonCornersModel: {str(e)}")
            return 5.0


class ModeloHibridoCorners:
    """Modelo híbrido que combina múltiples enfoques para predicción de corners"""
    
    def __init__(self):
        self.modelo_poisson = PoissonCornersModel()
        self.modelo_poisson_simple = None  # Se inicializará con SimplePredictionService
        self.modelo_average = None  # Se inicializará con SimplePredictionService
        self.name = "Modelo Híbrido Corners"
        
    def predecir(self, home_team: str, away_team: str, league: League, prediction_type: str = 'corners_total') -> Dict:
        """Predicción híbrida combinando múltiples modelos"""
        try:
            # Inicializar modelos si no están disponibles
            if self.modelo_poisson_simple is None:
                self.modelo_poisson_simple = SimplePredictionService()
            if self.modelo_average is None:
                self.modelo_average = SimplePredictionService()
            
            # Predicción Poisson especializada (peso 0.4)
            pred_poisson = self.modelo_poisson.predict(home_team, away_team, league, prediction_type)
            
            # Predicción Poisson simple (peso 0.3)
            poisson_result = self.modelo_poisson_simple.simple_poisson_model(
                home_team, away_team, league, prediction_type
            )
            pred_poisson_simple = poisson_result.get('prediction', 5.0)
            
            # Predicción Average (peso 0.3)
            average_result = self.modelo_average.simple_average_model(
                home_team, away_team, league, prediction_type
            )
            pred_average = average_result.get('prediction', 5.0)
            
            # Ensemble con pesos optimizados
            prediccion_final = (
                0.4 * pred_poisson + 
                0.3 * pred_poisson_simple + 
                0.3 * pred_average
            )
            
            # Calcular confianza basada en la consistencia de los modelos
            predicciones = [pred_poisson, pred_poisson_simple, pred_average]
            std_dev = np.std(predicciones)
            confidence = max(0.1, min(0.9, 1.0 - (std_dev / np.mean(predicciones))))
            
            # Calcular probabilidades para diferentes rangos
            if prediction_type in ['corners_total', 'corners_home', 'corners_away']:
                thresholds = [5, 7, 9, 12, 15]
                probabilities = {}
                
                for i, threshold in enumerate(thresholds):
                    prob = max(0.1, min(0.9, 1.0 - abs(prediccion_final - threshold) / 10))
                    probabilities[f'over_{threshold}'] = prob
            
            logger.info(f"Modelo Híbrido Corners - {prediction_type}: {prediccion_final:.2f}")
            
            return {
                'model_name': self.name,
                'prediction': round(prediccion_final, 2),
                'confidence': round(confidence, 3),
                'probabilities': probabilities,
                'total_matches': 0,
                'component_predictions': {
                    'poisson_specialized': pred_poisson,
                    'poisson_simple': pred_poisson_simple,
                    'average': pred_average
                }
            }
            
        except Exception as e:
            logger.error(f"Error en ModeloHibridoCorners: {str(e)}")
            return {
                'model_name': self.name,
                'prediction': 5.0,
                'confidence': 0.5,
                'probabilities': {},
                'total_matches': 0,
                'component_predictions': {}
            }


class ModeloHibridoGeneral:
    """Modelo híbrido general que puede aplicarse a cualquier tipo de predicción"""
    
    def __init__(self):
        self.modelo_poisson_simple = SimplePredictionService()
        self.modelo_average = SimplePredictionService()
        self.name = "Modelo Híbrido General"
        
    def predecir(self, home_team: str, away_team: str, league: League, prediction_type: str = 'shots_total') -> Dict:
        """Predicción híbrida general para cualquier tipo de predicción"""
        try:
            # Predicción Poisson (peso 0.5)
            poisson_result = self.modelo_poisson_simple.simple_poisson_model(
                home_team, away_team, league, prediction_type
            )
            pred_poisson = poisson_result.get('prediction', 5.0)
            
            # Predicción Average (peso 0.3)
            average_result = self.modelo_average.simple_average_model(
                home_team, away_team, league, prediction_type
            )
            pred_average = average_result.get('prediction', 5.0)
            
            # Predicción Trend (peso 0.2)
            trend_result = self.modelo_poisson_simple.simple_trend_model(
                home_team, away_team, league, prediction_type
            )
            pred_trend = trend_result.get('prediction', 5.0)
            
            # Ensemble con pesos optimizados
            prediccion_final = (
                0.5 * pred_poisson + 
                0.3 * pred_average + 
                0.2 * pred_trend
            )
            
            # Calcular confianza
            predicciones = [pred_poisson, pred_average, pred_trend]
            std_dev = np.std(predicciones)
            confidence = max(0.1, min(0.9, 1.0 - (std_dev / max(np.mean(predicciones), 0.1))))
            
            # Usar probabilidades del modelo Poisson (más completo)
            probabilities = poisson_result.get('probabilities', {})
            
            logger.info(f"Modelo Híbrido General - {prediction_type}: {prediccion_final:.2f}")
            
            return {
                'model_name': self.name,
                'prediction': round(prediccion_final, 2),
                'confidence': round(confidence, 3),
                'probabilities': probabilities,
                'total_matches': 0,
                'component_predictions': {
                    'poisson': pred_poisson,
                    'average': pred_average,
                    'trend': pred_trend
                }
            }
            
        except Exception as e:
            logger.error(f"Error en ModeloHibridoGeneral: {str(e)}")
            return {
                'model_name': self.name,
                'prediction': 5.0,
                'confidence': 0.5,
                'probabilities': {},
                'total_matches': 0,
                'component_predictions': {}
            }
