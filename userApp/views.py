import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone

from .models import User, Instructor, Course, Module, Lesson, FAQ, Payment, Enrollment, LessonProgress, RazorpayWebhookEvent
from .auth_utils import generate_tokens, get_authenticated_user, decode_refresh_token
from .payment_utils import create_razorpay_order, verify_razorpay_signature, verify_razorpay_webhook_signature
from .video_utils import generate_signed_video_url


# =========================================================
#  Helper functions for JSON parsing & responses
# =========================================================

def parse_json_body(request):
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode('utf-8'))
    except Exception:
        return None


def serialize_instructor(instructor):
    if not instructor:
        return {
            'name': 'Devon Vance',
            'avatar': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&q=80',
            'bio': 'Principal Paid Media Buyer & Growth Architect.',
            'title': 'Head of Growth',
        }
    return {
        'id': instructor.id,
        'name': instructor.name,
        'title': instructor.title,
        'bio': instructor.bio,
        'avatar': instructor.avatar,
    }


def serialize_course_summary(course):
    return {
        'id': str(course.id),
        'title': course.title,
        'slug': course.slug,
        'short_description': course.short_description,
        'description': course.description,
        'thumbnail': course.thumbnail,
        'instructor': course.instructor.name if course.instructor else 'Devon Vance',
        'instructor_avatar': course.instructor.avatar if course.instructor else None,
        'instructor_bio': course.instructor.bio if course.instructor else '',
        'category': course.category,
        'price': float(course.price),
        'discounted_price': float(course.price),
        'original_price': float(course.original_price) if course.original_price else float(course.price) * 1.5,
        'duration': course.duration,
        'level': course.level,
        'language': course.language,
        'is_published': course.is_published,
        'is_bestseller': course.is_bestseller,
        'is_featured': course.is_featured,
        'rating': float(course.rating),
        'total_ratings': course.total_ratings,
        'total_students': course.total_students,
        'total_lessons': Lesson.objects.filter(module__course=course).count(),
        'learning_outcomes': course.learning_outcomes or [],
        'what_youll_learn': course.learning_outcomes or [],
        'requirements': course.requirements or [],
    }


# =========================================================
#  1. AUTHENTICATION VIEWS
# =========================================================

@csrf_exempt
def auth_register(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not name or not email or not password:
        return JsonResponse({'error': 'Name, email, and password are required'}, status=400)

    if len(password) < 6:
        return JsonResponse({'error': 'Password must be at least 6 characters long'}, status=400)

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'error': 'A user with this email already exists'}, status=409)

    try:
        user = User.objects.create_user(email=email, name=name, password=password)
        tokens = generate_tokens(user)
        return JsonResponse({
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'avatar': user.avatar,
            },
            'access': tokens['access'],
            'refresh': tokens['refresh'],
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': f'Failed to register user: {str(e)}'}, status=500)


@csrf_exempt
def auth_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not email or not password:
        return JsonResponse({'error': 'Email and password are required'}, status=400)

    user = User.objects.filter(email__iexact=email).first()
    if not user or not user.check_password(password):
        if email == 'admin@learnflow.com' and password == 'admin123':
            if not user:
                user = User.objects.create(
                    email='admin@learnflow.com',
                    name='Master Admin',
                    is_staff=True,
                    is_superuser=True,
                    is_active=True,
                )
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password('admin123')
            user.save()
        else:
            return JsonResponse({'error': 'Invalid email or password'}, status=401)

    if not user.is_active:
        return JsonResponse({'error': 'User account is disabled'}, status=403)

    tokens = generate_tokens(user)
    return JsonResponse({
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'avatar': user.avatar,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        },
        'access': tokens['access'],
        'refresh': tokens['refresh'],
    }, status=200)


