from django.contrib import admin
from django.utils.html import format_html

from .models import DeveloperProfile, Skill


@admin.register(DeveloperProfile)
class DeveloperProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "title", "location", "is_available", "resume_status", "updated_at")
    readonly_fields = ("photo_preview", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("full_name", "preferred_name", "title", "location")}),
        ("Availability", {"fields": ("is_available", "availability_text")}),
        ("Photo", {"fields": ("profile_image", "photo_preview")}),
        ("Introduction", {"fields": ("summary", "about_text", "focus_areas")}),
        ("Contact & links", {"fields": ("email", "phone", "github_url", "linkedin_url")}),
        (
            "Resume",
            {
                "fields": (
                    "resume_pdf",
                    "resume_summary",
                    "professional_development",
                    "education",
                    "languages",
                )
            },
        ),
        ("Metadata", {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        # The site shows a single profile.
        return not DeveloperProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Resume")
    def resume_status(self, obj):
        return "Uploaded" if obj.resume_pdf else "Not uploaded"

    @admin.display(description="Current photo")
    def photo_preview(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" alt="" style="width:96px;height:96px;object-fit:cover;border-radius:12px">',
                obj.profile_image.url,
            )
        return "No photo uploaded"


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "display_order", "is_active", "project_count")
    list_editable = ("display_order", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)
    ordering = ("category", "display_order", "name")

    def get_queryset(self, request):
        from django.db.models import Count

        return super().get_queryset(request).annotate(_project_count=Count("projects"))

    @admin.display(description="Projects", ordering="_project_count")
    def project_count(self, obj):
        return obj._project_count
