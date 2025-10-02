#!/usr/bin/env python
"""
Prueba final para verificar los 4 modelos
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

def test_final():
    """Prueba final de los 4 modelos"""
    print("=== PRUEBA FINAL DE LOS 4 MODELOS ===")
    
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
        if len(predictions) == 4 and 'Ensemble Average' in model_names:
            print("[EXITO] Los 4 modelos se generan correctamente")
        else:
            print("[ERROR] No se generaron los 4 modelos correctamente")
            print(f"   Esperados: 4, Obtenidos: {len(predictions)}")
            print(f"   Ensemble presente: {'Ensemble Average' in model_names}")
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_final()
