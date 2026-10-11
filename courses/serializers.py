from django.utils.text import slugify
from rest_framework import serializers

from .models import Category, Course, Instructor, Lesson, Skill


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ["id", "name", "role", "avatar_initials"]


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "title", "order", "duration_minutes", "video_url", "resource_url", "is_preview"]


class CourseListSerializer(serializers.ModelSerializer):
    """Shape used for the public catalog / 'Explore Catalog' grid."""

    category = serializers.CharField(source="category.name", read_only=True)
    instructor = InstructorSerializer(read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    duration = serializers.CharField(source="duration_display", read_only=True)
    totalLessons = serializers.IntegerField(source="total_lessons", read_only=True)
    bannerGradient = serializers.CharField(source="banner_gradient", read_only=True)
    accentColor = serializers.CharField(source="accent_color", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id", "slug", "title", "category", "level", "icon",
            "bannerGradient", "accentColor", "duration", "instructor",
            "skills", "totalLessons", "short_description",
        ]


class CourseDetailSerializer(CourseListSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + ["description", "lessons", "is_published"]


class AdminCourseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    instructor_name = serializers.CharField(source="instructor.name", read_only=True)
    enrollment_count = serializers.SerializerMethodField()
    completed_enrollments = serializers.SerializerMethodField()
    average_progress = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    enrolled_students = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "title", "slug", "category", "category_name", "instructor",
            "instructor_name", "level", "icon", "banner_gradient", "accent_color",
            "duration_weeks", "short_description", "description", "is_published",
            "created_at", "enrollment_count", "completed_enrollments",
            "average_progress", "lesson_count", "enrolled_students",
        ]
        read_only_fields = [
            "id", "slug", "created_at", "enrollment_count",
            "completed_enrollments", "average_progress", "lesson_count",
            "enrolled_students",
        ]

    def validate_title(self, value):
        slug = slugify(value)
        if not slug:
            raise serializers.ValidationError("Enter a course title with letters or numbers.")
        matches = Course.objects.filter(slug=slug)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError("A course with this title already exists.")
        return value.strip()

    def validate_duration_weeks(self, value):
        if value < 1:
            raise serializers.ValidationError("Duration must be at least one week.")
        return value

    @staticmethod
    def _student_enrollments(course):
        return [
            enrollment for enrollment in course.enrollments.all()
            if not enrollment.student.is_staff and not enrollment.student.is_superuser
        ]

    @staticmethod
    def _progress(enrollment, total_lessons):
        completed = sum(
            1 for progress in enrollment.lesson_progress.all()
            if progress.is_completed
        )
        return round(completed / total_lessons * 100) if total_lessons else 0

    def get_enrollment_count(self, obj):
        return len(self._student_enrollments(obj))

    def get_completed_enrollments(self, obj):
        return sum(
            enrollment.status == "completed"
            for enrollment in self._student_enrollments(obj)
        )

    def get_average_progress(self, obj):
        enrollments = self._student_enrollments(obj)
        total_lessons = len(obj.lessons.all())
        values = [self._progress(enrollment, total_lessons) for enrollment in enrollments]
        return round(sum(values) / len(values)) if values else 0

    def get_lesson_count(self, obj):
        return len(obj.lessons.all())

    def get_enrolled_students(self, obj):
        enrollments = self._student_enrollments(obj)
        total_lessons = len(obj.lessons.all())
        students = []
        for enrollment in enrollments:
            profile = getattr(enrollment.student, "student_profile", None)
            students.append({
                "id": enrollment.student_id,
                "name": enrollment.student.username,
                "email": enrollment.student.email,
                "status": profile.status if profile else "unknown",
                "enrollment_status": enrollment.status,
                "progress": self._progress(enrollment, total_lessons),
            })
        return students
