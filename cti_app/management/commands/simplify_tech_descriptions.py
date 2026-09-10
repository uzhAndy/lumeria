from django.core.management.base import BaseCommand
from django.db import transaction

from cti_app.services.llm_precomputed_tasks import generate_technique_usage_in_campaign_summaries


class Command(BaseCommand):
    help = (
        "Simplifies and shortens technique usage descriptions for display in the attack example."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Starting technique usage description simplification...")
        )

        with transaction.atomic():
            generate_technique_usage_in_campaign_summaries()
            self.stdout.write(
                self.style.SUCCESS("Campaign technique usage description are rewritten to short explanations.")
            )