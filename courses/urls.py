from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, CourseViewSet
from .admin_views import AdminCourseViewSet

router = DefaultRouter()
router.register("admin/courses", AdminCourseViewSet, basename="admin-courses")
router.register("categories", CategoryViewSet, basename="category")
router.register("courses", CourseViewSet, basename="course")

urlpatterns = [path("", include(router.urls))]
