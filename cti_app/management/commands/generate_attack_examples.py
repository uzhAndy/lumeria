from collections import defaultdict
from django.core.management.base import BaseCommand

from cti_app.models import Campaign, CampaignTechnique
from cti_app.services.unified_kill_chain import KILL_CHAIN_MAPPING_ORDERED
from cti_app.utils import sort_techniques_by_parent


class Command(BaseCommand):
    help = "Generate and save attack examples for all campaigns"

    def handle(self, *args, **kwargs):
        # campaigns = Campaign.objects.all()
        campaigns = Campaign.objects.filter(attack_example__isnull=True)
        total = campaigns.count()
        self.stdout.write(f"Found {total} campaigns. Generating attack examples...")

        for campaign in campaigns:
            campaign_techniques = CampaignTechnique.objects.filter(
                campaign=campaign
            ).select_related("technique", "technique__parent_technique")

            # Group techniques by tactic
            # (a tactic represents the selected context for a technique within the generated attack example for a campaign and is associated with a specific kill chain phase)
            techniques_by_tactic = defaultdict(list)
            for ct in campaign_techniques:
                techniques_by_tactic[ct.selected_tactic].append({
                    "technique_id": ct.technique.mitre_id,
                    "technique_name": ct.technique.name,
                    "technique_parent": (
                        ct.technique.parent_technique.name
                        if ct.technique.parent_technique else None
                    ),
                    "usage_description": ct.usage_summary,
                    "mitigations": [
                        {"name": m.name, "description": m.summary}
                        for m in ct.technique.mitigations.all()
                    ],
                })

            # Iterates through the ordered kill chain’s tactical progression and,
            # if a tactic is present in the campaign, collects its associated techniques.
            # Techniques of a tactic are always ordered such that the parent technique is always coming directly before all its children
            ordered_attack_example = []
            for tactic, phase in KILL_CHAIN_MAPPING_ORDERED.items():
                if tactic not in techniques_by_tactic:
                    continue
                ordered_attack_example.append({
                    "tactic": tactic,
                    "phase": phase,
                    "techniques": sort_techniques_by_parent(techniques_by_tactic[tactic]),
                })

            # Save to database
            campaign.attack_example = {
                "campaign": campaign.name,
                "attack_example": ordered_attack_example
            }
            campaign.save(update_fields=["attack_example"])
            self.stdout.write(f"Generated attack example for campaign '{campaign.name}'")

        self.stdout.write(self.style.SUCCESS("Attack examples generated for all campaigns."))