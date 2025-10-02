from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from betting.models import BacktestRun, BettingStrategy, StrategyParameterSet


class Command(BaseCommand):
    help = 'Crea un BacktestRun vacío para verificar migraciones y modelo'

    def add_arguments(self, parser):
        parser.add_argument('--strategy-id', type=int, required=True)
        parser.add_argument('--start', type=str, required=True)
        parser.add_argument('--end', type=str, required=True)
        parser.add_argument('--initial', type=str, default='1000')

    def handle(self, *args, **options):
        strategy = BettingStrategy.objects.get(id=options['strategy_id'])
        start = timezone.datetime.fromisoformat(options['start'])
        end = timezone.datetime.fromisoformat(options['end'])
        initial = Decimal(options['initial'])

        run = BacktestRun.objects.create(
            strategy=strategy,
            start_datetime=start,
            end_datetime=end,
            initial_bankroll=initial,
            final_bankroll=initial,
        )
        self.stdout.write(self.style.SUCCESS(f'BacktestRun creado: {run.id}'))


