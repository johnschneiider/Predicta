from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import json

from betting.models import BettingStrategy, StrategyParameterSet, BacktestRun
from betting.services import BacktesterService
from betting.backtesting import TickSnapshotPriceSource


class Command(BaseCommand):
    help = 'Evalúa una estrategia variando parámetros (grid) y reporta métricas'

    def add_arguments(self, parser):
        parser.add_argument('--strategy-id', type=int, required=True)
        parser.add_argument('--grid', type=str, required=True, help='JSON con parámetros a barrer')
        parser.add_argument('--start', type=str, required=True)
        parser.add_argument('--end', type=str, required=True)
        parser.add_argument('--initial', type=str, default='1000')

    def handle(self, *args, **options):
        strategy = BettingStrategy.objects.get(id=options['strategy_id'])
        grid = json.loads(options['grid'])
        start = timezone.datetime.fromisoformat(options['start'])
        end = timezone.datetime.fromisoformat(options['end'])
        initial = Decimal(options['initial'])

        price_source = TickSnapshotPriceSource()
        svc = BacktesterService(price_source=price_source)

        if not hasattr(strategy, 'generate_signals'):
            self.stderr.write('La estrategia debe implementar generate_signals(price_source, parameter_set, start_dt, end_dt)')
            return

        # Producto cartesiano simple
        def cartesian(product):
            if not product:
                return [{}]
            (k, values), *rest = product.items()
            tail = cartesian(dict(rest))
            out = []
            for v in values:
                for t in tail:
                    d = dict(t)
                    d[k] = v
                    out.append(d)
            return out

        combos = cartesian(grid)
        results = []
        for idx, params in enumerate(combos):
            param_name = f'grid_{idx}'
            param_set, _ = StrategyParameterSet.objects.get_or_create(
                strategy=strategy,
                name=param_name,
                defaults={'parameters': params},
            )

            result = svc.run_backtest(strategy, param_set, start, end, initial)
            BacktestRun.objects.create(
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
                notes=json.dumps(params),
            )
            results.append((params, result))
            self.stdout.write(self.style.SUCCESS(
                f"{param_name} -> ROI={result['roi']:.4f}, MDD={result['max_drawdown']:.4f}, Hit={result['hit_rate']:.3f}"
            ))

        # Top 5 por ROI
        results.sort(key=lambda x: x[1]['roi'], reverse=True)
        self.stdout.write(self.style.WARNING('Top 5 ROI:'))
        for params, result in results[:5]:
            self.stdout.write(f"ROI={result['roi']:.4f} params={json.dumps(params)}")


