from django.contrib.auth import get_user_model
from portfolio.models import Holding  # adjust import to your actual app/model
from ..models import KeywordMatch

User = get_user_model()

def keyword_prefilter(articles):
    """Cheap pass: does the holding's company name or ticker appear in title/content?"""
    # Pull distinct holdings once, not per-article
    holdings = Holding.objects.select_related("user").all()
    matches = []
    for article in articles:
        haystack = f"{article.title} {article.raw_content}".lower()
        for holding in holdings:
            candidates = {holding.company_name.lower(), holding.ticker.lower()}
            hit = next((kw for kw in candidates if kw and kw in haystack), None)
            if hit:
                km, created = KeywordMatch.objects.get_or_create(
                    article=article, holding=holding, defaults={"matched_keyword": hit}
                )
                if created:
                    matches.append(km)
    return matches