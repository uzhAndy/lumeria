# only used for testing file with main (must be before importing any app models):
import django
import os
from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from cti_app.models import Campaign
from cti_app.services.agents import get_rag_agent
from cti_app.services.llm_tasks import invoke_agent

# For testing reasons:
def main():
    campaign = Campaign.objects.get(name="Cutting Edge")

    # summary = generate_campaign_summary(agent_simple, campaign)
    # prompt = "When was the campaign Cutting Edge last seen?"
    # prompt = "What techniques were used in the Cutting Edge?"
    # prompt = "What groups are behind the campaign Cutting Edge? Tell me more about them."
    # prompt = "What are mitigations for Protocol Tunneling?"
    # prompt = "How can you find out if you're affected by Protocol Tunneling?"
    #result = invoke_agent(agent, str(campaign.mitre_id), prompt)
    #prompt = "What are possible detections against techniques used in Cutting Edge?"
    # prompt = "Which ATT&CK tactics and techniques best characterize this campaign?"
    prefix = f"In the context of the campaign {campaign.name}: "
    prompt = "What techniques were used?"
    prompt = prefix + prompt
    print(prompt)
    AGENT = get_rag_agent()
    result = invoke_agent(AGENT, str(campaign.mitre_id), prompt)
    # Get the checkpointer from the agent
    memory = AGENT.checkpointer.get(            {
                "configurable": {
                    "thread_id": f"{campaign.mitre_id}",
                }
            })
    print(memory)
    # print("Answer:", result)
    print(result)


if __name__ == "__main__":
    main()