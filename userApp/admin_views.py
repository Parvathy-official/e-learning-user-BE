import json
from decimal import Decimal
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.text import slugify

from .models import User, Instructor, Course, Module, Lesson, Payment, Enrollment, LessonProgress
from .auth_utils import get_authenticated_user


def parse_json_body(request):
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode('utf-8'))
    except Exception:
        return None


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)
        if not (user.is_staff or user.is_superuser):
            return JsonResponse({'error': 'Access Denied: Administrator privileges required.'}, status=403)
        request.admin_user = user
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# =========================================================
#  Serializers
# =========================================================

def serialize_instructor_summary(instructor):
    if not instructor:
        return None
    return {
        'id': instructor.id,
        'name': instructor.name,
        'title': instructor.title,
        'bio': instructor.bio,
        'avatar': instructor.avatar,
        'courses_count': Course.objects.filter(instructor=instructor).count(),
        'created_at': instructor.created_at.strftime('%Y-%m-%d %H:%M') if instructor.created_at else None,
    }


def serialize_course_admin(course):
    # Compute aggregates
    total_enrollments = Enrollment.objects.filter(course=course).count()
    active_enrollments = Enrollment.objects.filter(course=course, status='active').count()
    revenue_paise = Payment.objects.filter(course=course, status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    modules_count = course.modules.count()
    lessons_count = Lesson.objects.filter(module__course=course).count()

    return {
        'id': course.id,
        'title': course.title,
        'slug': course.slug,
        'short_description': course.short_description,
        'description': course.description,
        'thumbnail': course.thumbnail,
        'instructor': serialize_instructor_summary(course.instructor),
        'instructor_id': course.instructor_id,
        'category': course.category,
        'price': float(course.price),
        'original_price': float(course.original_price) if course.original_price else None,
        'duration': course.duration,
        'level': course.level,
        'language': course.language,
        'is_published': course.is_published,
        'is_bestseller': course.is_bestseller,
        'is_featured': course.is_featured,
        'rating': float(course.rating),
        'total_ratings': course.total_ratings,
        'total_students': course.total_students,
        'learning_outcomes': course.learning_outcomes or [],
        'requirements': course.requirements or [],
        'modules_count': modules_count,
        'lessons_count': lessons_count,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'total_revenue': round(revenue_paise / 100.0, 2),
        'created_at': course.created_at.strftime('%Y-%m-%d %H:%M') if course.created_at else None,
        'updated_at': course.updated_at.strftime('%Y-%m-%d %H:%M') if course.updated_at else None,
    }


def serialize_lesson_admin(lesson):
    return {
        'id': lesson.id,
        'module_id': lesson.module_id,
        'title': lesson.title,
        'duration': lesson.duration,
        'duration_seconds': lesson.duration_seconds,
        'video_url': lesson.video_url,
        'is_preview': lesson.is_preview,
        'order': lesson.order,
        'created_at': lesson.created_at.strftime('%Y-%m-%d %H:%M') if lesson.created_at else None,
    }


def serialize_module_admin(module):
    lessons = [serialize_lesson_admin(l) for l in module.lessons.all().order_by('order', 'id')]
    return {
        'id': module.id,
        'course_id': module.course_id,
        'title': module.title,
        'order': module.order,
        'lessons_count': len(lessons),
        'lessons': lessons,
        'created_at': module.created_at.strftime('%Y-%m-%d %H:%M') if module.created_at else None,
    }


def serialize_payment_admin(payment):
    return {
        'id': payment.id,
        'user_id': payment.user_id,
        'user_name': payment.user.name if payment.user else 'Unknown',
        'user_email': payment.user.email if payment.user else 'Unknown',
        'user_avatar': payment.user.avatar if payment.user else None,
        'course_id': payment.course_id,
        'course_title': payment.course.title if payment.course else 'Unknown',
        'course_thumbnail': payment.course.thumbnail if payment.course else None,
        'amount': round(payment.amount / 100.0, 2),  # Convert paise to INR
        'amount_paise': payment.amount,
        'currency': payment.currency,
        'status': payment.status,
        'razorpay_order_id': payment.razorpay_order_id,
        'razorpay_payment_id': payment.razorpay_payment_id,
        'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M:%S') if payment.created_at else None,
        'updated_at': payment.updated_at.strftime('%Y-%m-%d %H:%M:%S') if payment.updated_at else None,
    }


