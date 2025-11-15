"""
Comando para preparar y evaluar próximos partidos en busca de oportunidades.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from betting.analysis import MarketPreparationService


class Command(BaseCommand):
    help = (
        "Sincroniza partidos próximos desde The Odds API, calcula métricas básicas "
        "y muestra los encuentros con mayor edge potencial."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--sport",
            type=str,
            help="Clave de deporte específica (ej: soccer_germany_bundesliga). "
            "Por defecto utiliza settings.SPORT_KEY.",
        )
        parser.add_argument(
            "--multiple",
            action="store_true",
            help="Incluir múltiples ligas objetivo configuradas en TARGET_SPORT_KEYS.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Número máximo de partidos a mostrar (default: 10).",
        )

    def handle(self, *args, **options):
        sport_key = options.get("sport")
        include_multiple = options.get("multiple", False)
        limit = options.get("limit", 10)

        self.stdout.write(self.style.SUCCESS("🔎 Preparando análisis de próximos partidos...\n"))

        service = MarketPreparationService()
        evaluations = service.prepare_matches(sport_key, include_multiple)

        if not evaluations:
            self.stdout.write(self.style.WARNING("No se encontraron partidos con edge positivo."))
            return

        self.stdout.write(
            f"Configuración utilizada:\n"
            f"  • Sport objetivo: {sport_key or settings.SPORT_KEY}\n"
            f"  • Múltiples deportes: {'Sí' if include_multiple else 'No'}\n"
            f"  • Límite de resultados: {limit}\n"
            f"  • Bookmakers mínimos: {settings.MINIMUM_BOOKMAKER_COUNT}\n"
        )

        now = timezone.now().astimezone()
        self.stdout.write(f"Fecha de referencia: {now.isoformat()}\n")

        for index, evaluation in enumerate(evaluations[:limit], start=1):
            summary = evaluation.summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"{index}. {summary['match']} "
                    f"({summary['commence_time']})"
                )
            )
            self.stdout.write(
                f"   • Sport: {summary['sport']} | Casas: {summary['bookmaker_count']}"
            )
            self.stdout.write(
                f"   • Mayor edge: {summary['best_edge']}% "
                f"({summary['best_outcome']} @ {summary['best_price']} en {summary['best_bookmaker']})"
            )
            self.stdout.write(
                f"   • Cuota promedio: {summary['average_price']}"
            )
            self.stdout.write("")

        total = len(evaluations)
        if total > limit:
            self.stdout.write(
                f"[INFO] Hay {total} partidos con edge positivo. "
                f"Use --limit para ver más resultados."
            )


