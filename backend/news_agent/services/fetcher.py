import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime
from ..models import NewsArticle

NEWS_API_URL = "https://newsapi.org/v2/everything"

def fetch_financial_news(query: str = "stock market OR NSE OR BSE OR mutual fund", page_size: int = 50):
    """Pull recent articles from NewsAPI. Returns list of created/existing NewsArticle objs."""
    resp = requests.get(
        NEWS_API_URL,
        params={
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": settings.NEWS_API_KEY,
        },
        timeout=15,
    )
    resp.raise_for_status()
    articles = []
    for item in resp.json().get("articles", []):
        obj, _ = NewsArticle.objects.get_or_create(
            url=item["url"],
            defaults={
                "source_name": item.get("source", {}).get("name", "unknown"),
                "title": item["title"] or "",
                "published_at": parse_datetime(item["publishedAt"]),
                "raw_content": item.get("description") or "",
            },
        )
        articles.append(obj)
    return articles