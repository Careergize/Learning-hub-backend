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

            # Personal Information
            'phone': student_profile.phone,
            'date_of_birth': student_profile.date_of_birth,
            'age': self.calculate_age(student_profile.date_of_birth),
            'address': student_profile.address,
            'city': student_profile.city,

            # Learning & Career
            'course': student_profile.course,
            'career_goal': student_profile.career_goal,
            'experience_level': student_profile.experience_level,
            'skills': student_profile.skills,
            'github': student_profile.github,
            'linkedin': student_profile.linkedin,

            # About Me
            'bio': student_profile.bio,

            # System-controlled
            'status': student_profile.status,
            'created_at': student_profile.created_at,
        })


    def put(self, request, user_id):

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

        # Personal Information

        if 'phone' in request.data:
            student_profile.phone = request.data.get('phone', '')

        if 'date_of_birth' in request.data:
            date_of_birth = request.data.get('date_of_birth')

            if date_of_birth in ['', None]:
                student_profile.date_of_birth = None
            else:
                student_profile.date_of_birth = date_of_birth

        if 'address' in request.data:
            student_profile.address = request.data.get('address', '')

        if 'city' in request.data:
            student_profile.city = request.data.get('city', '')


        # Learning & Career

        if 'course' in request.data:
            student_profile.course = request.data.get('course', '')

        if 'career_goal' in request.data:
            student_profile.career_goal = request.data.get('career_goal', '')

        if 'experience_level' in request.data:
            student_profile.experience_level = request.data.get(
                'experience_level',
                ''
            )

        if 'skills' in request.data:
            skills = request.data.get('skills')

            if isinstance(skills, list):
                student_profile.skills = skills

        if 'github' in request.data:
            student_profile.github = request.data.get('github', '')

        if 'linkedin' in request.data:
            student_profile.linkedin = request.data.get('linkedin', '')


        # About Me

        if 'bio' in request.data:
            student_profile.bio = request.data.get('bio', '')


        # Save changes
        student_profile.save()


        return Response({
            'id': user.id,
            'name': user.username,
            'email': user.email,

            # Personal Information
            'phone': student_profile.phone,
            'date_of_birth': student_profile.date_of_birth,
            'age': self.calculate_age(student_profile.date_of_birth),
            'address': student_profile.address,
            'city': student_profile.city,

            # Learning & Career
            'course': student_profile.course,
            'career_goal': student_profile.career_goal,
            'experience_level': student_profile.experience_level,
            'skills': student_profile.skills,
            'github': student_profile.github,
            'linkedin': student_profile.linkedin,

            # About Me
            'bio': student_profile.bio,

            # System-controlled
            'status': student_profile.status,
            'created_at': student_profile.created_at,
        })


    @staticmethod
    def calculate_age(date_of_birth):

        if not date_of_birth:
            return None

        from datetime import date

        today = date.today()

        age = today.year - date_of_birth.year

        if (
            today.month,
            today.day
        ) < (
            date_of_birth.month,
            date_of_birth.day
        ):
            age -= 1

        return age