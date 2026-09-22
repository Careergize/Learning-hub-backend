from django.urls import path
from .views import (
    LoginView,
    RegisterView,
    StudentApprovalView,
    AdminLoginView,
    StudentProfileView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('students/', StudentApprovalView.as_view(), name='students'),
    path('admin-login/', AdminLoginView.as_view(), name='admin-login'),
    path('profile/<int:user_id>/', StudentProfileView.as_view(), name='student-profile'),
]