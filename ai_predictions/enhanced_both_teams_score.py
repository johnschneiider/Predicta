"""
Modelo Mejorado de "Ambos Marcan" - Versión Robusta
Combina múltiples enfoques estadísticos para predecir si ambos equipos marcarán
"""

import logging
import numpy as np
import math
from django.db.models import Avg, Count, Q
from football_data.models import Match, League
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class EnhancedBothTeamsScoreModel:
    """
    Modelo robusto para predecir 'ambos marcan' que combina:
    1. Análisis de fuerzas ofensivas/defensivas
    2. Estadísticas históricas del enfrentamiento
    3. Forma reciente de ambos equipos
    4. Características específicas de la liga
    """
    
    def __init__(self):
        self.league_stats_cache = {}
        
    def predict(self, home_team: str, away_team: str, league: League) -> float:
        """
        Predice la probabilidad de que ambos equipos marquen
        
        Returns:
            float: Probabilidad entre 0.0 y 1.0
        """
        try:
            logger.debug(f"🎯 Calculando 'ambos marcan' para {home_team} vs {away_team} en {league.name}")
            
            # 1. Análisis de fuerzas ofensivas/defensivas (Poisson mejorado)
            poisson_prob = self._calculate_poisson_probability(home_team, away_team, league)
            
            # 2. Estadísticas históricas del enfrentamiento directo
            h2h_prob = self._calculate_head_to_head_probability(home_team, away_team, league)
            
            # 3. Forma reciente de ambos equipos
            recent_form_prob = self._calculate_recent_form_probability(home_team, away_team, league)
            
            # 4. Características específicas de la liga
            league_prob = self._calculate_league_baseline_probability(league)
            
            # 5. Combinar todas las probabilidades con pesos inteligentes
            final_probability = self._combine_probabilities(
                poisson_prob, h2h_prob, recent_form_prob, league_prob,
                home_team, away_team, league
            )
            
            # 6. Aplicar calibración final
            calibrated_prob = self._apply_final_calibration(final_probability, league)
            
            logger.debug(f"✅ Probabilidad final 'ambos marcan': {calibrated_prob:.3f}")
            
            return calibrated_prob
            
        except Exception as e:
            logger.error(f"❌ Error en predicción ambos marcan: {e}")
            # Fallback robusto basado en liga
            return self._get_league_fallback(league)
    
    def _calculate_poisson_probability(self, home_team: str, away_team: str, league: League) -> float:
        """Calcula probabilidad usando modelo Poisson mejorado"""
        
        # Obtener estadísticas de ambos equipos
        home_offensive, home_defensive = self._get_team_stats(home_team, league, is_home=True)
        away_offensive, away_defensive = self._get_team_stats(away_team, league, is_home=False)
        
        # Calcular goles esperados considerando ventaja local
        home_advantage = self._get_home_advantage_factor(league)
        
        # Goles esperados del equipo local (ofensiva local vs defensiva visitante)
        lambda_home = max(0.1, home_offensive * away_defensive * home_advantage)
        
        # Goles esperados del equipo visitante (ofensiva visitante vs defensiva local)
        lambda_away = max(0.1, away_offensive * home_defensive)
        
        # Calcular probabilidad de que ambos marquen usando Poisson
        # P(ambos marcan) = 1 - P(local no marca) - P(visitante no marca) + P(ninguno marca)
        p_home_no_goal = math.exp(-lambda_home)
        p_away_no_goal = math.exp(-lambda_away)
        p_both_no_goal = p_home_no_goal * p_away_no_goal
        
        poisson_prob = 1 - p_home_no_goal - p_away_no_goal + p_both_no_goal
        
        logger.debug(f"📊 Poisson - λ_home: {lambda_home:.2f}, λ_away: {lambda_away:.2f}, prob: {poisson_prob:.3f}")
        
        return max(0.1, min(0.9, poisson_prob))
    
    def _get_team_stats(self, team_name: str, league: League, is_home: bool) -> Tuple[float, float]:
        """Obtiene estadísticas ofensivas y defensivas de un equipo"""
        
        # Obtener partidos recientes del equipo
        matches = Match.objects.filter(
            Q(home_team=team_name) | Q(away_team=team_name),
            league=league,
            fthg__isnull=False,
            ftag__isnull=False
        ).order_by('-date')[:20]  # Últimos 20 partidos
        
        if not matches.exists():
            # Valores por defecto basados en la liga
            league_avg = self._get_league_average_stats(league)
            return league_avg, league_avg
        
        goals_scored = []
        goals_conceded = []
        
        for match in matches:
            if match.home_team == team_name:
                goals_scored.append(match.fthg or 0)
                goals_conceded.append(match.ftag or 0)
            else:
                goals_scored.append(match.ftag or 0)
                goals_conceded.append(match.fthg or 0)
        
        # Calcular promedios
        avg_goals_scored = np.mean(goals_scored) if goals_scored else 1.0
        avg_goals_conceded = np.mean(goals_conceded) if goals_conceded else 1.0
        
        # Ajustar por ventaja local/visitante
        if is_home:
            avg_goals_scored *= 1.1  # Ligera ventaja ofensiva en casa
            avg_goals_conceded *= 0.95  # Ligera ventaja defensiva en casa
        
        return max(0.1, avg_goals_scored), max(0.1, avg_goals_conceded)
    
    def _calculate_head_to_head_probability(self, home_team: str, away_team: str, league: League) -> float:
        """Calcula probabilidad basada en enfrentamientos directos"""
        
        h2h_matches = Match.objects.filter(
            Q(home_team=home_team, away_team=away_team) | 
            Q(home_team=away_team, away_team=home_team),
            league=league,
            fthg__isnull=False,
            ftag__isnull=False
        ).order_by('-date')[:10]  # Últimos 10 enfrentamientos
        
        if not h2h_matches.exists():
            return 0.5  # Valor neutro si no hay historial
        
        both_score_count = 0
        total_matches = len(h2h_matches)
        
        for match in h2h_matches:
            if match.fthg > 0 and match.ftag > 0:
                both_score_count += 1
        
        h2h_prob = both_score_count / total_matches
        
        logger.debug(f"🤝 H2H - {both_score_count}/{total_matches} partidos ambos marcan: {h2h_prob:.3f}")
        
        return max(0.1, min(0.9, h2h_prob))
    
    def _calculate_recent_form_probability(self, home_team: str, away_team: str, league: League) -> float:
        """Calcula probabilidad basada en forma reciente"""
        
        # Obtener forma reciente de ambos equipos
        home_form = self._get_team_recent_form(home_team, league, is_home=True)
        away_form = self._get_team_recent_form(away_team, league, is_home=False)
        
        # Combinar formas (equipos con buena forma ofensiva → mayor probabilidad ambos marcan)
        form_factor = (home_form + away_form) / 2
        
        # Convertir a probabilidad
        recent_form_prob = 0.3 + (form_factor * 0.4)  # Entre 0.3 y 0.7
        
        logger.debug(f"📈 Forma reciente - {home_team}: {home_form:.2f}, {away_team}: {away_form:.2f} → prob: {recent_form_prob:.3f}")
        
        return max(0.1, min(0.9, recent_form_prob))
    
    def _get_team_recent_form(self, team_name: str, league: League, is_home: bool) -> float:
        """Obtiene forma reciente de un equipo (0-1, donde 1 es excelente)"""
        
        matches = Match.objects.filter(
            Q(home_team=team_name) | Q(away_team=team_name),
            league=league,
            fthg__isnull=False,
            ftag__isnull=False
        ).order_by('-date')[:8]  # Últimos 8 partidos
        
        if not matches.exists():
            return 0.5
        
        form_score = 0
        total_matches = len(matches)
        
        for match in matches:
            if match.home_team == team_name:
                team_goals = match.fthg or 0
                opponent_goals = match.ftag or 0
            else:
                team_goals = match.ftag or 0
                opponent_goals = match.fthg or 0
            
            # Calcular puntuación del partido
            if team_goals > opponent_goals:
                form_score += 1.0  # Victoria
            elif team_goals == opponent_goals:
                form_score += 0.5  # Empate
            else:
                form_score += 0.0  # Derrota
            
            # Bonus por goles marcados
            form_score += min(0.2, team_goals * 0.05)
        
        # Normalizar entre 0 y 1
        normalized_form = form_score / (total_matches * 1.2)  # 1.2 para dar espacio al bonus
        
        return max(0.0, min(1.0, normalized_form))
    
    def _calculate_league_baseline_probability(self, league: League) -> float:
        """Calcula probabilidad base de la liga"""
        
        # Usar caché para evitar consultas repetidas
        if league.name in self.league_stats_cache:
            return self.league_stats_cache[league.name]
        
        matches = Match.objects.filter(
            league=league,
            fthg__isnull=False,
            ftag__isnull=False
        )
        
        if not matches.exists():
            # Valor por defecto para ligas sin datos
            baseline = 0.45
        else:
            both_score_count = matches.filter(fthg__gt=0, ftag__gt=0).count()
            baseline = both_score_count / matches.count()
        
        # Cachear resultado
        self.league_stats_cache[league.name] = baseline
        
        logger.debug(f"🏆 Liga {league.name} - Probabilidad base ambos marcan: {baseline:.3f}")
        
        return baseline
    
    def _combine_probabilities(self, poisson_prob: float, h2h_prob: float, 
                             recent_form_prob: float, league_prob: float,
                             home_team: str, away_team: str, league: League) -> float:
        """Combina todas las probabilidades con pesos inteligentes"""
        
        # Determinar pesos basados en la cantidad de datos disponibles
        h2h_matches = Match.objects.filter(
            Q(home_team=home_team, away_team=away_team) | 
            Q(home_team=away_team, away_team=home_team),
            league=league
        ).count()
        
        # Pesos dinámicos
        if h2h_matches >= 5:
            # Si hay suficiente historial H2H, darle más peso
            weights = {
                'poisson': 0.35,
                'h2h': 0.35,
                'recent_form': 0.20,
                'league': 0.10
            }
        elif h2h_matches >= 2:
            # Historial moderado
            weights = {
                'poisson': 0.40,
                'h2h': 0.25,
                'recent_form': 0.25,
                'league': 0.10
            }
        else:
            # Poco historial H2H, confiar más en otros factores
            weights = {
                'poisson': 0.45,
                'h2h': 0.10,
                'recent_form': 0.30,
                'league': 0.15
            }
        
        # Combinación ponderada
        combined_prob = (
            weights['poisson'] * poisson_prob +
            weights['h2h'] * h2h_prob +
            weights['recent_form'] * recent_form_prob +
            weights['league'] * league_prob
        )
        
        logger.debug(f"⚖️ Pesos: Poisson={weights['poisson']}, H2H={weights['h2h']}, Forma={weights['recent_form']}, Liga={weights['league']}")
        logger.debug(f"🔗 Probabilidad combinada: {combined_prob:.3f}")
        
        return combined_prob
    
    def _apply_final_calibration(self, probability: float, league: League) -> float:
        """Aplica calibración final basada en características de la liga"""
        
        # Obtener estadísticas de la liga
        league_stats = self._get_league_average_stats(league)
        
        # Ajustar según el promedio de goles de la liga
        if league_stats < 2.0:
            # Ligas defensivas → reducir probabilidad
            calibrated = probability * 0.85
        elif league_stats > 3.0:
            # Ligas ofensivas → aumentar probabilidad
            calibrated = probability * 1.15
        else:
            # Ligas balanceadas → mantener
            calibrated = probability
        
        # Limitar entre rangos realistas
        calibrated = max(0.15, min(0.80, calibrated))
        
        logger.debug(f"🎯 Calibración final: {probability:.3f} → {calibrated:.3f}")
        
        return calibrated
    
    def _get_league_average_stats(self, league: League) -> float:
        """Obtiene promedio de goles por partido en la liga"""
        
        matches = Match.objects.filter(
            league=league,
            fthg__isnull=False,
            ftag__isnull=False
        )
        
        if not matches.exists():
            return 2.5  # Valor por defecto
        
        total_goals = sum((match.fthg or 0) + (match.ftag or 0) for match in matches)
        avg_goals = total_goals / matches.count()
        
        return avg_goals
    
    def _get_home_advantage_factor(self, league: League) -> float:
        """Calcula factor de ventaja local para la liga"""
        
        # Valores típicos por liga (pueden ajustarse con datos históricos)
        home_advantage_factors = {
            'Premier League': 1.15,
            'Bundesliga': 1.12,
            'La Liga': 1.10,
            'Serie A': 1.08,
            'Ligue 1': 1.10,
            'Championship': 1.18,
            'League One': 1.20,
            'League Two': 1.22,
        }
        
        return home_advantage_factors.get(league.name, 1.12)  # Valor por defecto
    
    def _get_league_fallback(self, league: League) -> float:
        """Fallback robusto basado en estadísticas de la liga"""
        
        try:
            # Usar probabilidad base de la liga con pequeña variación
            baseline = self._calculate_league_baseline_probability(league)
            
            # Añadir pequeña variación aleatoria para evitar valores idénticos
            variation = np.random.normal(0, 0.02)
            fallback_prob = baseline + variation
            
            # Limitar a rango realista
            fallback_prob = max(0.20, min(0.70, fallback_prob))
            
            logger.info(f"🔄 Usando fallback para {league.name}: {fallback_prob:.3f}")
            
            return fallback_prob
            
        except Exception as e:
            logger.error(f"❌ Error en fallback: {e}")
            return 0.45  # Valor por defecto absoluto

# Instancia global del modelo mejorado
enhanced_both_teams_score_model = EnhancedBothTeamsScoreModel()
