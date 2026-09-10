from cti_app.models import CampaignTechnique
from cti_app.services.agent_builder import build_simple_agent
from cti_app.services.prompt_templates import SUMMARY_PROMPT, MITIGATION_PROMPT, \
    FAQ_PROMPT_QUESTION, FAQ_PROMPT_ANSWER, USAGE_DESCRIPTION_PROMPT


def build_campaign_relevant_content(campaign) -> str:
    lines = [
        "CAMPAIGN OVERVIEW",
        f"Name: {campaign.name}",
    ]

    if campaign.description:
        lines += ["\nDescription:", campaign.description]

    lines += ["\n---\n", "TECHNIQUES USED IN THIS CAMPAIGN"]

    campaign_techniques = (
        CampaignTechnique.objects
        .filter(campaign=campaign)
        .select_related("technique")
        .prefetch_related("technique__mitigations")
        .order_by("technique__name")
    )

    for ct in campaign_techniques:
        tech = ct.technique

        # Technique block
        lines.append(f"\n- {tech.name}\n")
        if ct.usage_summary:
            lines.append(f"  Usage: {ct.usage_summary}\n")

        # Mitigations
        # Get all mitigations for this technique
        mitigations = list(tech.mitigations.all())
        if mitigations:
            mitigation_line = ", ".join(mitigation.name for mitigation in mitigations)
        else:
            mitigation_line = "No mitigations in dataset"

        lines.append(f"  Mitigations for {tech.name}: {mitigation_line}")
    return " ".join(lines)


def generate_campaign_summary(agent, campaign_name: str, campaign_description: str, group_info: str) -> str:
    """
    Use the RAG agent and the C-level prompt to generate a campaign summary.
    """
    # Fill the prompt
    user_message = SUMMARY_PROMPT.format(campaign=campaign_name, campaign_description=campaign_description, group_info=group_info)

    # Invoke the agent
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })

    # Return the final content
    return result["messages"][-1].content

def generate_mitigation_summary(agent, mitigation_name: str, mitigation_description: str) -> str:
    """
    Use the RAG agent and the C-level prompt to generate a mitigation summary.
    """
    # Fill the prompt
    user_message = MITIGATION_PROMPT.format(mitigation=mitigation_name, mitigation_description=mitigation_description)

    # Invoke the agent
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })

    # Return the final content
    return result["messages"][-1].content

def generate_campaign_question(agent, campaign_name: str, relevant_content: str, existing_questions: str) -> str:
    user_message = FAQ_PROMPT_QUESTION.format(
        campaign_name=campaign_name,
        relevant_content=relevant_content,
        existing_questions=existing_questions,
    )

    # Invoke the agent
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })

    # Return the final content
    return result["messages"][-1].content

def generate_campaign_answer(agent, campaign_name: str, relevant_content: str, question: str) -> str:
    user_message = FAQ_PROMPT_ANSWER.format(
        campaign_name=campaign_name,
        relevant_content=relevant_content,
        question=question,
    )

    # Invoke the agent
    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })

    # Return the final content
    return result["messages"][-1].content

def simplify_usage_description(ct: CampaignTechnique, agent) -> str:
    """
    Generate a simplified, executive-friendly usage summary
    using the USAGE_DESCRIPTION_PROMPT.
    """

    user_message = USAGE_DESCRIPTION_PROMPT.format(
        campaign=ct.campaign.name,
        technique_name=ct.technique.name,
        usage_description=ct.usage_description,
    )

    result = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
    )

    simplified_description = result["messages"][-1].content.strip()
    return simplified_description


def generate_technique_usage_in_campaign_summaries():
    """
    Uses an LLM to generate concise, executive-friendly summaries of technique usage
    descriptions and saves them to the database for the attack example.
    """
    agent = build_simple_agent()

    # Only CampaignTechniques with a usage description but no summary yet to not generate unnecessary ones
    queryset = (
        CampaignTechnique.objects
        .select_related("campaign", "technique")
        .exclude(usage_description="")
        .filter(usage_summary="")
    )
    print(f"CampaignTechnique to process: {queryset.count()}")

    for ct in queryset:
        try:
            simplified = simplify_usage_description(ct, agent)
            print(simplified)

            ct.usage_summary = simplified
            ct.save(update_fields=["usage_summary"])

            # print(f"✔ Updated CampaignTechnique {ct.id}")

        except Exception as exc:
            print(f"Failed CampaignTechnique {ct.id}: {exc}")
