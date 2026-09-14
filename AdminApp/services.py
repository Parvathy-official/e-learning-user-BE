from django.db import transaction
from django.db.models import Sum, Count, Q
from userApp.models import (
    User,
    Instructor,
    Course,
    Module,
    Lesson,
    Payment,
    Enrollment,
)
from .utils import format_datetime


def get_dashboard_statistics():
    """
    Computes real-time analytical figures and collections for the Admin Dashboard.
    """
    total_students = User.objects.filter(is_staff=False).count()
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_enrollments = Enrollment.objects.count()
    active_enrollments = Enrollment.objects.filter(status='active').count()
    total_revenue_paise = Payment.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    total_revenue = round(total_revenue_paise / 100.0, 2)

    # Course Performance Breakdown
    courses = Course.objects.all().order_by('-created_at')
    course_performance = []
    for c in courses:
        enroll_count = Enrollment.objects.filter(course=c).count()
        rev_paise = Payment.objects.filter(course=c, status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
        course_performance.append({
            'id': c.id,
            'title': c.title,
            'thumbnail': c.thumbnail,
            'category': c.category,
            'price': float(c.price),
            'total_enrollments': enroll_count,
            'total_revenue': round(rev_paise / 100.0, 2),
            'rating': float(c.rating) if c.rating is not None else 4.95,
            'is_published': bool(c.is_published),
        })

    # Recent Enrollments
    recent_enrollment_records = (
        Enrollment.objects
        .select_related('user', 'course')
        .order_by('-enrolled_at')[:10]
    )
    recent_enrollments = []
    for e in recent_enrollment_records:
        recent_enrollments.append({
            'id': e.id,
            'user_name': e.user.name if e.user else 'Unknown',
            'user_email': e.user.email if e.user else 'N/A',
            'user_avatar': e.user.avatar if e.user else None,
            'course_title': e.course.title if e.course else 'Unknown Course',
            'enrolled_at': format_datetime(e.enrolled_at),
            'status': e.status,
        })

    # Recent Payments
    recent_payment_records = (
        Payment.objects
        .select_related('user', 'course')
        .order_by('-created_at')[:10]
    )
    recent_payments = []
    for p in recent_payment_records:
        recent_payments.append({
            'id': p.id,
            'user_name': p.user.name if p.user else 'Unknown',
            'amount': round(p.amount / 100.0, 2),
            'status': p.status,
            'created_at': format_datetime(p.created_at),
        })

    return {
        'stats': {
            'total_students': total_students,
            'total_courses': total_courses,
            'published_courses': published_courses,
            'total_enrollments': total_enrollments,
            'active_enrollments': active_enrollments,
            'total_revenue': total_revenue,
        },
        'course_performance': course_performance,
        'recent_enrollments': recent_enrollments,
        'recent_payments': recent_payments,
    }


def reorder_modules_service(course_id, orders):
    """
    Reorders modules within a course atomically.
    orders: list of dicts [{'id': 1, 'order': 1}, ...]
    """
    with transaction.atomic():
        for item in orders:
            module_id = item.get('id')
            new_order = item.get('order')
            if module_id and new_order is not None:
                Module.objects.filter(id=module_id, course_id=course_id).update(order=new_order)


def reorder_lessons_service(module_id, orders):
    """
    Reorders lessons within a module atomically.
    orders: list of dicts [{'id': 1, 'order': 1}, ...]
    """
    with transaction.atomic():
        for item in orders:
            lesson_id = item.get('id')
            new_order = item.get('order')
            if lesson_id and new_order is not None:
                Lesson.objects.filter(id=lesson_id, module_id=module_id).update(order=new_order)
