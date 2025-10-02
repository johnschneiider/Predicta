from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from betting.models import BettingStrategy, StrategyParameterSet, BacktestRun, BacktestBet
from betting.services import BacktesterService
from betting.backtesting import TickSnapshotPriceSource


class Command(BaseCommand):
    help = 'Ejecuta un backtest para una estrategia entre fechas usando snapshots de precios'

    def add_arguments(self, parser):
        parser.add_argument('--strategy-id', type=int, required=True)
        parser.add_argument('--param-name', type=str, required=False)
        parser.add_argument('--start', type=str, required=True)
        parser.add_argument('--end', type=str, required=True)
        parser.add_argument('--initial', type=str, default='1000')

    def handle(self, *args, **options):
        strategy = BettingStrategy.objects.get(id=options['strategy_id'])
        param_set = None
        if options.get('param-name'):
            param_set = strategy.parameter_sets.get(name=options['param-name'])

        start = timezone.datetime.fromisoformat(options['start'])
        end = timezone.datetime.fromisoformat(options['end'])
        initial = Decimal(options['initial'])

        price_source = TickSnapshotPriceSource()
        svc = BacktesterService(price_source=price_source)

        if not hasattr(strategy, 'generate_signals'):
            self.stderr.write('La estrategia debe implementar generate_signals(price_source, parameter_set, start_dt, end_dt)')
            return

        result = svc.run_backtest(strategy, param_set, start, end, initial)

        run = BacktestRun.objects.create(
            strategy=strategy,
            parameter_set=param_set,
            start_datetime=start,
            end_datetime=end,
            initial_bankroll=initial,
            final_bankroll=result['final_bankroll'],
            roi=result['roi'],
            max_drawdown=result['max_drawdown'],
            hit_rate=result['hit_rate'],
            total_bets=result['total_bets'],
        )

        self.stdout.write(self.style.SUCCESS(
            f'Backtest completado: ROI={result["roi"]:.4f}, MDD={result["max_drawdown"]:.4f}, Hit={result["hit_rate"]:.3f}, Bets={result["total_bets"]}'
        ))
        self.stdout.write(self.style.SUCCESS(f'Run ID: {run.id}'))


