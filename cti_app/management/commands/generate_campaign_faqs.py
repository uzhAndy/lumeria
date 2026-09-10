from django.core.management.base import BaseCommand

from cti_app.models import Campaign, CampaignFAQ
from cti_app.services.llm_precomputed_tasks import generate_campaign_question, \
    generate_campaign_answer, build_campaign_relevant_content
from cti_app.services.agent_builder import build_simple_agent

AGENT = build_simple_agent()

class Command(BaseCommand):
    help = 'Generates and saves LLM faqs for all campaigns'

    def handle(self, *args, **options):
        # campaigns = Campaign.objects.all()
        campaigns = Campaign.objects.filter(faqs__isnull=True)
        self.stdout.write(f"Processing {campaigns.count()} campaigns...")

        for campaign in campaigns:
            self.stdout.write(f"Generating faq for: {campaign.name}")
            try:
                # Clear existing FAQs to avoid duplication
                campaign.faqs.all().delete()
                relevant_content = build_campaign_relevant_content(campaign) # generate relevant campaign content that should be used for creating and answering a question
                self.stdout.write(relevant_content)
                asked_questions: list[str] = []
                # generate five typical questions for the campaign and the corresponding answer with the help of LLM
                for _ in range(5):
                    # Format existing questions for PromptTemplate
                    existing_questions_prompt = (
                        "\n".join(f"- {q}" for q in asked_questions)
                        if asked_questions
                        else "None yet."
                    )
                    # Generate question
                    question = generate_campaign_question(
                        agent=AGENT,
                        campaign_name=campaign.name,
                        relevant_content=relevant_content,
                        existing_questions=existing_questions_prompt,
                    )

                    asked_questions.append(question)

                    # Generate answer
                    answer = generate_campaign_answer(
                        agent=AGENT,
                        campaign_name=campaign.name,
                        relevant_content=relevant_content,
                        question=question,
                    )

                    CampaignFAQ.objects.create(
                        campaign=campaign,
                        question=question,
                        answer=answer,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Successfully updated FAQ for {campaign.name}"))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed for {campaign.name}: {str(e)}")
                )
