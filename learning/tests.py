from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from authentication.models import StudentProfile
from courses.models import Category, Course, Instructor
from .models import Achievement, Enrollment, ScheduleSession

User = get_user_model()


class AdminLearningViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="pass", is_staff=True)
        self.student = User.objects.create_user("learner", password="pass", email="learner@example.com")
        StudentProfile.objects.create(user=self.student, status="approved")
        self.category = Category.objects.create(name="Development")
        self.instructor = Instructor.objects.create(name="Instructor One")
        self.course = Course.objects.create(
            title="Python Foundations", category=self.category, instructor=self.instructor,
        )
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.admin).key}")
        self.student_client = APIClient()
        self.student_client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.student).key}")

    def test_admin_can_create_update_and_list_schedule_without_touching_attendance(self):
        payload = {
            "course": self.course.id, "topic": "Intro session", "date": date.today().isoformat(),
            "start_time": "10:00", "end_time": "11:00", "instructor": self.instructor.id,
            "platform": "Zoom", "meet_url": "https://example.com/class",
        }
        created = self.admin_client.post("/api/admin/schedule/", payload, format="json")
        self.assertEqual(created.status_code, 201)
        session_id = created.data["id"]
        self.assertEqual(created.data["enrolled_students"], 0)
        updated = self.admin_client.patch(
            f"/api/admin/schedule/{session_id}/", {"topic": "Updated session"}, format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["topic"], "Updated session")
        invalid_time = self.admin_client.patch(
            f"/api/admin/schedule/{session_id}/", {"end_time": "09:00"}, format="json",
        )
        self.assertEqual(invalid_time.status_code, 400)
        self.assertEqual(self.admin_client.get("/api/admin/schedule/").status_code, 200)
        self.assertEqual(self.student_client.get("/api/admin/schedule/").status_code, 403)
        self.assertEqual(APIClient().get("/api/admin/schedule/").status_code, 401)
        self.assertFalse(Enrollment.objects.exists())

    def test_admin_achievement_list_only_shows_student_owned_records(self):
        Achievement.objects.create(student=self.student, title="First course milestone", unlocked=True)
        staff_with_achievement = User.objects.create_user("staff", password="pass", is_staff=True)
        Achievement.objects.create(student=staff_with_achievement, title="Staff record", unlocked=True)
        response = self.admin_client.get("/api/admin/achievements/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student_id"], self.student.id)
        self.assertEqual(response.data[0]["title"], "First course milestone")
        self.assertEqual(self.student_client.get("/api/admin/achievements/").status_code, 403)
