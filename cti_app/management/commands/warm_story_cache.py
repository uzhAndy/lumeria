from cti_app.models import Campaign
from cti_app.services.agents import get_plain_agent_with_memory
from cti_app.services.llm_tasks import get_story_response
from django.core.management.base import BaseCommand


def warmup_story_cache(agent):
    campaigns = Campaign.objects.all()

    for campaign in campaigns:
        # Generate the story for all tactics from the attack_example in the order they appear (order important to optimize response as agent has campaign dependent memory)
        attack_data = campaign.attack_example.get("attack_example", [])
        tactics = [step.get("tactic") for step in attack_data if step.get("tactic")]

        print(f"Processing Campaign: {campaign.name}")

        for tactic in tactics:
            print(f"  - Priming cache for tactic: {tactic}...")
            get_story_response(agent, campaign, tactic)
    print("Cache warmup complete")


class Command(BaseCommand):
    help = "Pre-generate and cache all campaign storytelling responses."

    def handle(self, *args, **options):
        PLAIN_AGENT = get_plain_agent_with_memory()
        warmup_story_cache(PLAIN_AGENT)