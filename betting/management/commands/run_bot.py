"""
Comando para ejecutar el bot de apuestas
"""

import signal
import sys
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from betting.models import BettingStrategy, BotSession
from betting.services import BettingService


class Command(BaseCommand):
    help = 'Ejecuta el bot de apuestas deportivas'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        self.session = None
        self.betting_service = BettingService()
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy',
            type=str,
            default='default',
            help='Nombre de la estrategia a usar'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Intervalo entre ciclos en segundos (default: 10)'
        )
        parser.add_argument(
            '--cycles',
            type=int,
            help='Número máximo de ciclos a ejecutar (default: infinito)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar en modo de prueba (no colocar apuestas reales)'
        )
    
    def handle(self, *args, **options):
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.stdout.write(
            self.style.SUCCESS('🤖 Iniciando Bot de Apuestas Deportivas')
        )
        
        # Obtener o crear estrategia
        try:
            strategy = BettingStrategy.objects.get(name=options['strategy'])
            self.stdout.write(f'📋 Usando estrategia: {strategy.name}')
        except BettingStrategy.DoesNotExist:
            # Crear estrategia por defecto
            strategy = BettingStrategy.objects.create(
                name=options['strategy'],
                description='Estrategia por defecto',
                min_edge=settings.MIN_EDGE,
                min_confidence=0.60,
                min_stake=settings.MIN_STAKE,
                max_stake=settings.MAX_STAKE,
                max_daily_bets=10
            )
            self.stdout.write(f'📋 Estrategia por defecto creada: {strategy.name}')
        
        # Crear sesión del bot
        session_id = f"BOT_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        self.session = BotSession.objects.create(
            session_id=session_id,
            strategy=strategy,
            status='STARTING',
            execution_interval=options['interval'],
            sandbox_mode=options['dry_run'] or settings.BETFAIR_SANDBOX
        )
        
        self.stdout.write(f'🎯 Sesión iniciada: {session_id}')
        self.stdout.write(f'⚙️ Configuración:')
        self.stdout.write(f'   - Deporte: {settings.SPORT_KEY}')
        self.stdout.write(f'   - Stake mínimo: {settings.MIN_STAKE}€')
        self.stdout.write(f'   - Stake máximo: {settings.MAX_STAKE}€')
        self.stdout.write(f'   - Edge mínimo: {settings.MIN_EDGE:.1%}')
        self.stdout.write(f'   - Intervalo: {options["interval"]}s')
        self.stdout.write(f'   - Modo sandbox: {"SÍ" if self.session.sandbox_mode else "NO"}')
        
        # Actualizar estado de la sesión
        self.session.status = 'RUNNING'
        self.session.save()
        
        self.running = True
        cycle_count = 0
        max_cycles = options.get('cycles')
        
        try:
            while self.running:
                cycle_count += 1
                
                self.stdout.write(
                    f'\n🔄 CICLO {cycle_count} - {timezone.now().strftime("%H:%M:%S")}'
                )
                
                # Ejecutar ciclo
                cycle = self.betting_service.execute_cycle(self.session)
                
                # Mostrar resultados del ciclo
                self.stdout.write(
                    f'📊 Resultados:'
                )
                self.stdout.write(f'   - Partidos analizados: {cycle.matches_analyzed}')
                self.stdout.write(f'   - Oportunidades encontradas: {cycle.opportunities_found}')
                self.stdout.write(f'   - Apuestas colocadas: {cycle.bets_placed}')
                self.stdout.write(f'   - Duración: {cycle.duration_seconds:.1f}s')
                self.stdout.write(f'   - Estado: {cycle.get_success_status_display()}')
                
                if cycle.errors:
                    for error in cycle.errors:
                        self.stdout.write(
                            self.style.ERROR(f'❌ Error: {error}')
                        )
                
                # Mostrar estadísticas de la sesión
                if cycle_count % 10 == 0:
                    self._show_session_stats()
                
                # Verificar límite de ciclos
                if max_cycles and cycle_count >= max_cycles:
                    self.stdout.write(
                        self.style.SUCCESS(f'🏁 Límite de ciclos alcanzado: {max_cycles}')
                    )
                    break
                
                # Pausa entre ciclos
                if self.running:
                    self.stdout.write(f'⏳ Esperando {options["interval"]} segundos...')
                    time.sleep(options['interval'])
        
        except KeyboardInterrupt:
            self.stdout.write('\n🛑 Bot interrumpido por el usuario')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error fatal en el bot: {e}')
            )
        finally:
            self._cleanup()
    
    def _signal_handler(self, signum, frame):
        """Maneja señales de interrupción"""
        self.stdout.write(f'\n🛑 Señal {signum} recibida. Cerrando bot...')
        self.running = False
    
    def _show_session_stats(self):
        """Muestra estadísticas de la sesión"""
        if not self.session:
            return
        
        self.stdout.write(f'\n📈 ESTADÍSTICAS DE LA SESIÓN')
        self.stdout.write(f'   - Ciclos ejecutados: {self.session.cycles_executed}')
        self.stdout.write(f'   - Oportunidades encontradas: {self.session.opportunities_found}')
        self.stdout.write(f'   - Apuestas colocadas: {self.session.bets_placed}')
        self.stdout.write(f'   - Profit/Loss total: {self.session.total_profit_loss:.2f}€')
        self.stdout.write(f'   - Duración: {self.session.duration}')
    
    def _cleanup(self):
        """Limpieza al cerrar el bot"""
        if self.session:
            self.session.status = 'STOPPED'
            self.session.ended_at = timezone.now()
            self.session.save()
            
            self.stdout.write(f'\n🧹 Limpiando recursos...')
            self._show_session_stats()
            self.stdout.write(self.style.SUCCESS('✅ Bot cerrado correctamente'))
