"""
Características avanzadas para mejorar la precisión de predicciones
"""

import numpy as np
import logging
from typing import Dict, List, Tuple
from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Avg, StdDev, Count, Q
from football_data.models import Match, League

logger = logging.getLogger('ai_predictions')


class AdvancedFeatureExtractor:
    """Extractor de características avanzadas para mejorar predicciones"""
    
    def __init__(self):
        pass
    
    def get_team_form_analysis(self, team_name: str, league: League, is_home: bool, days_back: int = 365) -> Dict:
        """Análisis de forma del equipo con múltiples métricas"""
        try:
            cutoff_date = timezone.now().date() - timedelta(days=days_back)
            
            if is_home:
                matches = Match.objects.filter(
                    league=league,
                    home_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:30]
                
                # Datos de goles y remates
                goals_data = [m.fthg for m in matches if m.fthg is not None]
                shots_data = [m.hs for m in matches if m.hs is not None]
                shots_on_target = [m.hst for m in matches if m.hst is not None]
                goals_conceded = [m.ftag for m in matches if m.ftag is not None]
                
                # Resultados
                wins = sum(1 for m in matches if m.fthg and m.ftag and m.fthg > m.ftag)
                draws = sum(1 for m in matches if m.fthg and m.ftag and m.fthg == m.ftag)
                losses = sum(1 for m in matches if m.fthg and m.ftag and m.fthg < m.ftag)
            else:
                matches = Match.objects.filter(
                    league=league,
                    away_team=team_name,
                    date__gte=cutoff_date
                ).order_by('-date')[:30]
                
                goals_data = [m.ftag for m in matches if m.ftag is not None]
                shots_data = [m.as_field for m in matches if m.as_field is not None]
                shots_on_target = [m.ast for m in matches if m.ast is not None]
                goals_conceded = [m.fthg for m in matches if m.fthg is not None]
                
                wins = sum(1 for m in matches if m.fthg and m.ftag and m.ftag > m.fthg)
                draws = sum(1 for m in matches if m.fthg and m.ftag and m.ftag == m.fthg)
                losses = sum(1 for m in matches if m.fthg and m.ftag and m.ftag < m.fthg)
            
            if not goals_data:
                return self._default_form_features()
            
            # Métricas básicas
            avg_goals = np.mean(goals_data)
            avg_shots = np.mean(shots_data) if shots_data else 0
            avg_shots_on_target = np.mean(shots_on_target) if shots_on_target else 0
            avg_goals_conceded = np.mean(goals_conceded) if goals_conceded else 0
            
            # Análisis de forma reciente (últimos 5 partidos vs anteriores 5)
            recent_goals = goals_data[:5] if len(goals_data) >= 5 else goals_data
            older_goals = goals_data[5:10] if len(goals_data) >= 10 else goals_data[5:]
            
            form_trend = np.mean(recent_goals) - np.mean(older_goals) if len(older_goals) > 0 else 0
            
            # Eficiencia ofensiva y defensiva
            conversion_rate = avg_goals / avg_shots if avg_shots > 0 else 0
            shots_on_target_rate = avg_shots_on_target / avg_shots if avg_shots > 0 else 0
            defensive_solidity = 1 / (avg_goals_conceded + 0.1)  # Inverso de goles concedidos
            
            # Consistencia (baja variabilidad = alta consistencia)
            goals_consistency = 1 / (np.std(goals_data) + 0.1)
            shots_consistency = 1 / (np.std(shots_data) + 0.1) if shots_data else 0.5
            
            # Momentum (tendencia de los últimos 3 partidos)
            momentum = np.mean(goals_data[:3]) - np.mean(goals_data[3:6]) if len(goals_data) >= 6 else 0
            
            # Puntos por partido
            total_matches = wins + draws + losses
            points_per_game = (wins * 3 + draws) / total_matches if total_matches > 0 else 1.0
            
            return {
                'avg_goals': avg_goals,
                'avg_shots': avg_shots,
                'avg_shots_on_target': avg_shots_on_target,
                'avg_goals_conceded': avg_goals_conceded,
                'form_trend': form_trend,
                'conversion_rate': conversion_rate,
                'shots_on_target_rate': shots_on_target_rate,
                'defensive_solidity': defensive_solidity,
                'goals_consistency': goals_consistency,
                'shots_consistency': shots_consistency,
                'momentum': momentum,
                'points_per_game': points_per_game,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'total_matches': total_matches,
                'home_advantage': 1.15 if is_home else 0.9
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de forma de {team_name}: {e}")
            return self._default_form_features()
    
    def get_head_to_head_analysis(self, home_team: str, away_team: str, league: League) -> Dict:
        """Análisis de enfrentamientos directos entre equipos"""
        try:
            # Buscar enfrentamientos directos en los últimos 3 años
            cutoff_date = timezone.now().date() - timedelta(days=1095)
            
            matches = Match.objects.filter(
                league=league,
                date__gte=cutoff_date
            ).filter(
                Q(home_team=home_team, away_team=away_team) |
                Q(home_team=away_team, away_team=home_team)
            ).order_by('-date')[:10]
            
            if not matches:
                return self._default_h2h_features()
            
            home_wins = 0
            away_wins = 0
            draws = 0
            home_goals = []
            away_goals = []
            home_shots = []
            away_shots = []
            
            for match in matches:
                if match.home_team == home_team:
                    # Partido donde el equipo es local
                    if match.fthg and match.ftag:
                        home_goals.append(match.fthg)
                        away_goals.append(match.ftag)
                        if match.hs: home_shots.append(match.hs)
                        if match.as_field: away_shots.append(match.as_field)
                        
                        if match.fthg > match.ftag:
                            home_wins += 1
                        elif match.fthg < match.ftag:
                            away_wins += 1
                        else:
                            draws += 1
                else:
                    # Partido donde el equipo es visitante
                    if match.fthg and match.ftag:
                        home_goals.append(match.ftag)  # Goles del equipo como visitante
                        away_goals.append(match.fthg)  # Goles del rival como local
                        if match.as_field: home_shots.append(match.as_field)
                        if match.hs: away_shots.append(match.hs)
                        
                        if match.ftag > match.fthg:
                            home_wins += 1
                        elif match.ftag < match.fthg:
                            away_wins += 1
                        else:
                            draws += 1
            
            if not home_goals:
                return self._default_h2h_features()
            
            # Estadísticas de enfrentamientos directos
            avg_home_goals = np.mean(home_goals)
            avg_away_goals = np.mean(away_goals)
            avg_home_shots = np.mean(home_shots) if home_shots else 0
            avg_away_shots = np.mean(away_shots) if away_shots else 0
            
            total_matches = len(matches)
            home_win_rate = home_wins / total_matches
            away_win_rate = away_wins / total_matches
            draw_rate = draws / total_matches
            
            # Dominio del equipo local
            home_dominance = (avg_home_goals - avg_away_goals) / (avg_home_goals + avg_away_goals + 0.1)
            
            return {
                'matches_count': total_matches,
                'home_wins': home_wins,
                'away_wins': away_wins,
                'draws': draws,
                'home_win_rate': home_win_rate,
                'away_win_rate': away_win_rate,
                'draw_rate': draw_rate,
                'avg_home_goals': avg_home_goals,
                'avg_away_goals': avg_away_goals,
                'avg_home_shots': avg_home_shots,
                'avg_away_shots': avg_away_shots,
                'home_dominance': home_dominance
            }
            
        except Exception as e:
            logger.error(f"Error en análisis H2H {home_team} vs {away_team}: {e}")
            return self._default_h2h_features()
    
    def get_league_context(self, league: League, prediction_type: str) -> Dict:
        """Contexto de la liga para normalizar predicciones"""
        try:
            # Estadísticas generales de la liga en los últimos 2 años
            cutoff_date = timezone.now().date() - timedelta(days=730)
            
            matches = Match.objects.filter(
                league=league,
                date__gte=cutoff_date
            ).exclude(
                Q(fthg__isnull=True) | Q(ftag__isnull=True) |
                Q(hs__isnull=True) | Q(as_field__isnull=True)
            )
            
            if not matches:
                return self._default_league_context()
            
            if 'goals' in prediction_type:
                # Estadísticas de goles
                home_goals = [m.fthg for m in matches if m.fthg is not None]
                away_goals = [m.ftag for m in matches if m.ftag is not None]
                
                league_avg_home_goals = np.mean(home_goals)
                league_avg_away_goals = np.mean(away_goals)
                league_avg_total_goals = league_avg_home_goals + league_avg_away_goals
                
                return {
                    'league_avg_home_goals': league_avg_home_goals,
                    'league_avg_away_goals': league_avg_away_goals,
                    'league_avg_total_goals': league_avg_total_goals,
                    'home_advantage_factor': league_avg_home_goals / league_avg_away_goals if league_avg_away_goals > 0 else 1.2,
                    'total_matches': len(matches)
                }
            else:
                # Estadísticas de remates
                home_shots = [m.hs for m in matches if m.hs is not None]
                away_shots = [m.as_field for m in matches if m.as_field is not None]
                
                league_avg_home_shots = np.mean(home_shots)
                league_avg_away_shots = np.mean(away_shots)
                league_avg_total_shots = league_avg_home_shots + league_avg_away_shots
                
                return {
                    'league_avg_home_shots': league_avg_home_shots,
                    'league_avg_away_shots': league_avg_away_shots,
                    'league_avg_total_shots': league_avg_total_shots,
                    'home_advantage_factor': league_avg_home_shots / league_avg_away_shots if league_avg_away_shots > 0 else 1.15,
                    'total_matches': len(matches)
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo contexto de liga: {e}")
            return self._default_league_context()
    
    def get_team_strength_rating(self, team_name: str, league: League, is_home: bool) -> Dict:
        """Rating de fortaleza del equipo basado en múltiples factores"""
        try:
            form_data = self.get_team_form_analysis(team_name, league, is_home)
            
            # Calcular rating compuesto
            offensive_rating = (
                form_data['avg_goals'] * 0.3 +
                form_data['conversion_rate'] * 100 * 0.2 +
                form_data['shots_on_target_rate'] * 100 * 0.2 +
                form_data['avg_shots'] * 0.1 +
                form_data['points_per_game'] * 0.2
            )
            
            defensive_rating = (
                form_data['defensive_solidity'] * 0.4 +
                form_data['goals_consistency'] * 0.3 +
                form_data['shots_consistency'] * 0.3
            )
            
            form_rating = (
                form_data['form_trend'] * 10 + 5 +  # Normalizar a escala 0-10
                form_data['momentum'] * 5 + 2.5 +
                form_data['wins'] / max(form_data['total_matches'], 1) * 10
            )
            
            overall_rating = (offensive_rating * 0.4 + defensive_rating * 0.3 + form_rating * 0.3)
            
            return {
                'offensive_rating': offensive_rating,
                'defensive_rating': defensive_rating,
                'form_rating': form_rating,
                'overall_rating': overall_rating,
                'matches_analyzed': form_data['total_matches']
            }
            
        except Exception as e:
            logger.error(f"Error calculando rating de {team_name}: {e}")
            return self._default_rating_features()
    
    def prepare_advanced_features(self, home_team: str, away_team: str, league: League, 
                                 prediction_type: str) -> List[float]:
        """Prepara vector de características avanzadas para el modelo"""
        try:
            # Obtener datos de ambos equipos
            home_form = self.get_team_form_analysis(home_team, league, True)
            away_form = self.get_team_form_analysis(away_team, league, False)
            h2h_data = self.get_head_to_head_analysis(home_team, away_team, league)
            league_context = self.get_league_context(league, prediction_type)
            home_rating = self.get_team_strength_rating(home_team, league, True)
            away_rating = self.get_team_strength_rating(away_team, league, False)
            
            # Crear vector de características
            features = [
                # Características del equipo local
                home_form['avg_goals'],
                home_form['avg_shots'],
                home_form['conversion_rate'],
                home_form['form_trend'],
                home_form['momentum'],
                home_form['defensive_solidity'],
                home_form['points_per_game'],
                home_rating['offensive_rating'],
                home_rating['defensive_rating'],
                home_rating['overall_rating'],
                
                # Características del equipo visitante
                away_form['avg_goals'],
                away_form['avg_shots'],
                away_form['conversion_rate'],
                away_form['form_trend'],
                away_form['momentum'],
                away_form['defensive_solidity'],
                away_form['points_per_game'],
                away_rating['offensive_rating'],
                away_rating['defensive_rating'],
                away_rating['overall_rating'],
                
                # Enfrentamientos directos
                h2h_data['home_win_rate'],
                h2h_data['home_dominance'],
                h2h_data['avg_home_goals'],
                h2h_data['avg_away_goals'],
                
                # Contexto de liga
                league_context['home_advantage_factor'],
                league_context['league_avg_total_goals'] if 'goals' in prediction_type else league_context['league_avg_total_shots'],
                
                # Ventaja de local
                home_form['home_advantage']
            ]
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparando características avanzadas: {e}")
            return [0.0] * 27  # Vector por defecto
    
    def _default_form_features(self) -> Dict:
        """Características por defecto para análisis de forma"""
        return {
            'avg_goals': 1.5, 'avg_shots': 12.0, 'avg_shots_on_target': 4.0,
            'avg_goals_conceded': 1.2, 'form_trend': 0, 'conversion_rate': 0.12,
            'shots_on_target_rate': 0.33, 'defensive_solidity': 0.8,
            'goals_consistency': 0.5, 'shots_consistency': 0.5, 'momentum': 0,
            'points_per_game': 1.5, 'wins': 5, 'draws': 5, 'losses': 5,
            'total_matches': 15, 'home_advantage': 1.0
        }
    
    def _default_h2h_features(self) -> Dict:
        """Características por defecto para H2H"""
        return {
            'matches_count': 0, 'home_wins': 0, 'away_wins': 0, 'draws': 0,
            'home_win_rate': 0.33, 'away_win_rate': 0.33, 'draw_rate': 0.34,
            'avg_home_goals': 1.5, 'avg_away_goals': 1.2, 'avg_home_shots': 12.0,
            'avg_away_shots': 11.0, 'home_dominance': 0.1
        }
    
    def _default_league_context(self) -> Dict:
        """Contexto por defecto de liga"""
        return {
            'league_avg_home_goals': 1.5, 'league_avg_away_goals': 1.2,
            'league_avg_total_goals': 2.7, 'league_avg_home_shots': 12.0,
            'league_avg_away_shots': 11.0, 'league_avg_total_shots': 23.0,
            'home_advantage_factor': 1.2, 'total_matches': 0
        }
    
    def _default_rating_features(self) -> Dict:
        """Rating por defecto"""
        return {
            'offensive_rating': 5.0, 'defensive_rating': 5.0,
            'form_rating': 5.0, 'overall_rating': 5.0, 'matches_analyzed': 0
        }
