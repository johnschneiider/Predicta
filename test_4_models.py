#!/usr/bin/env python
"""
Prueba para verificar que se generen 4 modelos
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

def test_4_models():
    """Prueba que se generen 4 modelos"""
    print("=== PRUEBA DE 4 MODELOS ===")
    
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
        
        # Verificar que tenemos 4 modelos
        if len(predictions) == 4:
            print("[EXITO] Se generaron 4 modelos correctamente")
            if 'Ensemble Average' in model_names:
                print("[EXITO] Ensemble Average presente")
            else:
                print("[ERROR] Ensemble Average NO presente")
        else:
            print(f"[ERROR] Solo se generaron {len(predictions)} modelos, esperados 4")
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_4_models()
