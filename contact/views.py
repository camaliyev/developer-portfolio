import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ContactForm

logger = logging.getLogger(__name__)

SUCCESS_MESSAGE = "Thank you — your message was sent. I'll reply as soon as I can."


def client_ip(request) -> str:
    if getattr(settings, "CONTACT_TRUST_PROXY", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _rate_limit_key(ip: str) -> str:
    return f"contact-rate:{ip}"


def is_rate_limited(ip: str) -> bool:
    return cache.get(_rate_limit_key(ip), 0) >= settings.CONTACT_RATE_LIMIT


def record_submission(ip: str) -> None:
    key = _rate_limit_key(ip)
    if cache.add(key, 1, timeout=settings.CONTACT_RATE_WINDOW_SECONDS):
        return
    try:
        cache.incr(key)
    except ValueError:  # key expired between add() and incr()
        cache.set(key, 1, timeout=settings.CONTACT_RATE_WINDOW_SECONDS)


def notify_owner(message) -> None:
    """Email the site owner if notifications are configured. Never raises."""
    recipient = settings.CONTACT_NOTIFY_EMAIL
    if not recipient:
        return
    try:
        send_mail(
            subject=f"[Portfolio] {message.subject}",
            message=f"From: {message.name} <{message.email}>\n\n{message.message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001 - the message is already saved
        logger.exception("Contact notification email failed for message %s", message.pk)


@require_http_methods(["GET", "POST"])
def contact(request):
    if request.method == "GET":
        return render(request, "contact/contact.html", {"form": ContactForm()})

    ip = client_ip(request)
    if is_rate_limited(ip):
        form = ContactForm(request.POST)
        form.is_valid()
        form.add_error(None, "Too many messages were sent from your network. Please try again later.")
        return render(request, "contact/contact.html", {"form": form}, status=429)

    form = ContactForm(request.POST)
    if not form.is_valid():
        return render(request, "contact/contact.html", {"form": form}, status=400)

    record_submission(ip)
    if form.is_spam:
        # Respond as if successful so bots get no signal, but store nothing.
        logger.info("Contact submission discarded as spam from %s", ip)
    else:
        message = form.save(commit=False)
        message.ip_address = ip or None
        message.save()
        notify_owner(message)

    messages.success(request, SUCCESS_MESSAGE)
    return redirect(reverse("contact:contact") + "?sent=1")
