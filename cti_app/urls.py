from django.urls import path
from . import views

urlpatterns = [
    # path("ask/", ask),
    path("campaigns/", views.campaign_list, name="campaign-list"),
    path("campaigns/<int:campaign_id>/", views.campaign_detail, name="campaign-detail"),
    path("campaigns/<int:campaign_id>/techniques/", views.campaign_techniques, name="campaign-techniques"),
    path("campaigns/<int:campaign_id>/summary/", views.campaign_summary, name="campaign-summary"),
    path("campaigns/<int:campaign_id>/faqs/", views.campaign_faqs, name="campaign-faqs"),
    path("campaigns/<int:campaign_id>/faqs/", views.campaign_faqs),
    path("campaigns/<int:campaign_id>/faqs/<int:faq_id>/", views.delete_campaign_faq),
    path(
        "campaigns/<int:campaign_id>/attack-example/",
        views.campaign_attack_example,
        name="campaign-attack-example",
    ),
    path("campaigns/<int:campaign_id>/chatbot/", views.chatbot_query, name="chatbot-query"),
    path("campaigns/<int:campaign_id>/chatbot/attack-story/", views.chatbot_query_story, name="chatbot-query-story"),
    path(
        "campaigns/<int:campaign_id>/technique_visualization-data/",
        views.campaign_technique_visualization_data,
        name="campaign_technique_visualization_data"
    ),
    path(
        "campaigns/<int:campaign_id>/tactic-technique-count/",
        views.campaign_tactic_technique_count,
        name="campaign_tactic_technique_count"
    ),
    path(
        "campaigns/<int:campaign_id>/platform-technique-count/",
        views.campaign_platform_technique_count,
        name="campaign_platform_technique_count"
    ),
    path(
        "campaigns/<int:campaign_id>/group-similarity/",
        views.campaign_group_similarity,
        name="campaign_group_similarity"
    ),
]
