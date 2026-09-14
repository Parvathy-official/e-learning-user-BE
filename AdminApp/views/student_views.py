from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from userApp.models import User
from ..permissions import admin_required
from ..serializers import serialize_student_summary, serialize_student_detail
from ..utils import parse_json_body, json_response, error_response, log_admin_action


@csrf_exempt
@admin_required
def admin_students(request):
    """
    List students and users with optional filtering.
    GET /api/admin/students/
    Query params: search, role ('student' | 'admin')
    """
    if request.method != 'GET':
        return error_response('Method not allowed', status=405)

    search = request.GET.get('search', '').strip()
    role = request.GET.get('role', '').strip().lower()

    queryset = User.objects.all().order_by('-date_joined')

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )

    if role == 'student':
        queryset = queryset.filter(is_staff=False, is_superuser=False)
    elif role == 'admin':
        queryset = queryset.filter(Q(is_staff=True) | Q(is_superuser=True))

    results = [serialize_student_summary(u) for u in queryset]
    return json_response({
        'count': len(results),
        'results': results,
    }, status=200)


@csrf_exempt
@admin_required
def admin_student_detail(request, user_id):
    """
    Get full profile or update student account details.
    GET /api/admin/students/<user_id>/
    PATCH /api/admin/students/<user_id>/
    """
    user = User.objects.filter(id=user_id).first()
    if not user:
        return error_response('Student not found', status=404)

    if request.method == 'GET':
        return json_response(serialize_student_detail(user), status=200)

    elif request.method == 'PATCH':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        if 'is_active' in data:
            user.is_active = bool(data['is_active'])

        if 'is_staff' in data:
            user.is_staff = bool(data['is_staff'])

        if 'name' in data:
            name = data.get('name', '').strip()
            if name:
                user.name = name

        if 'bio' in data:
            user.bio = data.get('bio', user.bio)

        user.save()
        log_admin_action(request, 'Updated student profile', 'User', user.id, {'email': user.email})
        return json_response(serialize_student_detail(user), status=200)

    return error_response('Method not allowed', status=405)
