from django.shortcuts import render

# Create your views here.
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import FileResponse


from io import BytesIO
from reportlab.pdfgen import canvas

User = get_user_model()
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Lesson

from .models import (
    Certificate,
    Enrollment,
    LessonProgress,
    ScheduleSession,
    Attendance,
    ChecklistItem,
    Achievement,
)
from .serializers import (
    CertificateSerializer,
    EnrolledCourseSerializer,
    EnrollmentCreateSerializer,
    ScheduleSessionSerializer,
    ChecklistItemSerializer,
    AchievementSerializer,
)


class MyLearningViewSet(viewsets.ModelViewSet):
    """Backs the entire 'My Learning' page: filtered/sorted enrolled-course
    list, quick-stats cards, resume, review, and enrollment creation."""

    serializer_class = EnrolledCourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = Enrollment.objects.filter(student=self.request.user).select_related(
            "course", "course__category", "course__instructor", "certificate"
        ).prefetch_related("course__skills", "lesson_progress")

        params = self.request.query_params

        status_filter = params.get("status")  # "in_progress" | "completed"
        if status_filter in (Enrollment.Status.IN_PROGRESS, Enrollment.Status.COMPLETED):
            qs = qs.filter(status=status_filter)

        category = params.get("category")
        if category and category != "All Categories":
            qs = qs.filter(course__category__name=category)

        search = params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(course__title__icontains=search)
                | Q(course__category__name__icontains=search)
                | Q(course__instructor__name__icontains=search)
                | Q(course__skills__name__icontains=search)
            ).distinct()

        sort_by = params.get("sort", "recent")
        if sort_by == "alphabetical":
            qs = qs.order_by("course__title")
        elif sort_by != "progress":  # "recent" (default): in-progress first, then most recently touched
            qs = qs.order_by("status", "-last_accessed")
        # "progress" sort needs the computed property, applied after fetch:
        if sort_by == "progress":
            qs = sorted(qs, key=lambda e: e.progress_percent, reverse=True)

        return qs

    def create(self, request, *args, **kwargs):
        """POST {course: <id>} — enroll the current student in a course."""
        serializer = EnrollmentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save()
        out = self.get_serializer(enrollment)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """'Resume Learning' button — bumps last_accessed, returns the next lesson."""
        enrollment = self.get_object()
        enrollment.save(update_fields=["last_accessed"])  # auto_now bumps the timestamp
        nxt = enrollment.next_lesson
        return Response({
            "enrollmentId": enrollment.id,
            "nextLesson": {"id": nxt.id, "title": nxt.title} if nxt else None,
        })

    @action(detail=True, methods=["get"])
    def review(self, request, pk=None):
        """'Review' button on a completed course — archive material."""
        enrollment = self.get_object()
        lessons = enrollment.course.lessons.order_by("order").values(
            "id", "title", "order", "resource_url", "video_url"
        )
        return Response({
            "courseTitle": enrollment.course.title,
            "totalLessons": enrollment.total_lessons,
            "lessons": list(lessons),
        })

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Top quick-stats cards: enrolled / in-progress / completed / certificates."""
        qs = Enrollment.objects.filter(student=request.user)
        return Response({
            "totalEnrolled": qs.count(),
            "inProgressCount": qs.filter(status=Enrollment.Status.IN_PROGRESS).count(),
            "completedCount": qs.filter(status=Enrollment.Status.COMPLETED).count(),
            "certificatesEarned": Certificate.objects.filter(enrollment__student=request.user).count(),
        })


class LessonCompleteView(APIView):
    """POST — mark a lesson complete for the current student. Recomputes
    enrollment progress/status and auto-issues a certificate at 100%."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)
        enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.course)
        progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        progress.mark_complete()
        return Response(EnrolledCourseSerializer(enrollment).data)


