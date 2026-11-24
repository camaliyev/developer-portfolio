from django.db import models
from django.db.models.functions import Lower

from .validators import IMAGE_VALIDATORS, PDF_VALIDATORS


class DeveloperProfile(models.Model):
    """Site owner's profile. The site uses a single row (see `get_active`)."""

    full_name = models.CharField(max_length=120)
    preferred_name = models.CharField(
        max_length=60, blank=True, help_text="Name you go by professionally, e.g. Cameron."
    )
    title = models.CharField("professional title", max_length=120)
    location = models.CharField(max_length=120)
    summary = models.TextField(
        "hero introduction", help_text="Short introduction shown in the hero section."
    )
    about_text = models.TextField(
        help_text="About section. Separate paragraphs with a blank line."
    )
    focus_areas = models.TextField(
        blank=True,
        help_text='About section highlights, one per line as "Title: description".',
    )
    resume_summary = models.TextField(
        "resume professional summary",
        blank=True,
        help_text="Professional summary on the resume page. Separate paragraphs with a blank line.",
    )
    professional_development = models.TextField(
        blank=True, help_text="Resume: one item per line."
    )
    education = models.TextField(
        blank=True,
        help_text="Resume: one entry per line. Leave empty to hide the Education section.",
    )
    languages = models.CharField(
        "spoken languages", max_length=200, blank=True, help_text="Comma-separated."
    )

    profile_image = models.ImageField(
        upload_to="profile/", blank=True, validators=IMAGE_VALIDATORS,
        help_text="Square JPG, PNG or WebP, up to 5 MB.",
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    github_url = models.URLField("GitHub URL", blank=True)
    linkedin_url = models.URLField("LinkedIn URL", blank=True)
    resume_pdf = models.FileField(
        "resume PDF", upload_to="resume/", blank=True, validators=PDF_VALIDATORS,
        help_text="PDF up to 10 MB. Replacing it updates the Download Resume button.",
    )

    is_available = models.BooleanField(
        "open to work", default=True, help_text="Shows the availability indicator in the hero."
    )
    availability_text = models.CharField(
        max_length=120, default="Open to junior backend roles", blank=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "developer profile"
        verbose_name_plural = "developer profile"

    def __str__(self):
        return self.full_name

    @classmethod
    def get_active(cls):
        return cls.objects.order_by("pk").first()

    @property
    def display_name(self):
        return self.full_name

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""

    @property
    def initials(self):
        return "".join(part[0] for part in self.full_name.split()[:2]).upper()

    @property
    def has_resume(self):
        return bool(self.resume_pdf) and self.resume_pdf.storage.exists(self.resume_pdf.name)

    @property
    def language_list(self):
        return [item.strip() for item in self.languages.split(",") if item.strip()]

    @property
    def professional_development_list(self):
        return _lines(self.professional_development)

    @property
    def focus_area_list(self):
        items = []
        for line in _lines(self.focus_areas):
            title, _, text = line.partition(":")
            items.append({"title": title.strip(), "text": text.strip()})
        return items

    @property
    def education_list(self):
        return _lines(self.education)


class SkillQuerySet(models.QuerySet):
    def in_category_order(self):
        """Order by the site's category order, then display order, then name."""
        whens = [
            models.When(category=value, then=models.Value(index))
            for index, value in enumerate(Skill.CATEGORY_ORDER)
        ]
        return self.annotate(
            _category_rank=models.Case(*whens, default=models.Value(99), output_field=models.IntegerField())
        ).order_by("_category_rank", "display_order", "name")


class Skill(models.Model):
    class Category(models.TextChoices):
        PROGRAMMING = "programming", "Programming"
        FRAMEWORKS = "frameworks", "Backend frameworks"
        DATABASES = "databases", "Databases & ORM"
        API = "api", "API development"
        TOOLS = "tools", "Development tools"
        FRONTEND = "frontend", "Frontend fundamentals"
        CONCEPTS = "concepts", "Backend concepts"

    # Order in which categories appear on the site.
    CATEGORY_ORDER = [c.value for c in Category]

    name = models.CharField(max_length=60)
    category = models.CharField(max_length=20, choices=Category.choices)
    display_order = models.PositiveSmallIntegerField(default=0)
    icon = models.CharField(
        max_length=40, blank=True,
        help_text="Optional short label or icon identifier shown next to the skill.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive skills are hidden from the Skills section but can still tag projects.",
    )

    objects = SkillQuerySet.as_manager()

    class Meta:
        ordering = ["category", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="unique_skill_name_ci"),
        ]

    def __str__(self):
        return self.name


def _lines(text: str) -> list[str]:
    return [line.strip().lstrip("-•* ").strip() for line in text.splitlines() if line.strip()]
