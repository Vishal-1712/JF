import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.paginator import InvalidPage
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    ApplicationForm,
    InterviewForm,
    ProfileForm,
    RegisterForm,
    StyledPasswordChangeForm,
)
from .models import Interview, JobApplication

PAGE_SIZE = 8
STATUS_COLORS = {
    JobApplication.Status.APPLIED: "#2563EB",
    JobApplication.Status.UNDER_REVIEW: "#7C3AED",
    JobApplication.Status.SHORTLISTED: "#0891B2",
    JobApplication.Status.INTERVIEW: "#D97706",
    JobApplication.Status.SELECTED: "#059669",
    JobApplication.Status.REJECTED: "#DC2626",
    JobApplication.Status.OFFER: "#16A34A",
}
LOCKED_STATUSES = {
    JobApplication.Status.SELECTED,
    JobApplication.Status.REJECTED,
    JobApplication.Status.OFFER,
}


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


class PageTitleMixin:
    page_title = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", self.page_title)
        return context


class SafePaginationMixin:
    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(
            queryset,
            page_size,
            orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty(),
        )
        page = self.kwargs.get(self.page_kwarg) or self.request.GET.get(self.page_kwarg) or 1
        try:
            page_number = int(page)
        except (TypeError, ValueError):
            page_number = 1
        try:
            page_obj = paginator.page(page_number)
        except InvalidPage:
            page_obj = paginator.page(1)
        return (paginator, page_obj, page_obj.object_list, page_obj.has_other_pages())


class RegisterView(FormView):
    template_name = "tracker/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Your account is ready. Add your first application when you are.")
        return super().form_valid(form)


class TrackerLoginView(LoginView):
    template_name = "tracker/login.html"
    redirect_authenticated_user = True

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username"}
        )
        form.fields["password"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "current-password"}
        )
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        name = self.request.user.first_name or self.request.user.username
        messages.success(self.request, f"Welcome back, {name}.")
        return response


class DashboardView(LoginRequiredMixin, PageTitleMixin, TemplateView):
    template_name = "tracker/dashboard.html"
    page_title = "Dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applications = JobApplication.objects.filter(user=self.request.user)
        interviews = Interview.objects.filter(application__user=self.request.user)
        grouped = {
            row["status"]: row["total"]
            for row in applications.order_by().values("status").annotate(total=Count("id"))
        }
        status_labels = []
        status_counts = []
        status_colors = []
        for value, label in JobApplication.Status.choices:
            status_labels.append(label)
            status_counts.append(grouped.get(value, 0))
            status_colors.append(STATUS_COLORS[value])

        today = timezone.localdate()
        months = _month_series(today, 6)
        window_start = date(months[0][0], months[0][1], 1)
        dated = applications.filter(application_date__gte=window_start).values_list(
            "application_date",
            flat=True,
        )
        month_counts = {(year, month): 0 for year, month in months}
        for applied_on in dated:
            key = (applied_on.year, applied_on.month)
            if key in month_counts:
                month_counts[key] += 1

        context["stats"] = {
            "total": applications.count(),
            "interviews_scheduled": interviews.filter(result=Interview.Result.PENDING).count(),
            "rejected": applications.filter(status=JobApplication.Status.REJECTED).count(),
            "offers": applications.filter(status=JobApplication.Status.OFFER).count(),
            "shortlisted": applications.filter(status=JobApplication.Status.SHORTLISTED).count(),
        }
        context["chart_data"] = {
            "statusLabels": status_labels,
            "statusCounts": status_counts,
            "statusColors": status_colors,
            "monthLabels": [f"{calendar.month_abbr[month]} {year}" for year, month in months],
            "monthCounts": [month_counts[key] for key in months],
        }
        context["recent_applications"] = applications.select_related("user")[:5]
        context["follow_ups"] = interviews.select_related("application").filter(
            result=Interview.Result.PENDING
        ).order_by("scheduled_at")[:5]
        return context


