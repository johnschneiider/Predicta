from typing import Iterator, Dict, Any, Optional
from datetime import datetime

from django.db.models import QuerySet

from betfair.models import BetfairTickSnapshot


class TickSnapshotPriceSource:
    """Fuente de datos basada en snapshots de Betfair para backtesting/evaluación."""

    def __init__(self, market_ids=None, selection_ids=None):
        self.market_ids = set(market_ids) if market_ids else None
        self.selection_ids = set(selection_ids) if selection_ids else None

    def iter(self, start_dt: datetime, end_dt: datetime) -> Iterator[Dict[str, Any]]:
        qs: QuerySet = BetfairTickSnapshot.objects.select_related('market', 'runner') 
        qs = qs.filter(captured_at__gte=start_dt, captured_at__lte=end_dt).order_by('captured_at')

        if self.market_ids:
            qs = qs.filter(market__market_id__in=list(self.market_ids))
        if self.selection_ids:
            qs = qs.filter(runner__selection_id__in=list(self.selection_ids))

        for snap in qs.iterator(chunk_size=2000):
            yield {
                'timestamp': snap.captured_at,
                'market_id': snap.market.market_id,
                'selection_id': snap.runner.selection_id,
                'best_back': snap.best_back,
                'best_lay': snap.best_lay,
                'last_price_traded': snap.last_price_traded,
                'total_matched': snap.total_matched,
            }


