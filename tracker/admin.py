from django.contrib import admin

from .models import Interview, JobApplication


class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 0


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "job_title",
        "company_name",
        "user",
        "status",
        "job_type",
        "application_date",
    )
    list_filter = ("status", "job_type", "application_date")
    search_fields = ("company_name", "job_title", "location", "user__username")
    autocomplete_fields = ("user",)
    inlines = [InterviewInline]


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "interview_round",
        "scheduled_at",
        "interviewer_name",
        "result",
    )
    list_filter = ("result", "interview_round")
    search_fields = (
        "interviewer_name",
        "application__company_name",
        "application__job_title",
    )
