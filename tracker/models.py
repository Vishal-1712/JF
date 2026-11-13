from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class JobApplication(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        UNDER_REVIEW = "under_review", "Under Review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview_scheduled", "Interview Scheduled"
        SELECTED = "selected", "Selected"
        REJECTED = "rejected", "Rejected"
        OFFER = "offer_received", "Offer Received"

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        FREELANCE = "freelance", "Freelance"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    company_name = models.CharField(max_length=150)
    job_title = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    salary_package = models.CharField(max_length=100, blank=True)
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.FULL_TIME,
    )
    application_date = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.APPLIED,
    )
    job_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-application_date", "-created_at"]
        verbose_name = "job application"
        verbose_name_plural = "job applications"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "application_date"]),
        ]

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

    def get_absolute_url(self):
        return reverse("application_detail", args=[self.pk])


class Interview(models.Model):
    class Round(models.TextChoices):
        SCREENING = "screening", "Screening"
        TECHNICAL = "technical", "Technical"
        HR = "hr", "HR"
        MANAGERIAL = "managerial", "Managerial"
        FINAL = "final", "Final"
        OTHER = "other", "Other"

    class Result(models.TextChoices):
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        ON_HOLD = "on_hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    scheduled_at = models.DateTimeField()
    interview_round = models.CharField(
        max_length=20,
        choices=Round.choices,
        default=Round.SCREENING,
        verbose_name="interview round",
    )
    interviewer_name = models.CharField(max_length=150)
    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.PENDING,
    )
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["application", "scheduled_at"]),
            models.Index(fields=["result"]),
        ]

    def __str__(self):
        return f"{self.get_interview_round_display()} · {self.application}"

    @property
    def is_overdue(self):
        return self.result == self.Result.PENDING and self.scheduled_at < timezone.now()
