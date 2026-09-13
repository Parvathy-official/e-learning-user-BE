import hmac
import hashlib
import time
from django.conf import settings
import razorpay


def get_razorpay_client():
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    if key_id and key_secret:
        try:
            return razorpay.Client(auth=(key_id, key_secret))
        except Exception:
            return None
    return None


def create_razorpay_order(amount_paise, currency='INR', receipt=None):
    """
    Create an order using Razorpay API, or fallback to test order ID for development.
    """
    client = get_razorpay_client()
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_mock')

    if client and not key_id.startswith('rzp_test_mock'):
        try:
            order_data = {
                'amount': amount_paise,
                'currency': currency,
                'receipt': receipt or f"rcpt_{int(time.time())}",
                'payment_capture': 1,
            }
            order = client.order.create(data=order_data)
            return {
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key': key_id,
            }
        except Exception:
            pass

    # Development fallback
    order_id = f"order_rzp_{int(time.time() * 1000)}"
    return {
        'order_id': order_id,
        'amount': amount_paise,
        'currency': currency,
        'key': key_id,
    }


def verify_razorpay_signature(order_id, payment_id, signature):
    """
    Cryptographically verify the Razorpay HMAC-SHA256 signature.
    """
    if not order_id or not payment_id or not signature:
        return False

    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    
    # Allow mock signatures in local development mode
    if getattr(settings, 'DEBUG', True) and (signature == 'mock_signature' or signature.startswith('mock_')):
        return True

    # 1. Try Razorpay SDK verification
    client = get_razorpay_client()
    if client:
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            })
            return True
        except Exception:
            pass

    # 2. Native HMAC-SHA256 verification
    try:
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        generated_signature = hmac.new(
            key_secret.encode('utf-8'),
            msg,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(generated_signature, signature)
    except Exception:
        return False
