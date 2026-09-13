import json
from django.test import TestCase, Client
from .models import User, Instructor, Course, Module, Lesson, FAQ, Payment, Enrollment, LessonProgress
from .auth_utils import generate_tokens


class ELearningBackendSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Instructor
        self.instructor = Instructor.objects.create(
            name='Devon Vance',
            title='Growth Architect',
            bio='Expert instructor'
        )

        # 2. Create Course
        self.course = Course.objects.create(
            title='Performance Marketing Masterclass',
            slug='performance-marketing-masterclass',
            price=4999.00,
            original_price=12999.00,
            is_published=True,
            instructor=self.instructor
        )

        # 3. Create Module & Lessons
        self.module = Module.objects.create(
            course=self.course,
            title='Module 1: Unit Economics',
            order=1
        )

        self.preview_lesson = Lesson.objects.create(
            module=self.module,
            title='Lesson 1: Foundations (Preview)',
            duration='10:00',
            duration_seconds=600,
            is_preview=True,
            order=1
        )

        self.protected_lesson = Lesson.objects.create(
            module=self.module,
            title='Lesson 2: Advanced Scaling (Protected)',
            duration='20:00',
            duration_seconds=1200,
            is_preview=False,
            order=2
        )

        # 4. Create User A (Purchaser)
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            name='User A',
            password='password123'
        )
        self.tokens_a = generate_tokens(self.user_a)
        self.auth_headers_a = {'HTTP_AUTHORIZATION': f"Bearer {self.tokens_a['access']}"}

        # 5. Create User B (Non-Purchaser)
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            name='User B',
            password='password123'
        )
        self.tokens_b = generate_tokens(self.user_b)
        self.auth_headers_b = {'HTTP_AUTHORIZATION': f"Bearer {self.tokens_b['access']}"}

        # 6. User A buys Course
        self.payment_a = Payment.objects.create(
            user=self.user_a,
            course=self.course,
            razorpay_order_id='order_user_a_123',
            amount=499900,
            status='paid'
        )
        self.enrollment_a = Enrollment.objects.create(
            user=self.user_a,
            course=self.course,
            payment=self.payment_a,
            status='active'
        )

    # ----------------------------------------------------
    #  Auth Tests
    # ----------------------------------------------------
    def test_user_registration_and_login(self):
        # Register
        resp = self.client.post('/api/auth/register/', data=json.dumps({
            'name': 'New Student',
            'email': 'student@example.com',
            'password': 'secretpassword'
        }), content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn('access', data)
        self.assertEqual(data['user']['email'], 'student@example.com')

        # Duplicate email registration rejected
        resp_dup = self.client.post('/api/auth/register/', data=json.dumps({
            'name': 'Duplicate',
            'email': 'student@example.com',
            'password': 'secretpassword'
        }), content_type='application/json')
        self.assertEqual(resp_dup.status_code, 409)

        # Login
        resp_login = self.client.post('/api/auth/login/', data=json.dumps({
            'email': 'student@example.com',
            'password': 'secretpassword'
        }), content_type='application/json')
        self.assertEqual(resp_login.status_code, 200)
        self.assertIn('access', resp_login.json())

    # ----------------------------------------------------
    #  Video Protection Security Tests
    # ----------------------------------------------------
    def test_preview_lesson_accessible_unauthenticated(self):
        resp = self.client.get(f'/api/courses/{self.course.id}/lessons/{self.preview_lesson.id}/video/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('video_url', resp.json())

    def test_protected_lesson_rejected_for_unauthenticated_user(self):
        resp = self.client.get(f'/api/courses/{self.course.id}/lessons/{self.protected_lesson.id}/video/')
        self.assertEqual(resp.status_code, 401)

    def test_user_b_non_purchaser_rejected_from_protected_video(self):
        """
        User B has NOT purchased Course 1. User B must be rejected with 403 Forbidden.
        """
        resp = self.client.get(
            f'/api/courses/{self.course.id}/lessons/{self.protected_lesson.id}/video/',
            **self.auth_headers_b
        )
        self.assertEqual(resp.status_code, 403)

    def test_user_a_purchaser_granted_access_to_protected_video(self):
        """
        User A purchased Course 1. User A must receive signed temporary video URL.
        """
        resp = self.client.get(
            f'/api/courses/{self.course.id}/lessons/{self.protected_lesson.id}/video/',
            **self.auth_headers_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('video_url', data)
        self.assertIn('expires_in', data)

    # ----------------------------------------------------
    #  Payment & Order Price Integrity Tests
    # ----------------------------------------------------
    def test_payment_order_price_determined_strictly_server_side(self):
        """
        Frontend cannot tamper with the price. Backend enforces 499900 paise from database.
        """
        resp = self.client.post('/api/payments/create-order/', data=json.dumps({
            'course_id': self.course.id,
            'tampered_amount': 100  # Attempting to pay 1 rupee
        }), content_type='application/json', **self.auth_headers_b)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['amount'], 499900)  # Correct database price

    def test_fake_razorpay_signature_rejected(self):
        # Create order
        order_resp = self.client.post('/api/payments/create-order/', data=json.dumps({
            'course_id': self.course.id
        }), content_type='application/json', **self.auth_headers_b)
        order_id = order_resp.json()['order_id']

        # Attempt verification with invalid signature
        verify_resp = self.client.post('/api/payments/verify/', data=json.dumps({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': 'pay_fake_123',
            'razorpay_signature': 'invalid_forged_signature',
            'course_id': self.course.id,
        }), content_type='application/json', **self.auth_headers_b)

        # In production or strict mode invalid signatures are rejected
        # Check that non-matching signatures fail
        payment = Payment.objects.get(razorpay_order_id=order_id)
        self.assertIn(payment.status, ['created', 'failed'])

    # ----------------------------------------------------
    #  User Isolation & Privacy Tests
    # ----------------------------------------------------
    def test_user_b_cannot_see_user_a_payment_status(self):
        resp = self.client.get(
            f'/api/payments/status/{self.payment_a.razorpay_order_id}/',
            **self.auth_headers_b
        )
        self.assertEqual(resp.status_code, 404)

    def test_user_b_cannot_update_progress_for_unowned_course(self):
        resp = self.client.patch(
            f'/api/courses/{self.course.id}/lessons/{self.protected_lesson.id}/progress/',
            data=json.dumps({'watched_seconds': 500, 'duration_seconds': 1200}),
            content_type='application/json',
            **self.auth_headers_b
        )
        self.assertEqual(resp.status_code, 403)

    def test_user_a_progress_tracking_and_lesson_completion(self):
        resp = self.client.patch(
            f'/api/courses/{self.course.id}/lessons/{self.protected_lesson.id}/progress/',
            data=json.dumps({'watched_seconds': 1100, 'duration_seconds': 1200}),
            content_type='application/json',
            **self.auth_headers_a
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['lesson_progress']['completed'])
        self.assertGreater(data['course_progress'], 0)

        # Verify My Learning endpoint returns updated progress
        my_enr_resp = self.client.get('/api/enrollments/my/', **self.auth_headers_a)
        self.assertEqual(my_enr_resp.status_code, 200)
        enr_list = my_enr_resp.json()
        self.assertEqual(len(enr_list), 1)
        self.assertIn(str(self.protected_lesson.id), enr_list[0]['completed_lessons'])
