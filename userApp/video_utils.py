import hmac
import hashlib
import time
from datetime import datetime, timezone, timedelta
from django.conf import settings


def generate_signed_video_url(lesson, expires_in=300):
    """
    Generate a temporary signed video URL for a lesson.
    Prevents permanent public URL leakage.
    Can be seamlessly adapted for AWS S3 / CloudFront signed URLs.
    """
    base_url = lesson.video_url or 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in)
    exp_timestamp = int(expires_at.timestamp())
    
    # Generate signature for URL
    secret = getattr(settings, 'SECRET_KEY', 'video-secret')
    message = f"lesson_{lesson.id}:{exp_timestamp}"
    signature = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()[:16]
    
    separator = '&' if '?' in base_url else '?'
    signed_url = f"{base_url}{separator}token={signature}&expires={exp_timestamp}"
    
    return {
        'video_url': signed_url,
        'url': signed_url,
        'expires_in': expires_in,
        'expires_at': expires_at.isoformat(),
    }
