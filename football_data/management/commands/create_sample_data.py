"""
Comando para crear datos de muestra para las ligas
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import random

from football_data.models import League, Match


class Command(BaseCommand):
    help = 'Crea datos de muestra para las ligas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--matches-per-league',
            type=int,
            default=50,
            help='Número de partidos a crear por liga'
        )

    def handle(self, *args, **options):
        matches_per_league = options['matches_per_league']
        
        # Equipos de muestra para diferentes ligas
        teams_data = {
            'Premier League': ['Manchester United', 'Manchester City', 'Liverpool', 'Chelsea', 'Arsenal', 'Tottenham', 'Newcastle', 'Brighton', 'West Ham', 'Aston Villa'],
            'La Liga': ['Real Madrid', 'Barcelona', 'Atletico Madrid', 'Sevilla', 'Real Sociedad', 'Real Betis', 'Villarreal', 'Valencia', 'Athletic Bilbao', 'Osasuna'],
            'Bundesliga': ['Bayern Munich', 'Borussia Dortmund', 'RB Leipzig', 'Bayer Leverkusen', 'Eintracht Frankfurt', 'Union Berlin', 'Freiburg', 'Wolfsburg', 'Mainz', 'Borussia Mönchengladbach'],
            'Serie A': ['Juventus', 'AC Milan', 'Inter Milan', 'Napoli', 'Atalanta', 'Roma', 'Lazio', 'Fiorentina', 'Bologna', 'Torino'],
            'Ligue 1': ['PSG', 'Marseille', 'Monaco', 'Lyon', 'Lille', 'Rennes', 'Nice', 'Lorient', 'Clermont', 'Toulouse'],
        }
        
        # Equipos genéricos para otras ligas
        generic_teams = ['Team A', 'Team B', 'Team C', 'Team D', 'Team E', 'Team F', 'Team G', 'Team H', 'Team I', 'Team J']
        
        leagues = League.objects.all()
        total_matches_created = 0
        
        for league in leagues:
            self.stdout.write(f'Creando datos para {league.name}...')
            
            # Seleccionar equipos según la liga
            if league.name in teams_data:
                teams = teams_data[league.name]
            else:
                teams = generic_teams
            
            # Crear partidos para esta liga
            matches_created = 0
            start_date = timezone.now().date() - timedelta(days=365)
            
            for i in range(matches_per_league):
                # Seleccionar equipos aleatorios
                home_team = random.choice(teams)
                away_team = random.choice([t for t in teams if t != home_team])
                
                # Fecha aleatoria en el último año
                match_date = start_date + timedelta(days=random.randint(0, 365))
                
                # Generar estadísticas del partido
                fthg = random.randint(0, 5)  # Goles local
                ftag = random.randint(0, 5)  # Goles visitante
                
                # Resultado
                if fthg > ftag:
                    ftr = 'H'
                elif ftag > fthg:
                    ftr = 'A'
                else:
                    ftr = 'D'
                
                # Goles al descanso
                hthg = random.randint(0, min(fthg, 3))
                htag = random.randint(0, min(ftag, 3))
                
                if hthg > htag:
                    htr = 'H'
                elif htag > hthg:
                    htr = 'A'
                else:
                    htr = 'D'
                
                # Estadísticas del partido
                hs = random.randint(5, 25)  # Tiros local
                as_shots = random.randint(5, 25)  # Tiros visitante
                hst = random.randint(0, min(hs, 10))  # Tiros a puerta local
                ast = random.randint(0, min(as_shots, 10))  # Tiros a puerta visitante
                
                hf = random.randint(8, 20)  # Faltas local
                af = random.randint(8, 20)  # Faltas visitante
                
                hc = random.randint(2, 12)  # Corners local
                ac = random.randint(2, 12)  # Corners visitante
                
                hy = random.randint(0, 5)  # Tarjetas amarillas local
                ay = random.randint(0, 5)  # Tarjetas amarillas visitante
                hr = random.randint(0, 2)  # Tarjetas rojas local
                ar = random.randint(0, 2)  # Tarjetas rojas visitante
                
                # Cuotas de ejemplo
                b365h = round(random.uniform(1.5, 5.0), 2)
                b365d = round(random.uniform(2.8, 4.5), 2)
                b365a = round(random.uniform(1.5, 5.0), 2)
                
                # Crear el partido
                match = Match.objects.create(
                    league=league,
                    date=match_date,
                    time=None,
                    home_team=home_team,
                    away_team=away_team,
                    fthg=fthg,
                    ftag=ftag,
                    ftr=ftr,
                    hthg=hthg,
                    htag=htag,
                    htr=htr,
                    hs=hs,
                    as_field=as_shots,
                    hst=hst,
                    ast=ast,
                    hf=hf,
                    af=af,
                    hc=hc,
                    ac=ac,
                    hy=hy,
                    ay=ay,
                    hr=hr,
                    ar=ar,
                    b365h=b365h,
                    b365d=b365d,
                    b365a=b365a,
                )
                
                matches_created += 1
                
                if matches_created % 10 == 0:
                    self.stdout.write(f'  Creados {matches_created} partidos...')
            
            total_matches_created += matches_created
            self.stdout.write(
                self.style.SUCCESS(f'✅ {league.name}: {matches_created} partidos creados')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Total: {total_matches_created} partidos creados para {leagues.count()} ligas')
        )
        self.stdout.write('Ahora puedes ver los datos en el dashboard!')
