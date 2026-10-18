from .models import Profile
from .services import upcoming_alerts


def app_context(request):
    if not request.user.is_authenticated:
        return {}
    profile = Profile.objects.get_or_create(user=request.user)[0]
    ctx = {"theme": profile.theme, "my_profile": profile, "alerts": upcoming_alerts(request.user, profile)}
    if profile.can_manage_teachers:
        ctx["pending_teachers"] = Profile.objects.filter(school=profile.school, role="teacher", teacher_approved=False).count()
    return ctx
