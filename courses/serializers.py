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
