from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Interview, JobApplication


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css}".strip()


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"autocomplete": "username"})
        self.fields["first_name"].widget.attrs.update({"autocomplete": "given-name"})
        self.fields["last_name"].widget.attrs.update({"autocomplete": "family-name"})
        self.fields["email"].widget.attrs.update({"autocomplete": "email"})
        self.order_fields(
            ["username", "first_name", "last_name", "email", "password1", "password2"]
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        if commit:
            user.save()
        return user


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_first_name(self):
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].strip()


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class ApplicationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = [
            "company_name",
            "job_title",
            "location",
            "salary_package",
            "job_type",
            "status",
            "application_date",
            "job_url",
            "description",
            "notes",
        ]
        widgets = {
            "company_name": forms.TextInput(attrs={"placeholder": "e.g. Northwind Labs"}),
            "job_title": forms.TextInput(attrs={"placeholder": "e.g. Backend Engineer"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Bengaluru or Remote"}),
            "salary_package": forms.TextInput(attrs={"placeholder": "e.g. 18 LPA"}),
            "application_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "job_url": forms.URLInput(attrs={"placeholder": "https://"}),
            "description": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Role summary, stack, or what stood out"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Referral, follow-up, questions to ask"}
            ),
        }
        labels = {
            "job_url": "Job posting URL",
            "salary_package": "Salary package",
            "notes": "Personal notes",
        }
        help_texts = {
            "salary_package": "Optional. Use the format from the posting.",
            "job_url": "Optional link to the original posting.",
            "notes": "Only you can see notes on your applications.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["application_date"].input_formats = ["%Y-%m-%d"]

    def clean_company_name(self):
        value = self.cleaned_data["company_name"].strip()
        if len(value) < 2:
            raise forms.ValidationError("Enter the company name.")
        return value

    def clean_job_title(self):
        value = self.cleaned_data["job_title"].strip()
        if len(value) < 2:
            raise forms.ValidationError("Enter the job title.")
        return value

    def clean_location(self):
        value = self.cleaned_data["location"].strip()
        if len(value) < 2:
            raise forms.ValidationError("Enter a location, or Remote.")
        return value

    def clean_salary_package(self):
        return self.cleaned_data["salary_package"].strip()

    def clean_application_date(self):
        value = self.cleaned_data["application_date"]
        today = timezone.localdate()
        if value > today:
            raise forms.ValidationError("Application date cannot be in the future.")
        if value.year < 1990:
            raise forms.ValidationError("Enter a realistic application date.")
        return value

    def clean_description(self):
        return self.cleaned_data["description"].strip()

    def clean_notes(self):
        return self.cleaned_data["notes"].strip()


class InterviewForm(BootstrapFormMixin, forms.ModelForm):
    update_status = forms.BooleanField(
        required=False,
        label="Mark this application as Interview Scheduled",
    )

    class Meta:
        model = Interview
        fields = [
            "application",
            "scheduled_at",
            "interview_round",
            "interviewer_name",
            "result",
            "feedback",
        ]
        widgets = {
            "scheduled_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "interviewer_name": forms.TextInput(attrs={"placeholder": "e.g. Priya Shah"}),
            "feedback": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Questions asked, outcome, next step"}
            ),
        }
        labels = {
            "scheduled_at": "Date and time",
            "interview_round": "Interview round",
            "interviewer_name": "Interviewer name",
            "feedback": "Feedback and notes",
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scheduled_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
        applications = JobApplication.objects.filter(user=user).order_by(
            "-application_date",
            "company_name",
        )
        self.fields["application"].queryset = applications
        self.fields["application"].empty_label = "Select an application"
        self.fields["application"].label_from_instance = (
            lambda obj: f"{obj.job_title} · {obj.company_name}"
        )

    def clean_interviewer_name(self):
        value = self.cleaned_data["interviewer_name"].strip()
        if len(value) < 2:
            raise forms.ValidationError("Enter the interviewer's name.")
        return value

    def clean_feedback(self):
        return self.cleaned_data["feedback"].strip()
