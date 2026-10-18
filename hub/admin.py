from django.contrib import admin
from . import models


@admin.register(models.School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "province", "board")
    list_filter = ("province",)
    search_fields = ("name", "city", "board")


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "teacher_approved", "school", "approved_by")
    list_filter = ("role", "teacher_approved")
    search_fields = ("user__username", "school__name")
    autocomplete_fields = ("school",)
    actions = ["approve_teachers"]

    @admin.action(description="Approve selected teachers / school administrators")
    def approve_teachers(self, request, queryset):
        queryset.filter(role__in=("teacher", "admin")).update(teacher_approved=True, approved_by=request.user)


@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "category", "start", "end")
    list_filter = ("category", "school__province")
    search_fields = ("title", "school__name")
    autocomplete_fields = ("school",)
    date_hierarchy = "start"


@admin.register(models.Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("title", "university", "kind", "due", "verified", "school")
    list_filter = ("kind", "verified", "university")
    autocomplete_fields = ("school",)
    list_editable = ("verified",)
    search_fields = ("title", "university__name")


@admin.register(models.University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "city", "uses_ouac", "deadline_status")
    list_filter = ("province", "uses_ouac")
    search_fields = ("name",)


@admin.register(models.ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "phase", "order")
    list_filter = ("phase",)


admin.site.register(models.Application)
admin.site.register(models.PersonalEvent)
