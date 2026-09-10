from django.core.management import BaseCommand
from sklearn.metrics import roc_auc_score
from sklearn.manifold import TSNE
import plotly.express as px
import numpy as np
import pandas as pd

from cti_app.management.commands.update_campaign_groups_similarity_scores import get_model
from cti_app.models import Campaign, Group, CampaignGroupSimilarity
from cti_app.utils import compute_campaign_group_similarity, compute_campaign_group_similarity_tfidf

USE_DB_SCORES = True # if scores are already saved into the DB, use them to evaluate the real output
K = 5  # Top-k for Recall (five chosen because more than five attributed groups is very unlikely)

def evaluate_scores(score_list, k=K):
    """
    Generic evaluation helper
    """

    if not score_list:
        return None

    group_similarity_scores = [(name, score) for name, score, _ in score_list]
    y_true = [1 if is_attr else 0 for _, _, is_attr in score_list]

    # return none if there aren't any attributed groups that can be taken as ground truth
    if len(set(y_true)) < 2:
        return None

    # sort by score descending
    group_similarity_scores.sort(key=lambda x: x[1], reverse=True)

    top_k = [name for name, _ in group_similarity_scores[:k]]

    attributed = {name for name, _, is_attr in score_list if is_attr}

    if not attributed:
        return None

    # recall@k
    attributed_in_top_k = sum(1 for name in top_k if name in attributed)
    recall_at_k = attributed_in_top_k / len(attributed)

    # auc
    y_score = [score for _, score in group_similarity_scores]
    auc = roc_auc_score(y_true, y_score)

    return {
        "auc": auc,
        "recall_at_k": recall_at_k,
    }


def evaluate_campaign_from_db(campaign, k=K):
    """
    Evaluate the graph embeddings results for a single campaign using the generated similarity scores
    from CampaignGroupSimilarity.

    Metrics:
    AUC: Measures overall ranking quality
    Recall@k: Measures how many of the true attributed groups appear within the top-k most similar groups
    """

    qs = CampaignGroupSimilarity.objects.filter(
        campaign=campaign
    ).select_related("group")

    if not qs.exists():
        return None

    score_list = []

    for obj in qs:
        score_list.append(
            (
                obj.group.name,
                obj.score,
                obj.is_attributed,
            )
        )

    return evaluate_scores(score_list, k)


def evaluate_campaign(campaign, k=K):
    """
    Evaluate the graph embeddings results for a single campaign:
    - AUC: Measures overall ranking quality
    - Recall: Measures how many of the true attributed groups appear within the top-k most similar groups
    """
    model, id_index = get_model()
    campaign_id = id_index.get(("Campaign", campaign.name))
    if campaign_id is None or campaign_id not in model.wv:
        return None

    attributed = set(campaign.groups.values_list("name", flat=True))
    if not attributed:
        return None

    # get calculated similarity scores between campaign and all groups
    sims = []
    for g in Group.objects.all():

        gid = id_index.get(("Group", g.name))
        if gid is None or gid not in model.wv:
            continue
        sim = model.wv.similarity(campaign_id, gid)
        sims.append(
            (
                g.name,
                sim,
                g.name in attributed,
            )
        )

    return evaluate_scores(sims, k)


def evaluate_campaign_cosine(campaign, k=K):

    groups = Group.objects.all()

    res = compute_campaign_group_similarity(campaign, groups)

    score_list = [
        (
            r["group_name"],
            r["similarity_score"],
            r["is_attributed"],
        )
        for r in res
    ]

    return evaluate_scores(score_list, k)


def evaluate_campaign_tfidf(campaign, k=K):

    groups = Group.objects.all()

    res = compute_campaign_group_similarity_tfidf(campaign, groups)

    score_list = [
        (
            r["group_name"],
            r["similarity_score"],
            r["is_attributed"],
        )
        for r in res
    ]

    return evaluate_scores(score_list, k)


