"""
Modelos para datos de NBA usando nba_api
"""

from django.db import models
from django.utils import timezone


class NBATeam(models.Model):
    """Modelo para equipos de NBA"""
    nba_id = models.CharField(max_length=20, unique=True, verbose_name="NBA ID")
    full_name = models.CharField(max_length=100, verbose_name="Nombre Completo")
    abbreviation = models.CharField(max_length=10, verbose_name="Abreviatura")
    nickname = models.CharField(max_length=50, verbose_name="Apodo")
    city = models.CharField(max_length=50, verbose_name="Ciudad")
    state = models.CharField(max_length=50, verbose_name="Estado")
    year_founded = models.IntegerField(verbose_name="Año de Fundación")
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Equipo NBA"
        verbose_name_plural = "Equipos NBA"
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name} ({self.abbreviation})"


class NBAPlayer(models.Model):
    """Modelo para jugadores de NBA"""
    nba_id = models.CharField(max_length=20, unique=True, verbose_name="NBA ID")
    full_name = models.CharField(max_length=100, verbose_name="Nombre Completo")
    first_name = models.CharField(max_length=50, verbose_name="Nombre")
    last_name = models.CharField(max_length=50, verbose_name="Apellido")
    is_active = models.BooleanField(default=False, verbose_name="Activo")
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Jugador NBA"
        verbose_name_plural = "Jugadores NBA"
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name}"


