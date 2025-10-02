#!/usr/bin/env python
"""
Prueba para verificar que se generen 3 modelos (sin Simple Trend)
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

def test_3_models():
    """Prueba que se generen 3 modelos"""
    print("=== PRUEBA DE 3 MODELOS (SIN SIMPLE TREND) ===")
    
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
        print(f"   Modelos: {model_names}")
        print(f"   Cantidad: {len(predictions)}")
        
        # Verificar que tenemos 3 modelos
        if len(predictions) == 3:
            print("[EXITO] Se generaron 3 modelos correctamente")
            if 'Ensemble Average' in model_names:
                print("[EXITO] Ensemble Average presente")
            else:
                print("[ERROR] Ensemble Average NO presente")
            if 'Simple Trend' in model_names:
                print("[ERROR] Simple Trend NO debería estar presente")
            else:
                print("[EXITO] Simple Trend eliminado correctamente")
        else:
            print(f"[ERROR] Solo se generaron {len(predictions)} modelos, esperados 3")
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_3_models()
