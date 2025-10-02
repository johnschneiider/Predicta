"""
Comando para crear ligas de ejemplo
"""

from django.core.management.base import BaseCommand
from football_data.models import League


class Command(BaseCommand):
    help = 'Crea ligas de ejemplo en la base de datos'

    def handle(self, *args, **options):
        leagues_data = [
            {'name': 'Premier League', 'country': 'Inglaterra', 'season': '2023-24', 'active': True},
            {'name': 'Championship', 'country': 'Inglaterra', 'season': '2023-24', 'active': True},
            {'name': 'League One', 'country': 'Inglaterra', 'season': '2023-24', 'active': True},
            {'name': 'League Two', 'country': 'Inglaterra', 'season': '2023-24', 'active': True},
            {'name': 'La Liga', 'country': 'España', 'season': '2023-24', 'active': True},
            {'name': 'Segunda División', 'country': 'España', 'season': '2023-24', 'active': True},
            {'name': 'Bundesliga', 'country': 'Alemania', 'season': '2023-24', 'active': True},
            {'name': '2. Bundesliga', 'country': 'Alemania', 'season': '2023-24', 'active': True},
            {'name': 'Ligue 1', 'country': 'Francia', 'season': '2023-24', 'active': True},
            {'name': 'Ligue 2', 'country': 'Francia', 'season': '2023-24', 'active': True},
            {'name': 'Serie A', 'country': 'Italia', 'season': '2023-24', 'active': True},
            {'name': 'Serie B', 'country': 'Italia', 'season': '2023-24', 'active': True},
            {'name': 'Eredivisie', 'country': 'Países Bajos', 'season': '2023-24', 'active': True},
            {'name': 'Jupiler Pro League', 'country': 'Bélgica', 'season': '2023-24', 'active': True},
            {'name': 'Primeira Liga', 'country': 'Portugal', 'season': '2023-24', 'active': True},
            {'name': 'Süper Lig', 'country': 'Turquía', 'season': '2023-24', 'active': True},
            {'name': 'Super League', 'country': 'Suiza', 'season': '2023-24', 'active': True},
            {'name': 'Scottish Premiership', 'country': 'Escocia', 'season': '2023-24', 'active': True},
            {'name': 'Scottish Championship', 'country': 'Escocia', 'season': '2023-24', 'active': True},
        ]

        created_count = 0
        for league_data in leagues_data:
            league, created = League.objects.get_or_create(
                name=league_data['name'],
                defaults=league_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Liga creada: {league.name} ({league.country})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Liga ya existe: {league.name} ({league.country})')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nProceso completado: {created_count} ligas nuevas creadas')
        )
