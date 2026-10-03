import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UserBackend.settings')
django.setup()

from django.test import Client
from userApp.models import User, Course, Module, Lesson, Enrollment, EmailOTP
from userApp.otp_utils import hash_otp, compute_otp_hashes

def run_test():
    client = Client()
    print("=== STARTING OTP VERIFICATION FLOW INTEGRATION TEST ===")

    # 1. Setup test user, course, and enrollment
    email = "purchaser.student@flairacademy.com"
    user, _ = User.objects.get_or_create(email=email, defaults={'name': 'Purchaser Student'})
    
    course, _ = Course.objects.get_or_create(
        id=1,
        defaults={
            'title': 'Digital Product & Marketing Masterclass',
            'slug': 'digital-product-masterclass',
            'price': 499.00,
            'is_published': True
        }
    )
    module, _ = Module.objects.get_or_create(course=course, title='Module 1', defaults={'order': 1})
    preview_lesson, _ = Lesson.objects.get_or_create(
        module=module,
        title='Free Preview Lesson',
        defaults={'order': 1, 'is_preview': True, 'video_url': 'https://example.com/preview.mp4'}
    )
    protected_lesson, _ = Lesson.objects.get_or_create(
        module=module,
        title='Protected Core Lesson',
        defaults={'order': 2, 'is_preview': False, 'video_url': 'https://example.com/protected.mp4'}
    )

    # Clean previous test OTPs and enrollments
    EmailOTP.objects.filter(email=email).delete()
    Enrollment.objects.filter(user=user, course=course).delete()
    Enrollment.objects.create(user=user, course=course, status='active')

    # 2. Test Unauthenticated Access to Protected Lesson
    print("\n1. Testing unauthenticated access to protected lesson...")
    unauth_resp = client.get(f'/api/courses/{course.id}/lessons/{protected_lesson.id}/video/')
    assert unauth_resp.status_code == 401, f"Expected 401, got {unauth_resp.status_code}"
    print("-> PASS: Unauthenticated access rejected with HTTP 401.")

    # 3. Test Invalid Email OTP Request
    print("\n2. Testing invalid email format...")
    bad_req = client.post('/api/auth/request-otp/', data=json.dumps({'email': 'invalid-email'}), content_type='application/json')
    assert bad_req.status_code == 400, f"Expected 400, got {bad_req.status_code}"
    print("-> PASS: Invalid email returns HTTP 400 (not 500).")

    # 4. Test Valid OTP Request
    print("\n3. Testing valid OTP request for purchase email...")
    otp_req = client.post('/api/auth/request-otp/', data=json.dumps({'email': email}), content_type='application/json')
    assert otp_req.status_code == 200, f"Expected 200, got {otp_req.status_code}: {otp_req.content}"
    data = otp_req.json()
    assert data['success'] is True
    print(f"-> PASS: OTP requested successfully. Response: {data}")

    # 5. Verify OTP Stored in Database
    print("\n4. Checking OTP in database...")
    otp_record = EmailOTP.objects.filter(email=email, is_used=False).first()
    assert otp_record is not None, "OTP record not found in database!"
    print(f"-> PASS: OTP record found in DB with expiration {otp_record.expires_at}.")

    # 6. Test Rate-Limiting (within 45 seconds)
    print("\n5. Testing rate-limiting on immediate second OTP request...")
    rate_resp = client.post('/api/auth/request-otp/', data=json.dumps({'email': email}), content_type='application/json')
    assert rate_resp.status_code == 429, f"Expected 429, got {rate_resp.status_code}"
    print("-> PASS: Second immediate request rate-limited with HTTP 429.")

    # 7. Test Wrong OTP Code
    print("\n6. Testing wrong verification code...")
    bad_verify = client.post('/api/auth/verify-otp/', data=json.dumps({'email': email, 'otp': '000000'}), content_type='application/json')
    assert bad_verify.status_code == 400, f"Expected 400, got {bad_verify.status_code}"
    print(f"-> PASS: Wrong OTP rejected with 400: {bad_verify.json()['error']}")

    # 8. Test Correct OTP Code Verification
    print("\n7. Testing correct OTP verification...")
    # Set a known test OTP code
    known_code = "789123"
    otp_record.otp_hash = hash_otp(email, known_code)
    otp_record.save()

    verify_resp = client.post('/api/auth/verify-otp/', data=json.dumps({'email': email, 'otp': known_code}), content_type='application/json')
    assert verify_resp.status_code == 200, f"Expected 200, got {verify_resp.status_code}: {verify_resp.content}"
    verify_data = verify_resp.json()
    assert verify_data['success'] is True
    assert 'access' in verify_data
    assert str(course.id) in verify_data['enrolled_course_ids']
    jwt_token = verify_data['access']
    print(f"-> PASS: Correct OTP verified! Returned JWT access token and enrolled course IDs: {verify_data['enrolled_course_ids']}.")

    # 9. Test Reusing Used OTP Code
    print("\n8. Testing reuse of already-verified OTP code...")
    reuse_resp = client.post('/api/auth/verify-otp/', data=json.dumps({'email': email, 'otp': known_code}), content_type='application/json')
    assert reuse_resp.status_code == 400, f"Expected 400, got {reuse_resp.status_code}"
    print(f"-> PASS: Reused OTP rejected: {reuse_resp.json()['error']}")

    # 10. Test Course Access & Protected Video with Verified JWT Token
    print("\n9. Testing course access check with verified session...")
    auth_headers = {'HTTP_AUTHORIZATION': f'Bearer {jwt_token}'}
    access_resp = client.get(f'/api/courses/{course.id}/access/', **auth_headers)
    assert access_resp.status_code == 200
    assert access_resp.json()['has_access'] is True
    print("-> PASS: Course access check returns has_access: True.")

    print("\n10. Testing protected lesson video URL fetching with verified session...")
    video_resp = client.get(f'/api/courses/{course.id}/lessons/{protected_lesson.id}/video/', **auth_headers)
    assert video_resp.status_code == 200
    assert 'url' in video_resp.json()
    print(f"-> PASS: Protected lesson video URL successfully generated: {video_resp.json()['url'][:60]}...")

    print("\n=======================================================")
    print("ALL 10 END-TO-END OTP VERIFICATION FLOW CHECKS PASSED!")
    print("=======================================================")

if __name__ == '__main__':
    run_test()
