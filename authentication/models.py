from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    """One-to-one extension of Django's built-in User model.

    Keeps auth (username/email/password) on the standard User model and
    stores learning-platform-specific fields here.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    phone = models.CharField(max_length=15, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    course = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    avatar_initials = models.CharField(max_length=4, blank=True)
    bio = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    career_goal = models.CharField(max_length=200, blank=True)
    experience_level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
        blank=True,
    )
    skills = models.JSONField(default=list, blank=True)
    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    headline = models.CharField(
        max_length=150, blank=True, help_text="e.g. 'Aspiring Full-Stack Developer'"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.avatar_initials and self.user_id:
            self.avatar_initials = self.user.username[:2].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile<{self.user.username}>"
