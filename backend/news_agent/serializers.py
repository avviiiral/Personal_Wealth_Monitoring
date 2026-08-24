from rest_framework import serializers
from .models import NewsAlert


class NewsAlertSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source="article.title", read_only=True)
    article_url = serializers.URLField(source="article.url", read_only=True)
    holding_name = serializers.CharField(source="holding.asset.name", read_only=True)

    class Meta:
        model = NewsAlert
        fields = [
            "id", "holding_name", "article_title", "article_url",
            "llm_summary", "llm_relevance_reason", "is_read", "created_at",
        ]
        read_only_fields = fields