def serialize_enrollment_admin(enrollment):
    return {
        'id': enrollment.id,
        'user_id': enrollment.user_id,
        'user_name': enrollment.user.name if enrollment.user else 'Unknown',
        'user_email': enrollment.user.email if enrollment.user else 'Unknown',
        'user_avatar': enrollment.user.avatar if enrollment.user else None,
        'course_id': enrollment.course_id,
        'course_title': enrollment.course.title if enrollment.course else 'Unknown',
        'course_thumbnail': enrollment.course.thumbnail if enrollment.course else None,
        'course_category': enrollment.course.category if enrollment.course else None,
        'payment_id': enrollment.payment_id,
        'payment_amount': round(enrollment.payment.amount / 100.0, 2) if enrollment.payment else None,
        'payment_status': enrollment.payment.status if enrollment.payment else None,
        'enrolled_at': enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M:%S') if enrollment.enrolled_at else None,
        'status': enrollment.status,
        'progress_percentage': enrollment.progress_percentage,
        'last_watched_lesson_id': enrollment.last_watched_lesson_id,
        'last_watched_lesson_title': enrollment.last_watched_lesson.title if enrollment.last_watched_lesson else None,
        'last_watched_position': enrollment.last_watched_position,
    }


def serialize_student_admin(student):
    enrollments_count = Enrollment.objects.filter(user=student).count()
    active_enrollments = Enrollment.objects.filter(user=student, status='active').count()
    total_spent_paise = Payment.objects.filter(user=student, status='paid').aggregate(Sum('amount'))['amount__sum'] or 0

    return {
        'id': student.id,
        'name': student.name,
        'email': student.email,
        'avatar': student.avatar,
        'bio': student.bio,
        'is_active': student.is_active,
        'is_staff': student.is_staff,
        'is_superuser': student.is_superuser,
        'date_joined': student.date_joined.strftime('%Y-%m-%d %H:%M') if student.date_joined else None,
        'enrollments_count': enrollments_count,
        'active_enrollments': active_enrollments,
        'total_spent': round(total_spent_paise / 100.0, 2),
    }


# =========================================================
#  1. Dashboard Stats
# =========================================================

