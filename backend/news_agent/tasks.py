from celery import shared_task
from .services.fetcher import fetch_financial_news
from .services.matcher import keyword_prefilter
from .services.llm_relevance import evaluate_and_alert
from .services.notifier import send_pending_email_alerts

@shared_task
def run_news_pipeline():
    articles = fetch_financial_news()
    matches = keyword_prefilter(articles)
    evaluate_and_alert(matches)
    send_pending_email_alerts()