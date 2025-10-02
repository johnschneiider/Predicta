#!/usr/bin/env python
"""
Script de debug para el modelo Ensemble
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

def debug_ensemble():
    """Debug específico del modelo Ensemble"""
    print("=== DEBUG DEL MODELO ENSEMBLE ===")
    
    try:
        league = League.objects.first()
        if not league:
            print("[ERROR] No hay ligas disponibles")
            return
        
        print(f"[OK] Usando liga: {league.name}")
        
        service = SimplePredictionService()
        prediction_type = 'shots_total'
        home_team = 'Bournemouth'
        away_team = 'Newcastle'
        
        print(f"\n[TEST] Generando predicciones para: {home_team} vs {away_team}")
        print(f"[TEST] Tipo: {prediction_type}")
        
        # Generar predicciones
        predictions = service.get_all_simple_predictions(home_team, away_team, league, prediction_type)
        
        print(f"\n[RESULTADOS]:")
        print(f"   Total de modelos: {len(predictions)}")
        
        for i, pred in enumerate(predictions, 1):
            print(f"   {i}. {pred['model_name']}: {pred['prediction']:.2f} (conf: {pred['confidence']:.3f})")
        
        # Verificar nombres únicos
        model_names = [pred['model_name'] for pred in predictions]
        unique_names = set(model_names)
        
        print(f"\n[ANALISIS]:")
        print(f"   Nombres únicos: {len(unique_names)}")
        print(f"   Lista: {sorted(unique_names)}")
        
        # Verificar si Ensemble está presente
        if 'Ensemble Average' in unique_names:
            print("[OK] Ensemble Average encontrado")
        else:
            print("[ERROR] Ensemble Average NO encontrado")
            
        # Verificar duplicados
        from collections import Counter
        name_counts = Counter(model_names)
        duplicates = {name: count for name, count in name_counts.items() if count > 1}
        if duplicates:
            print(f"[WARNING] Nombres duplicados: {duplicates}")
        else:
            print("[OK] No hay nombres duplicados")
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ensemble()
