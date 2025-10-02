"""
Comando de gestión para sincronizar cuotas desde The Odds API
"""

from django.core.management.base import BaseCommand
from odds.services import OddsAPIService


class Command(BaseCommand):
    help = 'Sincroniza cuotas desde The Odds API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sport',
            type=str,
            default='soccer_epl',
            help='Clave del deporte a sincronizar (ej: soccer_epl)'
        )
        parser.add_argument(
            '--sync-sports',
            action='store_true',
            help='Sincronizar también la lista de deportes'
        )

    def handle(self, *args, **options):
        sport_key = options['sport']
        sync_sports = options['sync_sports']

        self.stdout.write(
            self.style.SUCCESS(f'Iniciando sincronización para {sport_key}...')
        )

        try:
            odds_service = OddsAPIService()

            # Sincronizar deportes si se solicita
            synced_sports = 0
            if sync_sports:
                self.stdout.write('Sincronizando deportes...')
                synced_sports = odds_service.sync_sports()
                self.stdout.write(
                    self.style.SUCCESS(f'Sincronizados {synced_sports} deportes')
                )

            # Sincronizar cuotas
            self.stdout.write(f'Sincronizando cuotas para {sport_key}...')
            synced_matches = odds_service.sync_odds(sport_key)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'¡Sincronización completada! '
                    f'{synced_sports} deportes y {synced_matches} partidos sincronizados.'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error en la sincronización: {str(e)}')
            )
