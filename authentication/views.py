from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import StudentProfile


class LoginView(APIView):

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check student approval status
        try:
            student_profile = user.student_profile
        except StudentProfile.DoesNotExist:
            student_profile = None

        if student_profile and student_profile.status == 'pending':
            return Response(
                {'error': 'Your account is waiting for admin approval.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if student_profile and student_profile.status == 'rejected':
            return Response(
                {'error': 'Your registration request was rejected.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check password
        user = authenticate(
            username=user.username,
            password=password
        )

        if user is None:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        })



class RegisterView(APIView):

    def post(self, request):

        name = request.data.get('name')
        email = request.data.get('email')
        password = request.data.get('password')

        phone = request.data.get('phone')
        age = request.data.get('age')
        course = request.data.get('course')

        if not name or not email or not password:
            return Response(
                {'error': 'Name, email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create a unique username internally.
        # The student's actual name is still stored/displayed separately.
        username = name.strip()

        if User.objects.filter(username=username).exists():
            username = f"{username}_{User.objects.count() + 1}"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        StudentProfile.objects.create(
            user=user,
            phone=phone,
            age=age if age else None,
            course=course,
            status='pending'
        )

        return Response(
            {
                'message': 'Registration submitted. Waiting for admin approval.',
                'status': 'pending'
            },
            status=status.HTTP_201_CREATED
        )




class StudentApprovalView(APIView):

    def get(self, request):
        students = StudentProfile.objects.all().order_by('-created_at')

        student_list = []

        for student in students:
            student_list.append({
                'id': student.id,
                'name': student.user.username,
                'email': student.user.email,
                'status': student.status,
                'created_at': student.created_at,
            })

        return Response(student_list)


    def post(self, request):
        student_id = request.data.get('student_id')
        action = request.data.get('action')

        if not student_id or not action:
            return Response(
                {'error': 'student_id and action are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = StudentProfile.objects.get(id=student_id)
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if action == 'approve':
            student.status = 'approved'
            student.save()

            return Response({
                'message': 'Student approved successfully.',
                'status': student.status
            })

        elif action == 'reject':
            student.status = 'rejected'
            student.save()

            return Response({
                'message': 'Student rejected successfully.',
                'status': student.status
            })

        return Response(
            {'error': 'Invalid action. Use approve or reject.'},
            status=status.HTTP_400_BAD_REQUEST
        )
class AdminLoginView(APIView):

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {'error': 'Invalid username or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_staff:
            return Response(
                {'error': 'You do not have admin access.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response({
            'message': 'Admin login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
            }
        })



class StudentProfileView(APIView):

    def get(self, request, user_id):

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            student_profile = user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Student profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'id': user.id,
            'name': user.username,
            'email': user.email,
            'phone': student_profile.phone,
            'age': student_profile.age,
            'course': student_profile.course,
            'status': student_profile.status,
            'created_at': student_profile.created_at,
        })

