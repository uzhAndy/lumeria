from django.core.management.base import BaseCommand

from cti_app.models import Mitigation
from cti_app.services.llm_precomputed_tasks import generate_mitigation_summary
from cti_app.services.agent_builder import build_simple_agent

AGENT = build_simple_agent()

class Command(BaseCommand):
    help = 'Generates and saves LLM summaries for all campaigns'

    def handle(self, *args, **options):
        # mitigations = Mitigation.objects.all()
        mitigations = Mitigation.objects.filter(summary="")
        self.stdout.write(f"Processing {mitigations.count()} mitigations...")

        for mitigation in mitigations:
            self.stdout.write(f"Generating summary for: {mitigation.name}")
            try:
                # the summary text is created with a prompt template that ensures the technical description of the mitigation
                # is used to generate a shorter and easier to understand version of it
                summary_text = generate_mitigation_summary(AGENT, mitigation.name, mitigation.description)

                mitigation.summary = summary_text
                mitigation.save()

                self.stdout.write(self.style.SUCCESS(f"Successfully updated {mitigation.name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed for {mitigation.name}: {str(e)}"))