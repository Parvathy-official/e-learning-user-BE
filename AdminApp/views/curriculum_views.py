from django.db.models import Max
from django.views.decorators.csrf import csrf_exempt

from userApp.models import Course, Module, Lesson
from ..permissions import admin_required
from ..serializers import serialize_module_admin, serialize_lesson_admin
from ..services import reorder_modules_service, reorder_lessons_service
from ..utils import parse_json_body, json_response, error_response, log_admin_action


@csrf_exempt
@admin_required
def admin_course_curriculum(request, course_id):
    """
    Get full module & lesson curriculum tree for a course.
    GET /api/admin/courses/<course_id>/curriculum/
    """
    if request.method != 'GET':
        return error_response('Method not allowed', status=405)

    course = Course.objects.filter(id=course_id).first()
    if not course:
        return error_response('Course not found', status=404)

    modules = course.modules.all().order_by('order').prefetch_related('lessons')
    return json_response({
        'course_id': course.id,
        'course_title': course.title,
        'modules': [serialize_module_admin(m) for m in modules],
    }, status=200)


@csrf_exempt
@admin_required
def admin_course_modules(request, course_id):
    """
    Create a new module for a given course.
    POST /api/admin/courses/<course_id>/modules/
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    course = Course.objects.filter(id=course_id).first()
    if not course:
        return error_response('Course not found', status=404)

    data = parse_json_body(request)
    if data is None:
        return error_response('Invalid JSON payload', status=400)

    title = data.get('title', '').strip()
    if not title:
        return error_response('Module title is required', status=400)

    max_order = Module.objects.filter(course=course).aggregate(Max('order'))['order__max'] or 0
    module = Module.objects.create(
        course=course,
        title=title,
        order=max_order + 1,
    )

    log_admin_action(request, 'Created module', 'Module', module.id, {'title': title, 'course_id': course.id})
    return json_response(serialize_module_admin(module), status=201)


@csrf_exempt
@admin_required
def admin_module_detail(request, module_id):
    """
    Update or delete a module.
    PUT /api/admin/modules/<module_id>/
    DELETE /api/admin/modules/<module_id>/
    """
    module = Module.objects.filter(id=module_id).first()
    if not module:
        return error_response('Module not found', status=404)

    if request.method == 'PUT':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        if 'title' in data:
            title = data.get('title', '').strip()
            if not title:
                return error_response('Module title cannot be empty', status=400)
            module.title = title

        if 'order' in data:
            try:
                module.order = int(data['order'])
            except Exception:
                pass

        module.save()
        log_admin_action(request, 'Updated module', 'Module', module.id, {'title': module.title})
        return json_response(serialize_module_admin(module), status=200)

    elif request.method == 'DELETE':
        module_title = module.title
        module.delete()
        log_admin_action(request, 'Deleted module', 'Module', module_id, {'title': module_title})
        return json_response({'message': f'Module "{module_title}" deleted successfully'}, status=200)

    return error_response('Method not allowed', status=405)


@csrf_exempt
@admin_required
def admin_modules_reorder(request, course_id):
    """
    Batch update order sequence of modules within a course.
    POST /api/admin/courses/<course_id>/modules/reorder/
    Body: { "orders": [{ "id": 1, "order": 1 }, { "id": 2, "order": 2 }] }
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    course = Course.objects.filter(id=course_id).first()
    if not course:
        return error_response('Course not found', status=404)

    data = parse_json_body(request)
    if data is None:
        return error_response('Invalid JSON payload', status=400)

    orders = data.get('orders', [])
    if not isinstance(orders, list):
        return error_response('Orders must be an array of objects', status=400)

    reorder_modules_service(course.id, orders)
    log_admin_action(request, 'Reordered modules', 'Course', course.id)
    return json_response({'message': 'Modules reordered successfully'}, status=200)


@csrf_exempt
@admin_required
def admin_module_lessons(request, module_id):
    """
    Create a new lesson within a module.
    POST /api/admin/modules/<module_id>/lessons/
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    module = Module.objects.filter(id=module_id).first()
    if not module:
        return error_response('Module not found', status=404)

    data = parse_json_body(request)
    if data is None:
        return error_response('Invalid JSON payload', status=400)

    title = data.get('title', '').strip()
    if not title:
        return error_response('Lesson title is required', status=400)

    max_order = Lesson.objects.filter(module=module).aggregate(Max('order'))['order__max'] or 0
    duration = data.get('duration', '15:00')
    duration_seconds = int(data.get('duration_seconds', 900))
    video_url = data.get('video_url', '').strip()
    is_preview = bool(data.get('is_preview', False))

    lesson = Lesson.objects.create(
        module=module,
        title=title,
        duration=duration,
        duration_seconds=duration_seconds,
        video_url=video_url or None,
        is_preview=is_preview,
        order=max_order + 1,
    )

    log_admin_action(request, 'Created lesson', 'Lesson', lesson.id, {'title': title, 'module_id': module.id})
    return json_response(serialize_lesson_admin(lesson), status=201)


@csrf_exempt
@admin_required
def admin_lesson_detail(request, lesson_id):
    """
    Update or delete a lesson.
    PUT /api/admin/lessons/<lesson_id>/
    DELETE /api/admin/lessons/<lesson_id>/
    """
    lesson = Lesson.objects.filter(id=lesson_id).first()
    if not lesson:
        return error_response('Lesson not found', status=404)

    if request.method == 'PUT':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        if 'title' in data:
            title = data.get('title', '').strip()
            if not title:
                return error_response('Lesson title cannot be empty', status=400)
            lesson.title = title

        if 'duration' in data:
            lesson.duration = data.get('duration', lesson.duration)
        if 'duration_seconds' in data:
            try:
                lesson.duration_seconds = int(data['duration_seconds'])
            except Exception:
                pass
        if 'video_url' in data:
            lesson.video_url = data.get('video_url') or None
        if 'is_preview' in data:
            lesson.is_preview = bool(data.get('is_preview'))
        if 'order' in data:
            try:
                lesson.order = int(data['order'])
            except Exception:
                pass

        lesson.save()
        log_admin_action(request, 'Updated lesson', 'Lesson', lesson.id, {'title': lesson.title})
        return json_response(serialize_lesson_admin(lesson), status=200)

    elif request.method == 'DELETE':
        lesson_title = lesson.title
        lesson.delete()
        log_admin_action(request, 'Deleted lesson', 'Lesson', lesson_id, {'title': lesson_title})
        return json_response({'message': f'Lesson "{lesson_title}" deleted successfully'}, status=200)

    return error_response('Method not allowed', status=405)


@csrf_exempt
@admin_required
def admin_lessons_reorder(request, module_id):
    """
    Batch update order sequence of lessons within a module.
    POST /api/admin/modules/<module_id>/lessons/reorder/
    Body: { "orders": [{ "id": 1, "order": 1 }, { "id": 2, "order": 2 }] }
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    module = Module.objects.filter(id=module_id).first()
    if not module:
        return error_response('Module not found', status=404)

    data = parse_json_body(request)
    if data is None:
        return error_response('Invalid JSON payload', status=400)

    orders = data.get('orders', [])
    if not isinstance(orders, list):
        return error_response('Orders must be an array of objects', status=400)

    reorder_lessons_service(module.id, orders)
    log_admin_action(request, 'Reordered lessons', 'Module', module.id)
    return json_response({'message': 'Lessons reordered successfully'}, status=200)
