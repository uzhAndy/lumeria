from django.core.management.base import BaseCommand

from cti_app.models import Campaign
from cti_app.services.llm_precomputed_tasks import generate_campaign_summary
from cti_app.services.agent_builder import build_simple_agent

AGENT = build_simple_agent()

class Command(BaseCommand):
    help = 'Generates and saves LLM summaries for all campaigns'

    def handle(self, *args, **options):
        # campaigns = Campaign.objects.all()
        campaigns = Campaign.objects.filter(summary="")
        self.stdout.write(f"Processing {campaigns.count()} campaigns...")

        for campaign in campaigns:
            self.stdout.write(f"Generating summary for: {campaign.name}")
            try:
                groups = campaign.groups.all()
                if groups.exists():
                    group_lines = []
                    for g in groups:
                        desc = g.description.strip().replace("\n", " ")
                        group_lines.append(
                            f"- {g.name}: {desc}"
                        )
                    group_info = "\n".join(group_lines)
                else:
                    group_info = "No officially attributed groups."
                summary_text = generate_campaign_summary(AGENT, campaign.name, campaign.description, group_info)

                campaign.summary = summary_text
                campaign.save()

                self.stdout.write(self.style.SUCCESS(f"Successfully updated {campaign.name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed for {campaign.name}: {str(e)}"))