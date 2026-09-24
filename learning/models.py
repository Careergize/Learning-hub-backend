import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from courses.models import Course, Lesson


class Enrollment(models.Model):
	class Status(models.TextChoices):
		IN_PROGRESS = "in_progress", "In Progress"
		COMPLETED = "completed", "Completed"

	student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
	course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)

	enrolled_at = models.DateTimeField(auto_now_add=True)
	last_accessed = models.DateTimeField(auto_now=True)
	completed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		unique_together = ("student", "course")
		ordering = ["-last_accessed"]

	def __str__(self):
		return f"{self.student.username} → {self.course.title}"

	@property
	def total_lessons(self):
		return self.course.lessons.count()

	@property
	def completed_lessons(self):
		return self.lesson_progress.filter(is_completed=True).count()

	@property
	def progress_percent(self):
		total = self.total_lessons
		if total == 0:
			return 0
		return round((self.completed_lessons / total) * 100)

	@property
	def next_lesson(self):
		completed_ids = self.lesson_progress.filter(is_completed=True).values_list("lesson_id", flat=True)
		return self.course.lessons.exclude(id__in=completed_ids).order_by("order").first()

	def refresh_status(self):
		"""Recompute status/completed_at from lesson progress; issue a
		certificate automatically the moment every lesson is completed."""
		total = self.total_lessons
		if total > 0 and self.completed_lessons == total:
			if self.status != self.Status.COMPLETED:
				self.status = self.Status.COMPLETED
				self.completed_at = timezone.now()
				self.save(update_fields=["status", "completed_at"])
			Certificate.objects.get_or_create(enrollment=self)
		elif self.status != self.Status.IN_PROGRESS:
			self.status = self.Status.IN_PROGRESS
			self.completed_at = None
			self.save(update_fields=["status", "completed_at"])


class LessonProgress(models.Model):
	enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="lesson_progress")
	lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_entries")
	is_completed = models.BooleanField(default=False)
	completed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		unique_together = ("enrollment", "lesson")
		ordering = ["lesson__order"]

	def __str__(self):
		return f"{self.enrollment} — {self.lesson.title}"

	def mark_complete(self):
		if not self.is_completed:
			self.is_completed = True
			self.completed_at = timezone.now()
			self.save(update_fields=["is_completed", "completed_at"])
		self.enrollment.refresh_status()


def generate_certificate_id():
	return f"CG-{uuid.uuid4().hex[:6].upper()}-{uuid.uuid4().hex[:4].upper()}"


class Certificate(models.Model):
	enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="certificate")
	certificate_id = models.CharField(max_length=40, unique=True, default=generate_certificate_id, editable=False)
	issued_date = models.DateField(auto_now_add=True)
	share_count = models.PositiveIntegerField(default=0)
	verification_url = models.URLField(blank=True)

	def __str__(self):
		return self.certificate_id

	def save(self, *args, **kwargs):
		is_new = self._state.adding
		super().save(*args, **kwargs)
		if is_new and not self.verification_url:
			self.verification_url = f"/api/learning/certificates/verify/{self.certificate_id}/"
			super().save(update_fields=["verification_url"])
