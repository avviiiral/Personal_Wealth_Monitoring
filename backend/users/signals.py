from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Role, UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Guarantee every Django User has exactly one UserProfile.

    - On creation: a profile is created. Users created with
      Django's `is_superuser=True` (e.g. via `createsuperuser`)
      automatically get the SUPERUSER role so the CLI-created
      superuser is never locked out of admin-only PWMS features.
    - On later saves: if `is_superuser` was toggled directly
      (e.g. from Django admin or the ORM), the role is kept in
      sync so the two concepts never disagree.
    """

    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                "role": Role.SUPERUSER if instance.is_superuser else Role.VIEWER,
            },
        )
        return

    profile = getattr(instance, "profile", None)

    if profile is None:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                "role": Role.SUPERUSER if instance.is_superuser else Role.VIEWER,
            },
        )
        return

    if instance.is_superuser and profile.role != Role.SUPERUSER:
        profile.role = Role.SUPERUSER
        profile.save(update_fields=["role", "updated_at"])
