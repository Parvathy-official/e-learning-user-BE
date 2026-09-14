from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from userApp.models import Payment
from ..permissions import admin_required
from ..serializers import serialize_payment_admin
from ..utils import json_response, error_response


@csrf_exempt
@admin_required
def admin_payments(request):
    """
    List payment transactions with filters.
    GET /api/admin/payments/
    """
    if request.method != 'GET':
        return error_response('Method not allowed', status=405)

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip().lower()
    course_id = request.GET.get('course_id', '').strip()
    user_id = request.GET.get('user_id', '').strip()

    queryset = (
        Payment.objects
        .select_related('user', 'course')
        .order_by('-created_at')
    )

    if search:
        queryset = queryset.filter(
            Q(user__name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(razorpay_order_id__icontains=search) |
            Q(razorpay_payment_id__icontains=search) |
            Q(course__title__icontains=search)
        )

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    if course_id:
        queryset = queryset.filter(course_id=course_id)

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    results = [serialize_payment_admin(p) for p in queryset]
    return json_response({
        'count': len(results),
        'results': results,
    }, status=200)


@csrf_exempt
@admin_required
def admin_payment_detail(request, id):
    """
    Get detailed breakdown of a single payment order/transaction.
    GET /api/admin/payments/<id>/
    """
    if request.method != 'GET':
        return error_response('Method not allowed', status=405)

    payment = (
        Payment.objects
        .filter(id=id)
        .select_related('user', 'course')
        .first()
    )
    if not payment:
        return error_response('Payment transaction not found', status=404)

    return json_response(serialize_payment_admin(payment), status=200)
