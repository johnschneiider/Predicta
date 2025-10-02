"""
Comando para sincronizar cuotas de The Odds API
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from odds.services import OddsAPIService


class Command(BaseCommand):
    help = 'Sincroniza cuotas de The Odds API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sport',
            type=str,
            default='soccer_epl',
            help='Clave del deporte a sincronizar (default: soccer_epl)'
        )
        parser.add_argument(
            '--sync-sports',
            action='store_true',
            help='Sincronizar también la lista de deportes'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando sincronización de cuotas...')
        )
        
        odds_service = OddsAPIService()
        
        # Sincronizar deportes si se solicita
        if options['sync_sports']:
            self.stdout.write('📊 Sincronizando deportes...')
            synced_sports = odds_service.sync_sports()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sincronizados {synced_sports} deportes nuevos')
            )
        
        # Sincronizar cuotas
        sport_key = options['sport']
        self.stdout.write(f'📈 Sincronizando cuotas para {sport_key}...')
        
        start_time = timezone.now()
        synced_matches = odds_service.sync_odds(sport_key)
        end_time = timezone.now()
        
        duration = (end_time - start_time).total_seconds()
        
        if synced_matches > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Sincronizados {synced_matches} partidos en {duration:.1f} segundos'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ No se encontraron partidos para sincronizar')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎉 Sincronización completada')
        )
