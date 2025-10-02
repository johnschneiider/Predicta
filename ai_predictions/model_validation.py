"""
Sistema de validación y optimización de modelos
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from django.utils import timezone
from django.db import models
from football_data.models import Match, League
from .advanced_models import AdvancedStatisticalModels

logger = logging.getLogger('ai_predictions')


class ModelValidator:
    """Sistema de validación y optimización de modelos"""
    
    def __init__(self):
        self.advanced_models = AdvancedStatisticalModels()
    
    def temporal_cross_validation(self, league: League, prediction_type: str = 'shots_total') -> Dict:
        """Validación cruzada temporal para evaluar modelos"""
        try:
            # Obtener datos históricos ordenados por fecha
            matches = Match.objects.filter(league=league).exclude(
                models.Q(hs__isnull=True) | models.Q(as_field__isnull=True)
            ).order_by('date')
            
            if len(matches) < 50:
                return {'error': 'Datos insuficientes para validación'}
            
            # Preparar datos para validación
            validation_data = []
            for match in matches:
                try:
                    if prediction_type == 'shots_total':
                        target = (match.hs or 0) + (match.as_field or 0)
                    elif prediction_type == 'shots_home':
                        target = match.hs or 0
                    elif prediction_type == 'shots_away':
                        target = match.as_field or 0
                    else:
                        target = (match.hs or 0) + (match.as_field or 0)
                    
                    validation_data.append({
                        'home_team': match.home_team,
                        'away_team': match.away_team,
                        'target': target,
                        'date': match.date
                    })
                except:
                    continue
            
            if len(validation_data) < 30:
                return {'error': 'Datos insuficientes después del procesamiento'}
            
            # Dividir en 5 folds temporales
            n_splits = min(5, len(validation_data) // 10)
            tscv = TimeSeriesSplit(n_splits=n_splits)
            
            results = {
                'Enhanced Poisson': {'mae': [], 'rmse': [], 'r2': [], 'accuracy_2': [], 'accuracy_3': []},
                'Bayesian': {'mae': [], 'rmse': [], 'r2': [], 'accuracy_2': [], 'accuracy_3': []},
                'Ensemble': {'mae': [], 'rmse': [], 'r2': [], 'accuracy_2': [], 'accuracy_3': []}
            }
            
            # Convertir a arrays para validación cruzada
            X = np.arange(len(validation_data))
            y = np.array([item['target'] for item in validation_data])
            
            for train_idx, test_idx in tscv.split(X):
                train_data = [validation_data[i] for i in train_idx]
                test_data = [validation_data[i] for i in test_idx]
                
                # Evaluar cada modelo
                for model_name in ['Enhanced Poisson', 'Bayesian', 'Ensemble']:
                    try:
                        predictions = []
                        actuals = []
                        
                        for test_item in test_data:
                            if model_name == 'Enhanced Poisson':
                                pred = self.advanced_models.enhanced_poisson_model(
                                    test_item['home_team'], test_item['away_team'], league, prediction_type
                                )
                            elif model_name == 'Bayesian':
                                pred = self.advanced_models.bayesian_model(
                                    test_item['home_team'], test_item['away_team'], league, prediction_type
                                )
                            else:  # Ensemble
                                pred = self.advanced_models.ensemble_model(
                                    test_item['home_team'], test_item['away_team'], league, prediction_type
                                )
                            
                            predictions.append(pred['prediction'])
                            actuals.append(test_item['target'])
                        
                        # Calcular métricas
                        predictions = np.array(predictions)
                        actuals = np.array(actuals)
                        
                        mae = mean_absolute_error(actuals, predictions)
                        rmse = np.sqrt(mean_squared_error(actuals, predictions))
                        r2 = r2_score(actuals, predictions)
                        
                        # Accuracy con tolerancia
                        accuracy_2 = np.mean(np.abs(predictions - actuals) <= 2)
                        accuracy_3 = np.mean(np.abs(predictions - actuals) <= 3)
                        
                        results[model_name]['mae'].append(mae)
                        results[model_name]['rmse'].append(rmse)
                        results[model_name]['r2'].append(r2)
                        results[model_name]['accuracy_2'].append(accuracy_2)
                        results[model_name]['accuracy_3'].append(accuracy_3)
                        
                    except Exception as e:
                        logger.error(f"Error evaluando {model_name}: {e}")
                        continue
            
            # Calcular promedios
            final_results = {}
            for model_name, metrics in results.items():
                if metrics['mae']:  # Solo si hay datos
                    final_results[model_name] = {
                        'mae': np.mean(metrics['mae']),
                        'rmse': np.mean(metrics['rmse']),
                        'r2': np.mean(metrics['r2']),
                        'accuracy_2': np.mean(metrics['accuracy_2']),
                        'accuracy_3': np.mean(metrics['accuracy_3']),
                        'folds': len(metrics['mae']),
                        'std_mae': np.std(metrics['mae']),
                        'std_accuracy_2': np.std(metrics['accuracy_2'])
                    }
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error en validación cruzada temporal: {e}")
            return {'error': str(e)}
    
    def optimize_model_parameters(self, league: League, prediction_type: str = 'shots_total') -> Dict:
        """Optimiza parámetros de los modelos basándose en validación"""
        try:
            # Realizar validación cruzada
            cv_results = self.temporal_cross_validation(league, prediction_type)
            
            if 'error' in cv_results:
                return cv_results
            
            # Encontrar el mejor modelo
            best_model = None
            best_score = -np.inf
            
            for model_name, metrics in cv_results.items():
                # Score combinado: accuracy_2 * 0.4 + (1 - mae/20) * 0.3 + r2 * 0.3
                score = (metrics['accuracy_2'] * 0.4 + 
                        (1 - min(metrics['mae']/20, 1)) * 0.3 + 
                        max(metrics['r2'], 0) * 0.3)
                
                if score > best_score:
                    best_score = score
                    best_model = model_name
            
            return {
                'best_model': best_model,
                'best_score': best_score,
                'all_results': cv_results,
                'recommendations': self._generate_recommendations(cv_results)
            }
            
        except Exception as e:
            logger.error(f"Error optimizando parámetros: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, cv_results: Dict) -> List[str]:
        """Genera recomendaciones basadas en los resultados de validación"""
        recommendations = []
        
        # Analizar rendimiento general
        avg_accuracy_2 = np.mean([metrics['accuracy_2'] for metrics in cv_results.values()])
        avg_mae = np.mean([metrics['mae'] for metrics in cv_results.values()])
        
        if avg_accuracy_2 < 0.3:
            recommendations.append("Precisión general baja. Considerar aumentar la ventana temporal de datos.")
        
        if avg_mae > 5:
            recommendations.append("Error absoluto medio alto. Los modelos necesitan más datos históricos.")
        
        # Analizar consistencia entre modelos
        model_names = list(cv_results.keys())
        if len(model_names) > 1:
            accuracies = [cv_results[name]['accuracy_2'] for name in model_names]
            if np.std(accuracies) > 0.1:
                recommendations.append("Alta variabilidad entre modelos. Usar modelo Ensemble para mayor estabilidad.")
        
        # Recomendaciones específicas por modelo
        for model_name, metrics in cv_results.items():
            if metrics['accuracy_2'] > 0.5:
                recommendations.append(f"{model_name} muestra buen rendimiento. Considerar como modelo principal.")
            elif metrics['r2'] < -0.1:
                recommendations.append(f"{model_name} tiene R² negativo. Revisar características de entrada.")
        
        return recommendations
    
    def get_model_performance_summary(self, league: League, prediction_type: str = 'shots_total') -> Dict:
        """Obtiene un resumen del rendimiento de todos los modelos"""
        try:
            # Validación cruzada
            cv_results = self.temporal_cross_validation(league, prediction_type)
            
            if 'error' in cv_results:
                return cv_results
            
            # Calcular estadísticas generales
            all_mae = [metrics['mae'] for metrics in cv_results.values()]
            all_accuracy_2 = [metrics['accuracy_2'] for metrics in cv_results.values()]
            all_r2 = [metrics['r2'] for metrics in cv_results.values()]
            
            summary = {
                'total_models': len(cv_results),
                'best_accuracy_2': max(all_accuracy_2),
                'worst_accuracy_2': min(all_accuracy_2),
                'avg_accuracy_2': np.mean(all_accuracy_2),
                'best_mae': min(all_mae),
                'worst_mae': max(all_mae),
                'avg_mae': np.mean(all_mae),
                'best_r2': max(all_r2),
                'worst_r2': min(all_r2),
                'avg_r2': np.mean(all_r2),
                'model_rankings': self._rank_models(cv_results),
                'overall_quality': self._assess_overall_quality(cv_results)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generando resumen de rendimiento: {e}")
            return {'error': str(e)}
    
    def _rank_models(self, cv_results: Dict) -> List[Dict]:
        """Rankea los modelos por rendimiento"""
        rankings = []
        
        for model_name, metrics in cv_results.items():
            # Score combinado
            score = (metrics['accuracy_2'] * 0.4 + 
                    (1 - min(metrics['mae']/20, 1)) * 0.3 + 
                    max(metrics['r2'], 0) * 0.3)
            
            rankings.append({
                'model_name': model_name,
                'score': score,
                'accuracy_2': metrics['accuracy_2'],
                'mae': metrics['mae'],
                'r2': metrics['r2']
            })
        
        # Ordenar por score descendente
        rankings.sort(key=lambda x: x['score'], reverse=True)
        
        return rankings
    
    def _assess_overall_quality(self, cv_results: Dict) -> str:
        """Evalúa la calidad general del sistema"""
        avg_accuracy_2 = np.mean([metrics['accuracy_2'] for metrics in cv_results.values()])
        avg_mae = np.mean([metrics['mae'] for metrics in cv_results.values()])
        
        if avg_accuracy_2 > 0.6 and avg_mae < 3:
            return "Excelente"
        elif avg_accuracy_2 > 0.4 and avg_mae < 5:
            return "Bueno"
        elif avg_accuracy_2 > 0.3 and avg_mae < 7:
            return "Aceptable"
        else:
            return "Necesita Mejora"
