"""
Comando para sincronizar datos de Betfair
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from betfair.services import BetfairAPIService


class Command(BaseCommand):
    help = 'Sincroniza datos de Betfair Exchange API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--event-types',
            action='store_true',
            help='Sincronizar tipos de eventos'
        )
        parser.add_argument(
            '--events',
            action='store_true',
            help='Sincronizar eventos de fútbol'
        )
        parser.add_argument(
            '--markets',
            action='store_true',
            help='Sincronizar mercados de Match Odds'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sincronizar todos los datos'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando sincronización de Betfair...')
        )
        
        betfair_service = BetfairAPIService()
        
        # Login
        if not betfair_service.login():
            self.stdout.write(
                self.style.ERROR('❌ No se pudo conectar a Betfair')
            )
            return
        
        self.stdout.write(self.style.SUCCESS('✅ Conectado a Betfair'))
        
        synced_count = 0
        
        # Sincronizar tipos de eventos
        if options['event_types'] or options['all']:
            self.stdout.write('🏆 Sincronizando tipos de eventos...')
            count = betfair_service.sync_event_types()
            synced_count += count
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sincronizados {count} tipos de eventos')
            )
        
        # Sincronizar eventos de fútbol
        if options['events'] or options['all']:
            self.stdout.write('⚽ Sincronizando eventos de fútbol...')
            count = betfair_service.sync_events('1')
            synced_count += count
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sincronizados {count} eventos')
            )
        
        # Sincronizar mercados
        if options['markets'] or options['all']:
            self.stdout.write('📊 Sincronizando mercados de Match Odds...')
            count = betfair_service.sync_markets()
            synced_count += count
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sincronizados {count} mercados')
            )
        
        # Logout
        betfair_service.logout()
        
        if synced_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'🎉 Sincronización completada: {synced_count} elementos')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ No se sincronizó ningún elemento')
            )
