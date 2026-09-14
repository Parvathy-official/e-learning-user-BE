from django.views.decorators.csrf import csrf_exempt
from ..permissions import admin_required
from ..services import get_dashboard_statistics
from ..utils import json_response, error_response


@csrf_exempt
@admin_required
def admin_dashboard_stats(request):
    """
    Get consolidated metrics, performance records, and recent transactions for admin dashboard.
    GET /api/admin/dashboard/stats/
    """
    if request.method != 'GET':
        return error_response('Method not allowed', status=405)

    try:
        stats_data = get_dashboard_statistics()
        return json_response(stats_data, status=200)
    except Exception as e:
        return error_response(f'Failed to compute dashboard metrics: {str(e)}', status=500)
