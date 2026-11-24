import time

from django import forms
from django.core import signing

from .models import ContactMessage

# Submissions faster than this after the page loaded are treated as bots.
MIN_SUBMIT_SECONDS = 3
# Forms older than this are rejected; the visitor is asked to resubmit.
MAX_FORM_AGE_SECONDS = 60 * 60 * 24
TIMESTAMP_SALT = "contact.form.timestamp"


def make_form_token() -> str:
    return signing.dumps(time.time(), salt=TIMESTAMP_SALT)


class ContactForm(forms.ModelForm):
    # Honeypot: hidden from people with CSS and aria-hidden; bots tend to fill it.
    website = forms.CharField(required=False, label="Leave this field empty")
    # Signed render time, used to reject instant (scripted) submissions.
    form_token = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Jane Smith"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "jane@company.com"}),
            "subject": forms.TextInput(attrs={"placeholder": "Junior backend role at Acme"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "How can I help?"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["form_token"] = make_form_token()
        self.fields["website"].widget.attrs.update({"tabindex": "-1", "autocomplete": "off"})
        for name in ("name", "email", "subject", "message"):
            self.fields[name].widget.attrs["required"] = True
            self.fields[name].widget.attrs["id"] = f"contact-{name}"
        self.fields["message"].widget.attrs["maxlength"] = 5000

    def full_clean(self):
        super().full_clean()
        # Connect error messages to their inputs for screen readers.
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                attrs["aria-invalid"] = "true"
                attrs["aria-describedby"] = f"contact-{name}-error"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_subject(self):
        subject = self.cleaned_data["subject"].strip()
        if len(subject) < 3:
            raise forms.ValidationError("Please enter a subject of at least 3 characters.")
        return subject

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 20:
            raise forms.ValidationError("Please write a message of at least 20 characters.")
        if message.lower().count("http://") + message.lower().count("https://") > 3:
            raise forms.ValidationError("Please include no more than 3 links.")
        return message

    def clean(self):
        cleaned = super().clean()
        self.is_spam = bool(cleaned.get("website"))
        token = cleaned.get("form_token")
        try:
            rendered_at = signing.loads(token or "", salt=TIMESTAMP_SALT, max_age=MAX_FORM_AGE_SECONDS)
        except signing.SignatureExpired:
            raise forms.ValidationError("This form has expired. Please reload the page and try again.")
        except signing.BadSignature:
            raise forms.ValidationError("The form could not be verified. Please reload the page and try again.")
        if time.time() - float(rendered_at) < MIN_SUBMIT_SECONDS:
            self.is_spam = True
        return cleaned
