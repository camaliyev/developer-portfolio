from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve

from core.sitemaps import ProjectSitemap, StaticViewSitemap
from core.views import robots_txt

admin.site.site_header = "Portfolio administration"
admin.site.site_title = "Portfolio admin"
admin.site.index_title = "Manage portfolio content"

sitemaps = {"static": StaticViewSitemap, "projects": ProjectSitemap}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("projects/", include("projects.urls")),
    path("contact/", include("contact.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("", include("core.urls")),
]

if settings.SERVE_MEDIA:
    # Uploaded media (profile photo, project screenshots). In production this
    # assumes a persistent disk; see README "Media storage".
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