class CertificateDetailView(APIView):
    """Powers the certificate preview modal."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, certificate_id):
        cert = get_object_or_404(Certificate, certificate_id=certificate_id, enrollment__student=request.user)
        data = CertificateSerializer(cert).data
        data.update({
            "studentName": request.user.get_full_name() or request.user.username,
            "courseTitle": cert.enrollment.course.title,
        })
        return Response(data)


class CertificateListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        enrollments = Enrollment.objects.filter(
            student=request.user
        ).select_related(
            "course",
            "course__category",
            "course__instructor",
        ).prefetch_related(
            "course__skills",
            "lesson_progress",
        )

        certificates = []

        for enrollment in enrollments:
            course = enrollment.course

            completed_lessons = enrollment.completed_lessons
            total_lessons = enrollment.total_lessons
            progress = enrollment.progress_percent

            remaining_lessons = max(
                total_lessons - completed_lessons,
                0
            )

            if enrollment.status == Enrollment.Status.COMPLETED:
                certificate = getattr(
                    enrollment,
                    "certificate",
                    None
                )

                if certificate:
                    certificates.append({
                        "id": certificate.certificate_id,
                        "title": course.title,
                        "track": course.category.name,
                        "credentialId": certificate.certificate_id,
                        "issueDate": certificate.issued_date,
                        "expiryDate": "",
                        "grade": "Completed",
                        "instructor": course.instructor.name,
                        "skills": list(
                            course.skills.values_list(
                                "name",
                                flat=True
                            )
                        ),
                        "status": "verified",
                        "progress": 100,
                        "remainingModules": "Course completed",
                        "verificationHash": certificate.certificate_id,
                    })

            else:
                certificates.append({
                    "id": f"progress-{enrollment.id}",
                    "title": course.title,
                    "track": course.category.name,
                    "credentialId": "",
                    "issueDate": "",
                    "expiryDate": "",
                    "grade": "In Progress",
                    "instructor": course.instructor.name,
                    "skills": list(
                        course.skills.values_list(
                            "name",
                            flat=True
                        )
                    ),
                    "status": "in_progress",
                    "progress": progress,
                    "remainingModules": (
                        f"{remaining_lessons} modules remaining"
                    ),
                    "verificationHash": "",
                })

        return Response(certificates)


class CertificateShareView(APIView):
    """'Share Credential' button — bumps a share counter, returns the link to copy."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, certificate_id):
        cert = get_object_or_404(Certificate, certificate_id=certificate_id, enrollment__student=request.user)
        cert.share_count += 1
        cert.save(update_fields=["share_count"])
        return Response({"verificationUrl": cert.verification_url, "shareCount": cert.share_count})


class CertificateVerifyView(APIView):
    """Public, unauthenticated endpoint for anyone who opens a shared
    verification link to confirm a certificate is genuine."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, certificate_id):
        cert = get_object_or_404(Certificate, certificate_id=certificate_id)
        return Response({
            "valid": True,
            "certificateId": cert.certificate_id,
            "studentName": cert.enrollment.student.get_full_name() or cert.enrollment.student.username,
            "courseTitle": cert.enrollment.course.title,
            "issuedDate": cert.issued_date,
        })

class ScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns the schedule sessions for the Schedule page.
    Attendance and checklist information are specific to the
    currently authenticated student.
    """

    serializer_class = ScheduleSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        enrolled_course_ids = Enrollment.objects.filter(
             student=self.request.user
        ).values_list("course_id", flat=True)

        return ScheduleSession.objects.select_related(
        "course",
        "instructor",
    ).prefetch_related(
        "checklist_items",
        "attendance_records",
    ).filter(
        course_id__in=enrolled_course_ids
    )


