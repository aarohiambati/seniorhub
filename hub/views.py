import calendar as pycal
import re
from collections import defaultdict
from datetime import date, timedelta
from functools import wraps

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ApplicationForm, ChecklistForm, DeadlineForm, EventForm, SettingsForm, SignupForm
from .models import PROVINCES, Application, ChecklistItem, ChecklistTemplate, Deadline, Event, PersonalEvent, Profile, School, University
from .services import ensure_checklist, user_deadlines, visible_deadlines


def get_profile(user):
    return Profile.objects.get_or_create(user=user)[0]


def teacher_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile.can_edit_school:
            return render(request, "teacher_pending.html", {"profile": profile}, status=403)
        return view(request, *args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile.can_manage_teachers:
            return render(request, "teacher_pending.html", {"profile": profile, "need_admin": True}, status=403)
        return view(request, *args, **kwargs)
    return wrapper


def scope_deadlines(request):
    """'all' = master list of every deadline, 'mine' = only the user's universities + general ones."""
    scope = "mine" if request.GET.get("scope") == "mine" else "all"
    qs = visible_deadlines(request.user) if scope == "all" else user_deadlines(request.user)
    return scope, qs


def school_search(request):
    q, prov = request.GET.get("q", "").strip(), request.GET.get("province", "")
    if len(q) < 2:
        return JsonResponse({"results": []})
    qs = School.objects.filter(Q(name__icontains=q) | Q(city__icontains=q))
    if prov:
        qs = qs.filter(province=prov)
    return JsonResponse({"results": [{"id": s.id, "label": str(s)} for s in qs[:20]]})


def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")
    return render(request, "registration/signup.html", {"form": form, "provinces": PROVINCES})


@login_required
def dashboard(request):
    ensure_checklist(request.user)
    today = date.today()
    profile = get_profile(request.user)
    items = request.user.checklist.all()
    total, done = items.count(), items.filter(done=True).count()
    apps = request.user.applications.select_related("university")
    return render(request, "dashboard.html", {
        "deadlines": user_deadlines(request.user).filter(due__gte=today)[:6],
        "events": Event.objects.filter(school=profile.school, start__gte=today)[:5] if profile.school else [],
        "todo": items.filter(done=False, list_name="")[:5],
        "total": total, "done": done, "percent": round(100 * done / total) if total else 0,
        "apps": apps, "attention": [a for a in apps if a.needs_attention],
    })


@login_required
def calendar_view(request):
    today = date.today()
    try:
        y, m = int(request.GET.get("y", today.year)), int(request.GET.get("m", today.month))
        weeks = pycal.Calendar(6).monthdatescalendar(y, m)
    except (ValueError, pycal.IllegalMonthError, OverflowError):
        y, m = today.year, today.month
        weeks = pycal.Calendar(6).monthdatescalendar(y, m)
    first, last = weeks[0][0], weeks[-1][-1]
    scope, dl_qs = scope_deadlines(request)
    entries = defaultdict(list)
    school = get_profile(request.user).school
    if school:
        for e in Event.objects.filter(school=school, start__lte=last).filter(Q(end__gte=first) | Q(end__isnull=True, start__gte=first)):
            d, end = max(e.start, first), min(e.end or e.start, last)
            while d <= end:
                entries[d].append({"label": e.title, "cls": e.category})
                d += timedelta(days=1)
    for pe in request.user.personal_events.filter(date__range=(first, last)):
        entries[pe.date].append({"label": pe.title, "cls": "personal", "pid": pe.pk})
    for dl in dl_qs.filter(due__range=(first, last)):
        label = f"{dl.university.name}: {dl.title}" if dl.university else dl.title
        entries[dl.due].append({"label": label, "cls": "deadline"})
    grid = [[{"date": d, "other": d.month != m, "today": d == today, "entries": entries.get(d, [])} for d in w] for w in weeks]
    prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    next_y, next_m = (y + 1, 1) if m == 12 else (y, m + 1)
    return render(request, "calendar.html", {
        "grid": grid, "title": date(y, m, 1).strftime("%B %Y"), "scope": scope, "y": y, "m": m,
        "prev": f"?y={prev_y}&m={prev_m}&scope={scope}", "next": f"?y={next_y}&m={next_m}&scope={scope}",
        "weekdays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], "school": school,
    })


@login_required
def deadlines(request):
    scope, qs = scope_deadlines(request)
    return render(request, "deadlines.html", {"deadlines": qs.filter(due__gte=date.today()), "scope": scope})


@login_required
def applications(request):
    return render(request, "applications.html", {"apps": request.user.applications.select_related("university")})


@login_required
def application_edit(request, pk=None):
    app = get_object_or_404(Application, pk=pk, user=request.user) if pk else None
    form = ApplicationForm(request.POST or None, instance=app)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        return redirect("applications")
    return render(request, "application_form.html", {"form": form, "app": app})


@login_required
@require_POST
def application_delete(request, pk):
    get_object_or_404(Application, pk=pk, user=request.user).delete()
    return redirect("applications")


@login_required
def checklist(request):
    ensure_checklist(request.user)
    form = ChecklistForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        return redirect("checklist")
    items = list(request.user.checklist.all())
    groups = [(label, [i for i in items if not i.list_name and i.phase == key], False) for key, label in ChecklistTemplate.PHASES]
    custom = defaultdict(list)
    for i in items:
        if i.list_name:
            custom[i.list_name].append(i)
    groups += [(name, lst, True) for name, lst in sorted(custom.items())]
    total, done = len(items), sum(i.done for i in items)
    return render(request, "checklist.html", {"groups": groups, "form": form, "done": done, "total": total,
                                              "percent": round(100 * done / total) if total else 0})


@login_required
@require_POST
def checklist_toggle(request, pk):
    item = get_object_or_404(ChecklistItem, pk=pk, user=request.user)
    item.done = not item.done
    item.save(update_fields=["done"])
    nxt = request.POST.get("next")
    return redirect(nxt if nxt in ("/", "/checklist/") else "checklist")


@login_required
@require_POST
def checklist_delete(request, pk):
    get_object_or_404(ChecklistItem, pk=pk, user=request.user, template=None).delete()
    return redirect("checklist")


@login_required
def settings_page(request):
    form = SettingsForm(request.POST or None, instance=get_profile(request.user))
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("settings")
    return render(request, "settings.html", {"form": form})


@teacher_required
def manage_events(request):
    school = get_profile(request.user).school
    return render(request, "manage_events.html", {"school": school, "events": school.events.all()})


@teacher_required
def event_edit(request, pk=None):
    school = get_profile(request.user).school
    event = get_object_or_404(Event, pk=pk, school=school) if pk else None
    form = EventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.school = school
        obj.save()
        return redirect("manage_events")
    return render(request, "event_form.html", {"form": form, "event": event})


@teacher_required
@require_POST
def event_delete(request, pk):
    get_object_or_404(Event, pk=pk, school=get_profile(request.user).school).delete()
    return redirect("manage_events")


@login_required
def universities(request):
    today = date.today()
    prov = request.GET.get("province", "")
    qs = University.objects.prefetch_related("deadlines")
    if prov:
        qs = qs.filter(province=prov)
    sid = get_profile(request.user).school_id
    rows = [(u, [d for d in u.deadlines.all() if d.due >= today and d.school_id in (None, sid)]) for u in qs]
    return render(request, "universities.html", {"rows": rows, "provinces": PROVINCES, "prov": prov})


def calendar_back(request, d=None):
    """Return to the month the user was looking at (only accepts a plain ?query string)."""
    nxt = request.POST.get("next", "")
    if re.fullmatch(r"\?[\w=&%.-]*", nxt):
        return reverse("calendar") + nxt
    return f"{reverse('calendar')}?y={d.year}&m={d.month}" if d else reverse("calendar")


@login_required
@require_POST
def personal_add(request):
    title = request.POST.get("title", "").strip()[:140]
    try:
        d = date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        return redirect("calendar")
    if title:
        PersonalEvent.objects.create(user=request.user, title=title, date=d)
    return redirect(calendar_back(request, d))


@login_required
@require_POST
def personal_delete(request, pk):
    get_object_or_404(PersonalEvent, pk=pk, user=request.user).delete()
    return redirect(calendar_back(request))


@admin_required
def manage_teachers(request):
    school = get_profile(request.user).school
    teachers = Profile.objects.filter(school=school, role="teacher").select_related("user").order_by("teacher_approved", "user__username")
    return render(request, "manage_teachers.html", {"school": school, "teachers": teachers})


@admin_required
@require_POST
def teacher_decide(request, pk, approve):
    me = get_profile(request.user)
    target = get_object_or_404(Profile, pk=pk, school=me.school, role="teacher")  # same school, teachers only
    target.teacher_approved = approve
    target.approved_by = request.user if approve else None
    target.save(update_fields=["teacher_approved", "approved_by"])
    return redirect("manage_teachers")


@teacher_required
def manage_deadlines(request):
    school = get_profile(request.user).school
    return render(request, "manage_deadlines.html", {
        "school": school, "deadlines": school.local_deadlines.select_related("university", "added_by").order_by("due")})


@teacher_required
def deadline_edit(request, pk=None):
    school = get_profile(request.user).school
    dl = get_object_or_404(Deadline, pk=pk, school=school) if pk else None
    form = DeadlineForm(request.POST or None, instance=dl)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.school, obj.verified = school, False
        obj.added_by = obj.added_by or request.user
        obj.save()
        return redirect("manage_deadlines")
    return render(request, "deadline_form.html", {"form": form, "deadline": dl})


@teacher_required
@require_POST
def deadline_delete(request, pk):
    get_object_or_404(Deadline, pk=pk, school=get_profile(request.user).school).delete()
    return redirect("manage_deadlines")
