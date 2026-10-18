from datetime import date, timedelta

from django.db.models import Q

from .models import ChecklistItem, ChecklistTemplate, Deadline, Event, Profile


def ensure_checklist(user):
    """Give the user any default checklist items they don't have yet."""
    have = set(user.checklist.exclude(template=None).values_list("template_id", flat=True))
    for t in ChecklistTemplate.objects.exclude(id__in=have):
        ChecklistItem.objects.create(user=user, template=t, phase=t.phase, title=t.title,
                                     help_text=t.help_text, order=t.order)


def visible_deadlines(user):
    """Official deadlines plus any a teacher added for this user's own school."""
    sid = Profile.objects.filter(user=user).values_list("school_id", flat=True).first()
    return Deadline.objects.filter(Q(school__isnull=True) | Q(school_id=sid)).select_related("university")


def user_deadlines(user):
    unis = user.applications.values_list("university_id", flat=True)
    return visible_deadlines(user).filter(Q(university__isnull=True) | Q(university_id__in=unis))


def upcoming_alerts(user, profile):
    today = date.today()
    end = today + timedelta(days=profile.remind_days)
    alerts = [{"title": d.title, "due": d.due, "days": (d.due - today).days}
              for d in user_deadlines(user).filter(due__range=(today, end))]
    if profile.school_id:
        alerts += [{"title": e.title, "due": e.start, "days": (e.start - today).days}
                   for e in Event.objects.filter(school_id=profile.school_id, category="school_deadline",
                                                 start__range=(today, end))]
    return sorted(alerts, key=lambda a: a["due"])[:5]
