from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from datetime import date
from django.db.models import Count, Q
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAdminUser

from .models import StudentProfile
from courses.models import Course
from learning.models import Achievement, Enrollment, ScheduleSession


class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
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

        if user.is_staff or user.is_superuser:
            return Response(
                {'error': 'Admin accounts must use the Admin Login page.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check student approval status after authenticating the credentials.
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

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'message': 'Login successful',
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
            }
        })

       


class RegisterView(APIView):
    permission_classes = [AllowAny]

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
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = StudentProfile.objects.filter(
            user__is_staff=False,
            user__is_superuser=False,
        ).select_related('user').prefetch_related(
            'user__enrollments__course__lessons',
            'user__enrollments__lesson_progress',
        ).order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter in {'pending', 'approved', 'rejected'}:
            students = students.filter(status=status_filter)

        search = request.query_params.get('search', '').strip()
        if search:
            students = students.filter(
                Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(course__icontains=search)
            )

        student_list = []

        for student in students:
            enrollments = list(student.user.enrollments.all())
            course_data = []
            progress_values = []
            for enrollment in enrollments:
                total_lessons = len(enrollment.course.lessons.all())
                completed_lessons = sum(
                    1 for progress in enrollment.lesson_progress.all()
                    if progress.is_completed
                )
                progress_percent = (
                    round(completed_lessons / total_lessons * 100)
                    if total_lessons else 0
                )
                progress_values.append(progress_percent)
                course_data.append({
                    'id': enrollment.course_id,
                    'title': enrollment.course.title,
                    'status': enrollment.status,
                    'progress': progress_percent,
                    'completed_lessons': completed_lessons,
                    'total_lessons': total_lessons,
                })

            student_list.append({
                'id': student.id,
                'user_id': student.user_id,
                'name': student.user.username,
                'email': student.user.email,
                'status': student.status,
                'created_at': student.created_at,
                'phone': student.phone,
                'age': student.age,
                'course': student.course,
                'career_goal': student.career_goal,
                'experience_level': student.experience_level,
                'enrollment_count': len(enrollments),
                'completed_courses': sum(
                    enrollment.status == 'completed' for enrollment in enrollments
                ),
                'average_progress': (
                    round(sum(progress_values) / len(progress_values))
                    if progress_values else 0
                ),
                'courses': course_data,
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
            student = StudentProfile.objects.get(
                id=student_id,
                user__is_staff=False,
                user__is_superuser=False,
            )
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


class AdminDashboardView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = StudentProfile.objects.filter(
            user__is_staff=False,
            user__is_superuser=False,
        )
        enrollments = Enrollment.objects.filter(
            student__is_staff=False,
            student__is_superuser=False,
        )

        enrollment_progress = enrollments.annotate(
            lesson_count=Count('course__lessons', distinct=True),
            completed_lesson_count=Count(
                'lesson_progress',
                filter=Q(lesson_progress__is_completed=True),
                distinct=True,
            ),
        ).values_list('lesson_count', 'completed_lesson_count')
        progress_values = [
            round(completed / total * 100) if total else 0
            for total, completed in enrollment_progress
        ]

        now = timezone.localtime()
        months = []
        month_keys = []
        for offset in range(5, -1, -1):
            month_index = now.month - 1 - offset
            year = now.year + month_index // 12
            month = month_index % 12 + 1
            month_keys.append((year, month))
        registration_counts = students.filter(
            created_at__year__in={year for year, _ in month_keys}
        ).values('created_at__year', 'created_at__month').annotate(total=Count('id'))
        registration_lookup = {
            (item['created_at__year'], item['created_at__month']): item['total']
            for item in registration_counts
        }
        for year, month in month_keys:
            months.append({
                'month': date(year, month, 1).strftime('%b'),
                'year': year,
                'count': registration_lookup.get((year, month), 0),
            })

        progress_buckets = [
            {'label': '0–24%', 'count': 0},
            {'label': '25–49%', 'count': 0},
            {'label': '50–74%', 'count': 0},
            {'label': '75–99%', 'count': 0},
            {'label': '100%', 'count': 0},
        ]
        for value in progress_values:
            bucket = min(value // 25, 4)
            progress_buckets[bucket]['count'] += 1

        course_enrollments = Course.objects.annotate(
            enrollment_count=Count(
                'enrollments',
                filter=Q(
                    enrollments__student__is_staff=False,
                    enrollments__student__is_superuser=False,
                ),
                distinct=True,
            )
        ).order_by('-enrollment_count', 'title').values(
            'title', 'enrollment_count'
        )[:6]

        recent_registrations = students.select_related('user').order_by('-created_at')[:6]
        recent_enrollments = enrollments.select_related(
            'student', 'course'
        ).order_by('-enrolled_at')[:6]
        today = timezone.localdate()
        upcoming_classes = ScheduleSession.objects.filter(
            Q(date__gt=today)
            | Q(date=today, start_time__gte=timezone.localtime().time())
        ).select_related('course', 'instructor').order_by('date', 'start_time')[:6]
        student_achievements = Achievement.objects.filter(
            student__is_staff=False,
            student__is_superuser=False,
            student__student_profile__isnull=False,
        )

        return Response({
            'admin': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
            },
            'stats': {
                'total_students': students.count(),
                'pending_students': students.filter(status='pending').count(),
                'approved_students': students.filter(status='approved').count(),
                'rejected_students': students.filter(status='rejected').count(),
                'total_courses': Course.objects.count(),
                'published_courses': Course.objects.filter(is_published=True).count(),
                'enrollments': enrollments.count(),
                'completed_enrollments': enrollments.filter(status='completed').count(),
                'in_progress_enrollments': enrollments.filter(status='in_progress').count(),
                'average_progress': (
                    round(sum(progress_values) / len(progress_values))
                    if progress_values else 0
                ),
                'achievements': student_achievements.count(),
                'unlocked_achievements': student_achievements.filter(unlocked=True).count(),
            },
            'registrations_by_month': months,
            'progress_distribution': progress_buckets,
            'enrollments_by_course': list(course_enrollments),
            'recent_registrations': [{
                'id': profile.id,
                'name': profile.user.get_full_name() or profile.user.username,
                'email': profile.user.email,
                'status': profile.status,
                'created_at': profile.created_at,
            } for profile in recent_registrations],
            'recent_enrollments': [{
                'id': enrollment.id,
                'student': enrollment.student.get_full_name() or enrollment.student.username,
                'course': enrollment.course.title,
                'status': enrollment.status,
                'enrolled_at': enrollment.enrolled_at,
            } for enrollment in recent_enrollments],
            'upcoming_classes': [{
                'id': session.id,
                'course': session.course.title,
                'topic': session.topic,
                'date': session.date,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'instructor': session.instructor.name,
            } for session in upcoming_classes],
        })
class AdminLoginView(APIView):

    permission_classes = [AllowAny]

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

        
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'Admin login successful',
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
            }
        })


class StudentProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        if request.user.id != user_id:
            return Response(
                {'error': 'You can only access your own profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Automatically get or create the profile
        student_profile, _ = StudentProfile.objects.get_or_create(
            user=user,
            defaults={'status': 'approved'}
        )
       
        
        return Response({
            'id': user.id,
            'name': user.username,
            'email': user.email,
            'phone': student_profile.phone,
            'date_of_birth': student_profile.date_of_birth,
            'age': self.calculate_age(student_profile.date_of_birth),
            'address': student_profile.address,
            'city': student_profile.city,
            'course': student_profile.course,
            'career_goal': student_profile.career_goal,
            'experience_level': student_profile.experience_level,
            'skills': student_profile.skills,
            'github': student_profile.github,
            'linkedin': student_profile.linkedin,
            'bio': student_profile.bio,
            'status': student_profile.status,
            'created_at': student_profile.created_at,
        })

    def put(self, request, user_id):
        if request.user.id != user_id:
            return Response(
                {'error': 'You can only update your own profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

               # Automatically get or create the profile
        student_profile, _ = StudentProfile.objects.get_or_create(
            user=user,
            defaults={'status': 'approved'}
        )

        if 'name' in request.data:
            user.username = request.data.get('name', '')
            user.save()

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

        from datetime import date, datetime

        if isinstance(date_of_birth, str):
            date_of_birth = datetime.strptime(
                date_of_birth,
                "%Y-%m-%d"
            ).date()

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
class MyProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

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
            'date_of_birth': student_profile.date_of_birth,
            'age': self.calculate_age(student_profile.date_of_birth),
            'address': student_profile.address,
            'city': student_profile.city,

            'course': student_profile.course,
            'career_goal': student_profile.career_goal,
            'experience_level': student_profile.experience_level,
            'skills': student_profile.skills,
            'github': student_profile.github,
            'linkedin': student_profile.linkedin,

            'bio': student_profile.bio,
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

        if (today.month, today.day) < (
            date_of_birth.month,
            date_of_birth.day
        ):
            age -= 1

        return age
