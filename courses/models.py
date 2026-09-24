

# Create your models here.
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Instructor(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=160, blank=True, help_text="e.g. 'Principal Architect, Cloud Systems'")
    avatar_initials = models.CharField(max_length=4, blank=True)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.avatar_initials and self.name:
            parts = self.name.split()
            self.avatar_initials = "".join(p[0] for p in parts[:2]).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "Beginner", "Beginner"
        INTERMEDIATE = "Intermediate", "Intermediate"
        ADVANCED = "Advanced", "Advanced"
        BEGINNER_TO_PRO = "Beginner to Pro", "Beginner to Pro"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="courses")
    instructor = models.ForeignKey(Instructor, on_delete=models.PROTECT, related_name="courses")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)

    icon = models.CharField(max_length=10, default="📘", help_text="Emoji shown on the course card")
    banner_gradient = models.CharField(
        max_length=150, blank=True,
        default="from-blue-600/10 via-cyan-500/10 to-brand-primary/10",
        help_text="Tailwind gradient utility classes used by the frontend card banner",
    )
    accent_color = models.CharField(max_length=7, default="#006399", help_text="Hex color, e.g. #006399")

    duration_weeks = models.PositiveIntegerField(default=1)
    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, related_name="courses", blank=True)

    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def duration_display(self):
        return f"{self.duration_weeks} Weeks"

    @property
    def total_lessons(self):
        return self.lessons.count()


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    duration_minutes = models.PositiveIntegerField(default=30)
    video_url = models.URLField(blank=True)
    resource_url = models.URLField(blank=True, help_text="Slides / notes / repo link")
    is_preview = models.BooleanField(default=False, help_text="Viewable without enrolling")

    class Meta:
        ordering = ["course", "order"]
        unique_together = ("course", "order")

    def __str__(self):
        return f"{self.course.title} — Lesson {self.order}: {self.title}"
