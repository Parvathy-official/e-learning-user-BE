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


class RazorpayWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Instructor
        self.instructor = Instructor.objects.create(
            name='Devon Vance',
            title='Growth Architect'
        )

        # Course
        self.course = Course.objects.create(
            title='Paid Media Mastery',
            slug='paid-media-mastery',
            price=4999.00,
            original_price=9999.00,
            is_published=True,
            instructor=self.instructor
        )

        # User
        self.user = User.objects.create_user(
            email='webhook_student@example.com',
            name='Webhook Student',
            password='Password123!'
        )
        self.tokens = generate_tokens(self.user)
        self.auth_headers = {'HTTP_AUTHORIZATION': f"Bearer {self.tokens['access']}"}

        # Payment record created (pending)
        self.payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            razorpay_order_id='order_webhook_test_100',
            amount=499900,
            currency='INR',
            status='created'
        )

    def test_webhook_invalid_signature_rejected(self):
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test_001',
                        'order_id': self.payment.razorpay_order_id,
                        'amount': 499900,
                        'status': 'captured'
                    }
                }
            }
        }
        resp = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='invalid_tampered_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_invalid_sig_test'
        )
        self.assertEqual(resp.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'created')
        self.assertFalse(Enrollment.objects.filter(user=self.user, course=self.course).exists())

    def test_webhook_payment_captured_success(self):
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test_captured_001',
                        'order_id': self.payment.razorpay_order_id,
                        'amount': 499900,
                        'status': 'captured'
                    }
                }
            }
        }
        resp = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='mock_webhook_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_cap_001'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['event'], 'payment.captured')

        # Verify Payment & Enrollment updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
        self.assertEqual(self.payment.razorpay_payment_id, 'pay_test_captured_001')
        self.assertTrue(Enrollment.objects.filter(user=self.user, course=self.course, status='active').exists())

    def test_webhook_order_paid_success(self):
        payload = {
            'event': 'order.paid',
            'payload': {
                'order': {
                    'entity': {
                        'id': self.payment.razorpay_order_id,
                        'amount': 499900,
                        'status': 'paid'
                    }
                },
                'payment': {
                    'entity': {
                        'id': 'pay_order_paid_002',
                        'order_id': self.payment.razorpay_order_id,
                    }
                }
            }
        }
        resp = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='mock_webhook_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_order_paid_001'
        )
        self.assertEqual(resp.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
        self.assertEqual(self.payment.razorpay_payment_id, 'pay_order_paid_002')
        self.assertTrue(Enrollment.objects.filter(user=self.user, course=self.course).exists())

    def test_webhook_idempotency_duplicate_event_ignored(self):
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test_dup_001',
                        'order_id': self.payment.razorpay_order_id,
                        'amount': 499900,
                    }
                }
            }
        }
        # First delivery
        resp1 = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='mock_webhook_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_duplicate_test_100'
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()['status'], 'success')
        self.assertEqual(Enrollment.objects.filter(user=self.user, course=self.course).count(), 1)

        # Duplicate delivery with same event_id
        resp2 = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='mock_webhook_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_duplicate_test_100'
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()['status'], 'ignored')
        # Ensure enrollment was not duplicated
        self.assertEqual(Enrollment.objects.filter(user=self.user, course=self.course).count(), 1)

    def test_webhook_arrives_before_frontend_verification(self):
        """
        Scenario: User pays, Webhook arrives first and enrolls student.
        User's browser later calls /payments/verify/.
        Must succeed cleanly without duplicate enrollment.
        """
        # 1. Webhook arrives
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_first_arrival_100',
                        'order_id': self.payment.razorpay_order_id,
                    }
                }
            }
        }
        wb_resp = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='mock_webhook_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_arrival_first'
        )
        self.assertEqual(wb_resp.status_code, 200)

        # 2. Frontend /verify/ arrives second
        verify_resp = self.client.post(
            '/api/payments/verify/',
            data=json.dumps({
                'razorpay_order_id': self.payment.razorpay_order_id,
                'razorpay_payment_id': 'pay_first_arrival_100',
                'razorpay_signature': 'mock_signature',
            }),
            content_type='application/json',
            **self.auth_headers
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertTrue(verify_resp.json()['success'])
        self.assertEqual(Enrollment.objects.filter(user=self.user, course=self.course).count(), 1)

    def test_frontend_verification_arrives_before_webhook(self):
        """
        Scenario: User pays, Frontend /payments/verify/ arrives first.
        Webhook arrives second.
        Must succeed cleanly without duplicate enrollment.
        """
        # 1. Frontend /verify/ arrives first
        verify_resp = self.client.post(
            '/api/payments/verify/',
            data=json.dumps({
                'razorpay_order_id': self.payment.razorpay_order_id,
                'razorpay_payment_id': 'pay_frontend_first_200',
                'razorpay_signature': 'mock_signature',
            }),
            content_type='application/json',
            **self.auth_headers
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertEqual(Enrollment.objects.filter(user=self.user, course=self.course).count(), 1)

        # 2. Webhook arrives second
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_frontend_first_200',
                        'order_id': self.payment.razorpay_order_id,
                    }
                }
            }
        }
        wb_resp = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='mock_webhook_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_webhook_second_200'
        )
        self.assertEqual(wb_resp.status_code, 200)
        # Enrollment count remains strictly 1
        self.assertEqual(Enrollment.objects.filter(user=self.user, course=self.course).count(), 1)

    def test_webhook_payment_failed(self):
        payload = {
            'event': 'payment.failed',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_failed_300',
                        'order_id': self.payment.razorpay_order_id,
                    }
                }
            }
        }
        wb_resp = self.client.post(
            '/api/payments/webhook/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='mock_webhook_signature',
            HTTP_X_RAZORPAY_EVENT_ID='evt_failed_300'
        )
        self.assertEqual(wb_resp.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')
        self.assertFalse(Enrollment.objects.filter(user=self.user, course=self.course).exists())

