from datetime import date, datetime, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Interview, JobApplication

PASSWORD = "Tracker#2026pass"


def make_user(username="alex", email="alex@example.com"):
    return User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
        first_name="Alex",
        last_name="Rivera",
    )


def make_application(user, **overrides):
    data = {
        "company_name": "Acme",
        "job_title": "Backend Engineer",
        "location": "Remote",
        "salary_package": "20 LPA",
        "job_type": JobApplication.JobType.FULL_TIME,
        "application_date": timezone.localdate(),
        "status": JobApplication.Status.APPLIED,
        "job_url": "https://example.com/jobs/1",
        "description": "Build APIs",
        "notes": "Referral from Sam",
    }
    data.update(overrides)
    return JobApplication.objects.create(user=user, **data)


class TrackerFlowTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user(username="blair", email="blair@example.com")
        self.client.login(username="alex", password=PASSWORD)

    def test_registration_hashes_password_and_starts_session(self):
        self.client.logout()
        response = self.client.post(
            reverse("register"),
            {
                "username": "casey",
                "first_name": "Casey",
                "last_name": "Ng",
                "email": "Casey@Example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="casey")
        self.assertEqual(user.email, "casey@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.password.startswith(PASSWORD))
        self.assertTrue(user.password.startswith("pbkdf2_"))

    def test_duplicate_email_is_rejected(self):
        self.client.logout()
        response = self.client.post(
            reverse("register"),
            {
                "username": "casey",
                "first_name": "Casey",
                "last_name": "Ng",
                "email": "ALEX@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="casey").exists())

    def test_login_logout_and_protected_routes(self):
        self.client.logout()
        anonymous = self.client.get(reverse("dashboard"))
        self.assertRedirects(anonymous, f"{reverse('login')}?next={reverse('dashboard')}")
        logged_in = self.client.post(
            reverse("login"),
            {"username": "alex", "password": PASSWORD},
        )
        self.assertRedirects(logged_in, reverse("dashboard"))
        logged_out = self.client.post(reverse("logout"))
        self.assertRedirects(logged_out, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_requires_csrf_when_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse("login"),
            {"username": "alex", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 403)

    def test_application_crud_and_validation(self):
        created = self.client.post(
            reverse("application_create"),
            {
                "company_name": "Northwind",
                "job_title": "Platform Engineer",
                "location": "Bengaluru",
                "salary_package": "24 LPA",
                "job_type": JobApplication.JobType.FULL_TIME,
                "status": JobApplication.Status.APPLIED,
                "application_date": timezone.localdate().isoformat(),
                "job_url": "https://example.com/northwind",
                "description": "Owns the deploy pipeline",
                "notes": "Ask about on-call",
            },
        )
        application = JobApplication.objects.get(company_name="Northwind")
        self.assertRedirects(created, application.get_absolute_url())
        self.assertEqual(application.user, self.user)

        edited = self.client.post(
            reverse("application_edit", args=[application.pk]),
            {
                "company_name": "Northwind Labs",
                "job_title": "Platform Engineer",
                "location": "Bengaluru",
                "salary_package": "26 LPA",
                "job_type": JobApplication.JobType.CONTRACT,
                "status": JobApplication.Status.UNDER_REVIEW,
                "application_date": timezone.localdate().isoformat(),
                "job_url": "https://example.com/northwind",
                "description": "Owns the deploy pipeline",
                "notes": "Ask about on-call",
            },
        )
        self.assertRedirects(edited, application.get_absolute_url())
        application.refresh_from_db()
        self.assertEqual(application.company_name, "Northwind Labs")
        self.assertEqual(application.status, JobApplication.Status.UNDER_REVIEW)

        future = self.client.post(
            reverse("application_edit", args=[application.pk]),
            {
                "company_name": "Northwind Labs",
                "job_title": "Platform Engineer",
                "location": "Bengaluru",
                "salary_package": "",
                "job_type": JobApplication.JobType.CONTRACT,
                "status": JobApplication.Status.UNDER_REVIEW,
                "application_date": (timezone.localdate() + timedelta(days=3)).isoformat(),
                "job_url": "",
                "description": "",
                "notes": "",
            },
        )
        self.assertEqual(future.status_code, 200)
        application.refresh_from_db()
        self.assertEqual(application.company_name, "Northwind Labs")

        detail = self.client.get(application.get_absolute_url())
        self.assertContains(detail, "Northwind Labs")
        self.assertContains(detail, "Ask about on-call")

        self.assertEqual(JobApplication.objects.count(), 1)
        self.client.get(reverse("application_delete", args=[application.pk]))
        self.assertEqual(JobApplication.objects.count(), 1)
        deleted = self.client.post(reverse("application_delete", args=[application.pk]))
        self.assertRedirects(deleted, reverse("application_list"))
        self.assertEqual(JobApplication.objects.count(), 0)

    def test_users_cannot_see_or_change_each_others_records(self):
        own = make_application(self.user, company_name="Own Co")
        theirs = make_application(self.other, company_name="Secret Co", job_title="Hidden Role")
        listing = self.client.get(reverse("application_list"))
        self.assertContains(listing, "Own Co")
        self.assertNotContains(listing, "Secret Co")
        self.assertEqual(self.client.get(theirs.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.post(reverse("application_edit", args=[theirs.pk]), {}).status_code, 404)
        self.assertEqual(self.client.post(reverse("application_delete", args=[theirs.pk])).status_code, 404)
        stolen = self.client.post(
            reverse("interview_create"),
            {
                "application": theirs.pk,
                "scheduled_at": "2026-12-01T10:00",
                "interview_round": Interview.Round.TECHNICAL,
                "interviewer_name": "Sneaky",
                "result": Interview.Result.PENDING,
                "feedback": "",
                "update_status": "on",
            },
        )
        self.assertEqual(stolen.status_code, 200)
        self.assertFalse(Interview.objects.filter(application=theirs).exists())
        self.assertTrue(JobApplication.objects.filter(pk=own.pk, user=self.user).exists())

    def test_search_filter_sort_and_pagination(self):
        older = timezone.localdate() - timedelta(days=10)
        make_application(
            self.user,
            company_name="Acme Analytics",
            job_title="Data Analyst",
            application_date=older,
            status=JobApplication.Status.REJECTED,
            job_type=JobApplication.JobType.CONTRACT,
        )
        make_application(
            self.user,
            company_name="Brightpath",
            job_title="Product Designer",
            application_date=timezone.localdate(),
            status=JobApplication.Status.SHORTLISTED,
            job_type=JobApplication.JobType.FULL_TIME,
        )
        for index in range(7):
            make_application(
                self.user,
                company_name=f"Batch {index}",
                job_title="Support Engineer",
                application_date=timezone.localdate() - timedelta(days=index + 1),
            )

        search = self.client.get(reverse("application_list"), {"q": "acme"})
        self.assertContains(search, "Data Analyst")
        self.assertNotContains(search, "Product Designer")

        status = self.client.get(
            reverse("application_list"),
            {"status": JobApplication.Status.SHORTLISTED},
        )
        self.assertContains(status, "Brightpath")
        self.assertNotContains(status, "Acme Analytics")

        job_type = self.client.get(
            reverse("application_list"),
            {"job_type": JobApplication.JobType.CONTRACT},
        )
        self.assertContains(job_type, "Acme Analytics")
        self.assertNotContains(job_type, "Brightpath")

        oldest = self.client.get(reverse("application_list"), {"sort": "oldest"})
        first_company = oldest.context["applications"][0].company_name
        self.assertEqual(first_company, "Acme Analytics")

        page_two = self.client.get(reverse("application_list"), {"page": 2})
        self.assertEqual(page_two.status_code, 200)
        self.assertEqual(len(page_two.context["applications"]), 1)
        invalid = self.client.get(reverse("application_list"), {"page": "nope"})
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(invalid.context["page_obj"].number, 1)

    def test_interview_create_updates_status_and_delete_cascades(self):
        application = make_application(self.user, status=JobApplication.Status.SHORTLISTED)
        created = self.client.post(
            reverse("interview_create"),
            {
                "application": application.pk,
                "scheduled_at": "2026-12-02T15:30",
                "interview_round": Interview.Round.TECHNICAL,
                "interviewer_name": "Priya Shah",
                "result": Interview.Result.PENDING,
                "feedback": "System design",
                "update_status": "on",
            },
        )
        interview = Interview.objects.get()
        self.assertRedirects(created, application.get_absolute_url())
        application.refresh_from_db()
        self.assertEqual(application.status, JobApplication.Status.INTERVIEW)
        self.assertEqual(interview.interviewer_name, "Priya Shah")

        rejected = make_application(
            self.user,
            company_name="Closed",
            job_title="Writer",
            status=JobApplication.Status.REJECTED,
        )
        self.client.post(
            reverse("interview_create"),
            {
                "application": rejected.pk,
                "scheduled_at": "2026-12-03T09:00",
                "interview_round": Interview.Round.HR,
                "interviewer_name": "Jordan Lee",
                "result": Interview.Result.PENDING,
                "feedback": "",
                "update_status": "on",
            },
        )
        rejected.refresh_from_db()
        self.assertEqual(rejected.status, JobApplication.Status.REJECTED)

        edit_page = self.client.get(reverse("interview_edit", args=[interview.pk]))
        self.assertContains(edit_page, "2026-12-02T15:30")
        self.client.post(reverse("interview_delete", args=[interview.pk]))
        self.assertFalse(Interview.objects.filter(pk=interview.pk).exists())
        self.client.post(reverse("application_delete", args=[rejected.pk]))
        self.assertFalse(Interview.objects.filter(application=rejected).exists())

    def test_other_user_cannot_open_interview(self):
        application = make_application(self.other, company_name="Other Co")
        interview = Interview.objects.create(
            application=application,
            scheduled_at=timezone.now() + timedelta(days=1),
            interview_round=Interview.Round.HR,
            interviewer_name="Pat Kim",
            result=Interview.Result.PENDING,
        )
        self.assertEqual(self.client.get(reverse("interview_edit", args=[interview.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("interview_delete", args=[interview.pk])).status_code, 404)

    def test_dashboard_counts_come_from_the_database(self):
        today = timezone.localdate()
        month = today.month - 2
        year = today.year
        if month <= 0:
            month += 12
            year -= 1
        make_application(self.user, company_name="Now Co", status=JobApplication.Status.OFFER)
        make_application(
            self.user,
            company_name="Earlier Co",
            job_title="Analyst",
            status=JobApplication.Status.REJECTED,
            application_date=date(year, month, 1),
        )
        make_application(
            self.user,
            company_name="Old Co",
            job_title="Archivist",
            application_date=date(today.year - 2, 1, 15),
            status=JobApplication.Status.SHORTLISTED,
        )
        Interview.objects.create(
            application=JobApplication.objects.get(company_name="Now Co"),
            scheduled_at=timezone.make_aware(datetime(2026, 12, 5, 11, 0)),
            interview_round=Interview.Round.FINAL,
            interviewer_name="Avery Cole",
            result=Interview.Result.PENDING,
        )
        response = self.client.get(reverse("dashboard"))
        stats = response.context["stats"]
        chart = response.context["chart_data"]
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["offers"], 1)
        self.assertEqual(stats["rejected"], 1)
        self.assertEqual(stats["shortlisted"], 1)
        self.assertEqual(stats["interviews_scheduled"], 1)
        self.assertEqual(sum(chart["statusCounts"]), 3)
        self.assertEqual(chart["monthCounts"][-1], 1)
        self.assertEqual(sum(chart["monthCounts"]), 2)
        self.assertContains(response, 'class="stat-value">3</p>')
        self.assertContains(response, "statusChart")
        self.assertContains(response, "trendChart")

    def test_profile_update_and_password_change_keep_session(self):
        response = self.client.post(
            reverse("profile"),
            {
                "action": "account",
                "account-first_name": "Alejandra",
                "account-last_name": "Rivera",
                "account-email": "alex@example.com",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alejandra")

        changed = self.client.post(
            reverse("profile"),
            {
                "action": "password",
                "password-old_password": PASSWORD,
                "password-new_password1": "NewerTracker#2026",
                "password-new_password2": "NewerTracker#2026",
            },
        )
        self.assertRedirects(changed, reverse("profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewerTracker#2026"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_interview_filters(self):
        application = make_application(self.user)
        Interview.objects.create(
            application=application,
            scheduled_at=timezone.now() + timedelta(days=2),
            interview_round=Interview.Round.TECHNICAL,
            interviewer_name="Priya Shah",
            result=Interview.Result.PENDING,
        )
        Interview.objects.create(
            application=application,
            scheduled_at=timezone.now() - timedelta(days=3),
            interview_round=Interview.Round.HR,
            interviewer_name="Owen Blake",
            result=Interview.Result.PASSED,
        )
        found = self.client.get(reverse("interview_list"), {"q": "priya"})
        self.assertContains(found, "Priya Shah")
        self.assertNotContains(found, "Owen Blake")
        by_result = self.client.get(reverse("interview_list"), {"result": Interview.Result.PASSED})
        self.assertContains(by_result, "Owen Blake")
        self.assertNotContains(by_result, "Priya Shah")
