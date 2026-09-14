from django.views.decorators.csrf import csrf_exempt
from userApp.models import User
from userApp.auth_utils import generate_tokens, decode_refresh_token
from ..permissions import admin_required
from ..serializers import serialize_admin_profile
from ..utils import parse_json_body, json_response, error_response


@csrf_exempt
def admin_login(request):
    """
    Authenticate an administrator or staff member.
    POST /api/admin/auth/login/ or /api/auth/login/
    Body: { "email": "...", "password": "..." }
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    data = parse_json_body(request)
    if data is None:
        return error_response('Invalid JSON body', status=400)

    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not email or not password:
        return error_response('Email and password are required', status=400)

    user = User.objects.filter(email__iexact=email).first()
    if not user or not user.check_password(password):
        return error_response('Invalid email or password', status=401)

    if not user.is_active:
        return error_response('Account is deactivated. Please contact support.', status=403)

    if not (user.is_staff or user.is_superuser):
        return error_response('Access Denied: Administrator privileges required.', status=403)

    tokens = generate_tokens(user)
    return json_response({
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'avatar': user.avatar,
            'bio': user.bio,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'joined': user.date_joined.strftime('%Y-%m-%d') if user.date_joined else None,
        },
        'access': tokens['access'],
        'refresh': tokens['refresh'],
    }, status=200)


@csrf_exempt
def admin_logout(request):
    """
    Admin logout endpoint.
    POST /api/admin/auth/logout/
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)
    return json_response({'message': 'Logged out successfully'}, status=200)


@csrf_exempt
@admin_required
def admin_me(request):
    """
    Get current logged in admin details.
    GET /api/admin/auth/me/
    """
    if request.method != 'GET':
        return error_response('Method not allowed', status=405)
    return json_response(serialize_admin_profile(request.admin_user), status=200)


@csrf_exempt
def admin_token_refresh(request):
    """
    Refresh JWT access token for admin session.
    POST /api/admin/auth/token/refresh/
    Body: { "refresh": "..." }
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    data = parse_json_body(request)
    if data is None or not data.get('refresh'):
        return error_response('Refresh token is required', status=400)

    user_id = decode_refresh_token(data.get('refresh'))
    if not user_id:
        return error_response('Invalid or expired refresh token', status=401)

    user = User.objects.filter(id=user_id, is_active=True).first()
    if not user or not (user.is_staff or user.is_superuser):
        return error_response('User not authorized or inactive', status=403)

    tokens = generate_tokens(user)
    return json_response({
        'access': tokens['access'],
        'refresh': tokens['refresh'],
    }, status=200)
