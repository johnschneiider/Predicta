from django.db import models
from django.utils import timezone
from odds.models import Match, AverageOdds
from betfair.models import BetfairMarket, BetfairRunner, BetfairOrder


class ArbitrageOpportunity(models.Model):
    """Modelo para oportunidades de arbitraje detectadas"""
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    betfair_market = models.ForeignKey(BetfairMarket, on_delete=models.CASCADE)
    betfair_runner = models.ForeignKey(BetfairRunner, on_delete=models.CASCADE)
    
    # Selección de apuesta
    SELECTION_CHOICES = [
        ('home', 'Local'),
        ('away', 'Visitante'),
        ('draw', 'Empate'),
    ]
    selection = models.CharField(max_length=10, choices=SELECTION_CHOICES)
    
    # Cuotas comparadas
    odds_api_odds = models.DecimalField(max_digits=10, decimal_places=3)
    betfair_odds = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Cálculo de arbitraje
    edge = models.DecimalField(max_digits=8, decimal_places=5)  # Edge como decimal (ej: 0.05 = 5%)
    recommended_stake = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 a 1.00
    
    # Estado de la oportunidad
    detected_at = models.DateTimeField(auto_now_add=True)
    acted_upon = models.BooleanField(default=False)
    
    # Referencia a la apuesta realizada (si existe)
    bet_order = models.OneToOneField(BetfairOrder, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Oportunidad de Arbitraje"
        verbose_name_plural = "Oportunidades de Arbitraje"
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"Arbitraje {self.match} - {self.get_selection_display()} (Edge: {self.edge:.2%})"
    
    @property
    def edge_percentage(self):
        """Retorna el edge como porcentaje"""
        return self.edge * 100


class BettingStrategy(models.Model):
    """Modelo para configurar estrategias de apuestas"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Parámetros de la estrategia
    min_edge = models.DecimalField(max_digits=5, decimal_places=4, default=0.05)  # 5% mínimo
    min_confidence = models.DecimalField(max_digits=3, decimal_places=2, default=0.60)  # 60% confianza
    min_stake = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    max_stake = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    max_daily_bets = models.IntegerField(default=10)
    
    # Configuración de deportes
    allowed_sports = models.JSONField(default=list, blank=True)  # Lista de sport_keys permitidos
    
    # Estado
    active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Estrategia de Apuestas"
        verbose_name_plural = "Estrategias de Apuestas"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class StrategyParameterSet(models.Model):
    """Conjunto de parámetros versionado para estrategias (para backtesting/evaluación)."""
    strategy = models.ForeignKey(BettingStrategy, on_delete=models.CASCADE, related_name='parameter_sets')
    name = models.CharField(max_length=100)
    parameters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Parámetros de Estrategia'
        verbose_name_plural = 'Parámetros de Estrategia'
        unique_together = [('strategy', 'name')]

    def __str__(self):
        return f"{self.strategy.name} :: {self.name}"


class BacktestRun(models.Model):
    """Ejecución de backtest para una estrategia y rango temporal."""
    strategy = models.ForeignKey(BettingStrategy, on_delete=models.CASCADE)
    parameter_set = models.ForeignKey(StrategyParameterSet, on_delete=models.SET_NULL, null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    initial_bankroll = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_bankroll = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    roi = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    max_drawdown = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    hit_rate = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    total_bets = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Ejecución de Backtest'
        verbose_name_plural = 'Ejecuciones de Backtest'
        ordering = ['-created_at']

    def __str__(self):
        return f"Backtest {self.strategy.name} [{self.start_datetime} → {self.end_datetime}]"


class BacktestBet(models.Model):
    """Apuestas simuladas durante un backtest para análisis detallado."""
    backtest = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name='bets')
    market_id = models.CharField(max_length=50)
    selection_id = models.BigIntegerField()
    side = models.CharField(max_length=10, choices=[('BACK', 'BACK'), ('LAY', 'LAY')])
    price = models.DecimalField(max_digits=10, decimal_places=3)
    stake = models.DecimalField(max_digits=10, decimal_places=2)
    pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    decided_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Apuesta Backtest'
        verbose_name_plural = 'Apuestas Backtest'



class BotSession(models.Model):
    """Modelo para registrar sesiones del bot"""
    session_id = models.CharField(max_length=100, unique=True)
    strategy = models.ForeignKey(BettingStrategy, on_delete=models.CASCADE)
    
    # Estado de la sesión
    STATUS_CHOICES = [
        ('STARTING', 'Iniciando'),
        ('RUNNING', 'Ejecutándose'),
        ('PAUSED', 'Pausado'),
        ('STOPPED', 'Detenido'),
        ('ERROR', 'Error'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='STARTING')
    
    # Estadísticas de la sesión
    cycles_executed = models.IntegerField(default=0)
    opportunities_found = models.IntegerField(default=0)
    bets_placed = models.IntegerField(default=0)
    total_profit_loss = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_cycle_at = models.DateTimeField(null=True, blank=True)
    
    # Configuración
    execution_interval = models.IntegerField(default=10)  # Segundos entre ciclos
    sandbox_mode = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Sesión del Bot"
        verbose_name_plural = "Sesiones del Bot"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Sesión {self.session_id} - {self.get_status_display()}"
    
    @property
    def duration(self):
        """Calcula la duración de la sesión"""
        if self.ended_at:
            return self.ended_at - self.started_at
        return timezone.now() - self.started_at


class BotCycle(models.Model):
    """Modelo para registrar cada ciclo de ejecución del bot"""
    session = models.ForeignKey(BotSession, on_delete=models.CASCADE, related_name='cycles')
    cycle_number = models.IntegerField()
    
    # Resultados del ciclo
    matches_analyzed = models.IntegerField(default=0)
    opportunities_found = models.IntegerField(default=0)
    bets_placed = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)
    
    # Tiempo de ejecución
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField()
    duration_seconds = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Estado
    SUCCESS_CHOICES = [
        ('SUCCESS', 'Exitoso'),
        ('PARTIAL', 'Parcial'),
        ('FAILED', 'Fallido'),
    ]
    success_status = models.CharField(max_length=20, choices=SUCCESS_CHOICES, default='SUCCESS')
    
    # Logs y errores
    logs = models.TextField(blank=True)
    errors = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name = "Ciclo del Bot"
        verbose_name_plural = "Ciclos del Bot"
        ordering = ['-started_at']
        unique_together = ['session', 'cycle_number']
    
    def __str__(self):
        return f"Ciclo {self.cycle_number} - {self.session.session_id}"


class BotConfiguration(models.Model):
    """Modelo para configuración global del bot"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    
    # Tipos de configuración
    TYPE_CHOICES = [
        ('STRING', 'Texto'),
        ('INTEGER', 'Entero'),
        ('FLOAT', 'Decimal'),
        ('BOOLEAN', 'Booleano'),
        ('JSON', 'JSON'),
    ]
    value_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='STRING')
    
    # Estado
    active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración del Bot"
        verbose_name_plural = "Configuraciones del Bot"
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key} = {self.value}"
    
    def get_typed_value(self):
        """Retorna el valor convertido al tipo correcto"""
        if self.value_type == 'INTEGER':
            return int(self.value)
        elif self.value_type == 'FLOAT':
            return float(self.value)
        elif self.value_type == 'BOOLEAN':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'JSON':
            import json
            return json.loads(self.value)
        return self.value


class Alert(models.Model):
    """Modelo para alertas del sistema"""
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Tipo de alerta
    LEVEL_CHOICES = [
        ('INFO', 'Información'),
        ('WARNING', 'Advertencia'),
        ('ERROR', 'Error'),
        ('SUCCESS', 'Éxito'),
    ]
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='INFO')
    
    # Estado
    read = models.BooleanField(default=False)
    
    # Contexto
    session = models.ForeignKey(BotSession, on_delete=models.CASCADE, null=True, blank=True)
    cycle = models.ForeignKey(BotCycle, on_delete=models.CASCADE, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"
