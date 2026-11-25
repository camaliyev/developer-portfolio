import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from core.models import DeveloperProfile, Skill
from core.validators import validate_pdf_signature
from projects.models import Project

MEDIA_ROOT = tempfile.mkdtemp()


def make_profile(**kwargs):
    data = dict(
        full_name="Kamran Aliyev",
        preferred_name="Cameron",
        title="Python Backend Developer",
        location="New York City, NY",
        summary="I build backend applications.",
        about_text="About paragraph one.\n\nAbout paragraph two.",
    )
    data.update(kwargs)
    return DeveloperProfile.objects.create(**data)


class HomePageTests(TestCase):
    def setUp(self):
        self.profile = make_profile()
        Skill.objects.create(name="Django", category=Skill.Category.FRAMEWORKS)

    def test_homepage_renders_profile_and_skills(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "Kamran Aliyev")
        self.assertContains(response, "Python Backend Developer")
        self.assertContains(response, "Django")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_homepage_has_seo_metadata(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, '<meta name="description"')
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, "favicon.svg")

    def test_inactive_skills_are_hidden(self):
        Skill.objects.create(name="HiddenSkill", category=Skill.Category.TOOLS, is_active=False)
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "HiddenSkill")

    def test_social_links_hidden_when_not_configured(self):
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "GitHub profile")
        self.assertNotContains(response, "LinkedIn profile")

    def test_social_links_shown_when_configured(self):
        self.profile.github_url = "https://github.com/example"
        self.profile.save()
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "https://github.com/example")

    def test_hero_contact_links(self):
        self.profile.email = "aliyevcameron@gmail.com"
        self.profile.github_url = "https://github.com/camaliyev"
        self.profile.linkedin_url = "https://www.linkedin.com/in/kamran-aliyev-b7a6a6323/"
        self.profile.phone = "555-0100"
        self.profile.save()
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, 'class="hero__links"')
        self.assertContains(response, 'href="mailto:aliyevcameron@gmail.com"')
        self.assertContains(
            response,
            'href="https://github.com/camaliyev" target="_blank" rel="noopener noreferrer"',
        )
        self.assertContains(
            response,
            'href="https://www.linkedin.com/in/kamran-aliyev-b7a6a6323/" target="_blank" rel="noopener noreferrer"',
        )
        hero = response.content.decode().split('class="hero__links"')[1].split("</ul>")[0]
        self.assertNotIn("555-0100", hero)
        self.assertNotIn("tel:", hero)

    def test_hero_contact_links_hidden_when_empty(self):
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, 'class="hero__links"')

    def test_availability_indicator_toggle(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "status-pill")
        self.profile.is_available = False
        self.profile.save()
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "status-pill")

    def test_homepage_without_profile_does_not_crash(self):
        DeveloperProfile.objects.all().delete()
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seed_portfolio")

    def test_homepage_query_count_is_bounded(self):
        skills = list(Skill.objects.all())
        for i in range(5):
            p = Project.objects.create(
                title=f"P{i}", slug=f"p{i}", short_description="x", full_description="x",
                key_features="a", is_published=True,
            )
            p.technologies.set(skills)
        # projects + prefetched technologies + skills + profile, regardless of project count
        with self.assertNumQueries(4):
            self.client.get(reverse("core:home"))


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ResumeTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.profile = make_profile(resume_summary="Resume summary text.", languages="English, Russian")

    def test_resume_page_renders(self):
        response = self.client.get(reverse("core:resume"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resume summary text.")
        self.assertContains(response, "English, Russian")

    def test_education_hidden_when_empty(self):
        response = self.client.get(reverse("core:resume"))
        self.assertNotContains(response, "<h2>Education</h2>", html=False)

    def test_download_404_without_resume(self):
        response = self.client.get(reverse("core:resume_download"))
        self.assertEqual(response.status_code, 404)
        home = self.client.get(reverse("core:home"))
        self.assertNotContains(home, reverse("core:resume_download"))

    def test_download_serves_uploaded_pdf(self):
        self.profile.resume_pdf = SimpleUploadedFile(
            "cv.pdf", b"%PDF-1.4 test", content_type="application/pdf"
        )
        self.profile.save()
        response = self.client.get(reverse("core:resume_download"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test")
        home = self.client.get(reverse("core:home"))
        self.assertContains(home, reverse("core:resume_download"))

    def test_pdf_signature_validator_rejects_fake_pdf(self):
        fake = SimpleUploadedFile("cv.pdf", b"not a pdf", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_pdf_signature(fake)

    def test_profile_full_clean_rejects_wrong_extension(self):
        self.profile.resume_pdf = SimpleUploadedFile("cv.exe", b"%PDF-1.4")
        with self.assertRaises(ValidationError):
            self.profile.full_clean()


class SkillModelTests(TestCase):
    def test_skill_names_unique_case_insensitive(self):
        from django.db import IntegrityError

        Skill.objects.create(name="Python", category=Skill.Category.PROGRAMMING)
        with self.assertRaises(IntegrityError):
            Skill.objects.create(name="python", category=Skill.Category.PROGRAMMING)

    def test_in_category_order(self):
        Skill.objects.create(name="Git", category=Skill.Category.TOOLS)
        Skill.objects.create(name="Python", category=Skill.Category.PROGRAMMING)
        Skill.objects.create(name="Django", category=Skill.Category.FRAMEWORKS)
        names = list(Skill.objects.in_category_order().values_list("name", flat=True))
        self.assertEqual(names, ["Python", "Django", "Git"])


class SeedCommandTests(TestCase):
    def test_seed_creates_content(self):
        call_command("seed_portfolio", verbosity=0, stdout=open("/dev/null", "w"))
        self.assertEqual(DeveloperProfile.objects.count(), 1)
        self.assertEqual(Project.objects.published().count(), 3)
        self.assertTrue(Skill.objects.filter(name="FastAPI").exists())
        stockflow = Project.objects.get(slug="stockflow")
        self.assertEqual(
            set(stockflow.technologies.values_list("name", flat=True)),
            {"Python", "Django", "Django ORM", "SQLite"},
        )

    def test_seed_is_idempotent_and_preserves_edits(self):
        devnull = open("/dev/null", "w")
        call_command("seed_portfolio", stdout=devnull)
        profile = DeveloperProfile.objects.get()
        profile.summary = "Edited in admin"
        profile.save()
        Project.objects.filter(slug="stockflow").update(short_description="Edited")
        counts = (Skill.objects.count(), Project.objects.count())

        call_command("seed_portfolio", stdout=devnull)

        self.assertEqual(DeveloperProfile.objects.count(), 1)
        self.assertEqual((Skill.objects.count(), Project.objects.count()), counts)
        self.assertEqual(DeveloperProfile.objects.get().summary, "Edited in admin")
        self.assertEqual(Project.objects.get(slug="stockflow").short_description, "Edited")

    def test_seed_contact_details_match_provided_values(self):
        call_command("seed_portfolio", stdout=open("/dev/null", "w"))
        profile = DeveloperProfile.objects.get()
        self.assertEqual(profile.email, "aliyevcameron@gmail.com")
        self.assertEqual(profile.github_url, "https://github.com/camaliyev")
        self.assertEqual(profile.phone, "")
        self.assertEqual(profile.education, "")
        self.assertFalse(Project.objects.exclude(github_url="").exists())


class RoutingTests(TestCase):
    def test_url_names_resolve(self):
        self.assertEqual(resolve("/").view_name, "core:home")
        self.assertEqual(resolve("/resume/").view_name, "core:resume")
        self.assertEqual(resolve("/projects/").view_name, "projects:list")
        self.assertEqual(resolve("/projects/some-slug/").view_name, "projects:detail")
        self.assertEqual(resolve("/contact/").view_name, "contact:contact")

    def test_robots_and_sitemap(self):
        make_profile()
        Project.objects.create(
            title="Visible", slug="visible", short_description="x", full_description="x",
            key_features="a", is_published=True,
        )
        Project.objects.create(
            title="Draft", slug="draft", short_description="x", full_description="x", key_features="a",
        )
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertContains(robots, "Sitemap:")
        self.assertContains(robots, "Disallow: /admin/")
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        self.assertContains(sitemap, "/projects/visible/")
        self.assertNotContains(sitemap, "/projects/draft/")

    def test_custom_404_page(self):
        make_profile()
        response = self.client.get("/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page doesn", status_code=404)

    def test_admin_requires_login(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])


class ErrorPageTests(TestCase):
    def test_500_template_renders_without_context(self):
        from django.test import RequestFactory
        from django.views.defaults import server_error

        response = server_error(RequestFactory().get("/"))
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Something went wrong", response.content)
