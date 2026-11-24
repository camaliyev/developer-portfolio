import time
from unittest import mock

from django.core import mail, signing
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from contact.forms import TIMESTAMP_SALT, ContactForm
from contact.models import ContactMessage


def token(seconds_ago=10):
    return signing.dumps(time.time() - seconds_ago, salt=TIMESTAMP_SALT)


def valid_data(**overrides):
    data = {
        "name": "Jane Recruiter",
        "email": "jane@example.com",
        "subject": "Junior backend role",
        "message": "Hello Cameron, I would like to talk about a junior backend position.",
        "website": "",
        "form_token": token(),
    }
    data.update(overrides)
    return data


class ContactFormTests(TestCase):
    def test_valid_form(self):
        form = ContactForm(data=valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.is_spam)

    def test_required_fields(self):
        form = ContactForm(data={"form_token": token()})
        self.assertFalse(form.is_valid())
        for field in ("name", "email", "subject", "message"):
            self.assertIn(field, form.errors)

    def test_invalid_email(self):
        form = ContactForm(data=valid_data(email="not-an-email"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_short_message_rejected(self):
        form = ContactForm(data=valid_data(message="Too short"))
        self.assertFalse(form.is_valid())
        self.assertIn("message", form.errors)

    def test_too_many_links_rejected(self):
        form = ContactForm(data=valid_data(message="see https://a.com https://b.com https://c.com https://d.com now"))
        self.assertFalse(form.is_valid())

    def test_tampered_token_rejected(self):
        form = ContactForm(data=valid_data(form_token="bogus"))
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_honeypot_marks_spam(self):
        form = ContactForm(data=valid_data(website="http://spam.example"))
        self.assertTrue(form.is_valid())
        self.assertTrue(form.is_spam)

    def test_instant_submission_marks_spam(self):
        form = ContactForm(data=valid_data(form_token=token(seconds_ago=0)))
        self.assertTrue(form.is_valid())
        self.assertTrue(form.is_spam)

    def test_errors_are_linked_to_inputs(self):
        form = ContactForm(data=valid_data(email="bad"))
        form.is_valid()
        html = str(form["email"])
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="contact-email-error"', html)


class ContactViewTests(TestCase):
    url = reverse("contact:contact")

    def setUp(self):
        cache.clear()

    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'for="contact-email"')

    def test_successful_submission_saves_and_redirects(self):
        response = self.client.post(self.url, valid_data())
        self.assertRedirects(response, self.url + "?sent=1")
        self.assertEqual(ContactMessage.objects.count(), 1)
        message = ContactMessage.objects.get()
        self.assertEqual(message.email, "jane@example.com")
        self.assertFalse(message.is_read)
        self.assertEqual(message.ip_address, "127.0.0.1")

    def test_success_message_shown_after_redirect(self):
        response = self.client.post(self.url, valid_data(), follow=True)
        self.assertContains(response, "your message was sent")

    def test_invalid_submission_shows_errors_and_saves_nothing(self):
        response = self.client.post(self.url, valid_data(email="nope", message="short"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter a valid email address", status_code=400)
        self.assertContains(response, "at least 20 characters", status_code=400)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_spam_is_discarded_silently(self):
        response = self.client.post(self.url, valid_data(website="http://spam"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 0)

    @override_settings(CONTACT_RATE_LIMIT=2)
    def test_rate_limit(self):
        self.client.post(self.url, valid_data())
        self.client.post(self.url, valid_data())
        response = self.client.post(self.url, valid_data())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 2)

    def test_csrf_enforced(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, valid_data())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_messages_are_not_publicly_listed(self):
        ContactMessage.objects.create(name="A", email="a@example.com", subject="Private subject", message="x" * 30)
        for url in ("/", "/contact/", "/projects/", "/sitemap.xml"):
            self.assertNotContains(self.client.get(url), "Private subject")

    @override_settings(CONTACT_NOTIFY_EMAIL="owner@example.com")
    def test_notification_email_sent_when_configured(self):
        self.client.post(self.url, valid_data())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Junior backend role", mail.outbox[0].subject)

    def test_no_email_when_not_configured(self):
        self.client.post(self.url, valid_data())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(ContactMessage.objects.count(), 1)

    @override_settings(CONTACT_NOTIFY_EMAIL="owner@example.com")
    def test_message_saved_even_if_email_fails(self):
        with mock.patch("contact.views.send_mail", side_effect=OSError("SMTP down")):
            response = self.client.post(self.url, valid_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)


class ContactAdminTests(TestCase):
    def test_opening_message_marks_it_read(self):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_superuser("admin", "admin@example.com", "test-pass-123!")
        self.client.force_login(admin)
        msg = ContactMessage.objects.create(name="A", email="a@example.com", subject="S", message="x" * 30)
        response = self.client.get(reverse("admin:contact_contactmessage_change", args=[msg.pk]))
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
