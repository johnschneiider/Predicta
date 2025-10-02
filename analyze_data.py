#!/usr/bin/env python
import os
import sys
import django
import pandas as pd

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'betting_bot.settings')
django.setup()

from football_data.models import Match, League, ExcelFile

def analyze_data():
    print("🔍 ANÁLISIS DE DATOS PARA PREDICCIÓN DE REMATES\n")
    
    # 1. Estadísticas generales
    total_matches = Match.objects.count()
    total_leagues = League.objects.count()
    total_files = ExcelFile.objects.count()
    
    print("📊 ESTADÍSTICAS GENERALES:")
    print(f"   Total partidos: {total_matches}")
    print(f"   Total ligas: {total_leagues}")
    print(f"   Total archivos: {total_files}")
    
    if total_matches == 0:
        print("\n❌ No hay partidos en la base de datos")
        return
    
    # 2. Análisis de ligas
    print(f"\n🏆 LIGAS DISPONIBLES:")
    leagues = League.objects.all()
    for league in leagues:
        matches_count = Match.objects.filter(league=league).count()
        print(f"   {league.name} ({league.season}): {matches_count} partidos")
    
    # 3. Análisis de campos de remates
    print(f"\n⚽ ANÁLISIS DE CAMPOS DE REMATES:")
    
    # Obtener una muestra de partidos
    sample_matches = Match.objects.all()[:10]
    
    # Verificar qué campos de remates tenemos
    remate_fields = ['hs', 'as_field', 'hst', 'ast']  # Remates, Remates a puerta
    
    print("   Campos disponibles:")
    for field in remate_fields:
        non_null_count = Match.objects.exclude(**{field: None}).count()
        print(f"   - {field}: {non_null_count}/{total_matches} partidos tienen datos")
    
    # 4. Análisis de una muestra de datos
    print(f"\n📋 MUESTRA DE DATOS (primeros 5 partidos):")
    for match in sample_matches:
        print(f"   {match.date}: {match.home_team} vs {match.away_team}")
        print(f"     Remates Local: {match.hs}, Remates Visitante: {match.as_field}")
        print(f"     Remates a puerta Local: {match.hst}, Remates a puerta Visitante: {match.ast}")
        print(f"     Resultado: {match.fthg}-{match.ftag}")
        print()
    
    # 5. Análisis estadístico de remates
    print(f"\n📈 ESTADÍSTICAS DE REMATES:")
    
    # Remates locales
    hs_data = Match.objects.exclude(hs=None).values_list('hs', flat=True)
    if hs_data:
        hs_series = pd.Series(list(hs_data))
        print(f"   Remates Local (HS):")
        print(f"     Media: {hs_series.mean():.2f}")
        print(f"     Mediana: {hs_series.median():.2f}")
        print(f"     Min: {hs_series.min()}")
        print(f"     Max: {hs_series.max()}")
        print(f"     Desviación: {hs_series.std():.2f}")
    
    # Remates visitantes
    as_data = Match.objects.exclude(as_field=None).values_list('as_field', flat=True)
    if as_data:
        as_series = pd.Series(list(as_data))
        print(f"   Remates Visitante (AS):")
        print(f"     Media: {as_series.mean():.2f}")
        print(f"     Mediana: {as_series.median():.2f}")
        print(f"     Min: {as_series.min()}")
        print(f"     Max: {as_series.max()}")
        print(f"     Desviación: {as_series.std():.2f}")
    
    # 6. Análisis de otros campos relevantes
    print(f"\n🔍 OTROS CAMPOS RELEVANTES:")
    relevant_fields = [
        'fthg', 'ftag',  # Goles
        'hf', 'af',      # Faltas
        'hc', 'ac',      # Corners
        'hy', 'ay',      # Tarjetas amarillas
        'hr', 'ar',      # Tarjetas rojas
    ]
    
    for field in relevant_fields:
        non_null_count = Match.objects.exclude(**{field: None}).count()
        print(f"   - {field}: {non_null_count}/{total_matches} partidos tienen datos")
    
    # 7. Análisis temporal
    print(f"\n📅 ANÁLISIS TEMPORAL:")
    matches_with_dates = Match.objects.exclude(date=None).order_by('date')
    if matches_with_dates.exists():
        first_match = matches_with_dates.first()
        last_match = matches_with_dates.last()
        print(f"   Primer partido: {first_match.date}")
        print(f"   Último partido: {last_match.date}")
        print(f"   Período: {(last_match.date - first_match.date).days} días")
    
    # 8. Análisis de equipos únicos
    print(f"\n👥 ANÁLISIS DE EQUIPOS:")
    home_teams = Match.objects.values_list('home_team', flat=True).distinct()
    away_teams = Match.objects.values_list('away_team', flat=True).distinct()
    all_teams = set(list(home_teams) + list(away_teams))
    
    print(f"   Total equipos únicos: {len(all_teams)}")
    print(f"   Primeros 10 equipos: {list(all_teams)[:10]}")
    
    # 9. Análisis de cuotas (si están disponibles)
    print(f"\n💰 ANÁLISIS DE CUOTAS:")
    odds_fields = ['b365h', 'b365d', 'b365a', 'bwh', 'bwd', 'bwa']
    for field in odds_fields:
        non_null_count = Match.objects.exclude(**{field: None}).count()
        print(f"   - {field}: {non_null_count}/{total_matches} partidos tienen datos")

if __name__ == "__main__":
    analyze_data()
