from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from userApp.models import Enrollment
from ..permissions import admin_required
from ..serializers import serialize_enrollment_admin
from ..utils import parse_json_body, json_response, error_response, log_admin_action


@csrf_exempt
@admin_required
def admin_enrollments(request):
    """
    List enrollments with search, status, and course/user filters.
    GET /api/admin/enrollments/
    """
    if request.method != 'GET':
        return error_response('Method not allowed', status=405)

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip().lower()
    course_id = request.GET.get('course_id', '').strip()
    user_id = request.GET.get('user_id', '').strip()

    queryset = (
        Enrollment.objects
        .select_related('user', 'course', 'payment', 'last_watched_lesson')
        .order_by('-enrolled_at')
    )

    if search:
        queryset = queryset.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(course__title__icontains=search)
        )

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    if course_id:
        queryset = queryset.filter(course_id=course_id)

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    results = [serialize_enrollment_admin(e) for e in queryset]
    return json_response({
        'count': len(results),
        'results': results,
    }, status=200)


@csrf_exempt
@admin_required
def admin_enrollment_detail(request, id):
    """
    Get or update enrollment details (status, progress).
    GET /api/admin/enrollments/<id>/
    PATCH /api/admin/enrollments/<id>/
    """
    enrollment = (
        Enrollment.objects
        .filter(id=id)
        .select_related('user', 'course', 'payment', 'last_watched_lesson')
        .first()
    )
    if not enrollment:
        return error_response('Enrollment record not found', status=404)

    if request.method == 'GET':
        return json_response(serialize_enrollment_admin(enrollment), status=200)

    elif request.method == 'PATCH':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        if 'status' in data:
            new_status = data.get('status')
            if new_status in ('active', 'completed', 'cancelled'):
                enrollment.status = new_status
            else:
                return error_response(f'Invalid status "{new_status}"', status=400)

        if 'progress_percentage' in data:
            try:
                progress = max(0, min(100, int(data['progress_percentage'])))
                enrollment.progress_percentage = progress
            except Exception:
                pass

        enrollment.save()
        log_admin_action(
            request,
            'Updated enrollment',
            'Enrollment',
            enrollment.id,
            {'user_email': enrollment.user.email, 'status': enrollment.status, 'progress': enrollment.progress_percentage}
        )
        return json_response(serialize_enrollment_admin(enrollment), status=200)

    return error_response('Method not allowed', status=405)
