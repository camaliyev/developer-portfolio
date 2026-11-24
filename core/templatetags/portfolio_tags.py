from django import template
from django.utils.html import format_html_join

register = template.Library()


@register.filter
def paragraphs(text):
    """Split text on blank lines into escaped <p> elements."""
    if not text:
        return ""
    parts = [(" ".join(p.split()),) for p in str(text).split("\n\n") if p.strip()]
    return format_html_join("\n", "<p>{}</p>", parts)
