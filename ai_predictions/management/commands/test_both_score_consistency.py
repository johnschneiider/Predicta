"""
Script para verificar la consistencia entre los valores de "ambos marcan" 
en las plantillas "analysis" y "result"
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from football_data.models import League, Match
from football_data.views import _process_match_with_predictions, _get_upcoming_matches_filtered
from ai_predictions.views import process_predictions_background
from ai_predictions.official_prediction_model import official_prediction_model
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica la consistencia de valores de ambos marcan entre analysis y result'

    def add_arguments(self, parser):
        parser.add_argument(
            '--match-id',
            type=int,
            help='ID de un partido específico para testear',
        )
        parser.add_argument(
            '--home-team',
            type=str,
            help='Nombre del equipo local',
        )
        parser.add_argument(
            '--away-team',
            type=str,
            help='Nombre del equipo visitante',
        )
        parser.add_argument(
            '--league',
            type=str,
            help='Nombre de la liga',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('[TEST] Iniciando test de consistencia de "Ambos Marcan"...'))
        
        # Obtener partidos para probar
        if options.get('match_id'):
            # Test con partido específico de la base de datos
            try:
                match = Match.objects.get(id=options['match_id'])
                self.test_match_from_db(match)
            except Match.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'[ERROR] No se encontro el partido con ID {options["match_id"]}'))
        elif options.get('home_team') and options.get('away_team'):
            # Test con equipos específicos
            league_name = options.get('league')
            self.test_with_teams(options['home_team'], options['away_team'], league_name)
        else:
            # Test con partidos próximos (simulando analysis)
            self.test_with_upcoming_matches()
    
    def test_match_from_db(self, match):
        """Prueba con un partido de la base de datos"""
        self.stdout.write(f'\n[INFO] Probando partido de BD: {match.home_team} vs {match.away_team}')
        
        # Simular cálculo de analysis
        analysis_result = self._calculate_analysis_way(match.home_team, match.away_team, match.league)
        
        # Simular cálculo de result
        result_value = self._calculate_result_way(match.home_team, match.away_team, match.league)
        
        self._compare_values(analysis_result, result_value, match.home_team, match.away_team)
    
    def test_with_teams(self, home_team, away_team, league_name=None):
        """Prueba con equipos específicos"""
        self.stdout.write(f'\n[INFO] Probando: {home_team} vs {away_team}')
        
        # Buscar liga
        league = None
        if league_name:
            league = League.objects.filter(name__icontains=league_name).first()
        
        if not league:
            # Buscar por equipos
            match = Match.objects.filter(
                home_team__iexact=home_team
            ).first()
            if match:
                league = match.league
        
        if not league:
            self.stdout.write(self.style.ERROR('[ERROR] No se pudo encontrar la liga'))
            return
        
        # Simular cálculo de analysis
        analysis_result = self._calculate_analysis_way(home_team, away_team, league)
        
        # Simular cálculo de result
        result_value = self._calculate_result_way(home_team, away_team, league)
        
        self._compare_values(analysis_result, result_value, home_team, away_team)
    
    def test_with_upcoming_matches(self):
        """Prueba con partidos próximos (como en analysis)"""
        self.stdout.write('\n[INFO] Probando con partidos proximos (modo analysis)...')
        
        upcoming_matches = _get_upcoming_matches_filtered()
        self.stdout.write(f'[INFO] Encontrados {len(upcoming_matches)} partidos proximos')
        
        if len(upcoming_matches) == 0:
            self.stdout.write(self.style.WARNING('[WARNING] No hay partidos proximos para probar'))
            return
        
        # Probar los primeros 3 partidos
        test_count = min(3, len(upcoming_matches))
        discrepancies = []
        
        for i, match_data in enumerate(upcoming_matches[:test_count]):
            home_team = match_data.get('home_team', '')
            away_team = match_data.get('away_team', '')
            
            if not home_team or not away_team:
                continue
            
            self.stdout.write(f'\n[TEST] Partido {i+1}/{test_count}: {home_team} vs {away_team}')
            
            # Procesar como en analysis
            analysis_result = _process_match_with_predictions(match_data)
            
            if not analysis_result:
                self.stdout.write(self.style.WARNING('  [WARNING] No se pudo procesar para analysis'))
                continue
            
            # Obtener valor de analysis
            analysis_value = analysis_result.get('prediction', 0)
            analysis_prob = analysis_result.get('probability', 0)
            
            # Buscar liga para result
            league_name = analysis_result.get('league', '')
            league = League.objects.filter(name__icontains=league_name).first()
            
            if not league:
                self.stdout.write(self.style.WARNING('  [WARNING] No se encontro la liga'))
                continue
            
            # Calcular como en result
            result_value = self._calculate_result_way(home_team, away_team, league)
            
            # Comparar
            self.stdout.write(f'  [ANALYSIS] {analysis_value:.1f}% (prob: {analysis_prob:.3f})')
            self.stdout.write(f'  [RESULT] {result_value:.1f}%')
            
            diff = abs(analysis_value - result_value)
            if diff > 1.0:  # Diferencia significativa (>1%)
                discrepancies.append({
                    'match': f'{home_team} vs {away_team}',
                    'analysis': analysis_value,
                    'result': result_value,
                    'diff': diff
                })
                self.stdout.write(self.style.ERROR(f'  [ERROR] DISCREPANCIA: {diff:.1f}% de diferencia'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Coinciden (diff: {diff:.1f}%)'))
        
        # Resumen
        if discrepancies:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Se encontraron {len(discrepancies)} discrepancias:'))
            for disc in discrepancies:
                self.stdout.write(f'  - {disc["match"]}: Analysis={disc["analysis"]:.1f}%, Result={disc["result"]:.1f}% (diff={disc["diff"]:.1f}%)')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n[OK] Todos los valores coinciden correctamente'))
    
    def _calculate_analysis_way(self, home_team, away_team, league):
        """Calcula como en analysis.html (views.py línea 1356)"""
        from ai_predictions.enhanced_both_teams_score import enhanced_both_teams_score_model
        from ai_predictions.simple_models import SimplePredictionService
        from ai_predictions.official_prediction_model import official_prediction_model
        
        try:
            prediction_types = ['both_teams_score']
            all_predictions_by_type = {}
            
            simple_service = SimplePredictionService()
            
            for pred_type in prediction_types:
                predictions = []
                
                try:
                    simple_predictions = simple_service.get_all_simple_predictions(
                        home_team, away_team, league, pred_type
                    )
                    predictions.extend(simple_predictions)
                except Exception as e:
                    logger.error(f"Error en simple_predictions: {e}")
                
                try:
                    enhanced_prob = enhanced_both_teams_score_model.predict(
                        home_team, away_team, league
                    )
                    enhanced_prediction = {
                        'model_name': 'Enhanced Both Teams Score',
                        'prediction': enhanced_prob,
                        'confidence': 0.80,
                        'probabilities': {'both_score': enhanced_prob},
                        'total_matches': 100
                    }
                    predictions.append(enhanced_prediction)
                except Exception as e:
                    logger.error(f"Error en enhanced: {e}")
                
                all_predictions_by_type[pred_type] = predictions
            
            official_predictions = official_prediction_model.calculate_official_predictions(all_predictions_by_type)
            
            match_predictions = {}
            for pred_type, official_pred in official_predictions.items():
                if official_pred and 'prediction' in official_pred:
                    match_predictions[pred_type] = {
                        'prediction': official_pred['prediction'],
                        'confidence': official_pred.get('confidence', 0.5),
                        'probabilities': official_pred.get('probabilities', {}),
                        'total_matches': official_pred.get('total_matches', 0),
                    }
            
            # Esta es la línea 1356 de views.py
            both_teams_score_pct = match_predictions.get('both_teams_score', {}).get('prediction', 0.5) * 100
            
            return {
                'percentage': both_teams_score_pct,
                'probability': match_predictions.get('both_teams_score', {}).get('prediction', 0.5),
                'probabilities': match_predictions.get('both_teams_score', {}).get('probabilities', {}),
                'raw': match_predictions.get('both_teams_score', {})
            }
        except Exception as e:
            logger.error(f"Error en _calculate_analysis_way: {e}", exc_info=True)
            return {'percentage': 0, 'probability': 0, 'probabilities': {}, 'raw': {}}
    
    def _calculate_result_way(self, home_team, away_team, league):
        """Calcula como en prediction_result_new.html (JavaScript línea 464)"""
        from ai_predictions.enhanced_both_teams_score import enhanced_both_teams_score_model
        from ai_predictions.simple_models import SimplePredictionService
        from ai_predictions.official_prediction_model import official_prediction_model
        
        try:
            prediction_types = ['both_teams_score']
            all_predictions_by_type = {}
            
            simple_service = SimplePredictionService()
            
            for pred_type in prediction_types:
                predictions = []
                
                try:
                    simple_predictions = simple_service.get_all_simple_predictions(
                        home_team, away_team, league, pred_type
                    )
                    predictions.extend(simple_predictions)
                except Exception as e:
                    logger.error(f"Error en simple_predictions: {e}")
                
                try:
                    enhanced_prob = enhanced_both_teams_score_model.predict(
                        home_team, away_team, league
                    )
                    enhanced_prediction = {
                        'model_name': 'Enhanced Both Teams Score',
                        'prediction': enhanced_prob,
                        'confidence': 0.80,
                        'probabilities': {'both_score': enhanced_prob},
                        'total_matches': 100
                    }
                    predictions.append(enhanced_prediction)
                except Exception as e:
                    logger.error(f"Error en enhanced: {e}")
                
                all_predictions_by_type[pred_type] = predictions
            
            official_predictions = official_prediction_model.calculate_official_predictions(all_predictions_by_type)
            
            # Buscar la predicción oficial
            official_pred = official_predictions.get('both_teams_score', {})
            
            if not official_pred:
                return 0
            
            # En result, se usa probabilities.both_score (línea 397 del template)
            # Y se multiplica por 100 en JavaScript (línea 464)
            both_score_prob = official_pred.get('probabilities', {}).get('both_score', 0)
            result_percentage = both_score_prob * 100
            
            return result_percentage
        except Exception as e:
            logger.error(f"Error en _calculate_result_way: {e}", exc_info=True)
            return 0
    
    def _compare_values(self, analysis_result, result_value, home_team, away_team):
        """Compara los valores y muestra el resultado"""
        analysis_pct = analysis_result.get('percentage', 0)
        analysis_prob = analysis_result.get('probability', 0)
        analysis_prob_both_score = analysis_result.get('probabilities', {}).get('both_score', 0)
        analysis_raw = analysis_result.get('raw', {})
        
        self.stdout.write(f'\n[INFO] Comparacion para {home_team} vs {away_team}:')
        self.stdout.write(f'  [ANALYSIS] (views.py linea 1356):')
        self.stdout.write(f'     - prediction * 100 = {analysis_pct:.1f}%')
        self.stdout.write(f'     - probability = {analysis_prob:.3f}')
        self.stdout.write(f'     - probabilities.both_score = {analysis_prob_both_score:.3f}')
        self.stdout.write(f'     - Raw data: {analysis_raw}')
        
        self.stdout.write(f'  [RESULT] (template + JS linea 464):')
        self.stdout.write(f'     - probabilities.both_score * 100 = {result_value:.1f}%')
        
        # Verificar si deberían ser iguales
        if abs(analysis_prob - analysis_prob_both_score) > 0.001:
            self.stdout.write(self.style.WARNING(f'  [WARNING] probability ({analysis_prob:.3f}) != probabilities.both_score ({analysis_prob_both_score:.3f})'))
        
        diff = abs(analysis_pct - result_value)
        if diff > 1.0:
            self.stdout.write(self.style.ERROR(f'  [ERROR] DISCREPANCIA: {diff:.1f}% de diferencia'))
            self.stdout.write(self.style.ERROR(f'  [ERROR] Esto explica por que el usuario ve valores diferentes'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Valores coinciden (diff: {diff:.1f}%)'))

