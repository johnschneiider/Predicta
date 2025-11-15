"""
Servicios de análisis para preparar y evaluar mercados de apuestas
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from django.utils import timezone as django_timezone
from django.conf import settings

from odds.services import OddsAPIService
from odds.models import Match


@dataclass
class OutcomeEvaluation:
    result: str
    average_price: float
    best_price: float
    best_bookmaker: Optional[str]
    edge: float


@dataclass
class MatchEvaluation:
    match: Match
    commence_time: datetime
    bookmaker_count: int
    outcomes: List[OutcomeEvaluation]
    best_edge: float

    @property
    def summary(self) -> Dict:
        """Devuelve un resumen serializable del análisis."""
        best_outcome = max(self.outcomes, key=lambda o: o.edge, default=None)
        return {
            "match": f"{self.match.home_team} vs {self.match.away_team}",
            "sport": self.match.sport.key if self.match.sport else None,
            "commence_time": self.commence_time.isoformat(),
            "bookmaker_count": self.bookmaker_count,
            "best_outcome": best_outcome.result if best_outcome else None,
            "best_edge": round(self.best_edge * 100, 2) if best_outcome else 0,
            "best_bookmaker": best_outcome.best_bookmaker if best_outcome else None,
            "best_price": best_outcome.best_price if best_outcome else None,
            "average_price": best_outcome.average_price if best_outcome else None,
        }


class MarketPreparationService:
    """
    Servicio que consulta The Odds API, normaliza información de próximos partidos y
    calcula métricas básicas para identificar los encuentros más atractivos.
    """

    def __init__(self, odds_service: Optional[OddsAPIService] = None):
        self.odds_service = odds_service or OddsAPIService()

    def prepare_matches(
        self,
        sport_key: Optional[str] = None,
        include_multiple_sports: bool = False,
    ) -> List[MatchEvaluation]:
        """
        Obtiene y procesa partidos próximos para un deporte (o múltiples deportes de fútbol).
        Devuelve una lista de evaluaciones ordenada por mejor edge.
        """
        raw_matches = self._fetch_matches(sport_key, include_multiple_sports)

        evaluations: List[MatchEvaluation] = []

        for match_data in raw_matches:
            normalized = self.odds_service.normalize_odds_data(match_data)
            if not normalized:
                continue

            stored_match = self.odds_service.save_odds_to_database(match_data)
            if not stored_match:
                continue

            evaluation = self._evaluate_match(stored_match, normalized)
            if evaluation and evaluation.best_edge > 0:
                evaluations.append(evaluation)

        evaluations.sort(key=lambda ev: ev.best_edge, reverse=True)
        return evaluations

    def _fetch_matches(
        self,
        sport_key: Optional[str],
        include_multiple_sports: bool,
    ) -> List[Dict]:
        if include_multiple_sports:
            matches: List[Dict] = []
            target_sports = (
                settings.TARGET_SPORT_KEYS or [settings.SPORT_KEY]
            )
            for sport in target_sports:
                matches.extend(self.odds_service.get_odds(sport))
            return matches

        return self.odds_service.get_odds(sport_key)

    def _evaluate_match(
        self,
        match: Match,
        normalized_data: Dict,
    ) -> Optional[MatchEvaluation]:
        bookmaker_count = normalized_data.get("bookmaker_count", 0)
        if bookmaker_count < settings.MINIMUM_BOOKMAKER_COUNT:
            return None

        outcomes = []
        best_edge = 0.0

        mapping = {
            "home": (
                normalized_data.get("avg_home_odds"),
                normalized_data.get("home_odds", []),
                match.home_team,
            ),
            "draw": (
                normalized_data.get("avg_draw_odds"),
                normalized_data.get("draw_odds", []),
                "Draw",
            ),
            "away": (
                normalized_data.get("avg_away_odds"),
                normalized_data.get("away_odds", []),
                match.away_team,
            ),
        }

        for result_key, (average, odds_list, lookup_name) in mapping.items():
            if not odds_list or not average:
                continue

            best_entry = max(odds_list, key=lambda item: item.get("price", 0))
            best_price = best_entry.get("price")
            best_bookmaker = best_entry.get("bookmaker")
            if not best_price or best_price <= 0:
                continue

            edge = (best_price - average) / average if average else 0.0

            outcome_eval = OutcomeEvaluation(
                result=result_key,
                average_price=average,
                best_price=best_price,
                best_bookmaker=best_bookmaker,
                edge=edge,
            )

            outcomes.append(outcome_eval)
            best_edge = max(best_edge, edge)

        if not outcomes:
            return None

        commence_time_str = normalized_data.get("commence_time")
        commence_time = (
            datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
            if commence_time_str
            else django_timezone.now()
        )

        return MatchEvaluation(
            match=match,
            commence_time=commence_time,
            bookmaker_count=bookmaker_count,
            outcomes=outcomes,
            best_edge=best_edge,
        )