class ApplicationListView(LoginRequiredMixin, SafePaginationMixin, PageTitleMixin, ListView):
    model = JobApplication
    template_name = "tracker/application_list.html"
    context_object_name = "applications"
    paginate_by = PAGE_SIZE
    page_title = "Applications"

    def get_queryset(self):
        queryset = JobApplication.objects.filter(user=self.request.user).annotate(
            interview_count=Count("interviews")
        )
        return _filter_applications(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        status = params.get("status", "")
        job_type = params.get("job_type", "")
        sort = params.get("sort", "newest")
        if sort not in {"newest", "oldest"}:
            sort = "newest"
        if status not in JobApplication.Status.values:
            status = ""
        if job_type not in JobApplication.JobType.values:
            job_type = ""
        query = params.get("q", "").strip()
        context.update(
            {
                "query": query,
                "selected_status": status,
                "selected_job_type": job_type,
                "selected_sort": sort,
                "status_choices": JobApplication.Status.choices,
                "job_type_choices": JobApplication.JobType.choices,
                "filters_active": bool(query or status or job_type or sort == "oldest"),
                "total_for_user": JobApplication.objects.filter(user=self.request.user).count(),
            }
        )
        return context


class ApplicationCreateView(LoginRequiredMixin, PageTitleMixin, CreateView):
    model = JobApplication
    form_class = ApplicationForm
    template_name = "tracker/application_form.html"
    page_title = "Add application"

    def get_initial(self):
        return {
            "application_date": timezone.localdate(),
            "status": JobApplication.Status.APPLIED,
            "job_type": JobApplication.JobType.FULL_TIME,
        }

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Application added.")
        return super().form_valid(form)


class OwnedApplicationMixin(LoginRequiredMixin):
    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user)


class ApplicationUpdateView(OwnedApplicationMixin, PageTitleMixin, UpdateView):
    model = JobApplication
    form_class = ApplicationForm
    template_name = "tracker/application_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit application"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Application updated.")
        return super().form_valid(form)


class ApplicationDetailView(OwnedApplicationMixin, PageTitleMixin, DetailView):
    model = JobApplication
    template_name = "tracker/application_detail.html"
    context_object_name = "application"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("interviews")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.job_title
        context["interviews"] = self.object.interviews.all()
        return context


class ApplicationDeleteView(OwnedApplicationMixin, PageTitleMixin, DeleteView):
    model = JobApplication
    template_name = "tracker/application_confirm_delete.html"
    success_url = reverse_lazy("application_list")
    page_title = "Delete application"

    def form_valid(self, form):
        messages.success(self.request, "Application deleted.")
        return super().form_valid(form)


