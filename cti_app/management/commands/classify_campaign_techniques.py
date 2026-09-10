# python manage.py classify_campaign_techniques
from django.core.management.base import BaseCommand
from django.db import transaction

from cti_app.services.kill_chain_classifier import (
    classify_all_campaign_techniques
)


class Command(BaseCommand):
    help = (
        "Classify campaign techniques by MITRE tactic and "
        "Unified Kill Chain phase using a BERT classifier."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Starting campaign technique classification...")
        )

        with transaction.atomic():
            classify_all_campaign_techniques()

        self.stdout.write(
            self.style.SUCCESS("Campaign technique classification completed successfully.")
        )
