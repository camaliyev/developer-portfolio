from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.models import Skill, _lines
from core.validators import IMAGE_VALIDATORS


class PublishedProjectQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def with_technologies(self):
        return self.prefetch_related(
            models.Prefetch("technologies", queryset=Skill.objects.in_category_order())
        )


class Project(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    short_description = models.CharField(
        max_length=300, help_text="One or two sentences for project cards and meta descriptions."
    )
    full_description = models.TextField(
        "overview", help_text="Project overview. Separate paragraphs with a blank line."
    )
    problem_statement = models.TextField(blank=True)
    architecture = models.TextField(
        "technical architecture", blank=True, help_text="Separate paragraphs with a blank line."
    )
    database_design = models.TextField(blank=True, help_text="Separate paragraphs with a blank line.")
    key_features = models.TextField(help_text="One feature per line.")
    challenges = models.TextField(
        "technical challenges", blank=True, help_text="One challenge per paragraph (blank line between)."
    )
    setup_instructions = models.TextField(
        blank=True, help_text="Shell commands shown as a code block. Leave empty to hide."
    )
    resume_highlights = models.TextField(
        blank=True, help_text="Resume bullet points, one per line. Falls back to key features."
    )

    image = models.ImageField(
        "cover image", upload_to="projects/", blank=True, validators=IMAGE_VALIDATORS,
        help_text="16:10 screenshot, JPG/PNG/WebP up to 5 MB.",
    )
    github_url = models.URLField("GitHub repository URL", blank=True)
    demo_url = models.URLField("live demo URL", blank=True)
    technologies = models.ManyToManyField(Skill, related_name="projects", blank=True)

    is_featured = models.BooleanField("featured", default=False)
    is_published = models.BooleanField("published", default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PublishedProjectQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "-created_at"]
        indexes = [models.Index(fields=["is_published", "display_order"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:160]
        super().save(*args, **kwargs)

    def clean(self):
        if self.is_featured and not self.is_published:
            raise ValidationError({"is_featured": "Only published projects can be featured."})

    def get_absolute_url(self):
        return reverse("projects:detail", kwargs={"slug": self.slug})

    @property
    def name(self):
        """Title before the em dash, e.g. 'StockFlow'."""
        return self.title.split(" — ")[0].strip()

    @property
    def subtitle(self):
        parts = self.title.split(" — ", 1)
        return parts[1].strip() if len(parts) == 2 else ""

    @property
    def feature_list(self):
        return _lines(self.key_features)

    @property
    def resume_highlight_list(self):
        return _lines(self.resume_highlights) or self.feature_list

    @property
    def challenge_list(self):
        """Paragraphs as {"title", "body"}; a short first sentence becomes the title."""
        items = []
        for para in (p.strip() for p in self.challenges.split("\n\n")):
            if not para:
                continue
            first, sep, rest = para.partition(". ")
            if sep and len(first) <= 60 and rest:
                items.append({"title": first, "body": rest})
            else:
                items.append({"title": "", "body": para})
        return items


class ProjectScreenshot(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="screenshots")
    image = models.ImageField(upload_to="projects/screenshots/", validators=IMAGE_VALIDATORS)
    caption = models.CharField(max_length=200, blank=True)
    alt_text = models.CharField(
        max_length=200, help_text="Describe what the screenshot shows, for screen readers."
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "pk"]

    def __str__(self):
        return self.caption or f"Screenshot for {self.project}"
