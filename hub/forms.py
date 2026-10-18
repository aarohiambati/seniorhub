from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Application, ChecklistItem, Deadline, Event, Profile, School


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=False)
    role = forms.ChoiceField(choices=Profile.ROLES, widget=forms.RadioSelect, initial="student")
    school = forms.ModelChoiceField(School.objects.all(), widget=forms.HiddenInput,
                                    error_messages={"required": "Search for your school and pick it from the list."})
    grad_year = forms.IntegerField(initial=2027, min_value=2025, max_value=2040, required=False)

    class Meta:
        model = User
        fields = ("username", "email")

    def clean(self):
        data = super().clean()
        if data.get("role") in ("teacher", "admin") and not data.get("email"):
            self.add_error("email", "Teachers and administrators must give their school email so they can be verified.")
        return data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.create(user=user, school=self.cleaned_data["school"], role=self.cleaned_data["role"],
                                   grad_year=self.cleaned_data.get("grad_year") or 2027)
        return user


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        exclude = ("user",)


class ChecklistForm(forms.ModelForm):
    list_name = forms.CharField(max_length=80, initial="My checklist", label="Checklist name")
    due = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = ChecklistItem
        fields = ("list_name", "title", "due")


class EventForm(forms.ModelForm):
    start = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Event
        fields = ("title", "category", "start", "end", "description")


class SettingsForm(forms.ModelForm):
    theme = forms.ChoiceField(choices=Profile.THEMES, widget=forms.RadioSelect)
    remind_days = forms.IntegerField(min_value=1, max_value=90, label="Remind me this many days before a deadline")

    class Meta:
        model = Profile
        fields = ("theme", "remind_days")


class DeadlineForm(forms.ModelForm):
    due = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Deadline
        fields = ("university", "kind", "title", "due", "source_url", "notes")
        help_texts = {"university": "Leave blank for a general deadline that applies to all your students."}
