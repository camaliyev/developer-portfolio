from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import DeveloperProfile, Skill
from projects.models import Project


def make_project(**kwargs):
    data = dict(
        title="StockFlow — Inventory & Order Management System",
        slug="stockflow",
        short_description="Inventory app.",
        full_description="Overview text.",
        key_features="Feature one\nFeature two\n\n- Feature three",
        is_published=True,
    )
    data.update(kwargs)
    return Project.objects.create(**data)


class ProjectModelTests(TestCase):
    def test_str_and_absolute_url(self):
        project = make_project()
        self.assertEqual(str(project), project.title)
        self.assertEqual(project.get_absolute_url(), "/projects/stockflow/")

    def test_name_and_subtitle_split_on_em_dash(self):
        project = make_project()
        self.assertEqual(project.name, "StockFlow")
        self.assertEqual(project.subtitle, "Inventory & Order Management System")
        plain = make_project(title="Plain", slug="plain")
        self.assertEqual(plain.name, "Plain")
        self.assertEqual(plain.subtitle, "")

    def test_slug_generated_when_blank(self):
        project = make_project(title="My New Project", slug="")
        self.assertEqual(project.slug, "my-new-project")

    def test_feature_list_strips_bullets_and_blank_lines(self):
        self.assertEqual(make_project().feature_list, ["Feature one", "Feature two", "Feature three"])

    def test_resume_highlights_fall_back_to_features(self):
        project = make_project()
        self.assertEqual(project.resume_highlight_list, project.feature_list)
        project.resume_highlights = "Custom bullet"
        self.assertEqual(project.resume_highlight_list, ["Custom bullet"])

    def test_challenge_list_extracts_titles(self):
        project = make_project(challenges="Short title. Body text here.\n\nNo title paragraph without period")
        self.assertEqual(project.challenge_list[0], {"title": "Short title", "body": "Body text here."})
        self.assertEqual(project.challenge_list[1]["title"], "")

    def test_unpublished_project_cannot_be_featured(self):
        project = make_project(is_published=False, is_featured=True)
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_published_queryset(self):
        make_project()
        make_project(slug="draft", title="Draft", is_published=False)
        self.assertEqual(list(Project.objects.published().values_list("slug", flat=True)), ["stockflow"])

    def test_technologies_many_to_many(self):
        django = Skill.objects.create(name="Django", category=Skill.Category.FRAMEWORKS)
        project = make_project()
        project.technologies.add(django)
        self.assertEqual(list(django.projects.all()), [project])


class ProjectViewTests(TestCase):
    def setUp(self):
        DeveloperProfile.objects.create(
            full_name="Kamran Aliyev", title="Python Backend Developer", location="New York City, NY",
            summary="s", about_text="a",
        )
        self.published = make_project()
        self.draft = make_project(slug="secret-draft", title="Secret Draft", is_published=False)

    def test_list_shows_only_published(self):
        response = self.client.get(reverse("projects:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "StockFlow")
        self.assertNotContains(response, "Secret Draft")

    def test_home_shows_only_published(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "StockFlow")
        self.assertNotContains(response, "Secret Draft")

    def test_detail_page_renders_case_study(self):
        response = self.client.get(self.published.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/detail.html")
        self.assertContains(response, "Overview text.")
        self.assertContains(response, "Feature two")
        self.assertContains(response, "<title>StockFlow")

    def test_unpublished_detail_returns_404(self):
        response = self.client.get(reverse("projects:detail", args=["secret-draft"]))
        self.assertEqual(response.status_code, 404)

    def test_missing_detail_returns_404(self):
        self.assertEqual(self.client.get("/projects/nope/").status_code, 404)

    def test_repo_and_demo_buttons_only_when_urls_exist(self):
        response = self.client.get(self.published.get_absolute_url())
        self.assertNotContains(response, "View repository")
        self.assertNotContains(response, "Live demo")
        self.published.github_url = "https://github.com/example/stockflow"
        self.published.demo_url = "https://stockflow.example.com"
        self.published.save()
        response = self.client.get(self.published.get_absolute_url())
        self.assertContains(response, "https://github.com/example/stockflow")
        self.assertContains(response, "https://stockflow.example.com")

    def test_content_is_autoescaped(self):
        self.published.full_description = "<script>alert(1)</script>"
        self.published.save()
        response = self.client.get(self.published.get_absolute_url())
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")
