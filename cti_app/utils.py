from sklearn.feature_extraction.text import TfidfTransformer
from collections import OrderedDict, defaultdict
from itertools import chain
import numpy as np
import re

def sort_techniques_by_parent(techniques):
    """
    Sort and group techniques so that each parent technique appears immediately
    before all of its child techniques. If a parent technique is not present,
    its child techniques are still grouped together.
    """
    tech_map = {t["technique_name"]: t for t in techniques}

    # collects for each parent its children
    children_map = defaultdict(list)

    parent_order = OrderedDict()

    # collects all the parents in parent_order and creates a dictionary for parent to children
    for tech in techniques:
        name = tech["technique_name"]
        parent = tech["technique_parent"]

        if parent:
            children_map[parent].append(tech)
            parent_order.setdefault(parent, None)
        else:
            parent_order.setdefault(name, None)

    sorted_list = []
    added = set()

    for parent in parent_order:
        # add the parent data first and then all its children
        if parent in tech_map and parent not in added:
            sorted_list.append(tech_map[parent])
            added.add(parent)

        for child in children_map.get(parent, []):
            child_name = child["technique_name"]
            if child_name not in added:
                sorted_list.append(child)
                added.add(child_name)

    return sorted_list


def normalize_tactic_name(kill_chain_phase: str) -> str:
    """
    Converts MITRE-style kill chain phase to a human-readable tactic name.
    Example: "credential-access" -> "Credential Access"
    """
    return kill_chain_phase.replace("-", " ").title()


def clean_entity_description(description: str) -> str:
    """
    Clean group description by:
    - Removing citations in parentheses, e.g., (Citation: FireEye FIN10 June 2017)
    - Removing URLs (http, https, www)
    - Removing unnecessary square brackets but keeping content inside
    """
    if not description:
        return ""

    # Remove URLs
    description = re.sub(r"https?://\S+|www\.\S+", "", description)

    # Remove parentheses that start with Citation: but keep surrounding text
    description = re.sub(r"\(\s*Citation:.*?\)", "", description, flags=re.IGNORECASE)

    # Remove any unmatched parentheses at the start or end of words
    description = re.sub(r"\(\s*", "", description)  # remove stray '('
    description = re.sub(r"\s*\)", "", description)  # remove stray ')'

    # Remove square brackets but keep content inside
    description = re.sub(r"\[(.*?)\]", r"\1 ", description)

    return description


def compute_campaign_group_similarity(campaign, groups):
    """
    Compute cosine similarity between a campaign and groups based on shared techniques.
    Returns list of dicts with similarity scores.
    """

    # fetching all techniques of the campaign and built a set with the techniques ids
    campaign_techniques_qs = campaign.campaigntechnique_set.select_related("technique")
    campaign_techniques = set(ct.technique.id for ct in campaign_techniques_qs if ct.technique)

    if not campaign_techniques:
        return []

    # collect all techniques of all groups and campaigns
    all_tech_ids = set(chain.from_iterable(g.techniques.values_list("id", flat=True) for g in groups))
    all_tech_ids.update(campaign_techniques)
    all_tech_ids = sorted(list(all_tech_ids))
    # print("techniques of all groups and campaigns: ", all_tech_ids)

    tech_index = {tid: i for i, tid in enumerate(all_tech_ids)}

    vector_length = len(all_tech_ids)

    # initialize campaign vector
    campaign_vector = np.zeros(vector_length, dtype=np.float32)

    for tid in campaign_techniques:
        # if technique was used in campaign set it to one
        campaign_vector[tech_index[tid]] = 1.0

    # will be used to determine whether groups that have already been connected to the campaign have a high similarity score
    attributed_groups = set(campaign.groups.values_list("name", flat=True))

    result = []
    for group in groups:
        group_techniques = set(group.techniques.values_list("id", flat=True))
        group_vector = np.zeros(vector_length, dtype=np.float32)
        for tid in group_techniques:
            # if technique was used by the group set it to one
            group_vector[tech_index[tid]] = 1.0

        if (np.linalg.norm(campaign_vector) == 0 or np.linalg.norm(group_vector) == 0):
            similarity = 0.0 # either campaign or group didn't use any techniques
        else:
            # calculate cosine similarity (dot(a,b) / (|a| * |b|)) between each group and the selected campaign
            similarity = float(np.dot(campaign_vector, group_vector) / (np.linalg.norm(campaign_vector) * np.linalg.norm(group_vector)))

        # add the similarity between the campaign and group to the result
        result.append(
            {
                "group_id": group.id,
                "group_name": group.name,
                "similarity_score": round(similarity, 3),
                "is_attributed": group.name in attributed_groups,
            }
        )

    return result


