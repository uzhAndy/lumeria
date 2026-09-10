from rest_framework import serializers
from .models import Campaign, Technique, CampaignFAQ


class ParentTechniqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technique
        fields = ["id", "name"]


class TechniqueBasicSerializer(serializers.ModelSerializer):
    parent_technique = ParentTechniqueSerializer(read_only=True)

    class Meta:
        model = Technique
        fields = ["id", "name", "parent_technique"]

class CampaignDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ["id", "name", "last_seen"]


class CampaignWithTechniquesSerializer(serializers.ModelSerializer):
    techniques = TechniqueBasicSerializer(many=True, read_only=True)

    class Meta:
        model = Campaign
        fields = ["id", "name", "techniques"]

# for summary widget:
class CampaignSummarySerializer(serializers.Serializer):
    campaign_id = serializers.IntegerField()
    text = serializers.CharField()

class CampaignFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignFAQ
        fields = ['id', 'question', 'answer', 'is_ai_generated']
