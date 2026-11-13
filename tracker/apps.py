from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tracker"
    verbose_name = "Job applications"

    def ready(self):
        from django.contrib import admin

        admin.site.site_header = "Job Application Tracker"
        admin.site.site_title = "JobTrack admin"
        admin.site.index_title = "Records"
