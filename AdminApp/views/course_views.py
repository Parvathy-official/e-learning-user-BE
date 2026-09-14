from decimal import Decimal
from django.db.models import Q
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from userApp.models import Course, Instructor
from ..permissions import admin_required
from ..serializers import serialize_course_admin
from ..utils import parse_json_body, json_response, error_response, log_admin_action


def _generate_unique_slug(title, existing_course_id=None):
    base_slug = slugify(title) or 'course'
    slug = base_slug
    counter = 1
    qs = Course.objects.all()
    if existing_course_id:
        qs = qs.exclude(id=existing_course_id)
    while qs.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


@csrf_exempt
@admin_required
def admin_courses(request):
    """
    List all courses or create a new course.
    GET /api/admin/courses/
    POST /api/admin/courses/
    """
    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        category = request.GET.get('category', '').strip()
        is_published = request.GET.get('is_published', '').strip()
        is_featured = request.GET.get('is_featured', '').strip()
        is_bestseller = request.GET.get('is_bestseller', '').strip()
        instructor_id = request.GET.get('instructor_id', '').strip()
        sort = request.GET.get('sort', '').strip()

        queryset = Course.objects.all().select_related('instructor')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(category__icontains=search) |
                Q(slug__icontains=search) |
                Q(instructor__name__icontains=search)
            )

        if category and category.lower() != 'all':
            queryset = queryset.filter(category__iexact=category)

        if is_published in ('true', '1', 'True'):
            queryset = queryset.filter(is_published=True)
        elif is_published in ('false', '0', 'False'):
            queryset = queryset.filter(is_published=False)

        if is_featured in ('true', '1', 'True'):
            queryset = queryset.filter(is_featured=True)
        elif is_featured in ('false', '0', 'False'):
            queryset = queryset.filter(is_featured=False)

        if is_bestseller in ('true', '1', 'True'):
            queryset = queryset.filter(is_bestseller=True)
        elif is_bestseller in ('false', '0', 'False'):
            queryset = queryset.filter(is_bestseller=False)

        if instructor_id:
            queryset = queryset.filter(instructor_id=instructor_id)

        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'rating':
            queryset = queryset.order_by('-rating')
        elif sort == 'oldest':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')

        results = [serialize_course_admin(c) for c in queryset]
        return json_response({
            'count': len(results),
            'results': results,
        }, status=200)

    elif request.method == 'POST':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        title = data.get('title', '').strip()
        if not title:
            return error_response('Course title is required', status=400)

        price = data.get('price')
        if price is None:
            return error_response('Course selling price is required', status=400)

        try:
            price_val = Decimal(str(price))
        except Exception:
            return error_response('Invalid price format', status=400)

        original_price_val = None
        if data.get('original_price'):
            try:
                original_price_val = Decimal(str(data.get('original_price')))
            except Exception:
                original_price_val = None

        slug = data.get('slug', '').strip()
        if not slug:
            slug = _generate_unique_slug(title)
        else:
            slug = _generate_unique_slug(slug)

        instructor = None
        instructor_id = data.get('instructor_id')
        if instructor_id:
            instructor = Instructor.objects.filter(id=instructor_id).first()

        course = Course.objects.create(
            title=title,
            slug=slug,
            short_description=data.get('short_description', ''),
            description=data.get('description', ''),
            thumbnail=data.get('thumbnail') or None,
            instructor=instructor,
            category=data.get('category') or 'Performance Marketing',
            price=price_val,
            original_price=original_price_val,
            duration=data.get('duration', '18h 45m'),
            level=data.get('level', 'Intermediate to Advanced'),
            language=data.get('language', 'English'),
            is_published=bool(data.get('is_published', True)),
            is_featured=bool(data.get('is_featured', False)),
            is_bestseller=bool(data.get('is_bestseller', False)),
            rating=Decimal(str(data.get('rating', '4.95'))),
            total_ratings=int(data.get('total_ratings', 120)),
            total_students=int(data.get('total_students', 580)),
            learning_outcomes=data.get('learning_outcomes', []),
            requirements=data.get('requirements', []),
        )

        log_admin_action(request, 'Created course', 'Course', course.id, {'title': course.title})
        return json_response(serialize_course_admin(course), status=201)

    return error_response('Method not allowed', status=405)


