import chromadb
from django.core.management.base import BaseCommand

from dotenv import load_dotenv
load_dotenv()

from mitreattack.attackToExcel import attackToExcel
from mitreattack.stix20 import MitreAttackData
from cti_app.embedding_constants import VECTOR_STORE_DIR, COLLECTION_NAME, DOC_PREFIX
from cti_app.services.embeddings import get_embeddings


class MitreEmbeddings:

    def __init__(self, vector_dir=VECTOR_STORE_DIR, collection_name=COLLECTION_NAME):
        self.embeddings = get_embeddings()
        self.client = chromadb.PersistentClient(path=vector_dir)
        try:
            # self.client.delete_collection(name=collection_name)
            self.collection = self.client.get_or_create_collection(name=collection_name)
        except Exception:
            print("Failed to get or create collection...")
            pass

    def embed_text(self, text, doc_id, stix_id=None, name=None, type=None):
        """ Embed an object text and store it in Chroma """
        existing = self.collection.get(ids=[doc_id])

        # check if the embedding already exists to avoid duplicated (if not, embeddings should return None)
        if existing["embeddings"] is not None and len(existing["embeddings"]) > 0:
            return

        embedding_text = f"{DOC_PREFIX} {text.strip()}"
        embedding = self.embeddings.embed_query(embedding_text)

        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[embedding_text],
            metadatas={
            "stix_id": stix_id,
            "type": type,
            "name": name
            }
        )

    def embed_relationship(self, doc_id, text, source_ref, target_ref, rel_type):
        """Embed a STIX relationship where source and target references are MITRE IDs."""
        # Check if already exists to avoid redundant embedding calls
        existing = self.collection.get(ids=[doc_id])
        if existing["embeddings"] is not None and len(existing["ids"]) > 0:
            return

        embedding_text = f"{DOC_PREFIX} {text.strip()}"
        embedding = self.embeddings.embed_query(embedding_text)
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[embedding_text],
            metadatas={
                "stix_id": doc_id,
                "type": "relationship",
                "relationship_type": rel_type,
                "source_ref": source_ref,
                "target_ref": target_ref,
            }
        )

    def embed_object_with_relationships(self, obj_type, obj, relationships, parent_name, parent_type, obj_text = None):
        """Embed object plus its relationships to a parent (campaign, technique, etc.)"""
        if obj_text is None:
            obj_text = f"{obj_type.capitalize()} Name: {obj.get('name', '')}\nDescription: {obj.get('description', '')}"
        self.embed_text(
            doc_id = obj["id"],
            text = obj_text,
            stix_id = obj["id"],
            name = obj.get("name", ""),
            type = obj_type
        )

        for rel in relationships:
            rel_type = rel.get("relationship_type", "")
            source_ref = rel.get("source_ref", "")
            target_ref = rel.get("target_ref", "")
            rel_text = (
                f"{obj_type.capitalize()} '{obj.get('name', '')}' is related to {parent_type} '{parent_name}'. "
                f"Relationship type: '{rel_type}'. "
                f"Relationship Description: {rel.get('description', '').strip()}"
            )
            self.embed_relationship(
                doc_id=rel["id"],
                text=rel_text,
                source_ref=source_ref,
                target_ref=target_ref,
                rel_type=rel_type,
            )

def build_campaign_embedding(mitre_data, campaign, embeddings):
    campaign_text = (
        f"Campaign Name: {campaign['name']}, "
        f"Description: {campaign.get('description', '')}, "
        f"Aliases: {', '.join(campaign.get('aliases', []))}, "
        f"First Seen: {campaign.get('first_seen')}, "
        f"Last Seen: {campaign.get('last_seen')}"
    )
    embeddings.embed_text(
        doc_id=campaign["id"],
        text=campaign_text,
        stix_id=campaign["id"],
        name= campaign["name"],
        type="campaign"
    )

    groups = mitre_data.get_groups_attributing_to_campaign(campaign["id"])
    for g in groups:
        embeddings.embed_object_with_relationships("group", g["object"], g["relationships"], parent_name=campaign["name"], parent_type="campaign")

    software_list = mitre_data.get_software_used_by_campaign(campaign["id"])
    for s in software_list:
        embeddings.embed_object_with_relationships("software", s["object"], s["relationships"], parent_name=campaign["name"], parent_type="campaign")

def build_technique_text(t_data):
    return (
        f"Technique Name: {t_data.get('name', '')}, "
        f"Description: {t_data.get('description', '')}, "
        f"Kill Chain Phases: {', '.join(phase['phase_name'] for phase in t_data.get('kill_chain_phases', []))}, "
        f"Platforms: {', '.join(t_data.get('x_mitre_platforms', []))}, "
        f"Domains: {', '.join(t_data.get('x_mitre_domains', []))}, "
        f"Subtechnique: {t_data.get('x_mitre_is_subtechnique', False)}"
    )

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

