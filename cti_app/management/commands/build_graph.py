"""
Build a Neo4j graph from MITRE ATT&CK campaigns, techniques, and relationships.
Requires Neo4j running locally (default bolt://localhost:7687) with username/password authentication.
"""
import os

from py2neo import Graph, Node, Relationship
from django.core.management.base import BaseCommand
from mitreattack.attackToExcel import attackToExcel
from mitreattack.stix20 import MitreAttackData

from cti_app.models import Domain

# CONFIG (needs a user that can edit the graph)
NEO4J_URI = os.getenv("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
NEO4J_DB = "neo4j"

def load_tactics(mitre, graph, domain):
    print("Adding tactics...")
    tactics = mitre.get_tactics()
    for tactic in tactics:
        tactic_node = Node(
            "Tactic",
            stix_id=tactic["id"],
            domain=domain,
            name=tactic.get("name", ""),
            description=tactic.get("description", ""),
            shortname=tactic.get("x_mitre_shortname"),
        )

        graph.merge(tactic_node, "Tactic", "stix_id")
        print(f"Added tactic: {tactic['name']}")

        techniques = mitre.get_techniques_by_tactic(
            tactic_shortname=tactic["x_mitre_shortname"],
            domain=domain,
        )

        for tech in techniques:
            technique_node = graph.nodes.match("Technique", stix_id=tech["id"]).first()

            if not technique_node:
                # If technique node doesn't already exist (e.g. used in a campaign) add node (such that graph embeddings has full picture)
                technique_node = _get_or_create_technique_node(graph, tech)

            graph.merge(Relationship(tactic_node, "INCLUDES_TECHNIQUE", technique_node))

            print(f"Linked technique {tech['id']} to tactic {tactic['name']}")

def load_groups(mitre, graph):
    print("Adding groups...")
    groups = mitre.get_groups()
    for group in groups:
        # Try to reuse existing node
        group_node = graph.nodes.match("Group", stix_id=group["id"]).first()
        if not group_node:
            group_node = Node(
                "Group",
                stix_id=group["id"],
                name=group.get("name", ""),
                description=group.get("description", "")
            )
            graph.merge(group_node, "Group", "stix_id")
            print(f"Created group: {group['name']}")
        else:
            print(f"Reusing group: {group['name']}")
        techniques = mitre.get_techniques_used_by_group(group["id"])

        for t_entry in techniques:
            t_data = t_entry["object"]
            technique_node = _get_or_create_technique_node(graph, t_data)
            graph.merge(Relationship(group_node, "USES", technique_node))

        software_list = mitre.get_software_used_by_group(group["id"])
        for s_entry in software_list:
            s_data = s_entry["object"]
            software_node = graph.nodes.match(
                "Software",
                stix_id=s_data["id"]
            ).first()
            if not software_node:
                software_node = Node(
                    "Software",
                    stix_id=s_data["id"],
                    name=s_data.get("name", ""),
                    description=s_data.get("description", "")
                )
                graph.merge(software_node, "Software", "stix_id")
            graph.merge(Relationship(group_node, "USES", software_node))

def _get_or_create_technique_node(graph, t_data):
    """
    Returns a technique node, creating it if it does not exist yet.
    Uses dual-label strategy:
      (:Technique)
      (:Technique:SubTechnique)
    """
    labels = ["Technique"]
    is_sub = t_data.get("x_mitre_is_subtechnique", False)
    if is_sub:
        labels.append("SubTechnique")
    technique_node = graph.nodes.match("Technique", stix_id=t_data["id"]).first()
    if not technique_node:
        technique_node = Node(
            *labels,
            stix_id=t_data["id"],
            name=t_data.get("name", ""),
            description=t_data.get("description", ""),
            platforms=", ".join(t_data.get("x_mitre_platforms", [])),
            domains=", ".join(t_data.get("x_mitre_domains", [])),
            kill_chain_phases=", ".join(phase['phase_name'] for phase in t_data.get("kill_chain_phases", []))
        )
        graph.merge(technique_node, "Technique", "stix_id")
        print(f"Created {'SubTechnique' if is_sub else 'Technique'} node: {t_data.get('name', '')}")
    return technique_node

def build_detection_text(mitre_data, detection):
    """
    Build detection description using analytics.
    """
    analytics = mitre_data.get_analytics_by_detection_strategy(detection.id)
    base = [
        f"Detection Strategy Name: {detection.name}",
    ]
    if analytics:
        analytic_blocks = []

        for a in analytics:
            a_name = getattr(a, "name", "")
            a_desc = getattr(a, "description", "")
            a_platform = a.get("x_mitre_platforms", [])
            a_domain = a.get("x_mitre_domains", [])

            analytic_blocks.append(
                "\n".join([
                    f"Analytic Name: {a_name}",
                    f"Analytic Description: {a_desc}",
                    f"Platforms: {', '.join(a_platform) if a_platform else 'Not specified'}",
                    f"Domains: {', '.join(a_domain) if a_domain else 'Not specified'}",
                ])
            )
        base.append(
            "\nAnalytics containing detection logic and implementation details:\n"
            + "\n\n".join(analytic_blocks)
        )
    return "\n".join(base)

def build_graph():
    # Connect to Neo4j
    graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), name=NEO4J_DB)
    print("Connected to Neo4j")

    # Clear existing graph (optional)
    graph.delete_all()
    print("Existing graph cleared.")

    # Load MITRE ATT&CK data
    print("Loading MITRE ATT&CK data...")

    # Loop through all domains
    for domain in Domain.values:
        attack_data = attackToExcel.get_stix_data(domain)
        mitre = MitreAttackData(src=attack_data)

        # Build Campaign nodes
        campaigns = mitre.get_campaigns()
        for campaign in campaigns:
            campaign_node = graph.nodes.match("Campaign", stix_id=campaign["id"]).first()
            if not campaign_node:
                campaign_node = Node(
                    "Campaign",
                    stix_id=campaign["id"],
                    name=campaign["name"],
                    description=campaign.get("description", ""),
                    first_seen=campaign.get("first_seen"),
                    last_seen=campaign.get("last_seen"),
                    aliases=", ".join(campaign.get("aliases", []))
                )
                graph.merge(campaign_node, "Campaign", "stix_id")
                print(f"Added campaign: {campaign['name']}")

            # Link groups and software to campaign
            groups = mitre.get_groups_attributing_to_campaign(campaign["id"])
            for g in groups:
                group_obj = g["object"]
                group_node = graph.nodes.match("Group", stix_id=group_obj["id"]).first()
                if not group_node:
                    group_node = Node(
                        "Group",
                        stix_id=group_obj["id"],
                        name=group_obj["name"],
                        description=group_obj.get("description", "")
                    )
                    graph.merge(group_node, "Group", "stix_id")
                for rel in g["relationships"]:
                    graph.merge(Relationship(campaign_node, rel["relationship_type"].upper().replace("-", "_"), group_node))
                print(f"  Linked group: {group_obj['name']}")

            software_list = mitre.get_software_used_by_campaign(campaign["id"])
            for s in software_list:
                software_obj = s["object"]
                software_node = Node(
                    "Software",
                    stix_id=software_obj["id"],
                    name=software_obj["name"],
                    description=software_obj.get("description", "")
                )
                graph.merge(software_node, "Software", "stix_id")
                graph.merge(Relationship(campaign_node, "USES", software_node))
                print(f"  Linked software: {software_obj['name']}")

            # Link techniques used by campaign
            used_techniques = mitre.get_techniques_used_by_campaign(campaign["id"])
            for technique_entry in used_techniques:
                t_data = technique_entry["object"]
                technique_node = _get_or_create_technique_node(graph, t_data)

                # Campaign USES technique
                graph.merge(Relationship(campaign_node, "USES", technique_node))
                print(f"  Linked technique: {t_data['name']}")

                # Sub-technique handling
                if t_data.get("x_mitre_is_subtechnique", False):
                    parent_rel_data = mitre.get_parent_technique_of_subtechnique(t_data["id"])
                    if parent_rel_data:
                        for entry in parent_rel_data:
                            parent_obj = entry["object"]
                            parent_node = _get_or_create_technique_node(graph, parent_obj)
                            graph.merge(Relationship(technique_node, "SUBTECHNIQUE_OF", parent_node))
                            print(f"    Linked sub-technique to parent: {parent_obj['name']}")

                # Procedures
                procedures = mitre.get_procedure_examples_by_technique(t_data["id"])
                for proc in procedures:
                    proc_node = Node(
                        "Procedure",
                        stix_id=proc["id"],
                        description=proc["description"]
                    )
                    graph.merge(proc_node, "Procedure", "stix_id")
                    graph.merge(Relationship(proc_node, "PROCEDURE_OF", technique_node))
                    print(f"    Added procedure for technique {t_data['name']}")

                # Mitigations
                mitigations = mitre.get_mitigations_mitigating_technique(t_data["id"])
                for m_entry in mitigations:
                    m = m_entry["object"]
                    mitigation_node = Node(
                        "Mitigation",
                        stix_id=m["id"],
                        domain=domain,
                        name=m.get("name", ""),
                        description=m.get("description", "")
                    )
                    graph.merge(mitigation_node, "Mitigation", "stix_id")
                    for rel in m_entry["relationships"]:
                        graph.merge(Relationship(mitigation_node, rel["relationship_type"].upper().replace("-", "_"), technique_node))
                    print(f"    Linked mitigation: {m.get('name', '')}")

                # Detections
                detections = mitre.get_detection_strategies_detecting_technique(t_data["id"])
                for d_entry in detections:
                    d = d_entry["object"]
                    detection_node = Node(
                        "Detection",
                        stix_id=d["id"],
                        domain=domain,
                        name=d.get("name", ""),
                        description=build_detection_text(mitre, d)
                    )
                    graph.merge(detection_node, "Detection", "stix_id")
                    for rel in d_entry.get("relationships", []):
                        graph.merge(Relationship(detection_node, rel["relationship_type"].upper().replace("-", "_"), technique_node))
                    print(f"    Linked detection: {d.get('name', '')}")

                # Assets
                assets = mitre.get_assets_targeted_by_technique(t_data["id"])
                for a_entry in assets:
                    a = a_entry["object"]
                    asset_node = Node(
                        "Asset",
                        stix_id=a["id"],
                        domain=domain,
                        name=a.get("name", ""),
                        description=a.get("description", "")
                    )
                    graph.merge(asset_node, "Asset", "stix_id")
                    for rel in a_entry.get("relationships", []):
                        graph.merge(Relationship(asset_node, rel["relationship_type"].upper().replace("-", "_"), technique_node))
                    print(f"    Linked asset: {a.get('name', '')}")
        # Tactics (not depending on techniques used in a certain campaign)
        load_tactics(mitre, graph, domain)
        load_groups(mitre, graph)
        print("Domain complete!")
    print("Graph construction complete!")

class Command(BaseCommand):
    help = "Build MITRE ATT&CK background / philosophy embeddings"

    def handle(self, *args, **options):
        self.stdout.write("Loading ATT&CK Design & Philosophy PDF...")
        build_graph()
