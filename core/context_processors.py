from django.conf import settings

from .models import DeveloperProfile


def site_context(request):
    return {
        "profile": DeveloperProfile.get_active(),
        "site_url": settings.SITE_URL or request.build_absolute_uri("/").rstrip("/"),
    }