class NBAGame(models.Model):
    """Modelo para partidos de NBA - Enfocado en predicción de puntos totales"""
    nba_game_id = models.CharField(max_length=20, unique=True, verbose_name="NBA Game ID")
    season_id = models.CharField(max_length=20, verbose_name="Season ID")
    game_date = models.DateField(verbose_name="Fecha del Partido")
    season_type = models.CharField(max_length=20, verbose_name="Tipo de Temporada")
    
    # Equipos
    home_team = models.ForeignKey(NBATeam, on_delete=models.CASCADE, related_name='home_games', verbose_name="Equipo Local")
    away_team = models.ForeignKey(NBATeam, on_delete=models.CASCADE, related_name='away_games', verbose_name="Equipo Visitante")
    
    # Resultado del partido
    home_win = models.BooleanField(null=True, blank=True, verbose_name="Victoria Local")
    
    # Puntos (target principal para predicción)
    home_points = models.IntegerField(null=True, blank=True, verbose_name="Puntos Local")
    away_points = models.IntegerField(null=True, blank=True, verbose_name="Puntos Visitante")
    total_points = models.IntegerField(null=True, blank=True, verbose_name="Puntos Totales")
    
    # Estadísticas básicas del equipo LOCAL
    home_minutes = models.IntegerField(null=True, blank=True, verbose_name="Minutos Local")
    home_fgm = models.IntegerField(null=True, blank=True, verbose_name="Tiros Anotados Local")
    home_fga = models.IntegerField(null=True, blank=True, verbose_name="Tiros Intentados Local")
    home_fg_pct = models.FloatField(null=True, blank=True, verbose_name="% Tiros Local")
    home_fg3m = models.IntegerField(null=True, blank=True, verbose_name="Triples Anotados Local")
    home_fg3a = models.IntegerField(null=True, blank=True, verbose_name="Triples Intentados Local")
    home_fg3_pct = models.FloatField(null=True, blank=True, verbose_name="% Triples Local")
    home_ftm = models.IntegerField(null=True, blank=True, verbose_name="Tiros Libres Anotados Local")
    home_fta = models.IntegerField(null=True, blank=True, verbose_name="Tiros Libres Intentados Local")
    home_ft_pct = models.FloatField(null=True, blank=True, verbose_name="% Tiros Libres Local")
    home_oreb = models.IntegerField(null=True, blank=True, verbose_name="Rebotes Ofensivos Local")
    home_dreb = models.IntegerField(null=True, blank=True, verbose_name="Rebotes Defensivos Local")
    home_reb = models.IntegerField(null=True, blank=True, verbose_name="Rebotes Totales Local")
    home_ast = models.IntegerField(null=True, blank=True, verbose_name="Asistencias Local")
    home_stl = models.IntegerField(null=True, blank=True, verbose_name="Robos Local")
    home_blk = models.IntegerField(null=True, blank=True, verbose_name="Tapones Local")
    home_tov = models.IntegerField(null=True, blank=True, verbose_name="Pérdidas Local")
    home_pf = models.IntegerField(null=True, blank=True, verbose_name="Faltas Local")
    home_plus_minus = models.IntegerField(null=True, blank=True, verbose_name="Plus/Minus Local")
    
    # Estadísticas básicas del equipo VISITANTE
    away_minutes = models.IntegerField(null=True, blank=True, verbose_name="Minutos Visitante")
    away_fgm = models.IntegerField(null=True, blank=True, verbose_name="Tiros Anotados Visitante")
    away_fga = models.IntegerField(null=True, blank=True, verbose_name="Tiros Intentados Visitante")
    away_fg_pct = models.FloatField(null=True, blank=True, verbose_name="% Tiros Visitante")
    away_fg3m = models.IntegerField(null=True, blank=True, verbose_name="Triples Anotados Visitante")
    away_fg3a = models.IntegerField(null=True, blank=True, verbose_name="Triples Intentados Visitante")
    away_fg3_pct = models.FloatField(null=True, blank=True, verbose_name="% Triples Visitante")
    away_ftm = models.IntegerField(null=True, blank=True, verbose_name="Tiros Libres Anotados Visitante")
    away_fta = models.IntegerField(null=True, blank=True, verbose_name="Tiros Libres Intentados Visitante")
    away_ft_pct = models.FloatField(null=True, blank=True, verbose_name="% Tiros Libres Visitante")
    away_oreb = models.IntegerField(null=True, blank=True, verbose_name="Rebotes Ofensivos Visitante")
    away_dreb = models.IntegerField(null=True, blank=True, verbose_name="Rebotes Defensivos Visitante")
    away_reb = models.IntegerField(null=True, blank=True, verbose_name="Rebotes Totales Visitante")
    away_ast = models.IntegerField(null=True, blank=True, verbose_name="Asistencias Visitante")
    away_stl = models.IntegerField(null=True, blank=True, verbose_name="Robos Visitante")
    away_blk = models.IntegerField(null=True, blank=True, verbose_name="Tapones Visitante")
    away_tov = models.IntegerField(null=True, blank=True, verbose_name="Pérdidas Visitante")
    away_pf = models.IntegerField(null=True, blank=True, verbose_name="Faltas Visitante")
    away_plus_minus = models.IntegerField(null=True, blank=True, verbose_name="Plus/Minus Visitante")
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Partido NBA"
        verbose_name_plural = "Partidos NBA"
        ordering = ['-game_date', 'home_team']
        unique_together = ['nba_game_id']
    
    def __str__(self):
        return f"{self.home_team.abbreviation} vs {self.away_team.abbreviation} - {self.game_date}"
    
    def save(self, *args, **kwargs):
        # Calcular puntos totales automáticamente
        if self.home_points is not None and self.away_points is not None:
            self.total_points = self.home_points + self.away_points
        super().save(*args, **kwargs)
    
    @property
    def is_over_220(self):
        """¿Fue Over 220 puntos?"""
        return self.total_points > 220 if self.total_points is not None else None
    
    @property
    def is_over_230(self):
        """¿Fue Over 230 puntos?"""
        return self.total_points > 230 if self.total_points is not None else None
    
    @property
    def is_over_240(self):
        """¿Fue Over 240 puntos?"""
        return self.total_points > 240 if self.total_points is not None else None
    
    @property
    def home_efficiency(self):
        """Eficiencia ofensiva del equipo local"""
        if self.home_fga and self.home_fga > 0:
            return (self.home_fgm or 0) / self.home_fga
        return None
    
    @property
    def away_efficiency(self):
        """Eficiencia ofensiva del equipo visitante"""
        if self.away_fga and self.away_fga > 0:
            return (self.away_fgm or 0) / self.away_fga
        return None


class NBAPrediction(models.Model):
    """Modelo para predicciones de puntos totales"""
    game = models.ForeignKey(NBAGame, on_delete=models.CASCADE, related_name='predictions', verbose_name="Partido")
    
    # Predicción
    predicted_total_points = models.FloatField(verbose_name="Puntos Totales Predichos")
    confidence = models.FloatField(null=True, blank=True, verbose_name="Confianza (%)")
    
    # Mercados de apuestas comunes
    over_220_probability = models.FloatField(null=True, blank=True, verbose_name="Probabilidad Over 220")
    over_230_probability = models.FloatField(null=True, blank=True, verbose_name="Probabilidad Over 230")
    over_240_probability = models.FloatField(null=True, blank=True, verbose_name="Probabilidad Over 240")
    
    # Modelo usado
    model_name = models.CharField(max_length=100, verbose_name="Nombre del Modelo")
    model_version = models.CharField(max_length=20, verbose_name="Versión del Modelo")
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Predicción NBA"
        verbose_name_plural = "Predicciones NBA"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Predicción {self.game} - {self.predicted_total_points:.1f} pts"
    
    @property
    def accuracy(self):
        """Precisión de la predicción"""
        if self.game.total_points is not None:
            error = abs(self.predicted_total_points - self.game.total_points)
            return max(0, 100 - (error / self.game.total_points) * 100)
        return None