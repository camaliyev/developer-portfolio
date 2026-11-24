from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Project


@require_GET
def project_list(request):
    projects = Project.objects.published().with_technologies()
    return render(request, "projects/list.html", {"projects": projects})


@require_GET
def project_detail(request, slug):
    project = get_object_or_404(
        Project.objects.published().with_technologies().prefetch_related("screenshots"),
        slug=slug,
    )
    others = Project.objects.published().with_technologies().exclude(pk=project.pk)[:2]
    return render(request, "projects/detail.html", {"project": project, "others": others})
