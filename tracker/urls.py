from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.TrackerLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("applications/", views.ApplicationListView.as_view(), name="application_list"),
    path("applications/new/", views.ApplicationCreateView.as_view(), name="application_create"),
    path("applications/<int:pk>/", views.ApplicationDetailView.as_view(), name="application_detail"),
    path("applications/<int:pk>/edit/", views.ApplicationUpdateView.as_view(), name="application_edit"),
    path(
        "applications/<int:pk>/delete/",
        views.ApplicationDeleteView.as_view(),
        name="application_delete",
    ),
    path("interviews/", views.InterviewListView.as_view(), name="interview_list"),
    path("interviews/new/", views.InterviewCreateView.as_view(), name="interview_create"),
    path("interviews/<int:pk>/edit/", views.InterviewUpdateView.as_view(), name="interview_edit"),
    path(
        "interviews/<int:pk>/delete/",
        views.InterviewDeleteView.as_view(),
        name="interview_delete",
    ),
]