def build_technique_embedding(mitre_data, technique, campaign_name, embeddings):
    t_data = technique["object"]
    embeddings.embed_text(
        doc_id = t_data["id"],
        text = build_technique_text(t_data),
        stix_id = t_data["id"],
        name = t_data.get("name", ""),
        type = "technique"
    )

    # 2. Embed Campaign-Specific Usage (The logic you requested to add)
    for rel in technique["relationships"]:
        rel_text = (
            f"Technique: '{t_data['name']}', "
            f"Campaign: '{campaign_name}', "
            f"Technique '{t_data['name']}' was employed in campaign '{campaign_name}'. "
            f"Observed usage: {rel.get('description', 'No description provided.')}"
        )
        # (campaign has relationship type "uses" for both software and techniques so changed it to employ for better differentiation)
        embeddings.embed_relationship(
            doc_id=rel["id"],
            text=rel_text,
            source_ref=rel.get("source_ref", ""),
            target_ref=rel.get("target_ref", ""),
            rel_type="employs"
        )

    # 3. Embed Parent Relationship (Sub-technique logic)
    if t_data.get("x_mitre_is_subtechnique", False):
        parent_rel_data = mitre_data.get_parent_technique_of_subtechnique(t_data["id"])
        if parent_rel_data:
            for entry in parent_rel_data:
                parent_obj = entry["object"]
                parent_rel = entry["relationships"][0]

                # Ensure parent object exists in vector store (if already embedded, it will get skipped)
                embeddings.embed_text(
                    doc_id=parent_obj["id"],
                    text=build_technique_text(parent_obj),
                    stix_id=parent_obj["id"],
                    name= parent_obj.get("name", ""),
                    type= "technique"
                )

                # Embed the subtechnique-of connection
                sub_rel_text = f"Technique '{t_data.get('name')}' is a sub-technique of '{parent_obj.get('name')}'."
                embeddings.embed_relationship(
                    doc_id=parent_rel["id"],
                    text=sub_rel_text,
                    source_ref=t_data["id"],
                    target_ref=parent_obj["id"],
                    rel_type="subtechnique-of"
                )

    # Procedures (are relationships not objects)
    procedures = mitre_data.get_procedure_examples_by_technique(t_data["id"])
    for proc in procedures:
        proc_text = (
            f"Technique '{t_data['name']}' procedure: {proc['description']}"
        )
        embeddings.embed_relationship(
            doc_id=proc["id"],
            text=proc_text,
            source_ref=proc["source_ref"],
            target_ref=proc["target_ref"],
            rel_type="procedure-of"
        )
    # Mitigations
    mitigations = mitre_data.get_mitigations_mitigating_technique(t_data["id"])
    for m_entry in mitigations:
        m = m_entry["object"]
        embeddings.embed_object_with_relationships("mitigation", m, m_entry["relationships"], parent_name=t_data["name"], parent_type="technique")

    # Detections
    detections = mitre_data.get_detection_strategies_detecting_technique(t_data["id"])
    for d_entry in detections:
        d = d_entry["object"]
        detection_text = build_detection_text(mitre_data, d)
        embeddings.embed_object_with_relationships("detection", d, d_entry.get("relationships", []), parent_name=t_data["name"], parent_type="technique", obj_text=detection_text)

    # Assets
    assets = mitre_data.get_assets_targeted_by_technique(t_data["id"])
    for a_entry in assets:
        a = a_entry["object"]
        embeddings.embed_object_with_relationships("asset", a, a_entry.get("relationships", []), parent_name=t_data["name"], parent_type="technique")


def build_tactic_embeddings(mitre_data, embeddings, domain="enterprise-attack"):
    tactics = mitre_data.get_tactics()

    for tactic in tactics:
        tactic_text = (
            f"Tactic Name: {tactic.get('name', '')}, "
            f"Description: {tactic.get('description', '')}, "
            f"Domain: {domain}"
        )
        embeddings.embed_text(
            doc_id=tactic["id"],
            text=tactic_text,
            stix_id=tactic["id"],
            name=tactic.get("name", ""),
            type="tactic"
        )

        techniques = mitre_data.get_techniques_by_tactic(tactic_shortname=tactic["x_mitre_shortname"], domain=domain)
        for technique in techniques:
            rel_text = f"Technique '{technique.get('name')}' belongs to tactic '{tactic.get('name')}' (Domain: {domain})."
            embeddings.embed_relationship(
                doc_id=f"{tactic["id"]}_{technique["id"]}",
                text=rel_text,
                source_ref=technique["id"],
                target_ref=tactic["id"],
                rel_type="belongs-to-tactic"
            )

class Command(BaseCommand):
    help = "Build MITRE ATT&CK embeddings for campaigns, techniques, and relationships"

    def handle(self, *args, **options):
        self.stdout.write("Loading MITRE ATT&CK data...")

        embeddings = MitreEmbeddings()

        domains = ["enterprise-attack", "mobile-attack", "ics-attack"]
        for domain in domains:
            attackdata = attackToExcel.get_stix_data(domain)
            mitre = MitreAttackData(src=attackdata)

            self.stdout.write("Building embeddings...")
            build_tactic_embeddings(mitre, embeddings, domain=domain)
            self.stdout.write("Tactics embeddings built...")

            campaigns = mitre.get_campaigns()
            for campaign in campaigns:
                # Embed campaign and related objects
                build_campaign_embedding(mitre, campaign, embeddings)
                self.stdout.write("Campaign embedding built...")

                # Embed techniques used by campaign
                used_techniques = mitre.get_techniques_used_by_campaign(campaign["id"])
                for technique in used_techniques:
                    build_technique_embedding(mitre, technique, campaign["name"], embeddings)
                    self.stdout.write("Technique embeddings built...")

                all_techniques_text = f"{DOC_PREFIX} Campaign '{campaign['name']}' uses the following techniques in the domain '{domain}': " + \
                                      ", ".join([t['object']['name'] for t in used_techniques])
                embeddings.embed_text(
                    doc_id=f"{campaign['id']}-{domain}-all-techniques",
                    text=all_techniques_text,
                    stix_id=campaign["id"],
                    name=campaign["name"],
                    type="campaign_techniques"
                )

                self.stdout.write("Campaign embeddings built...")

        self.stdout.write(f"Embedding process complete! Total embeddings: {len(embeddings.collection.get()['ids'])}")
