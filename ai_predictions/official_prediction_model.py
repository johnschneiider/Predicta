"""
Modelo de Predicción Oficial
Promedia las predicciones de todos los modelos por cada mercado específico.

Este modelo es completamente independiente y no altera otros modelos.
Solo promedia los datos disponibles en cada columna/mercado.
"""

import logging
import numpy as np
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class OfficialPredictionModel:
    """
    Modelo que promedia las predicciones de todos los otros modelos
    
    Características:
    - Independiente de otros modelos
    - Solo promedia datos disponibles por mercado
    - No altera el funcionamiento de otros modelos
    - Lógica: Si hay 2 datos en una columna, promedia esos 2
    """
    
    def __init__(self):
        self.name = "Predicción Oficial"
        
    def calculate_official_predictions(self, all_predictions: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Calcular predicciones oficiales promediando todos los modelos disponibles
        
        Args:
            all_predictions: Diccionario con todas las predicciones por tipo
            
        Returns:
            Diccionario con las predicciones oficiales por tipo
        """
        try:
            logger.info("🎯 OFICIAL - Iniciando cálculo de predicciones oficiales")
            
            official_predictions = {}
            
            # Procesar cada tipo de predicción
            for pred_type, predictions_list in all_predictions.items():
                if not predictions_list:
                    logger.warning(f"🎯 OFICIAL - No hay predicciones para {pred_type}")
                    continue
                
                logger.info(f"🎯 OFICIAL - Procesando {pred_type}: {len(predictions_list)} modelos")
                
                # Filtrar predicciones válidas (que tengan valor numérico)
                valid_predictions = []
                for pred in predictions_list:
                    if isinstance(pred, dict) and 'prediction' in pred:
                        try:
                            pred_value = float(pred['prediction'])
                            if not np.isnan(pred_value) and pred_value > 0:
                                valid_predictions.append({
                                    'value': pred_value,
                                    'model': pred.get('model_name', 'Unknown'),
                                    'confidence': pred.get('confidence', 0.5)
                                })
                        except (ValueError, TypeError):
                            logger.warning(f"🎯 OFICIAL - Valor inválido en {pred.get('model_name', 'Unknown')}: {pred.get('prediction')}")
                            continue
                
                if not valid_predictions:
                    logger.warning(f"🎯 OFICIAL - No hay predicciones válidas para {pred_type}")
                    continue
                
                # Calcular promedio
                values = [p['value'] for p in valid_predictions]
                confidences = [p['confidence'] for p in valid_predictions]
                model_names = [p['model'] for p in valid_predictions]
                
                # Promedio simple de valores
                average_value = np.mean(values)
                
                # Promedio ponderado por confianza
                if sum(confidences) > 0:
                    weighted_average = np.average(values, weights=confidences)
                else:
                    weighted_average = average_value
                
                # Usar promedio ponderado como predicción final
                final_prediction = weighted_average
                
                # Calcular confianza promedio
                avg_confidence = np.mean(confidences)
                
                # Calcular desviación estándar para indicar consistencia
                std_deviation = np.std(values) if len(values) > 1 else 0.0
                
                # Crear resultado oficial
                official_pred = {
                    'model_name': self.name,
                    'prediction': round(final_prediction, 2),
                    'confidence': round(avg_confidence, 3),
                    'total_matches': sum(p.get('total_matches', 0) for p in predictions_list if isinstance(p, dict)),
                    'method': 'Official Average',
                    'probabilities': self._calculate_official_probabilities(final_prediction, pred_type),
                    'details': {
                        'models_used': model_names,
                        'values_used': [round(v, 2) for v in values],
                        'simple_average': round(average_value, 2),
                        'weighted_average': round(weighted_average, 2),
                        'std_deviation': round(std_deviation, 2),
                        'consistency': 'High' if std_deviation < 2.0 else 'Medium' if std_deviation < 5.0 else 'Low'
                    }
                }
                
                official_predictions[pred_type] = official_pred
                
                logger.info(f"🎯 OFICIAL - {pred_type}: {final_prediction:.2f} (de {len(valid_predictions)} modelos)")
                logger.info(f"🎯 OFICIAL - Modelos usados: {model_names}")
                logger.info(f"🎯 OFICIAL - Valores: {[round(v, 2) for v in values]}")
            
            logger.info(f"🎯 OFICIAL - Predicciones oficiales calculadas: {len(official_predictions)} tipos")
            return official_predictions
            
        except Exception as e:
            logger.error(f"❌ OFICIAL - Error calculando predicciones oficiales: {e}")
            logger.error(f"❌ OFICIAL - Traceback:", exc_info=True)
            return {}
    
    def _calculate_official_probabilities(self, prediction: float, pred_type: str) -> Dict[str, float]:
        """Calcular probabilidades oficiales basadas en el tipo de predicción"""
        try:
            probabilities = {}
            
            if 'shots' in pred_type:
                # Probabilidades para remates
                thresholds = [5, 10, 15, 20, 25]
                for threshold in thresholds:
                    if prediction > threshold:
                        prob = min(0.9, (prediction - threshold) / prediction + 0.4)
                    else:
                        prob = max(0.1, prediction / threshold * 0.6)
                    probabilities[f'over_{threshold}'] = round(prob, 3)
                    
            elif 'goals' in pred_type:
                # Probabilidades para goles
                thresholds = [1, 2, 3, 4, 5]
                for threshold in thresholds:
                    if prediction > threshold:
                        prob = min(0.9, (prediction - threshold) / prediction + 0.3)
                    else:
                        prob = max(0.1, prediction / threshold * 0.5)
                    probabilities[f'over_{threshold}'] = round(prob, 3)
                    
            elif 'corners' in pred_type:
                # Probabilidades para corners
                thresholds = [3, 5, 7, 10, 12]
                for threshold in thresholds:
                    if prediction > threshold:
                        prob = min(0.9, (prediction - threshold) / prediction + 0.4)
                    else:
                        prob = max(0.1, prediction / threshold * 0.6)
                    probabilities[f'over_{threshold}'] = round(prob, 3)
                    
            elif 'both_teams_score' in pred_type:
                # Probabilidades para ambos marcan (ya es probabilidad)
                probabilities['both_score'] = round(prediction, 3)
                probabilities['no_both_score'] = round(1.0 - prediction, 3)
                
            return probabilities
            
        except Exception as e:
            logger.error(f"Error calculando probabilidades oficiales: {e}")
            return {'over_5': 0.5}
    
    def add_to_predictions(self, all_predictions: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        Agregar predicción oficial a todas las predicciones existentes
        
        Args:
            all_predictions: Diccionario con todas las predicciones
            
        Returns:
            Diccionario con predicción oficial agregada
        """
        try:
            logger.info("🎯 OFICIAL - Agregando predicción oficial a resultados")
            
            # Calcular predicciones oficiales
            official_predictions = self.calculate_official_predictions(all_predictions)
            
            # Agregar a cada tipo de predicción
            for pred_type, official_pred in official_predictions.items():
                if pred_type in all_predictions:
                    # Agregar al final de la lista
                    all_predictions[pred_type].append(official_pred)
                    logger.info(f"🎯 OFICIAL - Agregado a {pred_type}")
                else:
                    # Crear nueva entrada
                    all_predictions[pred_type] = [official_pred]
                    logger.info(f"🎯 OFICIAL - Creado nuevo tipo {pred_type}")
            
            logger.info(f"🎯 OFICIAL - Predicción oficial agregada a {len(official_predictions)} tipos")
            return all_predictions
            
        except Exception as e:
            logger.error(f"❌ OFICIAL - Error agregando predicción oficial: {e}")
            return all_predictions

# Instancia global del modelo
official_prediction_model = OfficialPredictionModel()
