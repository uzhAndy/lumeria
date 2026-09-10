import random
import os
import networkx as nx
from django.core.management import BaseCommand
from gensim.models import Word2Vec

from langchain_community.graphs import Neo4jGraph
from django.db import transaction
from cti_app.models import Campaign, Group, CampaignGroupSimilarity

NEO4J_URL = os.getenv("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = "neo4j"
NEO4J_PASS = "password"
NEO4J_DB = "neo4j"

_MODEL = None
_ID_INDEX = None


def get_graph():
    return Neo4jGraph(
        url = NEO4J_URL,
        username=NEO4J_USER,
        password=NEO4J_PASS,
        database=NEO4J_DB,
    )


def load_graph_from_neo4j(graph):
    nodes = graph.query("""
        MATCH (n)
        WHERE n.stix_id IS NOT NULL
        RETURN n.stix_id as id, labels(n) as labels, n.name as name
    """)

    edges = graph.query("""
        MATCH (a)-[r]->(b)
        WHERE a.stix_id IS NOT NULL AND b.stix_id IS NOT NULL AND type(r) <> 'ATTRIBUTED_TO'
        RETURN a.stix_id as source, b.stix_id as target, type(r) as type
    """)

    return nodes, edges


# Build NetworkX graph with labels for graph walks
def build_networkx_graph(nodes, edges):
    G = nx.Graph()
    for n in nodes:
        G.add_node(
            n["id"],
            label=n["labels"][0] if n["labels"] else "Unknown",
            name=n["name"],
        )
    for e in edges:
        G.add_edge(e["source"], e["target"])
    return G


# Metapath2Vec helper functions
def get_neighbors_by_label(G, node, label):
    return [n for n in G.neighbors(node) if G.nodes[n]["label"] == label]


def metapath_walk(G, start, metapath, length):
    walk = [start]
    current = start
    for i in range(length - 1):
        expected_label = metapath[i % len(metapath)]
        neigh = get_neighbors_by_label(G, current, expected_label)
        if not neigh:
            break
        current = random.choice(neigh)
        walk.append(current)
    return walk


def generate_metapath_walks(G):
    # metapaths = [["Technique", "Group", "Technique", "Campaign"], ["Software", "Group", "Software", "Campaign"], ["Technique", "Tactic", "Technique", "Campaign"]]
    metapaths = [
        ["Campaign", "Technique", "Group"],
        ["Campaign", "Software", "Group"],
        ["Campaign", "Technique", "Tactic", "Technique", "Group"],
        # ["Campaign", "Technique", "Technique", "Group"],  # was shown to not be effective, considers also parent techniques, e.g. campaign uses a sub-technique of the parent technique a group uses
    ]
    walks = []
    nodes = list(G.nodes())
    for n in nodes:
        for _ in range(20):  # number of walks per node
            for mp in metapaths:
                walk = metapath_walk(G, n, mp, length=10)
                if len(walk) > 3:
                    walks.append(walk)
    return walks


# Compute embeddings
def compute_metapath_embeddings(G):
    walks = generate_metapath_walks(G)
    model = Word2Vec(walks)
    model.wv.fill_norms()
    return model


# Load node id index
def load_ids(graph):
    res = graph.query("""
        MATCH (n)
        WHERE n.stix_id IS NOT NULL
        RETURN labels(n)[0] as label, n.name as name, n.stix_id as id
    """)
    index = {}
    for r in res:
        index[(r["label"], r["name"])] = r["id"]
    return index


# Cache model
def get_model():
    global _MODEL, _ID_INDEX
    if _MODEL is not None:
        return _MODEL, _ID_INDEX
    graph = get_graph()
    nodes, edges = load_graph_from_neo4j(graph)
    G = build_networkx_graph(nodes, edges)

    campaign_group_edges = [
        (u, v)
        for u, v in G.edges()
        if G.nodes[u]["label"] == "Campaign" and G.nodes[v]["label"] == "Group"
           or G.nodes[v]["label"] == "Campaign" and G.nodes[u]["label"] == "Group"
    ]
    print(f"Number of edges between Campaign and Group: {len(campaign_group_edges)}") # should be zero as ground truth was removed

    _MODEL = compute_metapath_embeddings(G)
    _ID_INDEX = load_ids(graph)
    return _MODEL, _ID_INDEX


# Compute similarity
def compute_similarity_for_campaign(campaign):
    model, id_index = get_model()
    campaign_id = id_index.get(("Campaign", campaign.name))
    if campaign_id is None or campaign_id not in model.wv:
        return
    attributed = set(campaign.groups.values_list("name", flat=True))
    results = []
    for g in Group.objects.all():
        gid = id_index.get(("Group", g.name))
        if gid is None or gid not in model.wv:
            continue
        sim = model.wv.similarity(campaign_id, gid)
        results.append((g, float(sim), g.name in attributed))
    save_similarity(campaign, results)


# Save similarity to DB
def save_similarity(campaign, results):
    CampaignGroupSimilarity.objects.filter(campaign=campaign).delete()
    objs = [
        CampaignGroupSimilarity(
            campaign=campaign,
            group=group,
            score=score,
            is_attributed=is_attr,
        )
        for group, score, is_attr in results
    ]
    CampaignGroupSimilarity.objects.bulk_create(objs, batch_size=500)


# Compute all campaign similarities
def compute_all_campaign_similarities():
    for c in Campaign.objects.all():
        if CampaignGroupSimilarity.objects.filter(campaign=c).exists():
            print(f"Skipping {c.name}, similarity already computed")
            continue
        print("processing", c.name)
        compute_similarity_for_campaign(c)


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Starting campaign similarity calculations...")
        )

        with transaction.atomic():
            compute_all_campaign_similarities()