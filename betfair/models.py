from django.db import models
from django.utils import timezone


class BetfairEventType(models.Model):
    """Modelo para tipos de eventos de Betfair (deportes)"""
    event_type_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    market_count = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Tipo de Evento Betfair"
        verbose_name_plural = "Tipos de Eventos Betfair"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class BetfairEvent(models.Model):
    """Modelo para eventos de Betfair"""
    event_id = models.CharField(max_length=50, unique=True)
    event_type = models.ForeignKey(BetfairEventType, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    country_code = models.CharField(max_length=10, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    open_date = models.DateTimeField()
    market_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Evento Betfair"
        verbose_name_plural = "Eventos Betfair"
        ordering = ['open_date']
    
    def __str__(self):
        return self.name


class BetfairMarket(models.Model):
    """Modelo para mercados de Betfair"""
    market_id = models.CharField(max_length=50, unique=True)
    event = models.ForeignKey(BetfairEvent, on_delete=models.CASCADE, related_name='markets')
    market_name = models.CharField(max_length=200)
    market_start_time = models.DateTimeField()
    market_type = models.CharField(max_length=50, default='MATCH_ODDS')
    
    # Estado del mercado
    STATUS_CHOICES = [
        ('INACTIVE', 'Inactivo'),
        ('OPEN', 'Abierto'),
        ('SUSPENDED', 'Suspendido'),
        ('CLOSED', 'Cerrado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INACTIVE')
    
    # Liquidez
    total_matched = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Mercado Betfair"
        verbose_name_plural = "Mercados Betfair"
        ordering = ['market_start_time']
    
    def __str__(self):
        return f"{self.market_name} - {self.event.name}"


class BetfairRunner(models.Model):
    """Modelo para corredores (opciones de apuesta) en mercados de Betfair"""
    market = models.ForeignKey(BetfairMarket, on_delete=models.CASCADE, related_name='runners')
    selection_id = models.BigIntegerField()
    runner_name = models.CharField(max_length=200)
    sort_priority = models.IntegerField(default=0)
    
    # Estado del corredor
    STATUS_CHOICES = [
        ('ACTIVE', 'Activo'),
        ('WINNER', 'Ganador'),
        ('LOSER', 'Perdedor'),
        ('REMOVED', 'Eliminado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # Precios
    last_price_traded = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    total_matched = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Precios disponibles (JSON)
    available_to_back = models.JSONField(default=dict, blank=True)
    available_to_lay = models.JSONField(default=dict, blank=True)
    
    # Timestamp de última actualización
    last_updated = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Corredor Betfair"
        verbose_name_plural = "Corredores Betfair"
        ordering = ['sort_priority']
        unique_together = ['market', 'selection_id']
    
    def __str__(self):
        return f"{self.runner_name} - {self.market.market_name}"
    
    def get_best_back_price(self):
        """Obtiene el mejor precio para apostar a favor"""
        if self.available_to_back:
            return max(self.available_to_back, key=lambda x: x.get('price', 0))
        return None
    
    def get_best_lay_price(self):
        """Obtiene el mejor precio para apostar en contra"""
        if self.available_to_lay:
            return min(self.available_to_lay, key=lambda x: x.get('price', float('inf')))
        return None


class BetfairOrder(models.Model):
    """Modelo para órdenes de apuesta en Betfair"""
    order_id = models.CharField(max_length=100, unique=True)
    market = models.ForeignKey(BetfairMarket, on_delete=models.CASCADE)
    runner = models.ForeignKey(BetfairRunner, on_delete=models.CASCADE)
    
    # Tipo de orden
    SIDE_CHOICES = [
        ('BACK', 'A favor'),
        ('LAY', 'En contra'),
    ]
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    
    ORDER_TYPE_CHOICES = [
        ('LIMIT', 'Límite'),
        ('MARKET_ON_CLOSE', 'Mercado al cierre'),
        ('LIMIT_ON_CLOSE', 'Límite al cierre'),
    ]
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    
    # Detalles de la orden
    price = models.DecimalField(max_digits=10, decimal_places=3)
    size = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Estado de la orden
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('EXECUTABLE', 'Ejecutable'),
        ('EXECUTION_COMPLETE', 'Ejecución completa'),
        ('CANCELLED', 'Cancelada'),
        ('FAILED', 'Fallida'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    
    # Resultado
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    placed_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    
    # Metadatos
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Orden Betfair"
        verbose_name_plural = "Órdenes Betfair"
        ordering = ['-placed_at']
    
    def __str__(self):
        return f"{self.side} {self.size}€ @ {self.price} - {self.runner.runner_name}"


class BetfairAccount(models.Model):
    """Modelo para información de cuenta de Betfair"""
    username = models.CharField(max_length=100, unique=True)
    
    # Información de fondos
    available_to_bet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    exposure = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    retained_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    exposure_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    points_balance = models.IntegerField(default=0)
    
    # Estado de la cuenta
    active = models.BooleanField(default=True)
    sandbox = models.BooleanField(default=True)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Cuenta Betfair"
        verbose_name_plural = "Cuentas Betfair"
    
    def __str__(self):
        return f"{self.username} ({'Sandbox' if self.sandbox else 'Producción'})"


class BetfairTickSnapshot(models.Model):
    """Snapshot compacto de precios (top-N niveles) para análisis y backtesting"""
    market = models.ForeignKey(BetfairMarket, on_delete=models.CASCADE, related_name='tick_snapshots')
    runner = models.ForeignKey(BetfairRunner, on_delete=models.CASCADE, related_name='tick_snapshots')

    # Datos de precios compactos
    best_back = models.JSONField(default=list, blank=True)  # lista de {price, size}
    best_lay = models.JSONField(default=list, blank=True)   # lista de {price, size}
    last_price_traded = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    total_matched = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Metadatos de captura
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Tick Snapshot Betfair"
        verbose_name_plural = "Tick Snapshots Betfair"
        indexes = [
            models.Index(fields=['market', 'captured_at']),
            models.Index(fields=['runner', 'captured_at']),
        ]

    def __str__(self):
        return f"Snapshot {self.market.market_id}/{self.runner.selection_id} @ {self.captured_at}"