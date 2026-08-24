from investments.models import Holding
from ..models import KeywordMatch


def keyword_prefilter(articles):
    """Cheap pass: does the holding's asset name or symbol appear in title/content?"""
    holdings = Holding.objects.select_related("asset", "owner").all()
    matches = []
    for article in articles:
        haystack = f"{article.title} {article.raw_content}".lower()
        for holding in holdings:
            asset = holding.asset
            candidates = {c.lower() for c in (asset.name, asset.symbol) if c}
            hit = next((kw for kw in candidates if kw in haystack), None)
            if hit:
                km, created = KeywordMatch.objects.get_or_create(
                    article=article, holding=holding, defaults={"matched_keyword": hit}
                )
                if created:
                    matches.append(km)
    return matches