class InterviewListView(LoginRequiredMixin, SafePaginationMixin, PageTitleMixin, ListView):
    model = Interview
    template_name = "tracker/interview_list.html"
    context_object_name = "interviews"
    paginate_by = PAGE_SIZE
    page_title = "Interviews"

    def get_queryset(self):
        queryset = Interview.objects.filter(application__user=self.request.user).select_related(
            "application"
        )
        return _filter_interviews(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        result = params.get("result", "")
        interview_round = params.get("round", "")
        sort = params.get("sort", "latest")
        if result not in Interview.Result.values:
            result = ""
        if interview_round not in Interview.Round.values:
            interview_round = ""
        if sort not in {"latest", "soonest"}:
            sort = "latest"
        query = params.get("q", "").strip()
        context.update(
            {
                "query": query,
                "selected_result": result,
                "selected_round": interview_round,
                "selected_sort": sort,
                "result_choices": Interview.Result.choices,
                "round_choices": Interview.Round.choices,
                "filters_active": bool(query or result or interview_round or sort == "soonest"),
                "has_applications": JobApplication.objects.filter(user=self.request.user).exists(),
            }
        )
        return context


class InterviewCreateView(LoginRequiredMixin, PageTitleMixin, CreateView):
    model = Interview
    form_class = InterviewForm
    template_name = "tracker/interview_form.html"
    page_title = "Schedule interview"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["update_status"] = True
        initial["result"] = Interview.Result.PENDING
        application_id = self.request.GET.get("application")
        if application_id and application_id.isdigit():
            if JobApplication.objects.filter(pk=int(application_id), user=self.request.user).exists():
                initial["application"] = int(application_id)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_applications"] = JobApplication.objects.filter(user=self.request.user).exists()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        _maybe_mark_interview_scheduled(form)
        messages.success(self.request, "Interview scheduled.")
        return response

    def get_success_url(self):
        return reverse("application_detail", args=[self.object.application_id])


class OwnedInterviewMixin(LoginRequiredMixin):
    def get_queryset(self):
        return Interview.objects.filter(application__user=self.request.user).select_related(
            "application"
        )


class InterviewUpdateView(OwnedInterviewMixin, PageTitleMixin, UpdateView):
    model = Interview
    form_class = InterviewForm
    template_name = "tracker/interview_form.html"
    page_title = "Edit interview"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        _maybe_mark_interview_scheduled(form)
        messages.success(self.request, "Interview updated.")
        return response

    def get_success_url(self):
        return reverse("application_detail", args=[self.object.application_id])


class InterviewDeleteView(OwnedInterviewMixin, PageTitleMixin, DeleteView):
    model = Interview
    template_name = "tracker/interview_confirm_delete.html"
    page_title = "Delete interview"

    def get_success_url(self):
        return reverse("application_detail", args=[self.object.application_id])

    def form_valid(self, form):
        messages.success(self.request, "Interview deleted.")
        return super().form_valid(form)


@login_required
def profile(request):
    account_form = ProfileForm(prefix="account", instance=request.user)
    password_form = StyledPasswordChangeForm(request.user, prefix="password")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "account":
            account_form = ProfileForm(request.POST, prefix="account", instance=request.user)
            if account_form.is_valid():
                account_form.save()
                messages.success(request, "Account details updated.")
                return redirect("profile")
        elif action == "password":
            password_form = StyledPasswordChangeForm(request.user, request.POST, prefix="password")
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated.")
                return redirect("profile")
        else:
            messages.error(request, "That form could not be submitted.")

    return render(
        request,
        "tracker/profile.html",
        {
            "page_title": "Account",
            "account_form": account_form,
            "password_form": password_form,
            "application_count": JobApplication.objects.filter(user=request.user).count(),
            "interview_count": Interview.objects.filter(application__user=request.user).count(),
        },
    )


def _filter_applications(queryset, params):
    query = params.get("q", "").strip()
    status = params.get("status", "")
    job_type = params.get("job_type", "")
    sort = params.get("sort", "newest")
    if query:
        queryset = queryset.filter(
            Q(company_name__icontains=query) | Q(job_title__icontains=query)
        )
    if status in JobApplication.Status.values:
        queryset = queryset.filter(status=status)
    if job_type in JobApplication.JobType.values:
        queryset = queryset.filter(job_type=job_type)
    if sort == "oldest":
        return queryset.order_by("application_date", "created_at")
    return queryset.order_by("-application_date", "-created_at")


def _filter_interviews(queryset, params):
    query = params.get("q", "").strip()
    result = params.get("result", "")
    interview_round = params.get("round", "")
    sort = params.get("sort", "latest")
    if query:
        queryset = queryset.filter(
            Q(application__company_name__icontains=query)
            | Q(application__job_title__icontains=query)
            | Q(interviewer_name__icontains=query)
        )
    if result in Interview.Result.values:
        queryset = queryset.filter(result=result)
    if interview_round in Interview.Round.values:
        queryset = queryset.filter(interview_round=interview_round)
    if sort == "soonest":
        return queryset.order_by("scheduled_at", "pk")
    return queryset.order_by("-scheduled_at", "-pk")


def _maybe_mark_interview_scheduled(form):
    if not form.cleaned_data.get("update_status"):
        return
    application = form.instance.application
    if application.status in LOCKED_STATUSES:
        return
    if application.status != JobApplication.Status.INTERVIEW:
        application.status = JobApplication.Status.INTERVIEW
        application.save()


def _month_series(today, count):
    year = today.year
    month = today.month - (count - 1)
    while month <= 0:
        month += 12
        year -= 1
    series = []
    for _ in range(count):
        series.append((year, month))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return series
