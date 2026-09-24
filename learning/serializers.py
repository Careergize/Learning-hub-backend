from rest_framework import serializers

from .models import Certificate, Enrollment


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ["certificate_id", "issued_date", "verification_url", "share_count"]


class EnrolledCourseSerializer(serializers.ModelSerializer):
    """Shaped to match the frontend's `EnrolledCourse` TS interface 1:1,
    so `MyLearning.tsx` can consume this response with no remapping."""

    title = serializers.CharField(source="course.title")
    category = serializers.CharField(source="course.category.name")
    level = serializers.CharField(source="course.level")
    icon = serializers.CharField(source="course.icon")
    bannerGradient = serializers.CharField(source="course.banner_gradient")
    accentColor = serializers.CharField(source="course.accent_color")
    duration = serializers.CharField(source="course.duration_display")
    instructor = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()

    progress = serializers.IntegerField(source="progress_percent", read_only=True)
    completedLessons = serializers.IntegerField(source="completed_lessons", read_only=True)
    totalLessons = serializers.IntegerField(source="total_lessons", read_only=True)
    status = serializers.CharField(read_only=True)
    nextLessonTitle = serializers.SerializerMethodField()
    completedDate = serializers.DateTimeField(source="completed_at", format="%B %d, %Y", read_only=True)
    certificateId = serializers.SerializerMethodField()
    lastAccessed = serializers.DateTimeField(source="last_accessed", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id", "title", "category", "level", "icon", "bannerGradient",
            "accentColor", "progress", "completedLessons", "totalLessons",
            "status", "instructor", "duration", "nextLessonTitle",
            "completedDate", "certificateId", "lastAccessed", "skills",
        ]

    def get_instructor(self, obj):
        instr = obj.course.instructor
        return {"name": instr.name, "role": instr.role, "avatarInitials": instr.avatar_initials}

    def get_skills(self, obj):
        return list(obj.course.skills.values_list("name", flat=True))

    def get_nextLessonTitle(self, obj):
        nxt = obj.next_lesson
        return nxt.title if nxt else None

    def get_certificateId(self, obj):
        cert = getattr(obj, "certificate", None)
        return cert.certificate_id if cert else None


class EnrollmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ["id", "course"]

    def create(self, validated_data):
        student = self.context["request"].user
        enrollment, _ = Enrollment.objects.get_or_create(student=student, course=validated_data["course"])
        return enrollment
