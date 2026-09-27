import os
import hashlib
import secrets
import threading
import logging
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import EmailOTP

logger = logging.getLogger(__name__)


def _send_otp_email_worker(subject: str, message: str, from_email: str, recipient_list: list[str]):
    # 1. Resend HTTPS REST API (Port 443 - Recommended for Render)
    resend_api_key = os.getenv('RESEND_API_KEY') or getattr(settings, 'RESEND_API_KEY', None)
    if resend_api_key:
        try:
            resend_from = os.getenv('RESEND_FROM_EMAIL') or getattr(settings, 'RESEND_FROM_EMAIL', None) or "LearnFlow Academy <onboarding@resend.dev>"
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": resend_from,
                    "to": recipient_list,
                    "subject": subject,
                    "text": message,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Successfully sent OTP via Resend API to {recipient_list}")
                return
            else:
                logger.error(f"Resend API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Resend HTTPS dispatch failed: {e}")

    # 2. Brevo HTTPS REST API (Port 443)
    brevo_api_key = os.getenv('BREVO_API_KEY') or getattr(settings, 'BREVO_API_KEY', None)
    if brevo_api_key:
        try:
            sender_email = os.getenv('EMAIL_HOST_USER') or "noreply@learnflow.com"
            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "sender": {"name": "LearnFlow Academy", "email": sender_email},
                    "to": [{"email": r} for r in recipient_list],
                    "subject": subject,
                    "textContent": message,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Successfully sent OTP via Brevo API to {recipient_list}")
                return
            else:
                logger.error(f"Brevo API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Brevo HTTPS dispatch failed: {e}")

    # 3. Fallback to standard Django send_mail (SMTP/Console)
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        logger.info(f"Successfully sent OTP via standard send_mail to {recipient_list}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {recipient_list}: {e}")


def generate_secure_otp() -> str:
    """Generates a cryptographically random 6-digit numeric OTP."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def compute_otp_hashes(email: str, otp: str) -> list[str]:
    """
    Computes possible valid hashes for the given email and OTP to be resilient across
    salt configurations (settings.SECRET_KEY, fixed salt, or default fallback).
    """
    email_clean = email.strip().lower()
    otp_clean = str(otp).strip().replace(' ', '').replace('-', '')

    salts = [
        getattr(settings, 'SECRET_KEY', 'learnflow-secure-otp-salt-v1'),
        'django-insecure-default-key-change-in-prod',
        'learnflow-secure-otp-salt-v1',
        'otp-salt-key',
        '',
    ]

    hashes = set()
    for s in salts:
        hashes.add(hashlib.sha256(f"{email_clean}:{otp_clean}:{s}".encode('utf-8')).hexdigest())
        hashes.add(hashlib.sha256(f"{email_clean}:{otp_clean}".encode('utf-8')).hexdigest())
    return list(hashes)


def hash_otp(email: str, otp: str) -> str:
    """Hashes the OTP combined with normalized email and SECRET_KEY."""
    salt = getattr(settings, 'SECRET_KEY', 'learnflow-secure-otp-salt-v1')
    return hashlib.sha256(f"{email.strip().lower()}:{str(otp).strip()}:{salt}".encode('utf-8')).hexdigest()


def create_and_send_otp(email: str) -> tuple[bool, str]:
    """
    Rate-limits, generates, stores hashed OTP, and sends email to user in background.
    Returns (success: bool, message: str).
    """
    email = email.strip().lower()
    now = timezone.now()

    # Rate limiting: max 1 OTP request every 45 seconds
    recent_otp = EmailOTP.objects.filter(
        email=email,
        created_at__gte=now - timedelta(seconds=45)
    ).first()
    if recent_otp:
        return False, "A verification code was already sent recently. Please wait 45 seconds before requesting a new one."

    raw_otp = generate_secure_otp()
    hashed = hash_otp(email, raw_otp)
    expires_at = now + timedelta(minutes=15)

    EmailOTP.objects.create(
        email=email,
        otp_hash=hashed,
        expires_at=expires_at,
        attempts=0,
        is_used=False
    )

    # Unique subject with code prevents Gmail from collapsing new messages into old threads
    subject = f"Your LearnFlow Access Code is {raw_otp}"
    message = (
        f"Hello,\n\n"
        f"Your one-time verification code is: {raw_otp}\n\n"
        f"This code will expire in 15 minutes. Enter this code to access your purchased courses.\n\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"— LearnFlow Academy"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'LearnFlow Academy <noreply@learnflow.com>')

    # Dispatch email asynchronously in background thread so API response is instant (<100ms)
    email_thread = threading.Thread(
        target=_send_otp_email_worker,
        args=(subject, message, from_email, [email]),
        daemon=True
    )
    email_thread.start()

    return True, "Verification code sent to your email."


def verify_otp_code(email: str, otp: str) -> tuple[bool, str]:
    """
    Validates the OTP code against stored hashes of any unexpired, unused OTP record for this email.
    Enforces expiration and attempt limits.
    Returns (success: bool, message: str).
    """
    email = email.strip().lower()
    otp = str(otp).strip().replace(' ', '').replace('-', '')
    now = timezone.now()

    if not otp:
        return False, "Verification code is required."

    active_records = list(
        EmailOTP.objects.filter(
            email=email,
            is_used=False,
            expires_at__gt=now,
            attempts__lt=5
        ).order_by('-created_at')
    )

    if not active_records:
        logger.warning(f"No active unused OTP found for {email} (expired or already used).")
        return False, "Verification code has expired or is invalid. Please request a new code."

    valid_hashes = set(compute_otp_hashes(email, otp))

    matched_record = None
    for rec in active_records:
        if rec.otp_hash in valid_hashes:
            matched_record = rec
            break

    if not matched_record:
        # Increment attempt counter on the latest active record
        latest_rec = active_records[0]
        latest_rec.attempts += 1
        latest_rec.save(update_fields=['attempts'])
        remaining = max(0, 5 - latest_rec.attempts)

        if remaining == 0:
            latest_rec.is_used = True
            latest_rec.save(update_fields=['is_used'])
            logger.warning(f"OTP for {email} exceeded max 5 attempts. Invalidated.")
            return False, "Too many failed attempts. This code is now invalid. Please request a new code."

        logger.warning(f"Invalid OTP entered for {email}. {remaining} attempts remaining.")
        return False, f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."

    # Mark ALL active OTPs for this email as used so none can be reused
    EmailOTP.objects.filter(email=email, is_used=False).update(is_used=True)
    logger.info(f"OTP verified successfully for {email}.")
    return True, "Code verified successfully."
