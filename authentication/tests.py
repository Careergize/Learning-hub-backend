from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import StudentProfile


class AuthenticationAndStudentListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="student-pass"
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student, status="approved"
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="admin-pass",
            is_staff=True,
        )
        self.admin_profile = StudentProfile.objects.create(
            user=self.admin, status="approved"
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.student_token = Token.objects.create(user=self.student)

    def test_student_login_accepts_student_and_rejects_admin(self):
        student_response = self.client.post(
            "/api/login/",
            {"email": "student@example.com", "password": "student-pass"},
            format="json",
        )
        self.assertEqual(student_response.status_code, 200)

        admin_response = self.client.post(
            "/api/login/",
            {"email": "admin@example.com", "password": "admin-pass"},
            format="json",
        )
        self.assertEqual(admin_response.status_code, 403)
        self.assertIn("Admin Login", admin_response.data["error"])

    def test_admin_login_accepts_admin_and_rejects_student(self):
        admin_response = self.client.post(
            "/api/admin-login/",
            {"username": "admin", "password": "admin-pass"},
            format="json",
        )
        self.assertEqual(admin_response.status_code, 200)

        student_response = self.client.post(
            "/api/admin-login/",
            {"username": "student", "password": "student-pass"},
            format="json",
        )
        self.assertEqual(student_response.status_code, 403)

    def test_student_list_and_actions_exclude_admin_profiles(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        self.student_profile.status = "pending"
        self.student_profile.save(update_fields=["status"])

        response = self.client.get("/api/students/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [self.student_profile.id])
        pending_response = self.client.get("/api/students/?status=pending&search=student%40example.com")
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual([item["id"] for item in pending_response.data], [self.student_profile.id])

        reject_admin = self.client.post(
            "/api/students/",
            {"student_id": self.admin_profile.id, "action": "reject"},
            format="json",
        )
        self.assertEqual(reject_admin.status_code, 404)
        self.admin_profile.refresh_from_db()
        self.assertEqual(self.admin_profile.status, "approved")

        approve_student = self.client.post(
            "/api/students/",
            {"student_id": self.student_profile.id, "action": "approve"},
            format="json",
        )
        self.assertEqual(approve_student.status_code, 200)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.status, "approved")

        reject_student = self.client.post(
            "/api/students/",
            {"student_id": self.student_profile.id, "action": "reject"},
            format="json",
        )
        self.assertEqual(reject_student.status_code, 200)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.status, "rejected")

    def test_admin_dashboard_stats_are_real_and_admin_only(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        response = self.client.get("/api/admin/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stats"]["total_students"], 1)
        self.assertEqual(response.data["stats"]["approved_students"], 1)
        self.assertEqual(len(response.data["registrations_by_month"]), 6)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}")
        forbidden = self.client.get("/api/admin/dashboard/")
        self.assertEqual(forbidden.status_code, 403)
