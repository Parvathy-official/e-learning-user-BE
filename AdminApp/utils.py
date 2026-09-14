import json
from datetime import datetime
from decimal import Decimal
from django.http import JsonResponse
from django.utils import timezone


def parse_json_body(request):
    """
    Parse JSON payload from request body safely.
    Returns python dict or None if invalid.
    """
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode('utf-8'))
    except Exception:
        return None


def json_response(data, status=200):
    """
    Standardized JSON response helper.
    """
    return JsonResponse(data, status=status, safe=False)


def error_response(message, status=400, details=None):
    """
    Standardized JSON error response helper matching frontend ApiError expectations.
    """
    payload = {'error': message}
    if details is not None:
        payload['details'] = details
    return JsonResponse(payload, status=status)


def format_datetime(dt):
    """
    Format datetime into standard ISO/readable string.
    """
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    return dt.strftime('%Y-%m-%d %H:%M')


def format_date(dt):
    """
    Format date into standard YYYY-MM-DD string.
    """
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    return dt.strftime('%Y-%m-%d')


def log_admin_action(request, action, target_model='', target_id='', details=None):
    """
    Helper to record admin actions in the audit log if desired.
    """
    try:
        from .models import AdminActivityLog
        admin_user = getattr(request, 'admin_user', None)
        ip = request.META.get('REMOTE_ADDR')
        AdminActivityLog.objects.create(
            admin_user=admin_user,
            action=action,
            target_model=str(target_model),
            target_id=str(target_id),
            details=details or {},
            ip_address=ip
        )
    except Exception:
        pass  # Non-blocking
