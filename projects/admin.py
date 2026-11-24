from django.contrib import admin
from django.utils.html import format_html

from .models import Project, ProjectScreenshot


class ProjectScreenshotInline(admin.TabularInline):
    model = ProjectScreenshot
    extra = 1
    fields = ("image", "alt_text", "caption", "display_order")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "is_featured", "display_order", "has_repo", "updated_at")
    list_editable = ("is_published", "is_featured", "display_order")
    list_filter = ("is_published", "is_featured", "technologies")
    search_fields = ("title", "short_description", "full_description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("technologies",)
    readonly_fields = ("cover_preview", "created_at", "updated_at")
    inlines = [ProjectScreenshotInline]
    actions = ["publish", "unpublish"]
    fieldsets = (
        ("Publishing", {"fields": ("is_published", "is_featured", "display_order")}),
        ("Basics", {"fields": ("title", "slug", "short_description", "technologies")}),
        ("Links", {"fields": ("github_url", "demo_url")}),
        ("Cover", {"fields": ("image", "cover_preview")}),
        (
            "Case study",
            {
                "fields": (
                    "full_description",
                    "problem_statement",
                    "architecture",
                    "database_design",
                    "key_features",
                    "challenges",
                    "setup_instructions",
                )
            },
        ),
        ("Resume", {"fields": ("resume_highlights",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(boolean=True, description="Repo link")
    def has_repo(self, obj):
        return bool(obj.github_url)

    @admin.display(description="Current cover")
    def cover_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" alt="" style="max-width:320px;border-radius:8px">', obj.image.url)
        return "No cover image — the site shows a generated cover."

    @admin.action(description="Publish selected projects")
    def publish(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"Published {updated} project(s).")

    @admin.action(description="Unpublish selected projects (also removes featured)")
    def unpublish(self, request, queryset):
        updated = queryset.update(is_published=False, is_featured=False)
        self.message_user(request, f"Unpublished {updated} project(s).")