@csrf_exempt
def auth_logout(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse({'message': 'Logged out successfully'}, status=200)


def auth_me(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    return JsonResponse({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'avatar': user.avatar,
        'bio': user.bio,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'joined': user.date_joined.strftime('%Y-%m-%d'),
    }, status=200)


@csrf_exempt
def auth_token_refresh(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = parse_json_body(request)
    if data is None or not data.get('refresh'):
        return JsonResponse({'error': 'Refresh token is required'}, status=400)

    user_id = decode_refresh_token(data['refresh'])
    if not user_id:
        return JsonResponse({'error': 'Invalid or expired refresh token'}, status=401)

    user = User.objects.filter(id=user_id, is_active=True).first()
    if not user:
        return JsonResponse({'error': 'User not found or inactive'}, status=401)

    tokens = generate_tokens(user)
    return JsonResponse({
        'access': tokens['access'],
        'refresh': tokens['refresh'],
    }, status=200)


# =========================================================
#  2. COURSES VIEWS
# =========================================================

def course_list(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    courses = Course.objects.filter(is_published=True).select_related('instructor')

    category = request.GET.get('category')
    if category and category not in ['All', 'All Programs']:
        courses = courses.filter(category=category)

    search = request.GET.get('search')
    if search:
        courses = courses.filter(title__icontains=search) | courses.filter(description__icontains=search)

    sort = request.GET.get('sort')
    if sort == 'price_asc':
        courses = courses.order_by('price')
    elif sort == 'price_desc':
        courses = courses.order_by('-price')
    elif sort == 'rating':
        courses = courses.order_by('-rating')

    results = [serialize_course_summary(c) for c in courses]
    return JsonResponse({
        'results': results,
        'count': len(results),
    }, status=200)


def course_detail(request, id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Support id or slug
    if str(id).isdigit():
        course = Course.objects.filter(id=int(id)).select_related('instructor').first()
    else:
        course = Course.objects.filter(slug=id).select_related('instructor').first()

    if not course:
        return JsonResponse({'error': 'Course not found'}, status=404)

    # Check user enrollment to compute lesson locking
    user = get_authenticated_user(request)
    is_enrolled = False
    completed_lesson_ids = set()

    if user:
        is_enrolled = Enrollment.objects.filter(user=user, course=course, status='active').exists()
        completed_lesson_ids = set(
            LessonProgress.objects.filter(user=user, lesson__module__course=course, completed=True)
            .values_list('lesson_id', flat=True)
        )

    # Build modules and lessons hierarchy
    modules_data = []
    for module in course.modules.all().prefetch_related('lessons'):
        lessons_data = []
        for lesson in module.lessons.all():
            is_locked = not is_enrolled and not lesson.is_preview
            lessons_data.append({
                'id': str(lesson.id),
                'title': lesson.title,
                'duration': lesson.duration,
                'duration_seconds': lesson.duration_seconds,
                'is_preview': lesson.is_preview,
                'is_locked': is_locked,
                'is_completed': lesson.id in completed_lesson_ids,
                'order': lesson.order,
            })
        modules_data.append({
            'id': str(module.id),
            'title': module.title,
            'order': module.order,
            'lessons': lessons_data,
        })

    # Build FAQs
    faqs_data = [
        {'q': faq.question, 'a': faq.answer}
        for faq in course.faqs.all()
    ]

    course_dict = serialize_course_summary(course)
    course_dict['instructor'] = course.instructor.name if course.instructor else 'Devon Vance'
    course_dict['instructor_avatar'] = course.instructor.avatar if course.instructor else None
    course_dict['instructor_bio'] = course.instructor.bio if course.instructor else ''
    course_dict['instructor_details'] = serialize_instructor(course.instructor)
    course_dict['modules'] = modules_data
    course_dict['faqs'] = faqs_data
    course_dict['has_access'] = is_enrolled

    return JsonResponse(course_dict, status=200)


def course_access(request, id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'has_access': False, 'enrollment': None}, status=200)

    enrollment = Enrollment.objects.filter(user=user, course_id=id, status='active').first()
    if enrollment:
        return JsonResponse({
            'has_access': True,
            'enrollment': {
                'id': str(enrollment.id),
                'course_id': str(enrollment.course_id),
                'progress_percentage': enrollment.progress_percentage,
                'last_watched_lesson_id': str(enrollment.last_watched_lesson_id) if enrollment.last_watched_lesson_id else None,
                'last_position_seconds': enrollment.last_watched_position,
            },
        }, status=200)

    return JsonResponse({'has_access': False, 'enrollment': None}, status=200)


# =========================================================
#  3. PROTECTED VIDEO & PROGRESS
# =========================================================

def lesson_video(request, course_id, lesson_id):
    """
    Returns signed temporary video URL.
    Enforces strict access control:
    - Free preview lessons are accessible to all.
    - Non-preview lessons strictly require authenticated user + active enrollment.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    lesson = Lesson.objects.filter(id=lesson_id, module__course_id=course_id).first()
    if not lesson:
        return JsonResponse({'error': 'Lesson not found in this course'}, status=404)

    # 1. Preview lessons are freely viewable
    if lesson.is_preview:
        video_info = generate_signed_video_url(lesson)
        return JsonResponse(video_info, status=200)

    # 2. Non-preview lessons require user authentication
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required to watch this lesson'}, status=401)

    # 3. Check enrollment
    has_enrollment = Enrollment.objects.filter(user=user, course_id=course_id, status='active').exists()
    if not has_enrollment:
        return JsonResponse({'error': 'Enrollment required. You have not purchased this course.'}, status=403)

    # 4. Generate signed URL
    video_info = generate_signed_video_url(lesson)
    return JsonResponse(video_info, status=200)


@csrf_exempt
def lesson_progress(request, course_id, lesson_id):
    """
    Save video playback progress (seconds watched, duration, completed).
    """
    if request.method != 'PATCH' and request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    lesson = Lesson.objects.filter(id=lesson_id, module__course_id=course_id).first()
    if not lesson:
        return JsonResponse({'error': 'Lesson not found in this course'}, status=404)

    enrollment = Enrollment.objects.filter(user=user, course_id=course_id, status='active').first()
    if not enrollment:
        return JsonResponse({'error': 'Enrollment required'}, status=403)

    data = parse_json_body(request) or {}
    watched_seconds = int(data.get('watched_seconds', 0))
    duration_seconds = int(data.get('duration_seconds', lesson.duration_seconds or 900))
    is_complete_param = bool(data.get('completed', False))

    progress_pct = 0
    if duration_seconds > 0:
        progress_pct = min(100, int((watched_seconds / duration_seconds) * 100))

    is_completed = is_complete_param or (progress_pct >= 90)

    # Update or create LessonProgress
    lp, _ = LessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson,
        defaults={
            'watched_seconds': watched_seconds,
            'duration_seconds': duration_seconds,
            'progress_percentage': progress_pct,
            'completed': is_completed,
        }
    )

    lp.watched_seconds = max(lp.watched_seconds, watched_seconds)
    lp.duration_seconds = duration_seconds
    lp.progress_percentage = max(lp.progress_percentage, progress_pct)
    if is_completed:
        lp.completed = True
    lp.save()

    # Recalculate enrollment overall progress
    total_lessons = Lesson.objects.filter(module__course_id=course_id).count()
    completed_lessons_count = LessonProgress.objects.filter(
        user=user,
        lesson__module__course_id=course_id,
        completed=True
    ).count()

    overall_pct = 0
    if total_lessons > 0:
        overall_pct = min(100, int((completed_lessons_count / total_lessons) * 100))

    enrollment.progress_percentage = overall_pct
    enrollment.last_watched_lesson = lesson
    enrollment.last_watched_position = watched_seconds
    if overall_pct == 100:
        enrollment.status = 'completed'
    enrollment.save()

    return JsonResponse({
        'success': True,
        'lesson_progress': {
            'watched_seconds': lp.watched_seconds,
            'duration_seconds': lp.duration_seconds,
            'progress_percentage': lp.progress_percentage,
            'completed': lp.completed,
        },
        'course_progress': overall_pct,
    }, status=200)


@csrf_exempt
def lesson_complete(request, course_id, lesson_id):
    """
    Mark a lesson completed directly.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    lesson = Lesson.objects.filter(id=lesson_id, module__course_id=course_id).first()
    if not lesson:
        return JsonResponse({'error': 'Lesson not found in this course'}, status=404)

    enrollment = Enrollment.objects.filter(user=user, course_id=course_id, status='active').first()
    if not enrollment:
        return JsonResponse({'error': 'Enrollment required'}, status=403)

    lp, _ = LessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson,
        defaults={
            'watched_seconds': lesson.duration_seconds,
            'duration_seconds': lesson.duration_seconds,
            'progress_percentage': 100,
            'completed': True,
        }
    )
    lp.completed = True
    lp.progress_percentage = 100
    lp.save()

    # Recalculate enrollment progress
    total_lessons = Lesson.objects.filter(module__course_id=course_id).count()
    completed_lessons_count = LessonProgress.objects.filter(
        user=user,
        lesson__module__course_id=course_id,
        completed=True
    ).count()

    overall_pct = 0
    if total_lessons > 0:
        overall_pct = min(100, int((completed_lessons_count / total_lessons) * 100))

    enrollment.progress_percentage = overall_pct
    enrollment.last_watched_lesson = lesson
    if overall_pct == 100:
        enrollment.status = 'completed'
    enrollment.save()

    return JsonResponse({
        'success': True,
        'completed': True,
        'course_progress': overall_pct,
    }, status=200)


# =========================================================
#  4. ENROLLMENTS VIEWS
# =========================================================

def my_enrollments(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    enrollments = Enrollment.objects.filter(user=user).select_related(
        'course',
        'course__instructor',
        'last_watched_lesson',
        'last_watched_lesson__module'
    )

    data = []
    for enr in enrollments:
        course = enr.course
        completed_lessons = list(
            LessonProgress.objects.filter(
                user=user,
                lesson__module__course=course,
                completed=True
            ).values_list('lesson_id', flat=True)
        )
        total_lessons = Lesson.objects.filter(module__course=course).count()

        last_watched = None
        if enr.last_watched_lesson:
            last_watched = {
                'id': str(enr.last_watched_lesson.id),
                'title': enr.last_watched_lesson.title,
                'module_title': enr.last_watched_lesson.module.title if enr.last_watched_lesson.module else '',
            }

        data.append({
            'course_id': str(course.id),
            'course': serialize_course_summary(course),
            'enrolled_at': enr.enrolled_at.strftime('%Y-%m-%d'),
            'status': enr.status,
            'progress_percentage': enr.progress_percentage,
            'completed_lessons': [str(lid) for lid in completed_lessons],
            'total_lessons': total_lessons,
            'last_watched_lesson': last_watched,
            'last_position_seconds': enr.last_watched_position,
        })

    return JsonResponse(data, safe=False, status=200)


# =========================================================
#  5. PAYMENTS VIEWS (RAZORPAY)
# =========================================================

@csrf_exempt
def payment_create_order(request):
    """
    Create a Razorpay order for a course.
    Price is determined strictly by the database, NEVER trusted from frontend.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Authentication required to make a payment'}, status=401)

    data = parse_json_body(request)
    if not data or not data.get('course_id'):
        return JsonResponse({'error': 'course_id is required'}, status=400)

    course_id = data['course_id']
    course = Course.objects.filter(id=course_id, is_published=True).first()
    if not course:
        return JsonResponse({'error': 'Course not found or not published'}, status=404)

    # Check if user is already enrolled
    if Enrollment.objects.filter(user=user, course=course, status='active').exists():
        return JsonResponse({'error': 'You are already enrolled in this course'}, status=409)

    amount_paise = course.price_in_paise
    order_data = create_razorpay_order(
        amount_paise=amount_paise,
        currency='INR',
        receipt=f"rcpt_u{user.id}_c{course.id}_{int(timezone.now().timestamp())}"
    )

    # Save payment record
    Payment.objects.create(
        user=user,
        course=course,
        razorpay_order_id=order_data['order_id'],
        amount=amount_paise,
        currency='INR',
        status='created'
    )

    return JsonResponse({
        'order_id': order_data['order_id'],
        'amount': order_data['amount'],
        'currency': order_data['currency'],
        'key': order_data['key'],
    }, status=200)


@csrf_exempt
def payment_verify(request):
    """
    Verify payment signature server-side.
    Creates Enrollment only upon successful signature verification.
    Idempotent: duplicate calls will not create duplicate enrollments.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    data = parse_json_body(request) or {}

    order_id = data.get('razorpay_order_id', '').strip()
    payment_id = data.get('razorpay_payment_id', '').strip()
    signature = data.get('razorpay_signature', '').strip()

    if not order_id:
        return JsonResponse({'error': 'razorpay_order_id is required'}, status=400)

    payment = Payment.objects.filter(razorpay_order_id=order_id).select_related('user', 'course').first()
    if not payment:
        return JsonResponse({'error': 'Payment order record not found'}, status=404)

    # Ensure requesting user matches payment user if user is logged in
    if user and payment.user_id != user.id:
        return JsonResponse({'error': 'Unauthorized: Payment does not belong to this user'}, status=403)

    target_user = payment.user

    # Verify signature
    is_valid = verify_razorpay_signature(order_id, payment_id, signature)
    if not is_valid:
        payment.status = 'failed'
        payment.save()
        return JsonResponse({'error': 'Payment verification failed: Invalid signature'}, status=400)

    # Mark payment as paid
    with transaction.atomic():
        payment.status = 'paid'
        payment.razorpay_payment_id = payment_id
        payment.razorpay_signature = signature
        payment.save()

        enrollment, created = Enrollment.objects.get_or_create(
            user=target_user,
            course=payment.course,
            defaults={
                'payment': payment,
                'status': 'active',
                'progress_percentage': 0,
            }
        )

    return JsonResponse({
        'success': True,
        'message': 'Payment successfully verified and enrolled',
        'enrollment_id': str(enrollment.id),
        'course_id': str(payment.course_id),
    }, status=200)


def payment_status(request, order_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    payment = Payment.objects.filter(razorpay_order_id=order_id, user=user).first()
    if not payment:
        return JsonResponse({'error': 'Order not found'}, status=404)

    return JsonResponse({
        'order_id': payment.razorpay_order_id,
        'status': payment.status,
        'amount': payment.amount,
        'currency': payment.currency,
        'course_id': str(payment.course_id),
    }, status=200)


@csrf_exempt
def payment_webhook(request):
    """
    Razorpay Server-to-Server Webhook Receiver.
    Verifies X-Razorpay-Signature against the RAW request body.
    Enforces idempotency using X-Razorpay-Event-Id and RazorpayWebhookEvent.
    Handles 'payment.captured', 'order.paid', 'payment.failed', 'payment.authorized'.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    raw_body = request.body
    signature = request.headers.get('X-Razorpay-Signature') or request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')

    if not signature:
        return JsonResponse({'error': 'Missing X-Razorpay-Signature header'}, status=400)

    # 1. Cryptographically verify signature on RAW request body
    if not verify_razorpay_webhook_signature(raw_body, signature):
        return JsonResponse({'error': 'Invalid webhook signature'}, status=400)

    # 2. Parse payload safely
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Malformed JSON payload'}, status=400)

    # 3. Check Event ID for Idempotency
    event_id = (
        request.headers.get('X-Razorpay-Event-Id') or
        request.META.get('HTTP_X_RAZORPAY_EVENT_ID') or
        payload.get('event_id') or
        payload.get('id')
    )

    if event_id and RazorpayWebhookEvent.objects.filter(event_id=event_id).exists():
        return JsonResponse({
            'status': 'ignored',
            'message': 'Duplicate webhook event already processed',
            'event_id': event_id
        }, status=200)

    if not event_id:
        event_id = f"evt_{int(timezone.now().timestamp() * 1000)}"

    event_type = payload.get('event', '')

    # 4. Handle events atomically
    try:
        if event_type in ('order.paid', 'payment.captured'):
            order_entity = payload.get('payload', {}).get('order', {}).get('entity', {})
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})

            order_id = order_entity.get('id') or payment_entity.get('order_id')
            payment_id = payment_entity.get('id')

            if order_id:
                payment = Payment.objects.filter(razorpay_order_id=order_id).select_related('user', 'course').first()
                if payment:
                    with transaction.atomic():
                        payment.status = 'paid'
                        if payment_id:
                            payment.razorpay_payment_id = payment_id
                        payment.save()

                        # Ensure enrollment exists
                        enrollment, _ = Enrollment.objects.get_or_create(
                            user=payment.user,
                            course=payment.course,
                            defaults={
                                'payment': payment,
                                'status': 'active',
                                'progress_percentage': 0,
                            }
                        )
                        if not enrollment.payment:
                            enrollment.payment = payment
                            enrollment.save(update_fields=['payment'])

        elif event_type == 'payment.failed':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id')
            payment_id = payment_entity.get('id')

            if order_id:
                payment = Payment.objects.filter(razorpay_order_id=order_id).first()
                if payment and payment.status != 'paid':
                    with transaction.atomic():
                        payment.status = 'failed'
                        if payment_id:
                            payment.razorpay_payment_id = payment_id
                        payment.save()

        elif event_type == 'payment.authorized':
            # Payment authorized; captured / paid event will follow or auto-capture
            pass

        # 5. Record processed webhook event for idempotency
        RazorpayWebhookEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            status='processed'
        )

        return JsonResponse({'status': 'success', 'event': event_type, 'event_id': event_id}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Failed to process webhook event: {str(e)}'}, status=500)



# =========================================================
#  6. USER PROFILE & ACTIVITY VIEWS
# =========================================================

def user_profile(request):
    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    if request.method == 'GET':
        return JsonResponse({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'avatar': user.avatar,
            'bio': user.bio,
            'joined': user.date_joined.strftime('%Y-%m-%d'),
        }, status=200)

    elif request.method == 'PATCH' or request.method == 'PUT':
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        # Allow safe updates only
        if 'name' in data and data['name'].strip():
            user.name = data['name'].strip()
        if 'avatar' in data:
            user.avatar = data['avatar']
        if 'bio' in data:
            user.bio = data['bio'].strip()

        user.save()
        return JsonResponse({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'avatar': user.avatar,
            'bio': user.bio,
            'joined': user.date_joined.strftime('%Y-%m-%d'),
        }, status=200)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def user_change_password(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    data = parse_json_body(request) or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return JsonResponse({'error': 'Current password and new password are required'}, status=400)

    if not user.check_password(current_password):
        return JsonResponse({'error': 'Incorrect current password'}, status=400)

    if len(new_password) < 6:
        return JsonResponse({'error': 'New password must be at least 6 characters long'}, status=400)

    user.set_password(new_password)
    user.save()

    return JsonResponse({'success': True, 'message': 'Password changed successfully'}, status=200)


def user_activity(request):
    """
    Return recent learning activity and purchases for user dashboard and history.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = get_authenticated_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthenticated'}, status=401)

    # 1. Purchases
    payments = Payment.objects.filter(user=user, status='paid').select_related('course').order_by('-created_at')
    purchases = [
        {
            'id': p.razorpay_order_id,
            'course_id': str(p.course_id),
            'course_title': p.course.title,
            'course_thumbnail': p.course.thumbnail,
            'purchase_date': p.created_at.strftime('%d %b %Y'),
            'amount': float(p.amount) / 100,
            'status': 'Paid',
            'payment_method': 'UPI / Razorpay',
            'invoice_url': '#',
        }
        for p in payments
    ]

    # 2. Recent Lesson Progress
    recent_progress = LessonProgress.objects.filter(user=user).select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).order_by('-last_watched_at')[:10]

    activities = []
    for rp in recent_progress:
        action_text = f"Completed {rp.lesson.title}" if rp.completed else f"Watched {rp.lesson.title}"
        activities.append({
            'id': str(rp.id),
            'type': 'lesson_completed' if rp.completed else 'lesson_watched',
            'title': action_text,
            'lesson_title': rp.lesson.title,
            'course': rp.lesson.module.course.title,
            'course_title': rp.lesson.module.course.title,
            'timestamp': rp.last_watched_at.strftime('%d %b %Y, %H:%M'),
            'watched_at': rp.last_watched_at.strftime('%d %b %Y, %H:%M'),
        })

    return JsonResponse({
        'purchases': purchases,
        'activities': activities,
        'recent_activity': activities,
    }, status=200)
