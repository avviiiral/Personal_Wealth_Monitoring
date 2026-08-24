import anthropic
from django.conf import settings
from ..models import NewsAlert

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

PROMPT_TEMPLATE = """You are screening a news article for relevance to a specific stock holding.

Holding: {company_name} ({ticker})
Article title: {title}
Article snippet: {snippet}

Respond ONLY in this exact format, nothing else:
RELEVANT: yes|no
REASON: <one short sentence>
SUMMARY: <2-3 sentence summary of what this means for the holding, if relevant; else "N/A">
"""

def evaluate_and_alert(keyword_matches):
    for km in keyword_matches:
        holding = km.holding
        asset = holding.asset
        article = km.article
        prompt = PROMPT_TEMPLATE.format(
            company_name=asset.name,
            ticker=asset.symbol or "N/A",
            title=article.title,
            snippet=article.raw_content[:800],
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text
        parsed = _parse(text)
        km.checked_by_llm = True
        km.save(update_fields=["checked_by_llm"])

        if parsed["relevant"]:
            NewsAlert.objects.get_or_create(
                user=holding.owner,
                article=article,
                holding=holding,
                defaults={
                    "llm_summary": parsed["summary"],
                    "llm_relevance_reason": parsed["reason"],
                },
            )

def _parse(text: str) -> dict:
    lines = {l.split(":", 1)[0].strip().upper(): l.split(":", 1)[1].strip()
             for l in text.strip().splitlines() if ":" in l}
    return {
        "relevant": lines.get("RELEVANT", "no").lower().startswith("y"),
        "reason": lines.get("REASON", ""),
        "summary": lines.get("SUMMARY", ""),
    }