def visualize_embeddings(model, id_index):
    """
    Create a 2D t-SNE plot of campaign and group embeddings
    """
    embedding_vectors = []
    labels = []
    node_types = []

    color_map = {
        "Campaign": "red",
        "Group": "green",
        "Technique": "blue",
        "Software": "yellow",
    }

    for (label, name), node_id in list(id_index.items()):
        if node_id not in model.wv:
            continue
        embedding_vectors.append(model.wv[node_id])
        labels.append(name)
        node_types.append(label)

    if not embedding_vectors:
        print("No embeddings to visualize.")
        return

    vectors_array = np.array(embedding_vectors)

    # reduce the multidimensional embedding vectors to 2D for visualization
    # (t-SNE used because good at preserving local structures which is needed for cluster identification)
    tsne = TSNE(n_components=2, random_state=42)
    X_embedded = tsne.fit_transform(vectors_array)
    print(X_embedded)

    # Create DataFrame for Plotly
    df = pd.DataFrame({
        "x": X_embedded[:, 0],
        "y": X_embedded[:, 1],
        "label": labels,
        "type": node_types,
    })

    # Interactive scatter plot
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="type",          # adds a color legend
        hover_name="label",    # show node name on hover
        color_discrete_map=color_map,
    )

    fig.update_traces(marker=dict(size=8, opacity=0.7))

    # add labels to each point
    fig.add_scatter(
        x=df["x"],
        y=df["y"],
        mode="text",
        text=df["label"],
        textposition="top center",
        textfont=dict(size=10),
        name="Labels",
        visible=False,  # start hidden (activate with show label button)
        showlegend=False,
    )

    # add buttons to activate labels
    num_traces = len(fig.data)

    # last trace = labels
    label_trace_index = num_traces - 1
    visible_with_labels = [True] * num_traces
    visible_without_labels = [True] * num_traces
    visible_without_labels[label_trace_index] = False

    fig.update_layout(
        title="t-SNE of Campaign and Group Embeddings",
        updatemenus=[
            dict(
                type="buttons",
                buttons=[
                    dict(
                        label="Hide labels",
                        method="update",
                        args=[{"visible": visible_without_labels}],
                    ),
                    dict(
                        label="Show labels",
                        method="update",
                        args=[{"visible": visible_with_labels}],
                    ),
                ],
            )
        ],
    )
    fig.show()


class Command(BaseCommand):
    help = "Evaluate campaign-group embeddings: AUC, Precision@k, Recall@k and t-SNE visualization"

    def handle(self, *args, **options):
        scores_embedding_auc = []
        scores_embedding_recall = []
        scores_cos_auc = []
        scores_cos_recall = []
        scores_tfidf_auc = []
        scores_tfidf_recall = []

        for c in Campaign.objects.all():

            print(f"Evaluating {c.name}")
            # DB / Embeddings
            if USE_DB_SCORES:
                result = evaluate_campaign_from_db(c, k=K)
            else:
                result = evaluate_campaign(c, k=K)

            if result is not None:
                print(
                    f"AUC: {result['auc']:.3f}, "
                    f"Recall@{K}: {result['recall_at_k']:.3f}"
                )
                scores_embedding_auc.append(result['auc'])
                scores_embedding_recall.append(result['recall_at_k'])

            # Cosine similarity
            cos = evaluate_campaign_cosine(c, k=K)

            if cos is not None:
                scores_cos_auc.append(cos["auc"])
                scores_cos_recall.append(cos["recall_at_k"])

            # TFIDF similarity
            tf = evaluate_campaign_tfidf(c, k=K)

            if tf is not None:
                scores_tfidf_auc.append(tf["auc"])
                scores_tfidf_recall.append(tf["recall_at_k"])

        print("\n=== Mean Scores ===")

        if scores_embedding_auc:
            print(f"Mean Embeddings AUC: {np.mean(scores_embedding_auc):.3f}")
            print(f"Mean Embeddings Recall@{K}: {np.mean(scores_embedding_recall):.3f}")

        if scores_cos_auc:
            print(f"Mean Cosine AUC: {np.mean(scores_cos_auc):.3f}")
            print(f"Mean Cosine Recall@{K}: {np.mean(scores_cos_recall):.3f}")

        if scores_tfidf_auc:
            print(f"Mean TFIDF AUC: {np.mean(scores_tfidf_auc):.3f}")
            print(f"Mean TFIDF Recall@{K}: {np.mean(scores_tfidf_recall):.3f}")

        # Visualize embeddings
        model, id_index = get_model()
        visualize_embeddings(model, id_index)