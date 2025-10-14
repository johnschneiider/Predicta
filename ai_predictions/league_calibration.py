"""
Sistema de Calibración por Liga
Analiza datos históricos para ajustar predicciones según la liga específica
"""

import logging
from typing import Dict, Tuple
from django.db.models import Avg, Count
from football_data.models import Match, League

logger = logging.getLogger(__name__)

class LeagueCalibrationService:
    """Servicio para calibrar predicciones según estadísticas históricas de cada liga"""
    
    def __init__(self):
        self.calibration_factors = {}
        self._calculate_calibration_factors()
    
    def _calculate_calibration_factors(self):
        """Calcula factores de calibración basados en datos históricos reales"""
        
        leagues = League.objects.all()
        
        for league in leagues:
            # Obtener datos históricos de la liga
            matches = Match.objects.filter(league=league)
            
            if matches.count() < 50:  # Mínimo de datos para calibración
                logger.warning(f"Liga {league.name} tiene pocos datos para calibración: {matches.count()}")
                continue
            
            # Calcular promedios históricos reales
            # Para goals_total: suma de fthg + ftag
            matches_with_goals = matches.filter(fthg__isnull=False, ftag__isnull=False)
            if matches_with_goals.exists():
                total_goals = sum(match.fthg + match.ftag for match in matches_with_goals)
                avg_goals_total = total_goals / matches_with_goals.count()
            else:
                avg_goals_total = 0
            
            # Para shots_total: suma de hs + as
            matches_with_shots = matches.filter(hs__isnull=False, as_field__isnull=False)
            if matches_with_shots.exists():
                total_shots = sum(match.hs + match.as_field for match in matches_with_shots)
                avg_shots_total = total_shots / matches_with_shots.count()
            else:
                avg_shots_total = 0
            
            avg_corners_total = matches.aggregate(avg=Avg('corners_total'))['avg'] or 0
            
            # Calcular ambos marcan real
            both_score_matches = matches.filter(fthg__gt=0, ftag__gt=0).count()
            both_score_rate = both_score_matches / matches.count() if matches.count() > 0 else 0
            
            # Factores de calibración (valores objetivo basados en datos reales)
            target_goals = 2.5  # Objetivo realista para goles
            target_shots = 22.0  # Objetivo realista para shots (más preciso)
            target_corners = 9.0  # Objetivo realista para corners
            target_both_score = 0.45  # Objetivo realista para ambos marcan
            
            # Calcular factores de reducción
            goals_factor = min(1.0, target_goals / max(avg_goals_total, 1.0))
            shots_factor = min(1.0, target_shots / max(avg_shots_total, 1.0))
            corners_factor = min(1.0, target_corners / max(avg_corners_total, 1.0))
            both_score_factor = min(1.0, target_both_score / max(both_score_rate, 0.1))
            
            self.calibration_factors[league.name] = {
                'goals': goals_factor,
                'shots': shots_factor,
                'corners': corners_factor,
                'both_score': both_score_factor,
                'historical_avg_goals': avg_goals_total,
                'historical_avg_shots': avg_shots_total,
                'historical_avg_corners': avg_corners_total,
                'historical_both_score_rate': both_score_rate
            }
            
            logger.info(f"Calibración {league.name}: Goals={goals_factor:.3f}, Shots={shots_factor:.3f}, Corners={corners_factor:.3f}, BothScore={both_score_factor:.3f}")
    
    def calibrate_prediction(self, prediction: float, prediction_type: str, league_name: str) -> float:
        """Aplica calibración a una predicción específica"""
        
        if league_name not in self.calibration_factors:
            logger.warning(f"No hay factores de calibración para {league_name}")
            return prediction
        
        factors = self.calibration_factors[league_name]
        
        # Determinar qué factor aplicar
        if 'goals' in prediction_type:
            factor = factors['goals']
        elif 'shots' in prediction_type:
            factor = factors['shots']
        elif 'corners' in prediction_type:
            factor = factors['corners']
        elif 'both_teams_score' in prediction_type:
            factor = factors['both_score']
        else:
            factor = 1.0
        
        # Aplicar calibración con suavizado
        calibrated = prediction * factor
        
        # Aplicar límites realistas adicionales
        if 'shots' in prediction_type:
            calibrated = min(calibrated, 35.0)  # Máximo 35 shots (más realista)
        elif 'goals' in prediction_type:
            calibrated = min(calibrated, 5.0)   # Máximo 5 goles
        elif 'corners' in prediction_type:
            calibrated = min(calibrated, 15.0)   # Máximo 15 corners
        
        logger.debug(f"Calibración {prediction_type}: {prediction:.2f} → {calibrated:.2f} (factor: {factor:.3f})")
        
        return calibrated
    
    def get_league_stats(self, league_name: str) -> Dict:
        """Obtiene estadísticas históricas de una liga"""
        return self.calibration_factors.get(league_name, {})

# Instancia global
league_calibration = LeagueCalibrationService()
