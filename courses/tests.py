from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from learning.models import Enrollment

from .models import Category, Course, Instructor


class AdminCourseApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user("course-admin", password="admin-pass", is_staff=True)
        self.student = User.objects.create_user("course-student", password="student-pass")
        self.admin_token = Token.objects.create(user=self.admin)
        self.student_token = Token.objects.create(user=self.student)
        self.category = Category.objects.create(name="Development")
        self.instructor = Instructor.objects.create(name="Test Instructor")

    def test_admin_can_create_update_and_view_enrolled_students_without_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

        created = self.client.post(
            "/api/admin/courses/",
            {
                "title": "Backend Foundations",
                "category": self.category.id,
                "instructor": self.instructor.id,
                "level": "Beginner",
                "duration_weeks": 4,
                "short_description": "API and database foundations",
                "description": "A real admin-managed course.",
                "is_published": False,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        course = Course.objects.get(pk=created.data["id"])

        Enrollment.objects.create(student=self.student, course=course)
        listed = self.client.get("/api/admin/courses/")
        self.assertEqual(listed.status_code, 200)
        data = listed.data["results"][0]
        self.assertEqual(data["enrollment_count"], 1)
        self.assertEqual(data["enrolled_students"][0]["name"], self.student.username)

        updated = self.client.patch(
            f"/api/admin/courses/{course.id}/",
            {"is_published": True},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        course.refresh_from_db()
        self.assertTrue(course.is_published)

        public_catalog = self.client.get("/api/courses/")
        self.assertEqual(public_catalog.status_code, 200)
        self.assertIn(course.slug, [item["slug"] for item in public_catalog.data["results"]])

        delete_response = self.client.delete(f"/api/admin/courses/{course.id}/")
        self.assertEqual(delete_response.status_code, 405)

    def test_course_admin_endpoints_reject_student_and_invalid_duration(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.student_token.key}")
        self.assertEqual(self.client.get("/api/admin/courses/").status_code, 403)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        invalid = self.client.post(
            "/api/admin/courses/",
            {
                "title": "Invalid Duration Course",
                "category": self.category.id,
                "instructor": self.instructor.id,
                "level": "Beginner",
                "duration_weeks": 0,
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
