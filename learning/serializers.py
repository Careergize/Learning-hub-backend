from rest_framework import serializers

from .models import (
    Certificate,
    Enrollment,
    ScheduleSession,
    ChecklistItem,
    Achievement,
)


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

class ChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ["id", "text", "done"]


class ScheduleSessionSerializer(serializers.ModelSerializer):
    course = serializers.CharField(source="course.title", read_only=True)
    instructor = serializers.CharField(source="instructor.name", read_only=True)
    dayOfWeek = serializers.SerializerMethodField()
    month = serializers.SerializerMethodField()
    fullDate = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    isToday = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    attendance = serializers.SerializerMethodField()
    checkInTime = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleSession
        fields = [
            "id",
            "course",
            "topic",
            "date",
            "start_time",
            "end_time",
            "dayOfWeek",
            "month",
            "fullDate",
            "time",
            "instructor",
            "platform",
            "meet_url",
            "isToday",
            "status",
            "attendance",
            "checkInTime",
            "items",
        ]

    def get_dayOfWeek(self, obj):
        return obj.date.strftime("%a")

    def get_month(self, obj):
        return obj.date.strftime("%b")

    def get_fullDate(self, obj):
        return obj.date.strftime("%B %d, %Y")

    def get_time(self, obj):
        return f"{obj.start_time.strftime('%I:%M %p')}–{obj.end_time.strftime('%I:%M %p')}"

    def get_isToday(self, obj):
        from django.utils import timezone
        return obj.date == timezone.localdate()

    def get_status(self, obj):
        from django.utils import timezone

        today = timezone.localdate()

        if obj.date < today:
            return "completed"
        elif obj.date == today:
            return "live"
        return "upcoming"

    def get_attendance(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return "unmarked"

        attendance = obj.attendance_records.filter(
            student=request.user
        ).first()

        return attendance.status if attendance else "unmarked"

    def get_checkInTime(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        attendance = obj.attendance_records.filter(
            student=request.user
        ).first()

        if not attendance or not attendance.check_in_time:
            return None

        return attendance.check_in_time.strftime("%I:%M %p")

    def get_items(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return []

        items = obj.checklist_items.filter(
            student=request.user
        )

        return ChecklistItemSerializer(items, many=True).data    

class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = [
            "id",
            "title",
            "description",
            "icon",
            "category",
            "tier",
            "xp",
            "unlocked",
            "unlocked_date",
            "progress",
            "progress_label",
            "requirement",
            "icon_type",
            "earned_at",
        ]