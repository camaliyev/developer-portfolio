from collections import OrderedDict

from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from contact.forms import ContactForm
from projects.models import Project

from .models import DeveloperProfile, Skill


def grouped_skills():
    """Active skills grouped by category, in the configured category order."""
    labels = dict(Skill.Category.choices)
    groups = OrderedDict((key, {"label": labels[key], "skills": []}) for key in Skill.CATEGORY_ORDER)
    for skill in Skill.objects.filter(is_active=True).order_by("display_order", "name"):
        groups[skill.category]["skills"].append(skill)
    return [dict(key=key, **group) for key, group in groups.items() if group["skills"]]


@require_GET
def home(request):
    projects = Project.objects.published().with_technologies()
    featured = [p for p in projects if p.is_featured] or list(projects)
    return render(
        request,
        "core/home.html",
        {
            "skill_groups": grouped_skills(),
            "projects": featured,
            "form": ContactForm(),
        },
    )


@require_GET
def resume(request):
    return render(
        request,
        "core/resume.html",
        {
            "skill_groups": grouped_skills(),
            "projects": Project.objects.published().with_technologies(),
        },
    )


@require_GET
def resume_download(request):
    profile = DeveloperProfile.get_active()
    if profile is None or not profile.has_resume:
        raise Http404("No resume has been uploaded.")
    filename = f"{profile.full_name.replace(' ', '_')}_Resume.pdf"
    return FileResponse(
        profile.resume_pdf.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


@require_GET
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("django.contrib.sitemaps.views.sitemap"))
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /resume/download/",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
