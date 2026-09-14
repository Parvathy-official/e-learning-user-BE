from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from userApp.models import Instructor
from ..permissions import admin_required
from ..serializers import serialize_instructor_summary, serialize_instructor_detail
from ..utils import parse_json_body, json_response, error_response, log_admin_action


@csrf_exempt
@admin_required
def admin_instructors(request):
    """
    List all instructors or create a new instructor.
    GET /api/admin/instructors/
    POST /api/admin/instructors/
    """
    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        queryset = Instructor.objects.all().order_by('-created_at')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(title__icontains=search) |
                Q(bio__icontains=search)
            )

        results = [serialize_instructor_summary(ins) for ins in queryset]
        return json_response({
            'count': len(results),
            'results': results,
        }, status=200)

    elif request.method == 'POST':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        name = data.get('name', '').strip()
        if not name:
            return error_response('Instructor name is required', status=400)

        instructor = Instructor.objects.create(
            name=name,
            title=data.get('title', '').strip(),
            bio=data.get('bio', '').strip(),
            avatar=data.get('avatar', '').strip() or None,
        )

        log_admin_action(request, 'Created instructor', 'Instructor', instructor.id, {'name': name})
        return json_response(serialize_instructor_detail(instructor), status=201)

    return error_response('Method not allowed', status=405)


@csrf_exempt
@admin_required
def admin_instructor_detail(request, id):
    """
    Get, update, or delete an instructor profile.
    GET /api/admin/instructors/<id>/
    PUT /api/admin/instructors/<id>/
    DELETE /api/admin/instructors/<id>/
    """
    instructor = Instructor.objects.filter(id=id).first()
    if not instructor:
        return error_response('Instructor not found', status=404)

    if request.method == 'GET':
        return json_response(serialize_instructor_detail(instructor), status=200)

    elif request.method == 'PUT':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        if 'name' in data:
            name = data.get('name', '').strip()
            if not name:
                return error_response('Instructor name cannot be empty', status=400)
            instructor.name = name

        if 'title' in data:
            instructor.title = data.get('title', '').strip()
        if 'bio' in data:
            instructor.bio = data.get('bio', '').strip()
        if 'avatar' in data:
            instructor.avatar = data.get('avatar', '').strip() or None

        instructor.save()
        log_admin_action(request, 'Updated instructor', 'Instructor', instructor.id, {'name': instructor.name})
        return json_response(serialize_instructor_detail(instructor), status=200)

    elif request.method == 'DELETE':
        name = instructor.name
        instructor.delete()
        log_admin_action(request, 'Deleted instructor', 'Instructor', id, {'name': name})
        return json_response({'message': f'Instructor "{name}" deleted successfully'}, status=200)

    return error_response('Method not allowed', status=405)
