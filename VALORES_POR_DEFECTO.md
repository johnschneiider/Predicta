# Valores por Defecto cuando no hay Datos Históricos

## Resumen de Valores Fallback

Cuando una liga no está creada en el proyecto o no hay datos históricos, el sistema usa los siguientes valores por defecto basados en promedios reales del fútbol:

### 1. Ambos Marcan (Both Teams Score)
- **Valor por defecto**: **45% (0.45)**
- **Rango permitido**: 20% - 70%
- **Ubicación**: `ai_predictions/enhanced_both_teams_score.py` líneas 232, 373
- **Nota**: Si no hay datos de la liga, se usa 45% que es el promedio realista en fútbol

### 2. Goles (Goals)
- **Goles Totales**: 3.0
- **Goles Local**: 1.5
- **Goles Visitante**: 1.2
- **Ubicación**: `ai_predictions/simple_models.py` líneas 316-351
- **Probabilidades Over**:
  - Over 1.5: 80%
  - Over 2.5: 50%
  - Over 3.5: 20%
  - Over 4.5: 5%
  - Over 5.5: 1%

### 3. Remates (Shots)
- **Remates Totales**: 15.0
- **Remates Local**: 12.0
- **Remates Visitante**: 11.0
- **Remates a Puerta Local**: 5.0
- **Remates a Puerta Visitante**: 4.0
- **Ubicación**: `ai_predictions/simple_models.py` líneas 327-351
- **Nota**: Los remates no se calculan en `get_all_simple_predictions` cuando no hay modelos específicos

### 4. Corners
- **Corners Totales**: ~9.8 (5.2 local + 4.6 visitante)
- **Corners Local**: 5.2
- **Corners Visitante**: 4.6
- **Ubicación**: `ai_predictions/simple_models.py` líneas 319, 342
- **Probabilidades Over**:
  - Over 8.5: 70%
  - Over 10.5: 50%
  - Over 12.5: 30%
  - Over 15.5: 10%
  - Over 20.5: 2%

## Comportamiento del Sistema

### Cuando NO existe la liga en la BD:
1. El sistema **crea automáticamente la liga** usando el mapeo `sport_key -> nombre`
2. Si no se puede crear, usa la primera liga disponible como fallback
3. Una vez creada, se usan los valores por defecto hasta que haya datos históricos

### Cuando la liga existe pero NO hay datos históricos:
1. Se usan los valores por defecto mencionados arriba
2. Los modelos intentan buscar datos históricos de los equipos en otras ligas
3. Si no encuentran nada, se usan los promedios realistas

### Cuando hay algunos datos pero insuficientes:
1. Se combinan los datos disponibles con valores por defecto
2. La confianza del modelo es menor (0.3-0.5 en lugar de 0.7-0.8)
3. Se muestra un indicador de baja confianza

## Valores Específicos por Tipo de Predicción

### Ambos Marcan sin datos:
```python
# enhanced_both_teams_score.py línea 373
return 0.45  # 45% - Valor por defecto absoluto
```

### Goles sin datos:
```python
# simple_models.py línea 316-351
default_value = 1.5  # Local
default_value = 1.2  # Visitante
default_prediction = 3.0  # Total
```

### Remates sin datos:
```python
# simple_models.py línea 328-351
default_value = 12.0  # Local
default_value = 11.0  # Visitante
default_prediction = 15.0  # Total
```

### Corners sin datos:
```python
# simple_models.py línea 319, 342
default_value = 5.2  # Local
default_value = 4.6  # Visitante
```

## Nota Importante

Estos valores por defecto están diseñados para ser **realistas y útiles** incluso sin datos históricos, basándose en promedios estadísticos reales del fútbol mundial. Sin embargo, las predicciones son mucho más precisas cuando hay datos históricos disponibles.

