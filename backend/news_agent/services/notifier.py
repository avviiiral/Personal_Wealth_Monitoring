from django.core.mail import send_mail
from django.conf import settings
from ..models import NewsAlert

def send_pending_email_alerts():
    pending = NewsAlert.objects.filter(email_sent=False).select_related("user", "holding", "article")
    for alert in pending:
        send_mail(
            subject=f"News alert: {alert.holding.company_name}",
            message=(
                f"{alert.article.title}\n\n"
                f"{alert.llm_summary}\n\n"
                f"Read more: {alert.article.url}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[alert.user.email],
        )
        alert.email_sent = True
        alert.save(update_fields=["email_sent"])