from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Campaign, CampaignFAQ, CampaignTechnique, Group, CampaignGroupSimilarity, Tactic, Domain
from .serializers import CampaignDropdownSerializer, CampaignWithTechniquesSerializer, CampaignSummarySerializer, \
    CampaignFAQSerializer
from .services.agents import get_rag_agent, get_plain_agent_with_memory, get_plain_agent_no_memory
from .services.llm_tasks import generate_campaign_answer_for_user_question, get_story_response
from .services.prompt_templates import QUERY_CLASSIFICATION_PROMPT
from .utils import compute_campaign_group_similarity_all, normalize_tactic_name, \
    clean_entity_description

from dotenv import load_dotenv
load_dotenv()

STORY_AGENT = get_plain_agent_with_memory()
MEMORYLESS_PLAIN_AGENT = get_plain_agent_no_memory()
# RAG_AGENT = get_rag_agent()

@api_view(['GET'])
def campaign_list(request):
    """
    Returns all campaigns ordered by their last seen date.
    Used to in the dropdown to select the campaign the user is interested in.
    """
    campaigns = Campaign.objects.all().order_by('-last_seen')
    serializer = CampaignDropdownSerializer(campaigns, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    serializer = CampaignDropdownSerializer(campaign)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
def campaign_techniques(request, campaign_id):
    """
    Return all techniques associated with a specific campaign and unified kill chain phase
    """
    try:
        campaign = (
            Campaign.objects
            .prefetch_related("techniques__parent_technique")
            .get(id=campaign_id)
        )
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = CampaignWithTechniquesSerializer(campaign)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def campaign_summary(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    if not campaign.summary:
        return Response(
            {"detail": "Summary not yet generated for this campaign."},
            status=status.HTTP_204_NO_CONTENT
        )

    serializer = CampaignSummarySerializer({
        "campaign_id": campaign.id,
        "text": campaign.summary
    })
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def campaign_attack_example(request, campaign_id):
    """
    Returns a list of all tactics and their associated techniques for a given campaign
    and unified kill chain phase.

    Tactics are ordered according to their logical progression, and techniques within
    each tactic are ordered so that parent techniques appear immediately before
    their child techniques.
    """

    # get tactics and techniques of a certain campaign and phase
    campaign = get_object_or_404(Campaign, id=campaign_id)

    selected_phase = request.query_params.get("phase")
    attack_example = campaign.attack_example.get("attack_example", [])
    if selected_phase:
        attack_example = [
            step for step in attack_example
            if step.get("phase") == selected_phase
        ]

    return Response({
        "campaign": campaign.name,
        "attack_example": attack_example
    })

def classify_query(question: str) -> bool:
    prompt = QUERY_CLASSIFICATION_PROMPT.format(
        question=question
    )

    result = MEMORYLESS_PLAIN_AGENT.invoke(
        {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    text = result["messages"][-1].content.strip()

    return text == "True"

@api_view(['POST'])
def chatbot_query(request, campaign_id):
    """
    Handles manual user questions
    """
    # Get the campaign
    campaign = get_object_or_404(Campaign, id=campaign_id)

    data = request.data
    user_message = data.get("message")
    reference = data.get("reference")

    if not user_message:
        return Response({"error": "No message provided"}, status=400)

    try:
        # if compatible with knowledge grapg: use knowledge graph and return results
        additional_kwargs = {"campaign_id": campaign.mitre_id}

        is_general = classify_query(user_message)
        print("Question is general: ", is_general)
        additional_kwargs["filter_pdf"] = "true" if not is_general else "false"

        if is_general:
            prompt_prefix = (
                "The following question is a general question about the MITRE ATT&CK framework: "
            )
        else:
            prompt_prefix = (
                f"The following question may pertain to the campaign named '{campaign.name}' "
                "or could be a general question about the MITRE ATT&CK framework: "
            )

        if reference:
            prompt_prefix = (
                f"The following question is about the {reference['type']} "
                f"\"{reference['label']}\". "
                f"It may be a general question or relate to its role within the campaign "
                f"\"{campaign.name}\". The question: "
            )
            additional_kwargs["reference"] = reference

        user_message = prompt_prefix + user_message
        response = get_rag_agent().invoke(
            {
                "messages": [{"role": "user", "content": user_message, "additional_kwargs": additional_kwargs}]
            },
            {
                "configurable": {
                    "thread_id": f"{campaign.mitre_id}",
                }
            }
        )

        # memory = RAG_AGENT.checkpointer.get({"configurable": {"thread_id": f"{campaign.mitre_id}",}}) # to check if the memory is working
        response = response["messages"][-1].content
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def chatbot_query_story(request, campaign_id):
    """
    Handles storytelling that is always automatically requested whenever a new tactic is shown
    """
    # Get the campaign
    data = request.data
    current_tactic = data.get("current_tactic")

    campaign = get_object_or_404(Campaign, id=campaign_id)
    try:
        response_text = get_story_response(STORY_AGENT, campaign, current_tactic)
        return Response({"response": response_text}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET', 'POST'])
def campaign_faqs(request, campaign_id):
    """
    GET: Returns all FAQ questions and answers for a specific campaign.
    POST: Add a new FAQ; answer is generated by the backend
    """

    if request.method == "GET":
        faqs = CampaignFAQ.objects.filter(campaign_id=campaign_id)
        serializer = CampaignFAQSerializer(faqs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "POST":
        question = request.data.get("question")

        if not question:
            return Response(
                {"detail": "Question is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign = get_object_or_404(Campaign, id=campaign_id)

        # Generate answer via LLM
        try:
            answer = generate_campaign_answer_for_user_question(
                agent=get_rag_agent(),
                campaign=campaign,
                question=question
            )
        except Exception:
            return Response(
                {"detail": "Failed to generate answer."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Save FAQ
        faq = CampaignFAQ.objects.create(
            campaign=campaign,
            question=question,
            answer=answer,
            is_ai_generated=False,
        )

        serializer = CampaignFAQSerializer(faq)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['DELETE'])
def delete_campaign_faq(request, campaign_id, faq_id):
    try:
        faq = CampaignFAQ.objects.get(id=faq_id, campaign_id=campaign_id)
    except CampaignFAQ.DoesNotExist:
        return Response(status=404)

    faq.delete()
    return Response(status=204)


@api_view(["POST"])
def campaign_technique_visualization_data(request, campaign_id):
    # Read parameters from POST body (JSON)
    show_mitigation = request.data.get("show_mitigation", True)
    show_tactic = request.data.get("show_tactic", False)
    show_usage = request.data.get("show_usage", False)
    order_by = request.data.get("order_by", "name")  # "name", "mitigation", "detection", "created_date"

    campaign = get_object_or_404(Campaign, id=campaign_id)

    data = []
    techniques = CampaignTechnique.objects.filter(
        campaign=campaign
    ).select_related("technique")
    for tech in techniques:
        usage_count = CampaignTechnique.objects.filter(
            technique=tech.technique
        ).values("campaign").distinct().count()

        data.append({
            "technique_name": tech.technique.name,
            "mitigation_count": tech.technique.mitigations.count(),
            "tactic_count": len(tech.technique.kill_chain_phases),
            "created_date": tech.technique.created_date.isoformat(),
            "usage_count": usage_count,
            "usage_summary": tech.usage_summary,
        })

    # Ordering
    if order_by == "mitigation":
        data.sort(key=lambda x: x["mitigation_count"], reverse=True)
    elif order_by == "tactic":
        data.sort(key=lambda x: x["tactic_count"], reverse=True)
    elif order_by == "created_date":
        data.sort(key=lambda x: x["created_date"] or "", reverse=True)
    elif order_by == "usage":
        data.sort(key=lambda x: x["usage_count"], reverse=True)
    else:
        data.sort(key=lambda x: x["technique_name"])

    total_campaigns = Campaign.objects.count()

    return Response({
        "show_mitigation": show_mitigation,
        "show_tactic": show_tactic,
        "show_usage": show_usage,
        "total_campaigns": total_campaigns,
        "techniques": data
    })


@api_view(["GET"])
def campaign_tactic_technique_count(request, campaign_id):
    """
    Returns a count of techniques per tactic for a given campaign.
    Used for the "Identify Most Targeted Tactics" visualization.
    Includes the tactic description for tooltips.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)

    # Fetch all techniques of the campaign
    techniques = CampaignTechnique.objects.filter(campaign=campaign).select_related("technique")
    tactic_counts = {}
    # Determine if campaign spans multiple domains
    campaign_domains = {ct.technique.domain for ct in techniques}
    multiple_domains = len(campaign_domains) > 1

    # Count techniques per tactic and add domain name if there are multiple domain in campaign
    for ct in techniques:
        for tactic in ct.technique.kill_chain_phases:
            tactic = normalize_tactic_name(tactic)
            key = f"{tactic}__{ct.technique.domain}"

            if key not in tactic_counts:
                try:
                    t_obj = Tactic.objects.get(
                        name__iexact=tactic,
                        domain=ct.technique.domain
                    )
                    description = clean_entity_description(t_obj.description)
                except Tactic.DoesNotExist:
                    description = ""

                if multiple_domains:
                    display_name = f"{tactic} {Domain(ct.technique.domain).label}"
                else:
                    display_name = tactic

                tactic_counts[key] = {
                    "count": 0,
                    "description": description,
                    "display": display_name,
                }

            tactic_counts[key]["count"] += 1

    data = [
        {"tactic": val["display"], "technique_count": val["count"], "description": val["description"]}
        for tactic, val in tactic_counts.items()
    ]

    # Sort descending by number of techniques
    data.sort(key=lambda x: x["technique_count"], reverse=True)

    return Response({
        "title": "Identify Most Targeted Tactics",
        "data": data
    })

@api_view(["GET"])
def campaign_platform_technique_count(request, campaign_id):
    """
    Returns a count of techniques per platform for a given campaign.
    Useful for the "Determine Platforms Targeted by Campaign" visualization.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)

    platform_counts = {}

    techniques = CampaignTechnique.objects.filter(campaign=campaign).select_related("technique")
    for ct in techniques:
        for platform in ct.technique.platforms:
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

    data = [{"platform": platform, "technique_count": count} for platform, count in platform_counts.items()]

    # Sort descending by number of techniques
    data.sort(key=lambda x: x["technique_count"], reverse=True)

    return Response({
        "title": "Determine Platforms Targeted by Campaign",
        "data": data
    })


@api_view(["GET"])
def campaign_group_similarity(request, campaign_id):
    """
    Returns similarity scores between a given campaign and all groups
    based on shared techniques using either the cosine similarity between techniques vectors or from the graph embeddings.
    For better understandability, cosine similarity only considers techniques.
    Why cosine similarity:
    - It measures the angle between vectors, focusing on pattern similarity
      rather than magnitude. This is important because groups typically
      accumulate many more techniques over time than short-lived campaigns.
    - It works well for sparse, high-dimensional technique vectors.
    """

    campaign = get_object_or_404(Campaign, id=campaign_id)
    groups = Group.objects.prefetch_related("techniques").all()
    attributed_groups = set(campaign.groups.values_list("name", flat=True))

    # determine which similarity type
    sim_type = request.GET.get("type", "cosine")  # default: cosine

    result = []

    if sim_type == "cosine":
        result = compute_campaign_group_similarity_all(campaign, groups)
        # sort by tfidf scores
        result.sort(key=lambda x: x.get("tfidf", 0), reverse=True)
    elif sim_type == "graph":
        # compute using graph embeddings stored in DB
        similarities = CampaignGroupSimilarity.objects.filter(campaign=campaign)
        for s in similarities:
            result.append({
                "group_id": s.group.id,
                "group_name": s.group.name,
                "graph": s.score,
                "is_attributed": s.is_attributed,
                "group_description": clean_entity_description(s.group.description),
            })
        result.sort(key=lambda x: x["graph"], reverse=True)

    if not result:
        return Response({
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "similar_groups": [],
            "campaign_groups": list(attributed_groups),
            "message": "This campaign has no associated techniques yet.",
        })

    return Response({
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "similar_groups": result,
        "campaign_groups": list(attributed_groups),
    })