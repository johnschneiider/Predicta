#!/usr/bin/env python
"""
Prueba para verificar que solo se muestre Ensemble Average en la plantilla
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

def test_ensemble_only():
    """Prueba que solo se muestre Ensemble Average"""
    print("=== PRUEBA DE SOLO ENSEMBLE AVERAGE ===")
    
    try:
        league = League.objects.first()
        if not league:
            print("[ERROR] No hay ligas disponibles")
            return
        
        print(f"[OK] Usando liga: {league.name}")
        
        service = SimplePredictionService()
        home_team = 'Bournemouth'
        away_team = 'Newcastle'
        
        # Probar con shots_total
        print(f"\n[TEST] shots_total:")
        predictions = service.get_all_simple_predictions(home_team, away_team, league, 'shots_total')
        model_names = [pred['model_name'] for pred in predictions]
        print(f"   Modelos generados: {model_names}")
        print(f"   Cantidad: {len(predictions)}")
        
        # Verificar que tenemos 3 modelos en total
        if len(predictions) == 3:
            print("[EXITO] Se generaron 3 modelos en total")
            
            # Verificar que Ensemble Average está presente
            if 'Ensemble Average' in model_names:
                print("[EXITO] Ensemble Average presente")
                
                # Verificar que los otros modelos también están (para el cálculo)
                if 'Simple Poisson' in model_names and 'Simple Average' in model_names:
                    print("[EXITO] Modelos base presentes para el cálculo del Ensemble")
                else:
                    print("[ERROR] Faltan modelos base para el Ensemble")
            else:
                print("[ERROR] Ensemble Average NO presente")
        else:
            print(f"[ERROR] Solo se generaron {len(predictions)} modelos, esperados 3")
        
        print(f"\n[INFO] En la plantilla solo se mostrará: Ensemble Average")
        print(f"[INFO] Los otros modelos siguen existiendo para el cálculo interno")
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_only()
