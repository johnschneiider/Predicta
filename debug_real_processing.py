#!/usr/bin/env python
"""
Debug del procesamiento real
"""

import os
import sys
import django

# Configurar Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'betting_bot.settings')
django.setup()

from ai_predictions.simple_models import SimplePredictionService
from football_data.models import League

def debug_real_processing():
    """Simula el procesamiento real"""
    print("=== DEBUG DEL PROCESAMIENTO REAL ===")
    
    try:
        league = League.objects.first()
        if not league:
            print("[ERROR] No hay ligas disponibles")
            return
        
        print(f"[OK] Usando liga: {league.name}")
        
        service = SimplePredictionService()
        home_team = 'Bournemouth'
        away_team = 'Newcastle'
        
        # Simular el procesamiento de todos los tipos
        prediction_types = [
            'shots_total', 'shots_home', 'shots_away',
            'goals_total', 'goals_home', 'goals_away',
            'corners_total', 'corners_home', 'corners_away',
            'both_teams_score'
        ]
        
        all_predictions_by_type = {}
        
        for pred_type in prediction_types:
            print(f"\n[PROCESANDO] {pred_type}")
            try:
                predictions = service.get_all_simple_predictions(home_team, away_team, league, pred_type)
                all_predictions_by_type[pred_type] = predictions
                model_names = [pred['model_name'] for pred in predictions]
                print(f"   Resultado: {len(predictions)} modelos - {model_names}")
                
                if len(predictions) < 4:
                    print(f"   [WARNING] Solo {len(predictions)} modelos, esperados 4")
                else:
                    print(f"   [OK] 4 modelos generados correctamente")
                    
            except Exception as e:
                print(f"   [ERROR] {e}")
                all_predictions_by_type[pred_type] = []
        
        # Análisis final
        print(f"\n[ANALISIS FINAL]")
        model_names = set()
        total_models = 0
        for pred_type, predictions in all_predictions_by_type.items():
            total_models += len(predictions)
            for pred in predictions:
                model_names.add(pred['model_name'])
        
        model_names = sorted(list(model_names))
        print(f"   Modelos únicos: {model_names}")
        print(f"   Total modelos: {total_models}")
        print(f"   Cantidad única: {len(model_names)}")
        
        if len(model_names) < 4:
            print(f"   [PROBLEMA] Solo {len(model_names)} modelos únicos, esperados 4")
        else:
            print(f"   [EXITO] {len(model_names)} modelos únicos correctamente")
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_real_processing()
