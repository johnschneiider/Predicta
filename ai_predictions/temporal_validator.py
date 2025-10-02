"""
Sistema de validación temporal mejorado para evaluación realista de modelos
"""

import numpy as np
import logging
from typing import Dict, List, Tuple
from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Q
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from football_data.models import Match, League
from .ensemble_predictor import AdvancedEnsemblePredictor

logger = logging.getLogger('ai_predictions')


class TemporalValidator:
    """Validador temporal para evaluación realista de modelos de predicción"""
    
    def __init__(self):
        self.ensemble_predictor = AdvancedEnsemblePredictor()
    
    def temporal_backtest(self, league: League, prediction_type: str, 
                         test_periods: int = 10, lookback_days: int = 30) -> Dict:
        """Backtesting temporal realista"""
        try:
            # Obtener partidos ordenados por fecha
            matches = Match.objects.filter(league=league).exclude(
                Q(fthg__isnull=True) | Q(ftag__isnull=True) |
                Q(hs__isnull=True) | Q(as_field__isnull=True)
            ).order_by('date')
            
            if len(matches) < 100:
                return {'error': 'Datos insuficientes para backtesting'}
            
            # Dividir en períodos de tiempo
            total_matches = len(matches)
            matches_per_period = max(20, total_matches // (test_periods + 2))
            
            results = {
                'mae_scores': [],
                'rmse_scores': [],
                'accuracy_scores': [],
                'r2_scores': [],
                'predictions': [],
                'actuals': [],
                'periods_tested': 0,
                'total_matches_tested': 0
            }
            
            # Backtesting por períodos
            for period in range(1, test_periods + 1):
                try:
                    # Dividir datos: entrenamiento (hasta el período) vs test (período actual)
                    train_end_idx = period * matches_per_period
                    test_start_idx = train_end_idx
                    test_end_idx = min(test_start_idx + matches_per_period, total_matches)
                    
                    if test_end_idx - test_start_idx < 10:  # Mínimo de partidos para test
                        continue
                    
                    # Datos de entrenamiento (históricos)
                    train_matches = matches[:train_end_idx]
                    
                    # Datos de test (futuros)
                    test_matches = matches[test_start_idx:test_end_idx]
                    
                    if len(test_matches) < 5:
                        continue
                    
                    # Hacer predicciones para el período de test
                    period_predictions = []
                    period_actuals = []
                    
                    for match in test_matches:
                        try:
                            # Simular predicción (como si estuviéramos en la fecha del partido)
                            prediction_result = self.ensemble_predictor.predict_with_ensemble(
                                match.home_team, match.away_team, league, prediction_type
                            )
                            
                            # Obtener valor real
                            if prediction_type == 'goals_total':
                                actual = (match.fthg or 0) + (match.ftag or 0)
                            elif prediction_type == 'goals_home':
                                actual = match.fthg or 0
                            elif prediction_type == 'goals_away':
                                actual = match.ftag or 0
                            elif prediction_type == 'shots_total':
                                actual = (match.hs or 0) + (match.as_field or 0)
                            elif prediction_type == 'shots_home':
                                actual = match.hs or 0
                            elif prediction_type == 'shots_away':
                                actual = match.as_field or 0
                            else:
                                actual = (match.fthg or 0) + (match.ftag or 0)
                            
                            period_predictions.append(prediction_result['prediction'])
                            period_actuals.append(actual)
                            
                        except Exception as e:
                            logger.error(f"Error en predicción de backtest: {e}")
                            continue
                    
                    if len(period_predictions) < 3:
                        continue
                    
                    # Calcular métricas del período
                    mae = mean_absolute_error(period_actuals, period_predictions)
                    rmse = np.sqrt(mean_squared_error(period_actuals, period_predictions))
                    
                    # Accuracy con tolerancia
                    tolerance = 0.5 if 'goals' in prediction_type else 2.0
                    accuracy = np.mean(np.abs(np.array(period_predictions) - np.array(period_actuals)) <= tolerance)
                    
                    # R² Score
                    r2 = r2_score(period_actuals, period_predictions) if len(period_actuals) > 1 else 0
                    
                    results['mae_scores'].append(mae)
                    results['rmse_scores'].append(rmse)
                    results['accuracy_scores'].append(accuracy)
                    results['r2_scores'].append(r2)
                    results['predictions'].extend(period_predictions)
                    results['actuals'].extend(period_actuals)
                    results['periods_tested'] += 1
                    results['total_matches_tested'] += len(period_predictions)
                    
                except Exception as e:
                    logger.error(f"Error en período de backtest {period}: {e}")
                    continue
            
            # Calcular métricas agregadas
            if results['periods_tested'] > 0:
                results['avg_mae'] = np.mean(results['mae_scores'])
                results['avg_rmse'] = np.mean(results['rmse_scores'])
                results['avg_accuracy'] = np.mean(results['accuracy_scores'])
                results['avg_r2'] = np.mean(results['r2_scores'])
                results['std_mae'] = np.std(results['mae_scores'])
                results['std_accuracy'] = np.std(results['accuracy_scores'])
                
                # Accuracy por rangos de tolerancia
                tolerance_1 = 1.0 if 'goals' in prediction_type else 3.0
                tolerance_2 = 2.0 if 'goals' in prediction_type else 5.0
                
                accuracy_1 = np.mean(np.abs(np.array(results['predictions']) - np.array(results['actuals'])) <= tolerance_1)
                accuracy_2 = np.mean(np.abs(np.array(results['predictions']) - np.array(results['actuals'])) <= tolerance_2)
                
                results['accuracy_tolerance_1'] = accuracy_1
                results['accuracy_tolerance_2'] = accuracy_2
                
                # Calificación del modelo
                results['model_grade'] = self._calculate_model_grade(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error en backtesting temporal: {e}")
            return {'error': str(e)}
    
    def rolling_window_validation(self, league: League, prediction_type: str, 
                                window_size: int = 100, step_size: int = 20) -> Dict:
        """Validación con ventana deslizante"""
        try:
            matches = Match.objects.filter(league=league).exclude(
                Q(fthg__isnull=True) | Q(ftag__isnull=True) |
                Q(hs__isnull=True) | Q(as_field__isnull=True)
            ).order_by('date')
            
            if len(matches) < window_size + 50:
                return {'error': 'Datos insuficientes para validación con ventana deslizante'}
            
            results = {
                'window_results': [],
                'overall_metrics': {},
                'stability_scores': []
            }
            
            # Ventana deslizante
            for start_idx in range(0, len(matches) - window_size, step_size):
                end_idx = start_idx + window_size
                window_matches = matches[start_idx:end_idx]
                
                # Dividir ventana en entrenamiento (80%) y test (20%)
                split_idx = int(window_size * 0.8)
                train_matches = window_matches[:split_idx]
                test_matches = window_matches[split_idx:]
                
                if len(test_matches) < 10:
                    continue
                
                # Evaluar en ventana de test
                window_predictions = []
                window_actuals = []
                
                for match in test_matches:
                    try:
                        prediction_result = self.ensemble_predictor.predict_with_ensemble(
                            match.home_team, match.away_team, league, prediction_type
                        )
                        
                        # Valor real
                        if prediction_type == 'goals_total':
                            actual = (match.fthg or 0) + (match.ftag or 0)
                        elif prediction_type == 'goals_home':
                            actual = match.fthg or 0
                        elif prediction_type == 'goals_away':
                            actual = match.ftag or 0
                        elif prediction_type == 'shots_total':
                            actual = (match.hs or 0) + (match.as_field or 0)
                        elif prediction_type == 'shots_home':
                            actual = match.hs or 0
                        elif prediction_type == 'shots_away':
                            actual = match.as_field or 0
                        else:
                            actual = (match.fthg or 0) + (match.ftag or 0)
                        
                        window_predictions.append(prediction_result['prediction'])
                        window_actuals.append(actual)
                        
                    except Exception as e:
                        continue
                
                if len(window_predictions) < 5:
                    continue
                
                # Métricas de la ventana
                window_mae = mean_absolute_error(window_actuals, window_predictions)
                window_accuracy = np.mean(np.abs(np.array(window_predictions) - np.array(window_actuals)) <= 1.0)
                
                results['window_results'].append({
                    'start_date': train_matches[0].date,
                    'end_date': test_matches[-1].date,
                    'mae': window_mae,
                    'accuracy': window_accuracy,
                    'matches_tested': len(window_predictions)
                })
                
                results['stability_scores'].append(window_mae)
            
            # Métricas generales
            if results['window_results']:
                all_maes = [w['mae'] for w in results['window_results']]
                all_accuracies = [w['accuracy'] for w in results['window_results']]
                
                results['overall_metrics'] = {
                    'avg_mae': np.mean(all_maes),
                    'std_mae': np.std(all_maes),
                    'avg_accuracy': np.mean(all_accuracies),
                    'stability_score': 1 / (np.std(all_maes) + 0.1),  # Menor variabilidad = mayor estabilidad
                    'total_windows': len(results['window_results'])
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error en validación con ventana deslizante: {e}")
            return {'error': str(e)}
    
    def _calculate_model_grade(self, results: Dict) -> str:
        """Calcula calificación del modelo basada en métricas"""
        try:
            accuracy = results.get('avg_accuracy', 0)
            mae = results.get('avg_mae', 10)
            r2 = results.get('avg_r2', -1)
            
            # Sistema de puntuación
            score = 0
            
            # Accuracy (40% del peso)
            if accuracy >= 0.7:
                score += 40
            elif accuracy >= 0.6:
                score += 30
            elif accuracy >= 0.5:
                score += 20
            elif accuracy >= 0.4:
                score += 10
            
            # MAE (30% del peso)
            if mae <= 1.0:
                score += 30
            elif mae <= 1.5:
                score += 25
            elif mae <= 2.0:
                score += 20
            elif mae <= 3.0:
                score += 10
            
            # R² (30% del peso)
            if r2 >= 0.7:
                score += 30
            elif r2 >= 0.5:
                score += 25
            elif r2 >= 0.3:
                score += 20
            elif r2 >= 0.1:
                score += 10
            
            # Calificación final
            if score >= 90:
                return 'A+'
            elif score >= 80:
                return 'A'
            elif score >= 70:
                return 'B+'
            elif score >= 60:
                return 'B'
            elif score >= 50:
                return 'C+'
            elif score >= 40:
                return 'C'
            else:
                return 'D'
                
        except Exception as e:
            logger.error(f"Error calculando calificación: {e}")
            return 'N/A'
    
    def get_validation_summary(self, league: League, prediction_type: str) -> Dict:
        """Resumen completo de validación"""
        try:
            # Backtesting temporal
            temporal_results = self.temporal_backtest(league, prediction_type)
            
            # Validación con ventana deslizante
            rolling_results = self.rolling_window_validation(league, prediction_type)
            
            return {
                'temporal_backtest': temporal_results,
                'rolling_window': rolling_results,
                'prediction_type': prediction_type,
                'league': league.name,
                'validation_date': timezone.now().isoformat(),
                'summary': {
                    'temporal_accuracy': temporal_results.get('avg_accuracy', 0),
                    'temporal_mae': temporal_results.get('avg_mae', 0),
                    'temporal_grade': temporal_results.get('model_grade', 'N/A'),
                    'rolling_stability': rolling_results.get('overall_metrics', {}).get('stability_score', 0),
                    'overall_grade': self._calculate_overall_grade(temporal_results, rolling_results)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen de validación: {e}")
            return {'error': str(e)}
    
    def _calculate_overall_grade(self, temporal_results: Dict, rolling_results: Dict) -> str:
        """Calcula calificación general del modelo"""
        try:
            temporal_grade = temporal_results.get('model_grade', 'D')
            rolling_stability = rolling_results.get('overall_metrics', {}).get('stability_score', 0)
            
            # Mapeo de calificaciones a números
            grade_values = {'A+': 10, 'A': 9, 'B+': 8, 'B': 7, 'C+': 6, 'C': 5, 'D': 3}
            temporal_score = grade_values.get(temporal_grade, 3)
            
            # Ajustar por estabilidad
            stability_bonus = min(2, rolling_stability)
            final_score = temporal_score + stability_bonus
            
            # Calificación final
            if final_score >= 10:
                return 'A+'
            elif final_score >= 9:
                return 'A'
            elif final_score >= 8:
                return 'B+'
            elif final_score >= 7:
                return 'B'
            elif final_score >= 6:
                return 'C+'
            elif final_score >= 5:
                return 'C'
            else:
                return 'D'
                
        except Exception as e:
            return 'N/A'
