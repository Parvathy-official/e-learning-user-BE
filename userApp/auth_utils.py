import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings
from .models import User


def generate_tokens(user):
    """
    Generate standard JWT access and refresh tokens for a user.
    """
    now = datetime.now(timezone.utc)
    access_exp = now + timedelta(hours=getattr(settings, 'JWT_ACCESS_EXPIRATION_HOURS', 24))
    refresh_exp = now + timedelta(days=getattr(settings, 'JWT_REFRESH_EXPIRATION_DAYS', 7))

    access_payload = {
        'user_id': user.id,
        'email': user.email,
        'name': user.name,
        'token_type': 'access',
        'iat': now,
        'exp': access_exp,
    }

    refresh_payload = {
        'user_id': user.id,
        'token_type': 'refresh',
        'iat': now,
        'exp': refresh_exp,
    }

    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    access_token = jwt.encode(access_payload, secret, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, secret, algorithm='HS256')

    return {
        'access': access_token,
        'refresh': refresh_token,
    }


def get_authenticated_user(request):
    """
    Helper function to extract and validate Bearer token from request.
    Returns User instance if valid, or None if unauthenticated/invalid.
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


def decode_refresh_token(refresh_token):
    """
    Decode and validate a refresh token.
    Returns user_id if valid, or None.
    """
    if not refresh_token:
        return None

    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    try:
        payload = jwt.decode(refresh_token, secret, algorithms=['HS256'])
        if payload.get('token_type') != 'refresh':
            return None
        return payload.get('user_id')
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None
