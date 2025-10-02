from django.db import models
from django.utils import timezone


class Sport(models.Model):
    """Modelo para deportes disponibles en The Odds API"""
    key = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    has_outrights = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Deporte"
        verbose_name_plural = "Deportes"
        ordering = ['title']
    
    def __str__(self):
        return self.title


class Bookmaker(models.Model):
    """Modelo para casas de apuestas"""
    key = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Casa de Apuestas"
        verbose_name_plural = "Casas de Apuestas"
        ordering = ['title']
    
    def __str__(self):
        return self.title


class Match(models.Model):
    """Modelo para partidos/matches"""
    match_id = models.CharField(max_length=100, unique=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)
    home_team = models.CharField(max_length=200)
    away_team = models.CharField(max_length=200)
    commence_time = models.DateTimeField()
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Partido"
        verbose_name_plural = "Partidos"
        ordering = ['commence_time']
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class Odds(models.Model):
    """Modelo para cuotas de partidos"""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='odds')
    bookmaker = models.ForeignKey(Bookmaker, on_delete=models.CASCADE)
    
    # Cuotas principales (formato decimal)
    home_odds = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    away_odds = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    draw_odds = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    
    # Timestamp de cuando se obtuvieron las cuotas
    odds_timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Cuota"
        verbose_name_plural = "Cuotas"
        ordering = ['-odds_timestamp']
        unique_together = ['match', 'bookmaker', 'odds_timestamp']
    
    def __str__(self):
        return f"{self.match} - {self.bookmaker} ({self.odds_timestamp})"


class AverageOdds(models.Model):
    """Modelo para cuotas promedio calculadas"""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='average_odds')
    
    # Cuotas promedio
    avg_home_odds = models.DecimalField(max_digits=10, decimal_places=3)
    avg_away_odds = models.DecimalField(max_digits=10, decimal_places=3)
    avg_draw_odds = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Estadísticas
    bookmaker_count = models.IntegerField()
    standard_deviation = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    
    # Timestamp de cálculo
    calculated_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Cuota Promedio"
        verbose_name_plural = "Cuotas Promedio"
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"Promedio {self.match} ({self.calculated_at})"