@csrf_exempt
@admin_required
def admin_dashboard_stats(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    total_students = User.objects.filter(is_staff=False, is_superuser=False).count()
    total_users = User.objects.count()
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_enrollments = Enrollment.objects.count()
    active_enrollments = Enrollment.objects.filter(status='active').count()
    
    total_revenue_paise = Payment.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    total_revenue = round(total_revenue_paise / 100.0, 2)

    # Recent enrollments
    recent_enrollments_qs = Enrollment.objects.select_related('user', 'course', 'payment').order_by('-enrolled_at')[:6]
    recent_enrollments = [serialize_enrollment_admin(e) for e in recent_enrollments_qs]

    # Recent payments
    recent_payments_qs = Payment.objects.select_related('user', 'course').order_by('-created_at')[:6]
    recent_payments = [serialize_payment_admin(p) for p in recent_payments_qs]

    # Course performance
    courses_qs = Course.objects.all().order_by('-total_students')[:6]
    course_performance = []
    for c in courses_qs:
        enr_count = Enrollment.objects.filter(course=c).count()
        rev_paise = Payment.objects.filter(course=c, status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
        course_performance.append({
            'id': c.id,
            'title': c.title,
            'thumbnail': c.thumbnail,
            'category': c.category,
            'price': float(c.price),
            'rating': float(c.rating),
            'total_students': c.total_students,
            'total_enrollments': enr_count,
            'total_revenue': round(rev_paise / 100.0, 2),
            'is_published': c.is_published,
        })

    return JsonResponse({
        'stats': {
            'total_students': total_students if total_students > 0 else total_users,
            'total_courses': total_courses,
            'published_courses': published_courses,
            'total_enrollments': total_enrollments,
            'active_enrollments': active_enrollments,
            'total_revenue': total_revenue,
        },
        'recent_enrollments': recent_enrollments,
        'recent_payments': recent_payments,
        'course_performance': course_performance,
    }, status=200)


# =========================================================
#  2. Courses Management
# =========================================================

@csrf_exempt
@admin_required
def admin_courses(request):
    if request.method == 'GET':
        courses = Course.objects.select_related('instructor').all()

        search = request.GET.get('search', '').strip()
        if search:
            courses = courses.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(category__icontains=search)
            )

        category = request.GET.get('category')
        if category and category != 'all':
            courses = courses.filter(category=category)

        is_published = request.GET.get('is_published')
        if is_published in ['true', '1']:
            courses = courses.filter(is_published=True)
        elif is_published in ['false', '0']:
            courses = courses.filter(is_published=False)

        is_featured = request.GET.get('is_featured')
        if is_featured in ['true', '1']:
            courses = courses.filter(is_featured=True)

        is_bestseller = request.GET.get('is_bestseller')
        if is_bestseller in ['true', '1']:
            courses = courses.filter(is_bestseller=True)

        instructor_id = request.GET.get('instructor_id')
        if instructor_id:
            courses = courses.filter(instructor_id=instructor_id)

        # Sorting
        sort = request.GET.get('sort', '-created_at')
        valid_sorts = ['created_at', '-created_at', 'title', '-title', 'price', '-price', 'rating', '-rating', 'total_students', '-total_students']
        if sort in valid_sorts:
            courses = courses.order_by(sort)
        else:
            courses = courses.order_by('-created_at')

        results = [serialize_course_admin(c) for c in courses]
        return JsonResponse({
            'count': len(results),
            'results': results,
        }, status=200)

    elif request.method == 'POST':
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': 'Course title is required'}, status=400)

        price = data.get('price')
        if price is None:
            return JsonResponse({'error': 'Price is required'}, status=400)

        slug = data.get('slug', '').strip()
        if not slug:
            base_slug = slugify(title)
            slug = base_slug
            count = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{count}"
                count += 1
        elif Course.objects.filter(slug=slug).exists():
            return JsonResponse({'error': f'Slug "{slug}" already exists. Please pick a unique slug.'}, status=400)

        try:
            course = Course.objects.create(
                title=title,
                slug=slug,
                short_description=data.get('short_description', ''),
                description=data.get('description', ''),
                thumbnail=data.get('thumbnail') or None,
                instructor_id=data.get('instructor_id') or None,
                category=data.get('category', 'Performance Marketing'),
                price=Decimal(str(price)),
                original_price=Decimal(str(data['original_price'])) if data.get('original_price') else None,
                duration=data.get('duration', '10h 00m'),
                level=data.get('level', 'Intermediate to Advanced'),
                language=data.get('language', 'English'),
                is_published=bool(data.get('is_published', True)),
                is_bestseller=bool(data.get('is_bestseller', False)),
                is_featured=bool(data.get('is_featured', False)),
                rating=Decimal(str(data.get('rating', '4.95'))),
                total_ratings=int(data.get('total_ratings', 0)),
                total_students=int(data.get('total_students', 0)),
                learning_outcomes=data.get('learning_outcomes', []),
                requirements=data.get('requirements', []),
            )
            return JsonResponse(serialize_course_admin(course), status=201)
        except Exception as e:
            return JsonResponse({'error': f'Failed to create course: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_course_detail(request, id):
    course = Course.objects.filter(id=id).select_related('instructor').first()
    if not course:
        return JsonResponse({'error': 'Course not found'}, status=404)

    if request.method == 'GET':
        data = serialize_course_admin(course)
        # Add full modules hierarchy
        modules = course.modules.all().prefetch_related('lessons').order_by('order', 'id')
        data['modules'] = [serialize_module_admin(m) for m in modules]
        return JsonResponse(data, status=200)

    elif request.method in ['PUT', 'PATCH']:
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        if 'title' in data:
            course.title = data['title'].strip()
        if 'slug' in data and data['slug'].strip():
            new_slug = data['slug'].strip()
            if Course.objects.filter(slug=new_slug).exclude(id=course.id).exists():
                return JsonResponse({'error': f'Slug "{new_slug}" already exists.'}, status=400)
            course.slug = new_slug
        if 'short_description' in data:
            course.short_description = data['short_description']
        if 'description' in data:
            course.description = data['description']
        if 'thumbnail' in data:
            course.thumbnail = data['thumbnail'] or None
        if 'instructor_id' in data:
            course.instructor_id = data['instructor_id'] or None
        if 'category' in data:
            course.category = data['category']
        if 'price' in data:
            course.price = Decimal(str(data['price']))
        if 'original_price' in data:
            course.original_price = Decimal(str(data['original_price'])) if data['original_price'] else None
        if 'duration' in data:
            course.duration = data['duration']
        if 'level' in data:
            course.level = data['level']
        if 'language' in data:
            course.language = data['language']
        if 'is_published' in data:
            course.is_published = bool(data['is_published'])
        if 'is_bestseller' in data:
            course.is_bestseller = bool(data['is_bestseller'])
        if 'is_featured' in data:
            course.is_featured = bool(data['is_featured'])
        if 'rating' in data:
            course.rating = Decimal(str(data['rating']))
        if 'total_ratings' in data:
            course.total_ratings = int(data['total_ratings'])
        if 'total_students' in data:
            course.total_students = int(data['total_students'])
        if 'learning_outcomes' in data:
            course.learning_outcomes = data['learning_outcomes']
        if 'requirements' in data:
            course.requirements = data['requirements']

        try:
            course.save()
            return JsonResponse(serialize_course_admin(course), status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to update course: {str(e)}'}, status=500)

    elif request.method == 'DELETE':
        try:
            course_title = course.title
            course.delete()
            return JsonResponse({'message': f'Course "{course_title}" deleted successfully.'}, status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to delete course: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_course_toggle_publish(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    course = Course.objects.filter(id=id).first()
    if not course:
        return JsonResponse({'error': 'Course not found'}, status=404)
    course.is_published = not course.is_published
    course.save()
    return JsonResponse({'id': course.id, 'is_published': course.is_published}, status=200)


@csrf_exempt
@admin_required
def admin_course_toggle_featured(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    course = Course.objects.filter(id=id).first()
    if not course:
        return JsonResponse({'error': 'Course not found'}, status=404)
    course.is_featured = not course.is_featured
    course.save()
    return JsonResponse({'id': course.id, 'is_featured': course.is_featured}, status=200)


@csrf_exempt
@admin_required
def admin_course_toggle_bestseller(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    course = Course.objects.filter(id=id).first()
    if not course:
        return JsonResponse({'error': 'Course not found'}, status=404)
    course.is_bestseller = not course.is_bestseller
    course.save()
    return JsonResponse({'id': course.id, 'is_bestseller': course.is_bestseller}, status=200)


# =========================================================
#  3. Course Content / Curriculum Management
# =========================================================

@csrf_exempt
@admin_required
def admin_course_curriculum(request, course_id):
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return JsonResponse({'error': 'Course not found'}, status=404)

    if request.method == 'GET':
        modules = course.modules.all().prefetch_related('lessons').order_by('order', 'id')
        return JsonResponse({
            'course_id': course.id,
            'course_title': course.title,
            'modules': [serialize_module_admin(m) for m in modules],
        }, status=200)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_course_modules(request, course_id):
    course = Course.objects.filter(id=course_id).first()
    if not course:
        return JsonResponse({'error': 'Course not found'}, status=404)

    if request.method == 'POST':
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': 'Module title is required'}, status=400)

        order = data.get('order')
        if order is None:
            max_order = course.modules.order_by('-order').values_list('order', flat=True).first() or 0
            order = max_order + 1

        try:
            module = Module.objects.create(course=course, title=title, order=int(order))
            return JsonResponse(serialize_module_admin(module), status=201)
        except Exception as e:
            return JsonResponse({'error': f'Failed to create module: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_module_detail(request, module_id):
    module = Module.objects.filter(id=module_id).prefetch_related('lessons').first()
    if not module:
        return JsonResponse({'error': 'Module not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse(serialize_module_admin(module), status=200)

    elif request.method in ['PUT', 'PATCH']:
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        if 'title' in data:
            module.title = data['title'].strip()
        if 'order' in data:
            module.order = int(data['order'])

        try:
            module.save()
            return JsonResponse(serialize_module_admin(module), status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to update module: {str(e)}'}, status=500)

    elif request.method == 'DELETE':
        try:
            module.delete()
            return JsonResponse({'message': 'Module deleted successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to delete module: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_modules_reorder(request, course_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = parse_json_body(request)
    if data is None or 'orders' not in data:
        return JsonResponse({'error': 'List of module orders required'}, status=400)

    try:
        with transaction.atomic():
            for item in data['orders']:
                Module.objects.filter(id=item['id'], course_id=course_id).update(order=item['order'])
        return JsonResponse({'message': 'Modules reordered successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': f'Failed to reorder modules: {str(e)}'}, status=500)


@csrf_exempt
@admin_required
def admin_module_lessons(request, module_id):
    module = Module.objects.filter(id=module_id).first()
    if not module:
        return JsonResponse({'error': 'Module not found'}, status=404)

    if request.method == 'POST':
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': 'Lesson title is required'}, status=400)

        order = data.get('order')
        if order is None:
            max_order = module.lessons.order_by('-order').values_list('order', flat=True).first() or 0
            order = max_order + 1

        duration = data.get('duration', '15:00')
        duration_seconds = data.get('duration_seconds')
        if duration_seconds is None:
            try:
                parts = duration.split(':')
                if len(parts) == 2:
                    duration_seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    duration_seconds = 900
            except Exception:
                duration_seconds = 900

        try:
            lesson = Lesson.objects.create(
                module=module,
                title=title,
                duration=duration,
                duration_seconds=int(duration_seconds),
                video_url=data.get('video_url') or None,
                is_preview=bool(data.get('is_preview', False)),
                order=int(order),
            )
            return JsonResponse(serialize_lesson_admin(lesson), status=201)
        except Exception as e:
            return JsonResponse({'error': f'Failed to create lesson: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_lesson_detail(request, lesson_id):
    lesson = Lesson.objects.filter(id=lesson_id).first()
    if not lesson:
        return JsonResponse({'error': 'Lesson not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse(serialize_lesson_admin(lesson), status=200)

    elif request.method in ['PUT', 'PATCH']:
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        if 'title' in data:
            lesson.title = data['title'].strip()
        if 'duration' in data:
            lesson.duration = data['duration'].strip()
        if 'duration_seconds' in data:
            lesson.duration_seconds = int(data['duration_seconds'])
        if 'video_url' in data:
            lesson.video_url = data['video_url'] or None
        if 'is_preview' in data:
            lesson.is_preview = bool(data['is_preview'])
        if 'order' in data:
            lesson.order = int(data['order'])

        try:
            lesson.save()
            return JsonResponse(serialize_lesson_admin(lesson), status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to update lesson: {str(e)}'}, status=500)

    elif request.method == 'DELETE':
        try:
            lesson.delete()
            return JsonResponse({'message': 'Lesson deleted successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to delete lesson: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_lessons_reorder(request, module_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = parse_json_body(request)
    if data is None or 'orders' not in data:
        return JsonResponse({'error': 'List of lesson orders required'}, status=400)

    try:
        with transaction.atomic():
            for item in data['orders']:
                Lesson.objects.filter(id=item['id'], module_id=module_id).update(order=item['order'])
        return JsonResponse({'message': 'Lessons reordered successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': f'Failed to reorder lessons: {str(e)}'}, status=500)


# =========================================================
#  4. Students Management
# =========================================================

@csrf_exempt
@admin_required
def admin_students(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    students = User.objects.all().order_by('-date_joined')

    search = request.GET.get('search', '').strip()
    if search:
        students = students.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )

    role = request.GET.get('role')
    if role == 'admin':
        students = students.filter(Q(is_staff=True) | Q(is_superuser=True))
    elif role == 'student':
        students = students.filter(is_staff=False, is_superuser=False)

    results = [serialize_student_admin(s) for s in students]
    return JsonResponse({
        'count': len(results),
        'results': results,
    }, status=200)


@csrf_exempt
@admin_required
def admin_student_detail(request, user_id):
    student = User.objects.filter(id=user_id).first()
    if not student:
        return JsonResponse({'error': 'Student not found'}, status=404)

    if request.method == 'GET':
        data = serialize_student_admin(student)

        # Get all enrollments
        enrollments = Enrollment.objects.filter(user=student).select_related('course', 'payment', 'last_watched_lesson').order_by('-enrolled_at')
        data['enrollments'] = [serialize_enrollment_admin(e) for e in enrollments]

        # Get all payments
        payments = Payment.objects.filter(user=student).select_related('course').order_by('-created_at')
        data['payments'] = [serialize_payment_admin(p) for p in payments]

        return JsonResponse(data, status=200)

    elif request.method in ['PUT', 'PATCH']:
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        if 'name' in data:
            student.name = data['name'].strip()
        if 'avatar' in data:
            student.avatar = data['avatar'] or None
        if 'bio' in data:
            student.bio = data['bio']
        if 'is_active' in data:
            student.is_active = bool(data['is_active'])

        try:
            student.save()
            return JsonResponse(serialize_student_admin(student), status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to update student: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# =========================================================
#  5. Instructors Management
# =========================================================

@csrf_exempt
@admin_required
def admin_instructors(request):
    if request.method == 'GET':
        instructors = Instructor.objects.all().order_by('-created_at')
        search = request.GET.get('search', '').strip()
        if search:
            instructors = instructors.filter(
                Q(name__icontains=search) |
                Q(title__icontains=search)
            )
        results = [serialize_instructor_summary(i) for i in instructors]
        return JsonResponse({'count': len(results), 'results': results}, status=200)

    elif request.method == 'POST':
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Instructor name is required'}, status=400)

        try:
            instructor = Instructor.objects.create(
                name=name,
                title=data.get('title', '').strip(),
                bio=data.get('bio', '').strip(),
                avatar=data.get('avatar') or None,
            )
            return JsonResponse(serialize_instructor_summary(instructor), status=201)
        except Exception as e:
            return JsonResponse({'error': f'Failed to create instructor: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_instructor_detail(request, id):
    instructor = Instructor.objects.filter(id=id).first()
    if not instructor:
        return JsonResponse({'error': 'Instructor not found'}, status=404)

    if request.method == 'GET':
        data = serialize_instructor_summary(instructor)
        courses = Course.objects.filter(instructor=instructor).order_by('-created_at')
        data['courses'] = [serialize_course_admin(c) for c in courses]
        return JsonResponse(data, status=200)

    elif request.method in ['PUT', 'PATCH']:
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        if 'name' in data:
            instructor.name = data['name'].strip()
        if 'title' in data:
            instructor.title = data['title'].strip()
        if 'bio' in data:
            instructor.bio = data['bio'].strip()
        if 'avatar' in data:
            instructor.avatar = data['avatar'] or None

        try:
            instructor.save()
            return JsonResponse(serialize_instructor_summary(instructor), status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to update instructor: {str(e)}'}, status=500)

    elif request.method == 'DELETE':
        try:
            Course.objects.filter(instructor=instructor).update(instructor=None)
            instructor.delete()
            return JsonResponse({'message': 'Instructor deleted successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to delete instructor: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# =========================================================
#  6. Enrollments Management
# =========================================================

@csrf_exempt
@admin_required
def admin_enrollments(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    enrollments = Enrollment.objects.select_related('user', 'course', 'payment', 'last_watched_lesson').all()

    search = request.GET.get('search', '').strip()
    if search:
        enrollments = enrollments.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(course__title__icontains=search)
        )

    status = request.GET.get('status')
    if status and status != 'all':
        enrollments = enrollments.filter(status=status)

    course_id = request.GET.get('course_id')
    if course_id:
        enrollments = enrollments.filter(course_id=course_id)

    user_id = request.GET.get('user_id')
    if user_id:
        enrollments = enrollments.filter(user_id=user_id)

    enrollments = enrollments.order_by('-enrolled_at')
    results = [serialize_enrollment_admin(e) for e in enrollments]
    return JsonResponse({
        'count': len(results),
        'results': results,
    }, status=200)


@csrf_exempt
@admin_required
def admin_enrollment_detail(request, id):
    enrollment = Enrollment.objects.filter(id=id).select_related('user', 'course', 'payment', 'last_watched_lesson').first()
    if not enrollment:
        return JsonResponse({'error': 'Enrollment not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse(serialize_enrollment_admin(enrollment), status=200)

    elif request.method in ['PUT', 'PATCH']:
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        if 'status' in data and data['status'] in ['active', 'completed', 'cancelled']:
            enrollment.status = data['status']
        if 'progress_percentage' in data:
            enrollment.progress_percentage = int(data['progress_percentage'])

        try:
            enrollment.save()
            return JsonResponse(serialize_enrollment_admin(enrollment), status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to update enrollment: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# =========================================================
#  7. Payments Management
# =========================================================

@csrf_exempt
@admin_required
def admin_payments(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    payments = Payment.objects.select_related('user', 'course').all()

    search = request.GET.get('search', '').strip()
    if search:
        payments = payments.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(course__title__icontains=search) |
            Q(razorpay_order_id__icontains=search) |
            Q(razorpay_payment_id__icontains=search)
        )

    status = request.GET.get('status')
    if status and status != 'all':
        payments = payments.filter(status=status)

    course_id = request.GET.get('course_id')
    if course_id:
        payments = payments.filter(course_id=course_id)

    user_id = request.GET.get('user_id')
    if user_id:
        payments = payments.filter(user_id=user_id)

    payments = payments.order_by('-created_at')
    results = [serialize_payment_admin(p) for p in payments]
    return JsonResponse({
        'count': len(results),
        'results': results,
    }, status=200)


@csrf_exempt
@admin_required
def admin_payment_detail(request, id):
    payment = Payment.objects.filter(id=id).select_related('user', 'course').first()
    if not payment:
        return JsonResponse({'error': 'Payment not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse(serialize_payment_admin(payment), status=200)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# =========================================================
#  8. Admin Profile & Settings
# =========================================================

@csrf_exempt
@admin_required
def admin_profile(request):
    admin_user = request.admin_user

    if request.method == 'GET':
        return JsonResponse({
            'id': admin_user.id,
            'name': admin_user.name,
            'email': admin_user.email,
            'avatar': admin_user.avatar,
            'bio': admin_user.bio,
            'is_staff': admin_user.is_staff,
            'is_superuser': admin_user.is_superuser,
            'date_joined': admin_user.date_joined.strftime('%Y-%m-%d %H:%M') if admin_user.date_joined else None,
        }, status=200)

    elif request.method in ['PUT', 'PATCH']:
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        if 'name' in data:
            admin_user.name = data['name'].strip()
        if 'avatar' in data:
            admin_user.avatar = data['avatar'] or None
        if 'bio' in data:
            admin_user.bio = data['bio'].strip()

        try:
            admin_user.save()
            return JsonResponse({
                'id': admin_user.id,
                'name': admin_user.name,
                'email': admin_user.email,
                'avatar': admin_user.avatar,
                'bio': admin_user.bio,
                'is_staff': admin_user.is_staff,
                'is_superuser': admin_user.is_superuser,
            }, status=200)
        except Exception as e:
            return JsonResponse({'error': f'Failed to update profile: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_change_password(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    admin_user = request.admin_user
    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return JsonResponse({'error': 'Current password and new password are required'}, status=400)

    if not admin_user.check_password(current_password):
        return JsonResponse({'error': 'Current password is incorrect'}, status=400)

    if len(new_password) < 6:
        return JsonResponse({'error': 'New password must be at least 6 characters long'}, status=400)

    try:
        admin_user.set_password(new_password)
        admin_user.save()
        return JsonResponse({'message': 'Password changed successfully'}, status=200)
    except Exception as e:
        return JsonResponse({'error': f'Failed to change password: {str(e)}'}, status=500)
