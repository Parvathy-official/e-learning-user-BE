from django.views.decorators.csrf import csrf_exempt

from ..permissions import admin_required
from ..serializers import serialize_admin_profile
from ..utils import parse_json_body, json_response, error_response, log_admin_action


@csrf_exempt
@admin_required
def admin_profile(request):
    """
    Get or update the current admin's profile.
    GET /api/admin/profile/
    PUT /api/admin/profile/
    """
    user = request.admin_user

    if request.method == 'GET':
        return json_response(serialize_admin_profile(user), status=200)

    elif request.method == 'PUT':
        data = parse_json_body(request)
        if data is None:
            return error_response('Invalid JSON payload', status=400)

        name = data.get('name', '').strip()
        if not name:
            return error_response('Name is required', status=400)

        user.name = name
        user.avatar = data.get('avatar') or None
        user.bio = data.get('bio', user.bio)
        user.save()

        log_admin_action(request, 'Updated admin profile', 'User', user.id)
        return json_response(serialize_admin_profile(user), status=200)

    return error_response('Method not allowed', status=405)


@csrf_exempt
@admin_required
def admin_change_password(request):
    """
    Change password for the logged-in administrator.
    POST /api/admin/change-password/
    Body: { "current_password": "...", "new_password": "..." }
    """
    if request.method != 'POST':
        return error_response('Method not allowed', status=405)

    data = parse_json_body(request)
    if data is None:
        return error_response('Invalid JSON payload', status=400)

    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()

    if not current_password or not new_password:
        return error_response('Current password and new password are required', status=400)

    user = request.admin_user
    if not user.check_password(current_password):
        return error_response('Current password does not match', status=400)

    if len(new_password) < 6:
        return error_response('New password must be at least 6 characters long', status=400)

    user.set_password(new_password)
    user.save()

    log_admin_action(request, 'Changed password', 'User', user.id)
    return json_response({'message': 'Password changed successfully.'}, status=200)
