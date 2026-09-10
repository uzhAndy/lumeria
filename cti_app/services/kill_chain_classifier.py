# cti_app/services/campaign_attack_flow/kill_chain_classifier.py

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from cti_app.models import CampaignTechnique
from cti_app.services.unified_kill_chain import KILL_CHAIN_MAPPING_ORDERED

UKC_ORDER = list(KILL_CHAIN_MAPPING_ORDERED.keys())

CONFIDENCE_THRESHOLD = 0.7

# Fine-tuned model for text classification, designed to identify the tactic associated with a given sentence.
# Helps determine which tactic a particular technique was likely employed for in a campaign.
MODEL_ID = "sarahwei/MITRE-tactic-bert-case-based"

_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
_model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
_model.eval()

_LABELS = _model.config.id2label

def _predict_tactics(text: str) -> dict:
    """
    Returns a dict {tactic: confidence}, sorted descending.
    """
    if not text.strip():
        return {}

    inputs = _tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True
    )

    with torch.no_grad():
        outputs = _model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)[0]

    predictions = {
        _LABELS[i]: float(probs[i])
        for i in range(len(probs))
    }

    return dict(sorted(predictions.items(), key=lambda x: x[1], reverse=True))


def _earliest_plausible_tactic(tactics):
    """
    Select earliest tactic in Unified Kill Chain order.
    """
    return sorted(tactics, key=lambda t: UKC_ORDER.index(t))[0]


def classify_campaign_technique(ct: CampaignTechnique):
    """
    Applies tactic + kill chain phase selection to a single CampaignTechnique.
    """

    possible_tactics = ct.technique.kill_chain_phases or []

    if not possible_tactics:
        return  # nothing to classify

    # Single tactic → use it in the campaign
    if len(possible_tactics) == 1:
        selected_tactic = possible_tactics[0]

    else:
        # Multiple possible tactics, try a finetuned BERT model to find the most fitting tactic for the technique usage in the campaign
        predictions = _predict_tactics(ct.usage_description)

        if predictions:
            top_tactic, confidence = next(iter(predictions.items()))
            top_tactic = top_tactic.strip().lower().replace(" ", "-")  # normalize for comparison

            # choose the found tactic for the technique if the confidence is high enough, else just choose the earliest tactic in the kill chain
            if (
                confidence >= CONFIDENCE_THRESHOLD
                and top_tactic in possible_tactics
            ):
                selected_tactic = top_tactic
                print("Selected tactic", top_tactic, confidence)
            else:
                selected_tactic = _earliest_plausible_tactic(possible_tactics)
        else:
            selected_tactic = _earliest_plausible_tactic(possible_tactics)

    ct.selected_kill_chain_phase = KILL_CHAIN_MAPPING_ORDERED[selected_tactic]
    ct.selected_tactic = selected_tactic
    ct.save(update_fields=["selected_kill_chain_phase", "selected_tactic"])


def classify_all_campaign_techniques():
    """
    Used to construct the attack example by selecting the most likely tactic
    under which the technique was applied in the campaign.
    A fine-tuned model evaluates all possible kill chain phases and chooses the
    best-matching tactic; if no tactic meets the confidence threshold, the
    first tactic is selected as a fallback.
    """
    queryset = CampaignTechnique.objects.select_related("technique").filter(
        selected_kill_chain_phase__isnull=True
    )

    for ct in queryset:
        classify_campaign_technique(ct)
