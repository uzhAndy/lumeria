# python manage.py load_mitre_data_into_relational_db
from django.core.management.base import BaseCommand
from django.db import transaction

from mitreattack.attackToExcel import attackToExcel
from mitreattack.stix20 import MitreAttackData

from cti_app.models import (
    Campaign,
    Technique,
    CampaignTechnique,
    Mitigation,
    Tactic,
    Detection,
    Group,
    Domain
)

# loads all the necessary mitre data that is used in the frontend into the django db
class Command(BaseCommand):
    help = "Load MITRE ATT&CK campaigns, techniques, mitigations, and usage descriptions into Django DB"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Loading MITRE ATT&CK STIX data..."))

        with transaction.atomic():
            # delete all the existing data to make sure there isn't any outdated ones
            Campaign.objects.all().delete()
            Group.objects.all().delete()
            Technique.objects.all().delete()
            Mitigation.objects.all().delete()
            Detection.objects.all().delete()
            Tactic.objects.all().delete()

            # Iterate over the three domain-specific matrices since a single campaign may include techniques from multiple domains
            for domain in Domain.values:
                attackdata = attackToExcel.get_stix_data(domain)
                mitre = MitreAttackData(src=attackdata)
                self.stdout.write(f"Processing domain: {domain}")

                self._load_campaigns(mitre, domain)
                self._load_all_groups(mitre, domain) # loads also campaigns not attributed yet to a campaign
                self._load_tactics(mitre, domain)

            self.stdout.write(self.style.SUCCESS("MITRE ATT&CK campaign data successfully loaded."))


    def _load_campaigns(self, mitre: MitreAttackData, domain):
        campaigns = mitre.get_campaigns()

        for campaign in campaigns:
            campaign_obj, _ = Campaign.objects.update_or_create(
                mitre_id=campaign["id"],
                defaults={
                    "name": campaign.get("name", ""),
                    "first_seen": campaign.get("first_seen"),
                    "last_seen": campaign.get("last_seen"),
                    "description": campaign.get("description", ""),
                }
            )

            self._load_campaign_techniques(mitre, campaign_obj, domain)
            self._load_groups_of_campaign(mitre, campaign_obj, domain)

    def _get_or_create_technique(self, technique_data, domain):
        """
        Returns Technique object, creates it if missing.
        """

        technique_obj = Technique.objects.filter(mitre_id=technique_data["id"]).first()
        if technique_obj:
            return technique_obj

        technique_obj, _ = Technique.objects.update_or_create(
            mitre_id=technique_data["id"],
            defaults={
                "domain": domain,
                "name": technique_data.get("name", ""),
                "description": technique_data.get("description", ""),
                "kill_chain_phases": [p["phase_name"] for p in technique_data.get("kill_chain_phases", [])],
                "platforms": technique_data.get("x_mitre_platforms",[]),
                "is_subtechnique": technique_data.get("x_mitre_is_subtechnique", False),
                "created_date": technique_data.get("created"),
            },
        )

        return technique_obj

    def _load_campaign_techniques(self, mitre, campaign, domain):
        used_techniques = mitre.get_techniques_used_by_campaign(campaign.mitre_id)

        for entry in used_techniques:
            technique_data = entry["object"]
            relationships = entry.get("relationships", [])
            technique_obj = self._get_or_create_technique(technique_data, domain)

            # Find Parent technique if sub-technique
            if technique_obj.is_subtechnique:
                parents = mitre.get_parent_technique_of_subtechnique(technique_obj.mitre_id)
                if parents:
                    parent_data = parents[0]["object"]
                    parent_obj = Technique.objects.filter(mitre_id=parent_data["id"]).first()
                    if not parent_obj:
                        parent_obj = self._get_or_create_technique(parent_data, domain)
                    technique_obj.parent_technique = parent_obj
                    technique_obj.save(update_fields=["parent_technique"])

            # Combine all relationship descriptions into one usage narrative
            usage_descriptions = [
                rel.get("description", "")
                for rel in relationships
                if rel.get("description")
            ]

            usage_text = "\n".join(usage_descriptions).strip()

            CampaignTechnique.objects.update_or_create(
                campaign=campaign,
                technique=technique_obj,
                defaults={
                    "usage_description": usage_text
                }
            )
            self._load_mitigations(mitre, technique_obj, domain)
            self._load_detections(mitre, technique_obj, domain)

    def _load_mitigations(self, mitre, technique_obj, domain):
        mitigations = mitre.get_mitigations_mitigating_technique(technique_obj.mitre_id)

        for entry in mitigations:
            mitigation = entry["object"]

            mitigation_obj, _ = Mitigation.objects.update_or_create(
                mitre_id=mitigation["id"],
                defaults={
                    "domain": domain,
                    "name": mitigation.get("name", ""),
                    "description": mitigation.get("description", ""),
                }
            )

            mitigation_obj.techniques.add(technique_obj)

    def _load_detections(self, mitre, technique_obj, domain):
        detections = mitre.get_detection_strategies_detecting_technique(technique_obj.mitre_id)

        for entry in detections:
            detection = entry["object"]

            detection_obj, _ = Detection.objects.update_or_create(
                mitre_id=detection["id"],
                defaults={
                    "domain": domain,
                    "name": detection.get("name", ""),
                }
            )

            detection_obj.techniques.add(technique_obj)

    def _get_or_create_group(self, mitre, group_data, domain):
        """
        Fetches group from DB if exists, otherwise creates it
        """
        group_obj = Group.objects.filter(mitre_id=group_data["id"]).first()
        if group_obj:
            return group_obj
        # create group if not existing
        group_obj = Group.objects.create(
            mitre_id=group_data["id"],
            name=group_data.get("name", ""),
            description=group_data.get("description", ""),
        )
        # load techniques for new group
        techniques = mitre.get_techniques_used_by_group(group_data["id"])
        for t_entry in techniques:
            t_data = t_entry["object"]
            technique_obj = self._get_or_create_technique(t_data, domain)
            group_obj.techniques.add(technique_obj)
        return group_obj

    def _load_groups_of_campaign(self, mitre, campaign, domain):
        groups = mitre.get_groups_attributing_to_campaign(campaign.mitre_id)

        for entry in groups:
            group_obj = self._get_or_create_group(mitre, entry["object"], domain)
            if not group_obj:
                continue
            # create campaign → group relationship
            campaign.groups.add(group_obj)

    def _load_tactics(self, mitre, domain):
        tactics = mitre.get_tactics()

        for tactic in tactics:
            tactic_obj, _ = Tactic.objects.update_or_create(
                mitre_id=tactic["id"],
                defaults={
                    "domain": domain,
                    "name": tactic.get("name", ""),
                    "description": tactic.get("description", ""),
                }
            )

            techniques = mitre.get_techniques_by_tactic(tactic_shortname=tactic["x_mitre_shortname"], domain="enterprise-attack")

            # collect mitre IDs of techniques used in tactic
            technique_ids = [t["id"] for t in techniques]

            # fetch techniques (load_tactics must be run after technique collection)
            existing_techniques = Technique.objects.filter(
                mitre_id__in=technique_ids
            )

            tactic_obj.techniques.set(existing_techniques)

    def _load_all_groups(self, mitre, domain):
        groups = mitre.get_groups()
        for entry in groups:
            group_obj = self._get_or_create_group(mitre, entry, domain)
            print("Loaded group: ", group_obj.name)
