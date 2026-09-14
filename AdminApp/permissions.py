import jwt
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from userApp.models import User
from .utils import error_response


def get_admin_user_from_request(request):
    """
    Extract and validate Bearer JWT token from request.
    Verifies that the user exists, is active, and is staff/superuser.
    Returns User instance or None.
    """
    auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None

    token = auth_header.split(' ')[1].strip()
    if not token:
        return None

    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        if payload.get('token_type') != 'access':
            return None

        user_id = payload.get('user_id')
        if not user_id:
            return None

        user = User.objects.filter(id=user_id, is_active=True).first()
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


def admin_required(view_func):
    """
    Decorator for views that checks if the request is from an authenticated admin or staff member.
    Attaches `request.admin_user` on success.
    Returns 401 if unauthenticated, 403 if user lacks admin privileges.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = get_admin_user_from_request(request)
        if not user:
            return error_response('Authentication required. Please log in.', status=401)

        if not (user.is_staff or user.is_superuser):
            return error_response('Access Denied: Administrator privileges required.', status=403)

        request.admin_user = user
        return view_func(request, *args, **kwargs)

    return _wrapped_view
