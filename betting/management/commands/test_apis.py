"""
Comando para probar las APIs
"""

from django.core.management.base import BaseCommand
from odds.services import OddsAPIService
from betfair.services import BetfairAPIService


class Command(BaseCommand):
    help = 'Prueba las conexiones con las APIs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--odds',
            action='store_true',
            help='Probar solo The Odds API'
        )
        parser.add_argument(
            '--betfair',
            action='store_true',
            help='Probar solo Betfair API'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🧪 Iniciando pruebas de APIs...')
        )
        
        # Probar The Odds API
        if not options['betfair']:
            self.stdout.write('\n📊 Probando The Odds API...')
            self._test_odds_api()
        
        # Probar Betfair API
        if not options['odds']:
            self.stdout.write('\n🎯 Probando Betfair API...')
            self._test_betfair_api()
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Pruebas completadas')
        )
    
    def _test_odds_api(self):
        """Prueba The Odds API"""
        try:
            odds_service = OddsAPIService()
            
            # Probar obtención de deportes
            self.stdout.write('   📋 Obteniendo deportes...')
            sports = odds_service.get_sports()
            if sports:
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ {len(sports)} deportes obtenidos')
                )
                # Mostrar algunos deportes
                for sport in sports[:5]:
                    self.stdout.write(f'      - {sport["title"]} ({sport["key"]})')
            else:
                self.stdout.write(
                    self.style.ERROR('   ❌ No se obtuvieron deportes')
                )
                return
            
            # Probar obtención de cuotas
            self.stdout.write('   📈 Obteniendo cuotas...')
            odds_data = odds_service.get_odds()
            if odds_data:
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ {len(odds_data)} partidos con cuotas obtenidos')
                )
                # Mostrar un ejemplo
                if odds_data:
                    match = odds_data[0]
                    self.stdout.write(f'      Ejemplo: {match["home_team"]} vs {match["away_team"]}')
                    self.stdout.write(f'      Casas de apuestas: {len(match.get("bookmakers", []))}')
            else:
                self.stdout.write(
                    self.style.WARNING('   ⚠️ No se obtuvieron cuotas (puede ser normal fuera de horarios)')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Error probando The Odds API: {e}')
            )
    
    def _test_betfair_api(self):
        """Prueba Betfair API"""
        try:
            betfair_service = BetfairAPIService()
            
            # Probar login
            self.stdout.write('   🔐 Probando login...')
            if betfair_service.login():
                self.stdout.write(
                    self.style.SUCCESS('   ✅ Login exitoso')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('   ❌ Error en login')
                )
                return
            
            # Probar obtención de tipos de eventos
            self.stdout.write('   🏆 Obteniendo tipos de eventos...')
            event_types = betfair_service.get_event_types()
            if event_types:
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ {len(event_types)} tipos de eventos obtenidos')
                )
                # Mostrar algunos tipos
                for event_type in event_types[:5]:
                    self.stdout.write(f'      - {event_type["name"]} (ID: {event_type["id"]})')
            else:
                self.stdout.write(
                    self.style.WARNING('   ⚠️ No se obtuvieron tipos de eventos')
                )
            
            # Probar obtención de eventos de fútbol
            self.stdout.write('   ⚽ Obteniendo eventos de fútbol...')
            football_events = betfair_service.get_football_events()
            if football_events:
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ {len(football_events)} eventos de fútbol obtenidos')
                )
                # Mostrar algunos eventos
                for event in football_events[:3]:
                    self.stdout.write(f'      - {event["name"]}')
            else:
                self.stdout.write(
                    self.style.WARNING('   ⚠️ No se obtuvieron eventos de fútbol')
                )
            
            # Probar obtención de mercados
            self.stdout.write('   📊 Obteniendo mercados de Match Odds...')
            markets = betfair_service.get_match_odds_markets()
            if markets:
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ {len(markets)} mercados de Match Odds obtenidos')
                )
                # Mostrar algunos mercados
                for market in markets[:3]:
                    self.stdout.write(f'      - {market["market_name"]} - {market["event_name"]}')
            else:
                self.stdout.write(
                    self.style.WARNING('   ⚠️ No se obtuvieron mercados')
                )
            
            # Probar obtención de fondos
            self.stdout.write('   💰 Obteniendo información de cuenta...')
            funds = betfair_service.get_account_funds()
            if funds:
                self.stdout.write(
                    self.style.SUCCESS('   ✅ Información de cuenta obtenida')
                )
                self.stdout.write(f'      - Saldo disponible: {funds.get("available_to_bet_balance", "N/A")}€')
                self.stdout.write(f'      - Exposición: {funds.get("exposure", "N/A")}€')
            else:
                self.stdout.write(
                    self.style.WARNING('   ⚠️ No se pudo obtener información de cuenta')
                )
            
            # Logout
            betfair_service.logout()
            self.stdout.write('   🔓 Sesión cerrada')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ❌ Error probando Betfair API: {e}')
            )