@csrf_exempt
@admin_required
def admin_course_detail(request, id):
    """
    Get, update, or delete a single course by ID.
    GET /api/admin/courses/<id>/
    PUT /api/admin/courses/<id>/
    DELETE /api/admin/courses/<id>/
    """
    course = Course.objects.filter(id=id).select_related('instructor').first()
    if not course:
        return error_response('Course not found', status=404)

    if request.method == 'GET':
        return json_response(serialize_course_admin(course), status=200)

    elif request.method == 'PUT':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        if 'title' in data:
            title = data.get('title', '').strip()
            if not title:
                return error_response('Course title cannot be empty', status=400)
            course.title = title

        if 'slug' in data and data.get('slug'):
            course.slug = _generate_unique_slug(data['slug'], existing_course_id=course.id)

        if 'short_description' in data:
            course.short_description = data.get('short_description', '')
        if 'description' in data:
            course.description = data.get('description', '')
        if 'thumbnail' in data:
            course.thumbnail = data.get('thumbnail') or None

        if 'instructor_id' in data:
            instructor_id = data.get('instructor_id')
            course.instructor = Instructor.objects.filter(id=instructor_id).first() if instructor_id else None

        if 'category' in data:
            course.category = data.get('category', 'Performance Marketing')

        if 'price' in data:
            try:
                course.price = Decimal(str(data['price']))
            except Exception:
                return error_response('Invalid price format', status=400)

        if 'original_price' in data:
            orig = data.get('original_price')
            course.original_price = Decimal(str(orig)) if orig else None

        if 'duration' in data:
            course.duration = data.get('duration', course.duration)
        if 'level' in data:
            course.level = data.get('level', course.level)
        if 'language' in data:
            course.language = data.get('language', course.language)
        if 'is_published' in data:
            course.is_published = bool(data.get('is_published'))
        if 'is_featured' in data:
            course.is_featured = bool(data.get('is_featured'))
        if 'is_bestseller' in data:
            course.is_bestseller = bool(data.get('is_bestseller'))
        if 'rating' in data:
            try:
                course.rating = Decimal(str(data['rating']))
            except Exception:
                pass
        if 'total_ratings' in data:
            try:
                course.total_ratings = int(data['total_ratings'])
            except Exception:
                pass
        if 'total_students' in data:
            try:
                course.total_students = int(data['total_students'])
            except Exception:
                pass
        if 'learning_outcomes' in data:
            course.learning_outcomes = data.get('learning_outcomes', [])
        if 'requirements' in data:
            course.requirements = data.get('requirements', [])

        course.save()
        log_admin_action(request, 'Updated course', 'Course', course.id, {'title': course.title})
        return json_response(serialize_course_admin(course), status=200)

    elif request.method == 'DELETE':
        course_title = course.title
        course.delete()
        log_admin_action(request, 'Deleted course', 'Course', id, {'title': course_title})
        return json_response({'message': f'Course "{course_title}" deleted successfully'}, status=200)

    return error_response('Method not allowed', status=405)


@csrf_exempt
@admin_required
def admin_course_toggle_publish(request, id):
    """
    Toggle is_published flag for course.
    POST /api/admin/courses/<id>/toggle-publish/
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    course = Course.objects.filter(id=id).first()
    if not course:
        return error_response('Course not found', status=404)

    course.is_published = not course.is_published
    course.save(update_fields=['is_published', 'updated_at'])

    log_admin_action(request, f'Toggled published to {course.is_published}', 'Course', course.id)
    return json_response({'is_published': course.is_published}, status=200)


@csrf_exempt
@admin_required
def admin_course_toggle_featured(request, id):
    """
    Toggle is_featured flag for course.
    POST /api/admin/courses/<id>/toggle-featured/
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    course = Course.objects.filter(id=id).first()
    if not course:
        return error_response('Course not found', status=404)

    course.is_featured = not course.is_featured
    course.save(update_fields=['is_featured', 'updated_at'])

    log_admin_action(request, f'Toggled featured to {course.is_featured}', 'Course', course.id)
    return json_response({'is_featured': course.is_featured}, status=200)


@csrf_exempt
@admin_required
def admin_course_toggle_bestseller(request, id):
    """
    Toggle is_bestseller flag for course.
    POST /api/admin/courses/<id>/toggle-bestseller/
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    course = Course.objects.filter(id=id).first()
    if not course:
        return error_response('Course not found', status=404)

    course.is_bestseller = not course.is_bestseller
    course.save(update_fields=['is_bestseller', 'updated_at'])

    log_admin_action(request, f'Toggled bestseller to {course.is_bestseller}', 'Course', course.id)
    return json_response({'is_bestseller': course.is_bestseller}, status=200)
