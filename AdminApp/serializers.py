from django.db.models import Sum
from userApp.models import (
    User,
    Instructor,
    Course,
    Module,
    Lesson,
    Payment,
    Enrollment,
)
from .utils import format_datetime, format_date


def serialize_instructor_summary(instructor):
    if not instructor:
        return None
    return {
        'id': instructor.id,
        'name': instructor.name,
        'title': instructor.title or 'Academy Instructor',
        'bio': instructor.bio or '',
        'avatar': instructor.avatar,
        'courses_count': Course.objects.filter(instructor=instructor).count(),
        'created_at': format_datetime(instructor.created_at),
    }


def serialize_instructor_detail(instructor):
    if not instructor:
        return None
    courses = Course.objects.filter(instructor=instructor)
    courses_data = []
    for c in courses:
        courses_data.append({
            'id': c.id,
            'title': c.title,
            'thumbnail': c.thumbnail,
            'category': c.category,
            'price': float(c.price),
            'is_published': c.is_published,
            'total_enrollments': Enrollment.objects.filter(course=c).count(),
        })

    return {
        'id': instructor.id,
        'name': instructor.name,
        'title': instructor.title or 'Academy Instructor',
        'bio': instructor.bio or '',
        'avatar': instructor.avatar,
        'courses_count': courses.count(),
        'courses': courses_data,
        'created_at': format_datetime(instructor.created_at),
    }


def serialize_lesson_admin(lesson):
    if not lesson:
        return None
    return {
        'id': lesson.id,
        'module_id': lesson.module_id,
        'title': lesson.title,
        'duration': lesson.duration or '15:00',
        'duration_seconds': lesson.duration_seconds or 900,
        'video_url': lesson.video_url or '',
        'is_preview': bool(lesson.is_preview),
        'order': lesson.order,
        'created_at': format_datetime(lesson.created_at),
    }


def serialize_module_admin(module):
    if not module:
        return None
    lessons = module.lessons.all().order_by('order')
    return {
        'id': module.id,
        'course_id': module.course_id,
        'title': module.title,
        'order': module.order,
        'lessons': [serialize_lesson_admin(l) for l in lessons],
        'lessons_count': lessons.count(),
        'created_at': format_datetime(module.created_at),
    }


def serialize_course_admin(course):
    if not course:
        return None
    total_enrollments = Enrollment.objects.filter(course=course).count()
    active_enrollments = Enrollment.objects.filter(course=course, status='active').count()
    revenue_paise = Payment.objects.filter(course=course, status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    modules_count = course.modules.count()
    lessons_count = Lesson.objects.filter(module__course=course).count()

    return {
        'id': course.id,
        'title': course.title,
        'slug': course.slug,
        'short_description': course.short_description or '',
        'description': course.description or '',
        'thumbnail': course.thumbnail,
        'instructor': serialize_instructor_summary(course.instructor),
        'instructor_id': course.instructor_id,
        'category': course.category or 'Performance Marketing',
        'price': float(course.price),
        'original_price': float(course.original_price) if course.original_price is not None else None,
        'duration': course.duration or '18h 45m',
        'level': course.level or 'Intermediate to Advanced',
        'language': course.language or 'English',
        'is_published': bool(course.is_published),
        'is_bestseller': bool(course.is_bestseller),
        'is_featured': bool(course.is_featured),
        'rating': float(course.rating) if course.rating is not None else 4.95,
        'total_ratings': course.total_ratings,
        'total_students': course.total_students,
        'learning_outcomes': course.learning_outcomes or [],
        'requirements': course.requirements or [],
        'modules_count': modules_count,
        'lessons_count': lessons_count,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'total_revenue': round(revenue_paise / 100.0, 2),
        'created_at': format_datetime(course.created_at),
        'updated_at': format_datetime(course.updated_at),
    }


def serialize_student_summary(user):
    if not user:
        return None
    enrollments_count = Enrollment.objects.filter(user=user).count()
    revenue_paise = Payment.objects.filter(user=user, status='paid').aggregate(Sum('amount'))['amount__sum'] or 0

    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'avatar': user.avatar,
        'bio': user.bio or '',
        'is_active': bool(user.is_active),
        'is_staff': bool(user.is_staff),
        'is_superuser': bool(user.is_superuser),
        'date_joined': format_datetime(user.date_joined),
        'last_login': format_datetime(user.last_login),
        'enrollments_count': enrollments_count,
        'total_spent': round(revenue_paise / 100.0, 2),
    }


