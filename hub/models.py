from datetime import date

from django.conf import settings
from django.db import models


PROVINCES = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"), ("NB", "New Brunswick"),
             ("NL", "Newfoundland and Labrador"), ("NS", "Nova Scotia"), ("NT", "Northwest Territories"),
             ("NU", "Nunavut"), ("ON", "Ontario"), ("PE", "Prince Edward Island"), ("QC", "Quebec"),
             ("SK", "Saskatchewan"), ("YT", "Yukon")]


class School(models.Model):
    name = models.CharField(max_length=160)
    city = models.CharField(max_length=80, blank=True)
    province = models.CharField(max_length=2, choices=PROVINCES, default="ON")
    board = models.CharField("school board / district", max_length=160, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("name", "city", "province")]
        indexes = [models.Index(fields=["province", "name"])]

    def __str__(self):
        return f"{self.name}, {self.city} ({self.province})" if self.city else f"{self.name} ({self.province})"


class Event(models.Model):
    """Schoolwide calendar entry. Managed by staff in /admin/."""
    CATEGORIES = [("academic", "Academic"), ("exam", "Exam"), ("holiday", "Holiday / No school"),
                  ("event", "School event"), ("guidance", "Guidance / university"),
                  ("school_deadline", "School deadline")]
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=140)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="event")
    start = models.DateField()
    end = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["start", "title"]

    def __str__(self):
        return f"{self.title} ({self.start})"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL)
    grad_year = models.PositiveIntegerField(default=2027)
    ROLES = [("student", "Student"), ("teacher", "Teacher / guidance counsellor"), ("admin", "School administrator")]
    THEMES = [("crimson", "Crimson"), ("ocean", "Ocean"), ("forest", "Forest"),
              ("violet", "Violet"), ("sunset", "Sunset"), ("midnight", "Midnight (dark)")]
    role = models.CharField(max_length=10, choices=ROLES, default="student")
    teacher_approved = models.BooleanField("approved", default=False, help_text="Teachers are approved by their school administrator; administrators by the site owner (in /admin/).")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    theme = models.CharField(max_length=10, choices=THEMES, default="crimson")
    remind_days = models.PositiveIntegerField("remind me this many days ahead", default=14)

    @property
    def can_edit_school(self):
        return self.role in ("teacher", "admin") and self.teacher_approved and self.school_id is not None

    @property
    def can_manage_teachers(self):
        return self.role == "admin" and self.teacher_approved and self.school_id is not None

    def __str__(self):
        return f"Profile of {self.user}"


class University(models.Model):
    name = models.CharField(max_length=140, unique=True)
    province = models.CharField(max_length=2, choices=PROVINCES, blank=True)
    uses_ouac = models.BooleanField("applies through OUAC", default=True)
    website = models.URLField("official admissions / deadlines page", max_length=300, blank=True)
    city = models.CharField(max_length=80, blank=True)
    deadline_status = models.CharField(max_length=120, blank=True)
    deadline_notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "universities"

    def __str__(self):
        return self.name


class Deadline(models.Model):
    """Leave university blank for deadlines that apply to everyone (e.g. OUAC)."""
    KINDS = [("ouac", "OUAC / central application"), ("early", "Early application"), ("regular", "Regular application"),
             ("supp", "Supplementary application"), ("ouac_fee", "OUAC payment"),
             ("scholarship", "Scholarship / award"), ("documents", "Documents / transcripts"),
             ("residence", "Residence"), ("offer", "Offer response / deposit"), ("other", "Other")]
    university = models.ForeignKey(University, null=True, blank=True, on_delete=models.CASCADE, related_name="deadlines")
    kind = models.CharField(max_length=20, choices=KINDS, default="regular")
    title = models.CharField(max_length=160)
    due = models.DateField()
    verified = models.BooleanField(default=False, help_text="Tick once confirmed against the official source.")
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.CASCADE, related_name="local_deadlines",
                               help_text="Set when a teacher adds it: only that school's students see it. Blank = visible to everyone.")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    source_url = models.URLField(blank=True)
    notes = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["due", "title"]

    def __str__(self):
        return f"{self.title} - {self.due}"

    @property
    def days_left(self):
        return (self.due - date.today()).days


class Application(models.Model):
    ROUNDS = [("early", "Early"), ("regular", "Regular")]
    STATUSES = [("planning", "Planning"), ("in_progress", "In progress"), ("submitted", "Submitted"),
                ("offer", "Offer received"), ("declined", "Declined / not admitted"), ("accepted", "Accepted")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    university = models.ForeignKey(University, on_delete=models.PROTECT)
    program = models.CharField(max_length=140)
    round = models.CharField(max_length=10, choices=ROUNDS, default="regular")
    status = models.CharField(max_length=20, choices=STATUSES, default="planning")
    supp_required = models.BooleanField("supplementary application required", default=False)
    supp_submitted = models.BooleanField("supplementary submitted", default=False)
    fee_paid = models.BooleanField("application fee paid", default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["university__name", "program"]

    def __str__(self):
        return f"{self.university} - {self.program}"

    @property
    def needs_attention(self):
        return (self.supp_required and not self.supp_submitted) or not self.fee_paid


class ChecklistTemplate(models.Model):
    """Default checklist every senior gets. Edit in /admin/ to change it for everyone."""
    PHASES = [("prepare", "1. Prepare"), ("submit", "2. Submit"), ("after", "3. After you apply")]
    phase = models.CharField(max_length=10, choices=PHASES, default="prepare")
    title = models.CharField(max_length=200)
    help_text = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["phase", "order"]

    def __str__(self):
        return self.title


class ChecklistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="checklist")
    template = models.ForeignKey(ChecklistTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    phase = models.CharField(max_length=10, choices=ChecklistTemplate.PHASES, default="prepare")
    title = models.CharField(max_length=200)
    list_name = models.CharField(max_length=80, blank=True, help_text="Set for student-made lists; blank for the default checklist.")
    help_text = models.CharField(max_length=300, blank=True)
    due = models.DateField(null=True, blank=True)
    done = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["phase", "order", "id"]

    def __str__(self):
        return self.title


class PersonalEvent(models.Model):
    """A note a student adds to their own calendar by clicking a date."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_events")
    title = models.CharField(max_length=140)
    date = models.DateField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "created"]

    def __str__(self):
        return f"{self.title} ({self.date})"