class AttendanceCheckInView(APIView):
    """
    Marks the current student as present for a schedule session.
    Only students enrolled in the session's course can check in.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        enrolled_course_ids = Enrollment.objects.filter(
            student=request.user
        ).values_list("course_id", flat=True)

        session = get_object_or_404(
            ScheduleSession,
            id=session_id,
            course_id__in=enrolled_course_ids,
        )

        attendance, created = Attendance.objects.get_or_create(
            student=request.user,
            session=session,
        )

        attendance.status = Attendance.Status.PRESENT
        attendance.check_in_time = timezone.now()
        attendance.save(
            update_fields=["status", "check_in_time"]
        )

        return Response({
            "sessionId": session.id,
            "attendance": attendance.status,
            "checkInTime": attendance.check_in_time,
        })
    
class ChecklistItemView(APIView):
    """
    Add a checklist item for the current student.
    Only students enrolled in the session's course can add checklist items.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        enrolled_course_ids = Enrollment.objects.filter(
            student=request.user
        ).values_list("course_id", flat=True)

        session = get_object_or_404(
            ScheduleSession,
            id=session_id,
            course_id__in=enrolled_course_ids,
        )

        text = request.data.get("text", "").strip()

        if not text:
            return Response(
                {"error": "Checklist text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = ChecklistItem.objects.create(
            session=session,
            student=request.user,
            text=text,
        )

        return Response(
            ChecklistItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class ChecklistItemDetailView(APIView):
    """
    Update or delete a checklist item belonging to the current student.
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, item_id):
        item = get_object_or_404(
            ChecklistItem,
            id=item_id,
            student=request.user,
        )

        serializer = ChecklistItemSerializer(
            item,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request, item_id):
        item = get_object_or_404(
            ChecklistItem,
            id=item_id,
            student=request.user,
        )

        item.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
class ScheduleStatsView(APIView):
    """
    Returns attendance statistics for the currently authenticated student.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        student = request.user

        attendances = Attendance.objects.filter(
            student=student
        ).select_related("session")

        total_sessions = attendances.count()

        attended_sessions = attendances.filter(
            status__in=[
                Attendance.Status.PRESENT,
                Attendance.Status.LATE,
            ]
        ).count()

        if total_sessions > 0:
            overall_attendance = round(
                (attended_sessions / total_sessions) * 100
            )
        else:
            overall_attendance = 0

        # Calculate the current attendance streak.
        attended_dates = set(
            attendances.filter(
                status__in=[
                    Attendance.Status.PRESENT,
                    Attendance.Status.LATE,
                ]
            ).values_list("session__date", flat=True)
        )

        today = timezone.localdate()
        attendance_streak = 0
        current_date = today

        while current_date in attended_dates:
            attendance_streak += 1
            current_date -= timezone.timedelta(days=1)

        return Response({
            "overallAttendance": overall_attendance,
            "attendanceStreak": attendance_streak,
            "attendedSessions": attended_sessions,
            "totalSessions": total_sessions,
        })

class StudentDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        student = request.user

        enrollments = Enrollment.objects.filter(
            student=student
        ).select_related(
            "course",
            "course__category",
            "course__instructor",
        ).prefetch_related(
            "course__skills",
            "lesson_progress",
        )

        profile = getattr(student, "student_profile", None)

        return Response({
            "student": {
                "id": student.id,
                "name": student.username,
                "email": student.email,
                "phone": profile.phone if profile else "",
                "course": profile.course if profile else "",
                "career_goal": profile.career_goal if profile else "",
                "experience_level": profile.experience_level if profile else "",
            },

            "learning": {
                "totalEnrolled": enrollments.count(),
                "completedCount": enrollments.filter(
                    status=Enrollment.Status.COMPLETED
                ).count(),
                "inProgressCount": enrollments.filter(
                    status=Enrollment.Status.IN_PROGRESS
                ).count(),
                "certificatesEarned": Certificate.objects.filter(
                    enrollment__student=student
                ).count(),
            },

            "courses": EnrolledCourseSerializer(
                enrollments,
                many=True
            ).data,
        })

class AchievementListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        achievements = Achievement.objects.filter(
            student=request.user
        )

        serializer = AchievementSerializer(
            achievements,
            many=True
        )

        total_xp = sum(
            achievement.xp
            for achievement in achievements
        )

        unlocked_count = achievements.filter(
            unlocked=True
        ).count()

        total_count = achievements.count()

        all_students = User.objects.filter(
            achievements__isnull=False
        ).distinct()

        student_xp = []

        for student in all_students:
            xp = sum(
                achievement.xp
                for achievement in student.achievements.all()
            )

            student_xp.append({
                "student": student,
                "xp": xp,
            })

        student_xp.sort(
            key=lambda item: item["xp"],
            reverse=True
        )

        rank = next(
            (
                index + 1
                for index, item in enumerate(student_xp)
                if item["student"].id == request.user.id
            ),
            None
        )

        total_students = len(student_xp)

        top_percentage = (
            round((rank / total_students) * 100)
            if rank and total_students
            else None
        )

        leaderboard = []

        for index, item in enumerate(student_xp):
            student = item["student"]

            attendances = Attendance.objects.filter(
                student=student
            ).select_related("session")

            attended_dates = set(
                attendances.filter(
                    status__in=[
                        Attendance.Status.PRESENT,
                        Attendance.Status.LATE,
                    ]
                ).values_list("session__date", flat=True)
            )

            today = timezone.localdate()
            attendance_streak = 0
            current_date = today

            while current_date in attended_dates:
                attendance_streak += 1
                current_date -= timezone.timedelta(days=1)

            leaderboard.append({
                "rank": index + 1,
                "name": student.username,
                "email": student.email,
                "xp": item["xp"],
                "badgesCount": student.achievements.filter(
                    unlocked=True
                ).count(),
                "tier": (
                    "Grandmaster" if item["xp"] >= 4000
                    else "Master" if item["xp"] >= 3000
                    else "Senior Learner" if item["xp"] >= 1000
                    else "Learner"
                ),
                "streak": attendance_streak,
            })

        return Response({
            "achievements": serializer.data,
            "summary": {
                "total_xp": total_xp,
                "unlocked_count": unlocked_count,
                "total_count": total_count,
                "rank": rank,
                "total_students": total_students,
                "top_percentage": top_percentage,
            },
            "leaderboard": leaderboard,
        })
class CertificatePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, certificate_id):
        certificate = get_object_or_404(
            Certificate,
            certificate_id=certificate_id,
            enrollment__student=request.user,
        )

        enrollment = certificate.enrollment
        course = enrollment.course

        # Create PDF in memory
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)

        # Certificate content
        student_name = (
            request.user.get_full_name()
            or request.user.username
        )

        pdf.setTitle("Careergize Certificate")

        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawCentredString(
            300,
            750,
            "CAREERGIZE"
        )

        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(
            300,
            690,
            "Certificate of Completion"
        )

        pdf.setFont("Helvetica", 14)
        pdf.drawCentredString(
            300,
            630,
            "This certificate is proudly presented to"
        )

        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawCentredString(
            300,
            580,
            student_name
        )

        pdf.setFont("Helvetica", 14)
        pdf.drawCentredString(
            300,
            520,
            "for successfully completing"
        )

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawCentredString(
            300,
            470,
            course.title
        )

        pdf.setFont("Helvetica", 11)
        pdf.drawString(
            80,
            390,
            f"Certificate ID: {certificate.certificate_id}"
        )

        pdf.drawString(
            80,
            365,
            f"Issued Date: {certificate.issued_date}"
        )

        pdf.drawString(
            80,
            340,
            f"Instructor: {course.instructor.name}"
        )

        pdf.setFont("Helvetica-Oblique", 11)
        pdf.drawCentredString(
            300,
            100,
            "Verified by Careergize Learning Hub"
        )

        pdf.save()

        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{certificate.certificate_id}.pdf",
            content_type="application/pdf",
        )

class TranscriptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        student = request.user

        enrollments = Enrollment.objects.filter(
            student=student
        ).select_related(
            "course",
            "course__category",
            "course__instructor",
        ).prefetch_related(
            "course__skills",
            "lesson_progress",
        )

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)

        student_name = student.get_full_name() or student.username

        pdf.setTitle("Careergize Student Transcript")

        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawCentredString(300, 750, "CAREERGIZE")

        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(300, 700, "Student Transcript")

        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(80, 650, f"Student: {student_name}")

        pdf.setFont("Helvetica", 12)
        pdf.drawString(80, 625, f"Email: {student.email}")

        y = 570

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(80, y, "Enrolled Courses")

        y -= 30

        pdf.setFont("Helvetica", 11)

        for enrollment in enrollments:
            course = enrollment.course

            pdf.drawString(
                80,
                y,
                f"{course.title} - {enrollment.progress_percent}%"
            )

            y -= 20

            if y < 80:
                pdf.showPage()
                y = 750
                pdf.setFont("Helvetica", 11)

        pdf.setFont("Helvetica-Oblique", 10)
        pdf.drawCentredString(
            300,
            50,
            "Generated by Careergize Learning Hub"
        )

        pdf.save()

        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename="student-transcript.pdf",
            content_type="application/pdf",
        )

class CertificateVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, certificate_id):
        certificate = get_object_or_404(
            Certificate,
            certificate_id=certificate_id
        )

        return Response({
            "valid": True,
            "certificateId": certificate.certificate_id,
            "studentName": (
                certificate.enrollment.student.get_full_name()
                or certificate.enrollment.student.username
            ),
            "courseTitle": certificate.enrollment.course.title,
            "issuedDate": certificate.issued_date,
            "instructor": certificate.enrollment.course.instructor.name,
        })