def serialize_student_detail(user):
    if not user:
        return None
    summary = serialize_student_summary(user)
    
    enrollments = Enrollment.objects.filter(user=user).select_related('course').order_by('-enrolled_at')
    enrollments_data = []
    for e in enrollments:
        enrollments_data.append({
            'id': e.id,
            'course_id': e.course_id,
            'course_title': e.course.title if e.course else 'Unknown Course',
            'course_thumbnail': e.course.thumbnail if e.course else None,
            'enrolled_at': format_datetime(e.enrolled_at),
            'status': e.status,
            'progress_percentage': e.progress_percentage,
        })

    payments = Payment.objects.filter(user=user).select_related('course').order_by('-created_at')
    payments_data = []
    for p in payments:
        payments_data.append({
            'id': p.id,
            'razorpay_order_id': p.razorpay_order_id,
            'razorpay_payment_id': p.razorpay_payment_id,
            'course_title': p.course.title if p.course else 'General Order',
            'amount': round(p.amount / 100.0, 2),
            'status': p.status,
            'created_at': format_datetime(p.created_at),
        })

    summary['enrollments'] = enrollments_data
    summary['payments'] = payments_data
    return summary


def serialize_enrollment_admin(enrollment):
    if not enrollment:
        return None
    return {
        'id': enrollment.id,
        'user_id': enrollment.user_id,
        'user_name': enrollment.user.name if enrollment.user else 'Unknown',
        'user_email': enrollment.user.email if enrollment.user else 'N/A',
        'user_avatar': enrollment.user.avatar if enrollment.user else None,
        'course_id': enrollment.course_id,
        'course_title': enrollment.course.title if enrollment.course else 'Unknown Course',
        'course_thumbnail': enrollment.course.thumbnail if enrollment.course else None,
        'course_price': float(enrollment.course.price) if enrollment.course else 0.0,
        'enrolled_at': format_datetime(enrollment.enrolled_at),
        'status': enrollment.status,
        'progress_percentage': enrollment.progress_percentage,
        'last_watched_lesson': enrollment.last_watched_lesson.title if enrollment.last_watched_lesson else None,
        'last_watched_position': enrollment.last_watched_position,
        'payment_id': enrollment.payment_id,
        'payment_status': enrollment.payment.status if enrollment.payment else None,
    }


def serialize_payment_admin(payment):
    if not payment:
        return None
    return {
        'id': payment.id,
        'user_id': payment.user_id,
        'user_name': payment.user.name if payment.user else 'Unknown',
        'user_email': payment.user.email if payment.user else 'N/A',
        'course_id': payment.course_id,
        'course_title': payment.course.title if payment.course else 'General Masterclass',
        'razorpay_order_id': payment.razorpay_order_id,
        'razorpay_payment_id': payment.razorpay_payment_id,
        'amount': round(payment.amount / 100.0, 2),
        'currency': payment.currency,
        'status': payment.status,
        'created_at': format_datetime(payment.created_at),
        'updated_at': format_datetime(payment.updated_at),
    }


def serialize_admin_profile(user):
    if not user:
        return None
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'avatar': user.avatar,
        'bio': user.bio or '',
        'is_staff': bool(user.is_staff),
        'is_superuser': bool(user.is_superuser),
        'joined': format_date(user.date_joined),
    }