def compute_campaign_group_similarity_tfidf(campaign, groups):
    """
    Compute TF-IDF weighted cosine similarity between a campaign and groups based on shared techniques.
    The advantage over normal cosine similarity is that rare techniques, which can be a distinctive mark of a group, are given more weight.
    """

    campaign_techniques_qs = campaign.campaigntechnique_set.select_related("technique")
    campaign_techniques = set(ct.technique.id for ct in campaign_techniques_qs if ct.technique)

    # collect all techniques of all groups and campaigns
    all_tech_ids = set(chain.from_iterable(g.techniques.values_list("id", flat=True) for g in groups))
    all_tech_ids.update(campaign_techniques)

    # assign each technique a specific position in a vector
    all_tech_ids = sorted(list(all_tech_ids))
    tech_index = {tid: i for i, tid in enumerate(all_tech_ids)}

    vector_length = len(all_tech_ids)

    # Build document-term matrix where rows are the groups + selected campaign and the columns are the techniques
    matrix = []
    group_list = list(groups)
    for group in group_list:
        vec = np.zeros(vector_length, dtype=np.float32)
        group_techniques = set(group.techniques.values_list("id", flat=True))

        for tid in group_techniques:
            # set the corresponding entry to one if technique was used by the group
            vec[tech_index[tid]] = 1.0

        matrix.append(vec)

    # campaign vector
    campaign_vec = np.zeros(vector_length, dtype=np.float32)
    for tid in campaign_techniques:
        # set the corresponding entry to one if technique was used by the campaign
        campaign_vec[tech_index[tid]] = 1.0

    # campaign vector as the last row of the matrix
    matrix.append(campaign_vec)
    matrix = np.array(matrix)

    # TF-IDF transform
    # (Replaces binary counts with weights that depend on the technique frequency. More common techniques have smaller weights.)
    transformer = TfidfTransformer()
    tfidf_matrix = transformer.fit_transform(matrix).toarray()
    # print("tfidf_matrix: ", tfidf_matrix)

    # last row = campaign
    campaign_vector = tfidf_matrix[-1]
    attributed_groups = set(campaign.groups.values_list("name", flat=True))
    result = []
    # cosine similarity between groups and selected campaign
    for i, group in enumerate(group_list):
        group_vector = tfidf_matrix[i]
        if (np.linalg.norm(campaign_vector) == 0 or np.linalg.norm(group_vector) == 0):
            similarity = 0.0
        else:
            similarity = float(np.dot(campaign_vector, group_vector) / (np.linalg.norm(campaign_vector) * np.linalg.norm(group_vector)))

        result.append(
            {
                "group_id": group.id,
                "group_name": group.name,
                "similarity_score": round(similarity, 3),
                "is_attributed": group.name in attributed_groups,
            }
        )

    return result


def compute_campaign_group_similarity_all(campaign, groups):

    cosine_res = compute_campaign_group_similarity(campaign, groups)

    tfidf_res = compute_campaign_group_similarity_tfidf(campaign, groups)

    # map by group_id
    cosine_map = {r["group_id"]: r for r in cosine_res}
    tfidf_map = {r["group_id"]: r for r in tfidf_res}

    result = []

    for gid, group in zip(cosine_map.keys(), groups):
        result.append(
            {
                "group_id": gid,
                "group_name": cosine_map[gid]["group_name"],
                "group_description": clean_entity_description(group.description),
                "cosine": cosine_map[gid]["similarity_score"],
                "tfidf": tfidf_map[gid]["similarity_score"],
                "is_attributed": cosine_map[gid]["is_attributed"],
            }
        )

    return result