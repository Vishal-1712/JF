from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tracker.urls")),
]

handler404 = "tracker.views.page_not_found"
