import json
from decimal import Decimal
from django.test import TestCase, Client
from userApp.models import (
    User,
    Instructor,
    Course,
    Module,
    Lesson,
    Payment,
    Enrollment,
)
from userApp.auth_utils import generate_tokens


class AdminAppTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Admin User
        self.admin_user = User.objects.create_user(
            email='superadmin@learnflow.com',
            name='Super Admin',
            password='AdminPassword123!',
            is_staff=True,
            is_superuser=True,
        )
        self.admin_tokens = generate_tokens(self.admin_user)
        self.admin_auth_headers = {
            'HTTP_AUTHORIZATION': f"Bearer {self.admin_tokens['access']}",
        }

        # 2. Create Regular Student User
        self.student_user = User.objects.create_user(
            email='student@learnflow.com',
            name='Regular Student',
            password='StudentPassword123!',
            is_staff=False,
            is_superuser=False,
        )
        self.student_tokens = generate_tokens(self.student_user)
        self.student_auth_headers = {
            'HTTP_AUTHORIZATION': f"Bearer {self.student_tokens['access']}",
        }

        # 3. Create Instructor
        self.instructor = Instructor.objects.create(
            name='Devon Vance',
            title='Principal Paid Media Buyer',
            bio='Specializes in scaling Meta & Google Ads.',
            avatar='https://example.com/avatar.jpg'
        )

        # 4. Create Course
        self.course = Course.objects.create(
            title='Performance Marketing Masterclass',
            slug='performance-marketing-masterclass',
            short_description='Master Meta and Google Ads',
            description='In-depth course on performance marketing',
            thumbnail='https://example.com/thumb.jpg',
            instructor=self.instructor,
            category='Performance Marketing',
            price=Decimal('4999.00'),
            original_price=Decimal('9999.00'),
            duration='18h 45m',
            level='Intermediate to Advanced',
            language='English',
            is_published=True,
            is_featured=False,
            is_bestseller=True,
            rating=Decimal('4.95'),
            total_ratings=120,
            total_students=580,
            learning_outcomes=['Outcome 1', 'Outcome 2'],
            requirements=['Prereq 1'],
        )

        # 5. Create Module & Lesson
        self.module = Module.objects.create(
            course=self.course,
            title='Module 1: Foundations',
            order=1,
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Lesson 1: Introduction',
            duration='10:00',
            duration_seconds=600,
            video_url='https://example.com/video.mp4',
            is_preview=True,
            order=1,
        )

        # 6. Create Payment & Enrollment
        self.payment = Payment.objects.create(
            user=self.student_user,
            course=self.course,
            razorpay_order_id='order_test_123',
            razorpay_payment_id='pay_test_123',
            amount=499900,  # paise
            currency='INR',
            status='paid',
        )
        self.enrollment = Enrollment.objects.create(
            user=self.student_user,
            course=self.course,
            payment=self.payment,
            status='active',
            progress_percentage=40,
        )

    # =========================================================
    #  1. Authentication & Authorization Tests
    # =========================================================

    def test_admin_login_success(self):
        response = self.client.post(
            '/api/admin/auth/login/',
            data=json.dumps({'email': 'superadmin@learnflow.com', 'password': 'AdminPassword123!'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertTrue(data['user']['is_staff'])

    def test_admin_login_invalid_password(self):
        response = self.client.post(
            '/api/admin/auth/login/',
            data=json.dumps({'email': 'superadmin@learnflow.com', 'password': 'WrongPassword'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_regular_student_cannot_login_as_admin(self):
        response = self.client.post(
            '/api/admin/auth/login/',
            data=json.dumps({'email': 'student@learnflow.com', 'password': 'StudentPassword123!'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_request_rejected(self):
        response = self.client.get('/api/admin/dashboard/stats/')
        self.assertEqual(response.status_code, 401)

    def test_student_token_forbidden_on_admin_api(self):
        response = self.client.get('/api/admin/dashboard/stats/', **self.student_auth_headers)
        self.assertEqual(response.status_code, 403)

    def test_admin_token_refresh(self):
        response = self.client.post(
            '/api/admin/auth/token/refresh/',
            data=json.dumps({'refresh': self.admin_tokens['refresh']}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access', data)

    # =========================================================
    #  2. Dashboard Statistics Tests
    # =========================================================

    def test_dashboard_stats_metrics(self):
        response = self.client.get('/api/admin/dashboard/stats/', **self.admin_auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('stats', data)
        self.assertEqual(data['stats']['total_courses'], 1)
        self.assertEqual(data['stats']['total_enrollments'], 1)
        self.assertEqual(data['stats']['total_revenue'], 4999.0)
        self.assertIn('course_performance', data)
        self.assertIn('recent_enrollments', data)
        self.assertIn('recent_payments', data)

    # =========================================================
    #  3. Course Management Tests
    # =========================================================

    def test_list_courses(self):
        response = self.client.get('/api/admin/courses/', **self.admin_auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['title'], 'Performance Marketing Masterclass')

    def test_create_course(self):
        payload = {
            'title': 'SEO Growth & Arbitrage',
            'category': 'Growth Marketing',
            'price': 3999,
            'original_price': 7999,
            'instructor_id': self.instructor.id,
            'duration': '12h 00m',
            'learning_outcomes': ['Master Technical SEO'],
            'requirements': ['Basic HTML'],
        }
        response = self.client.post(
            '/api/admin/courses/',
            data=json.dumps(payload),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['title'], 'SEO Growth & Arbitrage')
        self.assertTrue(Course.objects.filter(title='SEO Growth & Arbitrage').exists())

    def test_update_course(self):
        payload = {'title': 'Performance Marketing Masterclass (Updated)', 'price': 5999}
        response = self.client.put(
            f'/api/admin/courses/{self.course.id}/',
            data=json.dumps(payload),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Performance Marketing Masterclass (Updated)')
        self.assertEqual(float(self.course.price), 5999.0)

    def test_toggle_course_publish(self):
        response = self.client.post(
            f'/api/admin/courses/{self.course.id}/toggle-publish/',
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_published'])
        self.course.refresh_from_db()
        self.assertFalse(self.course.is_published)

    def test_delete_course(self):
        response = self.client.delete(
            f'/api/admin/courses/{self.course.id}/',
            **self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Course.objects.filter(id=self.course.id).exists())

    # =========================================================
    #  4. Curriculum Tests
    # =========================================================

    def test_get_curriculum(self):
        response = self.client.get(
            f'/api/admin/courses/{self.course.id}/curriculum/',
            **self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['modules']), 1)
        self.assertEqual(data['modules'][0]['title'], 'Module 1: Foundations')
        self.assertEqual(len(data['modules'][0]['lessons']), 1)

    def test_create_module_and_lesson(self):
        # Create module
        m_res = self.client.post(
            f'/api/admin/courses/{self.course.id}/modules/',
            data=json.dumps({'title': 'Module 2: Advanced Scaling'}),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(m_res.status_code, 201)
        mod_id = m_res.json()['id']

        # Create lesson
        l_res = self.client.post(
            f'/api/admin/modules/{mod_id}/lessons/',
            data=json.dumps({
                'title': 'Lesson 2.1: Meta Pixel Tracking',
                'duration': '20:00',
                'duration_seconds': 1200,
                'video_url': 'https://example.com/pixel.mp4',
                'is_preview': False
            }),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(l_res.status_code, 201)
        self.assertEqual(l_res.json()['title'], 'Lesson 2.1: Meta Pixel Tracking')

    def test_reorder_modules(self):
        mod2 = Module.objects.create(course=self.course, title='Module 2', order=2)
        payload = {'orders': [{'id': mod2.id, 'order': 1}, {'id': self.module.id, 'order': 2}]}
        response = self.client.post(
            f'/api/admin/courses/{self.course.id}/modules/reorder/',
            data=json.dumps(payload),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        mod2.refresh_from_db()
        self.assertEqual(mod2.order, 1)

    # =========================================================
    #  5. Student Directory & Updates
    # =========================================================

    def test_list_students(self):
        response = self.client.get('/api/admin/students/', **self.admin_auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data['count'], 2)

    def test_student_detail(self):
        response = self.client.get(f'/api/admin/students/{self.student_user.id}/', **self.admin_auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['email'], 'student@learnflow.com')
        self.assertEqual(len(data['enrollments']), 1)
        self.assertEqual(len(data['payments']), 1)

    def test_patch_student(self):
        response = self.client.patch(
            f'/api/admin/students/{self.student_user.id}/',
            data=json.dumps({'is_active': False}),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(response.status_code, 200)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)

    # =========================================================
    #  6. Instructor CRUD Tests
    # =========================================================

    def test_instructor_crud(self):
        # List
        res = self.client.get('/api/admin/instructors/', **self.admin_auth_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)

        # Create
        create_res = self.client.post(
            '/api/admin/instructors/',
            data=json.dumps({'name': 'Sarah Jenkins', 'title': 'Head of Creative', 'bio': 'Creative director'}),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(create_res.status_code, 201)
        new_id = create_res.json()['id']

        # Update
        upd_res = self.client.put(
            f'/api/admin/instructors/{new_id}/',
            data=json.dumps({'title': 'Senior Creative Strategist'}),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(upd_res.status_code, 200)
        self.assertEqual(upd_res.json()['title'], 'Senior Creative Strategist')

        # Delete
        del_res = self.client.delete(f'/api/admin/instructors/{new_id}/', **self.admin_auth_headers)
        self.assertEqual(del_res.status_code, 200)

    # =========================================================
    #  7. Enrollment & Payment Management
    # =========================================================

    def test_enrollment_list_and_patch(self):
        # List
        res = self.client.get('/api/admin/enrollments/', **self.admin_auth_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)

        # Patch status & progress
        patch_res = self.client.patch(
            f'/api/admin/enrollments/{self.enrollment.id}/',
            data=json.dumps({'status': 'completed', 'progress_percentage': 100}),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(patch_res.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, 'completed')
        self.assertEqual(self.enrollment.progress_percentage, 100)

    def test_payments_list_and_detail(self):
        res = self.client.get('/api/admin/payments/', **self.admin_auth_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)

        detail_res = self.client.get(f'/api/admin/payments/{self.payment.id}/', **self.admin_auth_headers)
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()['status'], 'paid')

    # =========================================================
    #  8. Settings Profile & Password Change
    # =========================================================

    def test_settings_profile_and_password(self):
        # Profile GET
        p_res = self.client.get('/api/admin/profile/', **self.admin_auth_headers)
        self.assertEqual(p_res.status_code, 200)
        self.assertEqual(p_res.json()['email'], 'superadmin@learnflow.com')

        # Profile PUT
        put_res = self.client.put(
            '/api/admin/profile/',
            data=json.dumps({'name': 'Chief Admin Officer', 'bio': 'Platform Director'}),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(put_res.status_code, 200)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.name, 'Chief Admin Officer')

        # Change Password
        pwd_res = self.client.post(
            '/api/admin/change-password/',
            data=json.dumps({'current_password': 'AdminPassword123!', 'new_password': 'BrandNewPassword456!'}),
            content_type='application/json',
            **self.admin_auth_headers
        )
        self.assertEqual(pwd_res.status_code, 200)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('BrandNewPassword456!'))
