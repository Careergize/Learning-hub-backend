from django.conf import settings
from django.db import models

from courses.models import Course, Instructor


class CourseNote(models.Model):
    """A PDF-style study resource (lecture handout, cheatsheet, architecture
    guide, or exam-prep pack) attached to a course module."""

    class NoteType(models.TextChoices):
        LECTURE_HANDOUT = "Lecture Handout", "Lecture Handout"
        CHEATSHEET = "Cheatsheet", "Cheatsheet"
        ARCHITECTURE_GUIDE = "Architecture Guide", "Architecture Guide"
        EXAM_PREP = "Exam Prep", "Exam Prep"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="notes")
    instructor = models.ForeignKey(
        Instructor, on_delete=models.SET_NULL, null=True, blank=True, related_name="authored_notes",
        help_text="Defaults to the course instructor if left blank.",
    )

    module_number = models.CharField(max_length=30, help_text="e.g. 'Module 01'")
    order = models.PositiveIntegerField(default=1, help_text="Sort order within the course")
    title = models.CharField(max_length=250)
    description = models.TextField()
    note_type = models.CharField(max_length=30, choices=NoteType.choices, default=NoteType.LECTURE_HANDOUT)

    pages = models.PositiveIntegerField(default=1)
    file_size_mb = models.DecimalField(max_digits=6, decimal_places=1, default=1.0)
    edition = models.CharField(max_length=60, blank=True, help_text="e.g. 'Fall 2026 Edition'")
    pdf_file = models.FileField(upload_to="course_notes/", blank=True, null=True)

    topics = models.JSONField(default=list, blank=True, help_text='List of short topic tags, e.g. ["OOP", "Generators"]')
    summary = models.TextField(blank=True)
    table_of_contents = models.JSONField(default=list, blank=True, help_text="List of TOC line strings")
    key_takeaways = models.JSONField(default=list, blank=True, help_text="List of revision bullet strings")

    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["course", "order"]

    def __str__(self):
        return f"{self.course.title} — {self.module_number}: {self.title}"

    @property
    def file_size_display(self):
        return f"{self.file_size_mb} MB"

    @property
    def effective_instructor(self):
        return self.instructor or self.course.instructor


class NoteSection(models.Model):
    """One numbered section of a CourseNote's lecture content."""

    note = models.ForeignKey(CourseNote, on_delete=models.CASCADE, related_name="sections")
    order = models.PositiveIntegerField(default=1)
    heading = models.CharField(max_length=250)
    content = models.TextField()
    bullet_points = models.JSONField(default=list, blank=True)
    key_highlight = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["note", "order"]

    def __str__(self):
        return f"{self.note.title} — {self.heading}"


class NoteCodeSnippet(models.Model):
    """A practical code sample embedded in a CourseNote."""

    note = models.ForeignKey(CourseNote, on_delete=models.CASCADE, related_name="code_snippets")
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=30)
    code = models.TextField()

    class Meta:
        ordering = ["note", "order"]

    def __str__(self):
        return f"{self.note.title} — {self.title}"


class NoteBookmark(models.Model):
    """A student saving a note for quick revision access later."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="note_bookmarks")
    note = models.ForeignKey(CourseNote, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "note")

    def __str__(self):
        return f"{self.student.username} ★ {self.note.title}"
