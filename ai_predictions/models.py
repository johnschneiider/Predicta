"""
Modelos para predicciones de IA
"""

from django.db import models
from django.utils import timezone
from football_data.models import League, Match


class PredictionModel(models.Model):
    """Modelo para almacenar información sobre los modelos de predicción entrenados"""
    
    MODEL_TYPES = [
        ('linear_regression', 'Regresión Lineal'),
        ('random_forest', 'Random Forest'),
        ('gradient_boosting', 'Gradient Boosting'),
        ('neural_network', 'Red Neuronal'),
    ]
    
    PREDICTION_TYPES = [
        ('shots_total', 'Remates Totales'),
        ('shots_home', 'Remates Local'),
        ('shots_away', 'Remates Visitante'),
        ('shots_on_target', 'Remates a Puerta'),
        ('goals_total', 'Goles Totales'),
        ('goals_home', 'Goles Local'),
        ('goals_away', 'Goles Visitante'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nombre del Modelo")
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES, verbose_name="Tipo de Modelo")
    prediction_type = models.CharField(max_length=50, choices=PREDICTION_TYPES, verbose_name="Tipo de Predicción")
    league = models.ForeignKey(League, on_delete=models.CASCADE, verbose_name="Liga")
    
    # Métricas del modelo
    accuracy = models.FloatField(null=True, blank=True, verbose_name="Precisión")
    mae = models.FloatField(null=True, blank=True, verbose_name="Error Absoluto Medio")
    rmse = models.FloatField(null=True, blank=True, verbose_name="Error Cuadrático Medio")
    r2_score = models.FloatField(null=True, blank=True, verbose_name="R² Score")
    
    # Configuración del modelo
    features_used = models.JSONField(default=list, verbose_name="Características Utilizadas")
    model_parameters = models.JSONField(default=dict, verbose_name="Parámetros del Modelo")
    
    # Metadatos
    trained_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Entrenamiento")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Modelo de Predicción"
        verbose_name_plural = "Modelos de Predicción"
        ordering = ['-trained_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_prediction_type_display()}"


class PredictionResult(models.Model):
    """Resultados de predicciones realizadas"""
    
    model = models.ForeignKey(PredictionModel, on_delete=models.CASCADE, verbose_name="Modelo")
    home_team = models.CharField(max_length=100, verbose_name="Equipo Local")
    away_team = models.CharField(max_length=100, verbose_name="Equipo Visitante")
    league = models.ForeignKey(League, on_delete=models.CASCADE, verbose_name="Liga")
    
    # Predicciones
    predicted_value = models.FloatField(verbose_name="Valor Predicho")
    confidence_score = models.FloatField(verbose_name="Puntuación de Confianza")
    
    # Probabilidades para diferentes rangos
    probability_over_10 = models.FloatField(null=True, blank=True, verbose_name="Probabilidad > 10")
    probability_over_15 = models.FloatField(null=True, blank=True, verbose_name="Probabilidad > 15")
    probability_over_20 = models.FloatField(null=True, blank=True, verbose_name="Probabilidad > 20")
    
    # Características utilizadas para la predicción
    features_used = models.JSONField(default=dict, verbose_name="Características Utilizadas")
    
    # Metadatos
    predicted_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Predicción")
    
    class Meta:
        verbose_name = "Resultado de Predicción"
        verbose_name_plural = "Resultados de Predicciones"
        ordering = ['-predicted_at']
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team} - {self.predicted_value:.1f}"


class TeamStats(models.Model):
    """Estadísticas de equipos para usar en predicciones"""
    
    team_name = models.CharField(max_length=100, verbose_name="Nombre del Equipo")
    league = models.ForeignKey(League, on_delete=models.CASCADE, verbose_name="Liga")
    
    # Estadísticas de remates (últimos 5 partidos)
    avg_shots_home = models.FloatField(default=0, verbose_name="Promedio Remates en Casa")
    avg_shots_away = models.FloatField(default=0, verbose_name="Promedio Remates como Visitante")
    avg_shots_total = models.FloatField(default=0, verbose_name="Promedio Remates Total")
    
    # Estadísticas de goles
    avg_goals_home = models.FloatField(default=0, verbose_name="Promedio Goles en Casa")
    avg_goals_away = models.FloatField(default=0, verbose_name="Promedio Goles como Visitante")
    
    # Forma reciente (últimos 5 partidos)
    recent_wins = models.IntegerField(default=0, verbose_name="Victorias Recientes")
    recent_draws = models.IntegerField(default=0, verbose_name="Empates Recientes")
    recent_losses = models.IntegerField(default=0, verbose_name="Derrotas Recientes")
    
    # Metadatos
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    class Meta:
        verbose_name = "Estadísticas de Equipo"
        verbose_name_plural = "Estadísticas de Equipos"
        unique_together = ['team_name', 'league']
        ordering = ['team_name']
    
    def __str__(self):
        return f"{self.team_name} - {self.league.name}"
    
    @property
    def recent_form_score(self):
        """Puntuación de forma reciente (0-1)"""
        total_matches = self.recent_wins + self.recent_draws + self.recent_losses
        if total_matches == 0:
            return 0.5
        return (self.recent_wins * 3 + self.recent_draws) / (total_matches * 3)
