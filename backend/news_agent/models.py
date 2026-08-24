from django.db import models
from django.conf import settings


class NewsArticle(models.Model):
    """Raw article fetched from a news API — deduped by URL."""
    source_name = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    url = models.URLField(unique=True)
    published_at = models.DateTimeField()
    raw_content = models.TextField(blank=True)  # snippet/description from API
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["published_at"])]


class KeywordMatch(models.Model):
    """Article passed the keyword pre-filter against a specific holding."""
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE, related_name="keyword_matches")
    # link to whatever your Holdings model is called, e.g. Instrument/Stock
    holding = models.ForeignKey("portfolio.Holding", on_delete=models.CASCADE)
    matched_keyword = models.CharField(max_length=100)  # e.g. company name, ticker
    checked_by_llm = models.BooleanField(default=False)

    class Meta:
        unique_together = ("article", "holding")


class NewsAlert(models.Model):
    """LLM confirmed this article is actually relevant — this is what gets notified."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="news_alerts")
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE)
    holding = models.ForeignKey("portfolio.Holding", on_delete=models.CASCADE)
    llm_summary = models.TextField()
    llm_relevance_reason = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "article", "holding")